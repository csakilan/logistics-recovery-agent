import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from pydantic import ValidationError

from logistics_recovery.domain import DomainError, Operator, Snapshot


def test_assignment_requires_approval(service, proposal, operator, repo):
    with pytest.raises(DomainError, match="approval_required"):
        service.commit(proposal.id, operator)
    assert repo.assignment("i1") is None


def test_valid_approved_assignment(service, approved, operator, repo):
    result = service.commit(approved.proposal_id, operator)
    assert result.status == "assigned"
    assert result.courier_id == "c1"
    assert repo.snapshot("i1").couriers[0].free_capacity == 0
    assert repo.stats("i1")["commit_events"] == 1


def test_replay_does_not_reserve_twice(service, approved, operator, repo):
    first = service.commit(approved.proposal_id, operator)
    assert service.commit(approved.proposal_id, operator).id == first.id
    assert repo.stats("i1")["assignments"] == 1
    assert repo.stats("i1")["commit_events"] == 1
    assert repo.snapshot("i1").couriers[0].free_capacity == 0


def test_wrong_operator_cannot_use_approval(service, approved, repo):
    with pytest.raises(DomainError, match="operator_mismatch"):
        service.commit(approved.proposal_id, Operator(id="someone_else"))
    assert repo.assignment("i1") is None


def test_proposal_payload_immutable(service, proposal, operator):
    with pytest.raises(ValidationError): proposal.candidate.quote_id = "q2"
    service.approve(proposal.id, 1, operator)
    assert service.commit(proposal.id, operator).courier_id == "c1"


def test_approval_wrong_incident_version(service, proposal, operator, repo):
    with pytest.raises(DomainError, match="stale_proposal"):
        service.approve(proposal.id, 99, operator)
    assert repo.assignment("i1") is None


def test_rejected_proposal_cannot_commit(service, proposal, operator):
    service.reject(proposal.id, operator)
    with pytest.raises(DomainError, match="proposal_rejected"):
        service.approve(proposal.id, 1, operator)


def test_changed_courier_requires_fresh_proposal(service, approved, operator, repo):
    with repo.transaction() as connection:
        row = connection.execute("SELECT payload FROM couriers WHERE id = ?", ("c1",)).fetchone()
        courier = json.loads(row[0]); courier.update(available=False, version=2)
        connection.execute("UPDATE couriers SET payload = ? WHERE id = ?", (json.dumps(courier), "c1"))
    with pytest.raises(DomainError, match="stale_proposal"):
        service.commit(approved.proposal_id, operator)
    assert repo.assignment("i1") is None


def test_rollback_leaves_no_partial_assignment(service, approved, operator, repo, monkeypatch):
    original = repo.transaction
    witnessed = []

    class FailingConnection:
        def __init__(self, connection): self.connection = connection
        def execute(self, sql, parameters=()):
            result = self.connection.execute(sql, parameters)
            if sql.startswith("UPDATE couriers"):
                witnessed.append(True)
                raise RuntimeError("injected after capacity update")
            return result
        def __getattr__(self, name): return getattr(self.connection, name)

    @contextmanager
    def failing_transaction():
        with original() as connection:
            yield FailingConnection(connection)

    monkeypatch.setattr(repo, "transaction", failing_transaction)
    with pytest.raises(RuntimeError, match="injected after capacity update"):
        service.commit(approved.proposal_id, operator)
    monkeypatch.setattr(repo, "transaction", original)
    assert witnessed
    assert repo.assignment("i1") is None
    assert repo.snapshot("i1").couriers[0].free_capacity == 3
    assert repo.stats("i1")["commit_events"] == 0
    assert service.commit(approved.proposal_id, operator).status == "assigned"


def test_concurrent_replay_creates_one_assignment(service, approved, operator, repo):
    barrier = threading.Barrier(2, timeout=5)
    def commit():
        barrier.wait()
        return service.commit(approved.proposal_id, operator)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: commit(), range(2)))
    assert results[0].id == results[1].id
    assert repo.stats("i1")["assignments"] == 1
    assert repo.snapshot("i1").couriers[0].free_capacity == 0


def test_concurrent_incidents_cannot_overbook(service, approved, operator, repo, snapshot_data):
    from logistics_recovery.assignments import AssignmentService
    from logistics_recovery.baseline import choose_baseline
    from logistics_recovery.repository import Repository
    other = copy.deepcopy(snapshot_data)
    other["incident_id"] = "i2"; other["job"]["id"] = "j2"
    other["events"][0].update(id="e2", job_id="j2")
    other["quotes"] = [dict(other["quotes"][0], id="q3", job_id="j2")]
    repo.seed(Snapshot.model_validate(other))
    second_service = AssignmentService(Repository(repo.path))
    candidate = choose_baseline(repo.snapshot("i2"))
    second = second_service.propose("i2", candidate)
    second_service.approve(second.id, 1, operator)
    barrier = threading.Barrier(2, timeout=5)
    def commit(pair):
        instance, proposal_id = pair
        barrier.wait()
        try: return instance.commit(proposal_id, operator).status
        except DomainError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(commit, [(service, approved.proposal_id), (second_service, second.id)]))
    assert results.count("assigned") == 1
    assert repo.stats("i1")["assignments"] + repo.stats("i2")["assignments"] == 1
    assert repo.snapshot("i1").couriers[0].free_capacity == 0
