import pytest


@pytest.fixture
def snapshot_data():
    return {
        "incident_id": "i1", "incident_version": 1, "now_min": 0,
        "job": {"id": "j1", "parcel_count": 3, "deadline_min": 60, "custody": "depot", "version": 1},
        "couriers": [
            {"id": "c1", "free_capacity": 3, "available": True, "version": 1},
            {"id": "c2", "free_capacity": 3, "available": True, "version": 1},
        ],
        "quotes": [
            {"id": "q1", "job_id": "j1", "courier_id": "c1", "cost_cents": 1200, "travel_min": 30, "expires_at_min": 10, "version": 1},
            {"id": "q2", "job_id": "j1", "courier_id": "c2", "cost_cents": 1400, "travel_min": 30, "expires_at_min": 10, "version": 1},
        ],
        "policy": {"id": "p1", "max_cost_cents": 1500, "version": 1},
        "events": [{"id": "e1", "job_id": "j1", "kind": "cancellation", "at_min": 0, "custody": "depot", "version": 1, "note": "Driver cancelled before pickup."}],
    }


@pytest.fixture
def feasible_snapshot(snapshot_data):
    from logistics_recovery.domain import Snapshot
    return Snapshot.model_validate(snapshot_data)


@pytest.fixture
def valid_candidate():
    from logistics_recovery.domain import Candidate
    return Candidate(quote_id="q1", evidence_ids=("job:j1@1", "courier:c1@1", "quote:q1@1", "policy:p1@1", "event:e1@1"), summary="Available courier within spending and delivery limits.")


@pytest.fixture
def repo(tmp_path, feasible_snapshot):
    from logistics_recovery.repository import Repository
    repository = Repository(tmp_path / "business.sqlite")
    repository.seed(feasible_snapshot)
    return repository


@pytest.fixture
def service(repo):
    from logistics_recovery.assignments import AssignmentService
    return AssignmentService(repo)


@pytest.fixture
def operator():
    from logistics_recovery.domain import Operator
    return Operator(id="dispatcher")


@pytest.fixture
def proposal(service, valid_candidate):
    return service.propose("i1", valid_candidate)


@pytest.fixture
def approved(service, proposal, operator):
    return service.approve(proposal.id, 1, operator)


@pytest.fixture
def settings(tmp_path):
    from logistics_recovery.config import Settings
    return Settings(data_dir=tmp_path, origin="http://127.0.0.1:8000", dispatcher_username="dispatcher", dispatcher_password="test-password")


@pytest.fixture
def auth(): return ("dispatcher", "test-password")


@pytest.fixture
def origin(): return {"Origin": "http://127.0.0.1:8000"}


@pytest.fixture
def client(settings, service):
    from fastapi.testclient import TestClient
    from logistics_recovery.web import create_app
    with TestClient(create_app(settings, service), base_url=settings.origin) as instance:
        yield instance


@pytest.fixture
def workflow_factory(repo, service, tmp_path, valid_candidate):
    from logistics_recovery.workflow import Workflow
    from logistics_recovery.model import ModelTurn, ReplayModel, ToolCall
    def reads():
        return ModelTurn(kind="tools", tool_calls=tuple(ToolCall(id=f"call-{name}", name=name, arguments={}) for name in ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")))
    instances = []
    def factory(model=None):
        model = model or ReplayModel({"i1": (reads(), ModelTurn(kind="proposal", candidate=valid_candidate))})
        instance = Workflow(repo, service, model, tmp_path / "graph.sqlite")
        instances.append(instance)
        return instance
    yield factory
    for instance in instances: instance.close()


