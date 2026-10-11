import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from logistics_recovery.domain import Candidate, DomainError
from logistics_recovery.model import ModelTurn, ReplayModel, ToolCall


def reads(names=None):
    names = names or ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")
    return ModelTurn(kind="tools", tool_calls=tuple(ToolCall(id=f"call-{name}", name=name, arguments={}) for name in names))


def test_pause_survives_restart(workflow_factory, repo, service, operator):
    paused = workflow_factory().start("i1")
    assert paused.status == "awaiting_approval"
    assert repo.assignment("i1") is None
    service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
    result = workflow_factory().resume("i1", paused.proposal.id)
    assert result.status == "assigned"
    assert repo.stats("i1")["model_calls"] == 2


def test_resume_requires_recorded_approval(workflow_factory, repo):
    workflow = workflow_factory()
    paused = workflow.start("i1")
    with pytest.raises(DomainError, match="approval_required"):
        workflow.resume("i1", paused.proposal.id)
    assert repo.assignment("i1") is None


def test_rejected_proposal_does_not_resume_into_assignment(workflow_factory, service, operator, repo):
    workflow = workflow_factory(); paused = workflow.start("i1")
    service.reject(paused.proposal.id, operator)
    assert workflow.recover("i1").status == "rejected"
    assert repo.assignment("i1") is None


def test_conditional_retrieval_has_inspectable_evidence(workflow_factory, valid_candidate, repo):
    model = ReplayModel({"i1": (reads(("get_order",)), reads(("get_couriers", "get_quotes", "get_policy", "get_events")), ModelTurn(kind="proposal", candidate=valid_candidate))})
    assert workflow_factory(model).start("i1").status == "awaiting_approval"
    assert repo.stats("i1")["model_calls"] == 3
    assert len([event for event in repo.history("i1") if event["kind"] == "tool_result"]) == 5


def test_call_limit_survives_restart(workflow_factory, repo):
    class FailingModel:
        def next_turn(self, context, tools): raise DomainError("provider_unavailable")
    assert workflow_factory(FailingModel()).start("i1").status == "escalated"
    assert workflow_factory(FailingModel()).recover("i1").status == "escalated"
    assert repo.stats("i1")["model_calls"] == 6


def test_three_invalid_drafts_escalate(workflow_factory, valid_candidate, repo):
    bad = valid_candidate.model_copy(update={"quote_id": "not-a-quote"})
    turn = ModelTurn(kind="proposal", candidate=bad)
    result = workflow_factory(ReplayModel({"i1": (reads(), turn, turn, turn)})).start("i1")
    assert result.status == "escalated"
    assert repo.stats("i1")["proposal_attempts"] == 3
    assert repo.assignment("i1") is None


def test_guessed_but_unretrieved_evidence_is_not_accepted(workflow_factory, valid_candidate, repo):
    turn = ModelTurn(kind="proposal", candidate=valid_candidate)
    assert workflow_factory(ReplayModel({"i1": (turn, turn, turn)})).start("i1").status == "escalated"
    assert repo.assignment("i1") is None


def test_forbidden_tool_escalates_without_side_effect(workflow_factory, repo):
    turn = ModelTurn(kind="tools", tool_calls=(ToolCall(id="attack", name="approve", arguments={}),))
    assert workflow_factory(ReplayModel({"i1": (turn,)})).start("i1").status == "escalated"
    assert repo.assignment("i1") is None


def test_parallel_same_incident_invocation_rejected(workflow_factory, repo):
    entered = threading.Event(); release = threading.Event()
    class BlockingModel:
        def next_turn(self, context, tools):
            entered.set(); assert release.wait(5)
            return ModelTurn(kind="escalate", reason="Needs review")
    first, second = workflow_factory(BlockingModel()), workflow_factory(BlockingModel())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(first.start, "i1")
        assert entered.wait(5)
        try:
            with pytest.raises(DomainError, match="workflow_busy"): second.start("i1")
        finally: release.set()
        assert future.result().status == "escalated"
    assert repo.stats("i1")["model_calls"] == 1


def test_web_workflow_approval_completes_assignment(workflow_factory, settings, service, repo, auth, origin):
    from fastapi.testclient import TestClient
    from logistics_recovery.web import create_app
    with TestClient(create_app(settings, service, workflow_factory()), base_url=settings.origin) as client:
        started = client.post("/incidents/i1/investigate", auth=auth, headers=origin)
        assert started.status_code == 200
        assert started.json()["status"] == "awaiting_approval"
        proposal = started.json()["proposal"]
        completed = client.post("/incidents/i1/decision", auth=auth, headers=origin, json={"proposal_id": proposal["id"], "incident_version": proposal["incident_version"], "decision": "approve"})
        assert completed.status_code == 200
        assert completed.json()["status"] == "assigned"
        assert repo.stats("i1")["assignments"] == 1


def test_escalated_case_is_visible_to_dispatcher(workflow_factory, settings, service, auth):
    from fastapi.testclient import TestClient
    from logistics_recovery.web import create_app
    workflow = workflow_factory(ReplayModel({"i1": (ModelTurn(kind="escalate", reason="Conflicting custody records"),)}))
    assert workflow.start("i1").status == "escalated"
    with TestClient(create_app(settings, service, workflow), base_url=settings.origin) as client:
        response = client.get("/incidents/i1", auth=auth)
    assert "Escalated" in response.text
