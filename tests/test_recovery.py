import copy

import pytest

from logistics_recovery.domain import Candidate, DomainError, Operator, Snapshot
from logistics_recovery.model import ModelTurn, ReplayModel, ToolCall


def reads():
    return ModelTurn(kind="tools", tool_calls=tuple(ToolCall(id=f"call-{name}", name=name, arguments={}) for name in ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")))


def test_stale_approval_cannot_book(service, approved, repo, operator):
    repo.change_courier("c1", available=False)
    with pytest.raises(DomainError, match="stale_proposal"):
        service.commit(approved.proposal_id, operator)
    assert repo.assignment("i1") is None


def test_clock_cannot_move_backward(repo):
    repo.advance_clock("i1", 10)
    with pytest.raises(DomainError, match="invalid_clock"):
        repo.advance_clock("i1", 9)
    assert repo.snapshot("i1").now_min == 10


def test_quote_expiry_after_approval_blocks_commit(service, approved, repo, operator):
    repo.advance_clock("i1", 10)
    with pytest.raises(DomainError, match="stale_proposal"):
        service.commit(approved.proposal_id, operator)
    assert repo.assignment("i1") is None


def test_lost_response_recovers_once(workflow_factory, service, repo, operator, monkeypatch):
    workflow = workflow_factory(); paused = workflow.start("i1")
    service.approve(paused.proposal.id, 1, operator)
    original = service.commit; witnessed = []
    def lost_response(proposal_id, actor):
        result = original(proposal_id, actor)
        witnessed.append(result.id)
        raise ConnectionError("injected lost response after commit")
    monkeypatch.setattr(service, "commit", lost_response)
    with pytest.raises(ConnectionError, match="injected lost response"):
        workflow.resume("i1", paused.proposal.id)
    result = workflow_factory().recover("i1")
    assert result.status == "assigned"
    assert result.assignment.id == witnessed[0]
    assert len(witnessed) == 1
    assert repo.stats("i1")["assignments"] == 1
    assert repo.stats("i1")["commit_events"] == 1
    assert repo.snapshot("i1").couriers[0].free_capacity == 0


def test_stale_state_replans_and_requires_new_approval(workflow_factory, valid_candidate, service, repo, operator):
    other = Candidate(quote_id="q2", evidence_ids=("job:j1@1", "courier:c2@1", "quote:q2@1", "policy:p1@1", "event:e1@1"), summary="Alternative after availability changed.")
    model = ReplayModel({"i1": (reads(), ModelTurn(kind="proposal", candidate=valid_candidate), reads(), ModelTurn(kind="proposal", candidate=other))})
    workflow = workflow_factory(model); first = workflow.start("i1")
    service.approve(first.proposal.id, 1, operator)
    repo.change_courier("c1", available=False)
    second = workflow.resume("i1", first.proposal.id)
    assert second.status == "awaiting_approval"
    assert second.proposal.id != first.proposal.id
    assert repo.assignment("i1") is None
    with pytest.raises(DomainError, match="approval_required"):
        workflow.resume("i1", second.proposal.id)
    service.approve(second.proposal.id, second.proposal.incident_version, operator)
    assert workflow.resume("i1", second.proposal.id).assignment.courier_id == "c2"


def test_pickup_and_delivery_have_accurate_custody(service, approved, repo, operator):
    service.commit(approved.proposal_id, operator)
    assert service.record_event("i1", "pickup-1", "pickup", operator).status == "picked_up"
    assert repo.snapshot("i1").job.custody == "in_transit"
    assert service.record_event("i1", "delivery-1", "delivery", operator).status == "delivered"
    assert repo.snapshot("i1").job.custody == "delivered"
    assert repo.snapshot("i1").couriers[0].free_capacity == 3


def test_duplicate_delivery_does_not_release_capacity_twice(service, approved, repo, operator):
    service.commit(approved.proposal_id, operator)
    service.record_event("i1", "pickup-1", "pickup", operator)
    service.record_event("i1", "delivery-1", "delivery", operator)
    service.record_event("i1", "delivery-1", "delivery", operator)
    assert repo.snapshot("i1").couriers[0].free_capacity == 3
    assert len([item for item in repo.history("i1") if item["kind"] == "simulated_delivery"]) == 1


def test_delivery_before_pickup_rejected(service, approved, repo, operator):
    service.commit(approved.proposal_id, operator)
    with pytest.raises(DomainError, match="invalid_transition"):
        service.record_event("i1", "delivery-1", "delivery", operator)
    assert repo.assignment("i1").status == "assigned"
    assert repo.snapshot("i1").couriers[0].free_capacity == 0


def test_reused_event_id_for_other_kind_rejected(service, approved, operator):
    service.commit(approved.proposal_id, operator)
    service.record_event("i1", "event-1", "pickup", operator)
    with pytest.raises(DomainError, match="event_conflict"):
        service.record_event("i1", "event-1", "delivery", operator)


def test_event_requires_approved_operator(service, approved, repo, operator):
    service.commit(approved.proposal_id, operator)
    with pytest.raises(DomainError, match="operator_mismatch"):
        service.record_event("i1", "pickup-1", "pickup", Operator(id="other"))
    assert repo.assignment("i1").status == "assigned"


def test_contradictory_same_time_custody_not_resolved_by_id(snapshot_data, valid_candidate):
    from logistics_recovery.policy import validate_candidate
    snapshot_data["events"].append({"id": "e0", "job_id": "j1", "kind": "pickup", "at_min": 0, "custody": "in_transit", "version": 1, "note": "Conflicting custody record."})
    candidate = valid_candidate.model_copy(update={"evidence_ids": (*valid_candidate.evidence_ids, "event:e0@1")})
    result = validate_candidate(candidate, Snapshot.model_validate(snapshot_data))
    assert not result.valid
    assert "custody" in result.errors
