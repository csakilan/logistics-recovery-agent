import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from logistics_recovery.baseline import choose_baseline
from logistics_recovery.domain import Candidate, DomainError, Snapshot
from logistics_recovery.evaluation import evaluate_case, load_scenarios
from logistics_recovery.model import ModelTurn, OpenRouterModel, ReplayModel, ToolCall
from logistics_recovery.web import build_application, create_app


def reads():
    return ModelTurn(kind="tools", tool_calls=tuple(ToolCall(id=name, name=name, arguments={}) for name in ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")))


@pytest.mark.parametrize("restart", [False, True])
def test_stale_before_approval_can_reinvestigate(workflow_factory, settings, repo, service, operator, auth, origin, valid_candidate, restart):
    alternative = Candidate(quote_id="q2", evidence_ids=("job:j1@1", "courier:c2@1", "quote:q2@1", "policy:p1@1", "event:e1@1"), summary="Current alternative courier.")
    model = ReplayModel({"i1": (reads(), ModelTurn(kind="proposal", candidate=valid_candidate), reads(), ModelTurn(kind="proposal", candidate=alternative))})
    workflow = workflow_factory(model)
    first = workflow.start("i1").proposal
    repo.change_courier("c1", False)
    with pytest.raises(DomainError, match="stale_proposal"): service.approve(first.id, 1, operator)
    if restart: workflow = workflow_factory(model)
    with TestClient(create_app(settings, service, workflow), base_url=settings.origin) as client:
        result = client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()
        assert result["status"] == "awaiting_approval"
        assert result["proposal"]["id"] != first.id
        assert result["proposal"]["candidate"]["quote_id"] == "q2"
        assert repo.assignment("i1") is None
        assert repo.approval(result["proposal"]["id"]) is None
        with pytest.raises(DomainError, match="approval_mismatch"): workflow.resume("i1", first.id)
        second = result["proposal"]
        booked = client.post("/incidents/i1/decision", auth=auth, headers=origin, json={"proposal_id": second["id"], "incident_version": second["incident_version"], "decision": "approve"}).json()
        assert booked["assignment"]["courier_id"] == "c2"
    assert repo.stats("i1")["model_calls"] == 4


def test_factory_replay_uses_current_shared_capacity(settings, repo, auth, origin, snapshot_data):
    data = copy.deepcopy(snapshot_data)
    data["incident_id"] = "i2"; data["job"]["id"] = "j2"
    for quote in data["quotes"]: quote["id"] += "-2"; quote["job_id"] = "j2"
    for event in data["events"]: event["job_id"] = "j2"
    repo.seed(Snapshot.model_validate(data))
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        for incident_id, courier_id in (("i1", "c1"), ("i2", "c2")):
            view = client.post(f"/incidents/{incident_id}/investigate", auth=auth, headers=origin).json()
            assert view["status"] == "awaiting_approval"
            proposal = view["proposal"]
            result = client.post(f"/incidents/{incident_id}/decision", auth=auth, headers=origin, json={"proposal_id": proposal["id"], "incident_version": proposal["incident_version"], "decision": "approve"}).json()
            assert result["assignment"]["courier_id"] == courier_id
            assert repo.stats(incident_id)["model_calls"] == 2


@pytest.mark.parametrize("attack", ["forbidden_tool", "malformed_model", "missing_evidence", "forged_evidence"])
def test_live_protocol_fault_cases_are_explicitly_not_applicable(attack):
    from pathlib import Path
    case = next(c for c in load_scenarios(Path(__file__).resolve().parents[1]/"fixtures") if c.attack == attack)
    class UnexpectedProvider:
        def next_turn(self, context, tools): raise AssertionError("Protocol-only fault case must not call a live model")
    result = evaluate_case(case, "live", UnexpectedProvider())
    assert result.applicable is False
    assert result.passed is None
    assert result.model_calls == result.assignment_count == 0
    assert result.skip_reason


def test_skipped_cases_do_not_inflate_live_success_denominators():
    from pathlib import Path
    from logistics_recovery.evaluation import summarize
    case = next(c for c in load_scenarios(Path(__file__).resolve().parents[1]/"fixtures") if c.attack == "forbidden_tool")
    result = evaluate_case(case, "live", object())
    summary = summarize([result])
    assert summary["modes"] == ["live"]
    assert summary["scheduled_cases"] == summary["skipped_cases"] == 1
    assert summary["cases"] == summary["safe_case_successes"] == 0
    assert summary["valid_success_rate"] is None


def test_factory_reinvestigation_after_quote_expiry_escalates_safely(settings, repo, auth, origin):
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        first = client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()
        assert first["status"] == "awaiting_approval"
        repo.advance_clock("i1", 10)
        result = client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()
        assert result["status"] == "escalated"
        assert repo.assignment("i1") is None
        assert repo.stats("i1")["model_calls"] == 4


def test_incident_history_has_one_event_in_operational_order(service, approved, operator, repo):
    service.commit(approved.proposal_id, operator)
    service.record_event("i1", "pickup-once", "pickup", operator)
    service.record_event("i1", "delivery-once", "delivery", operator)
    service.record_event("i1", "delivery-once", "delivery", operator)
    history = repo.history("i1")
    event_ids = [h["payload"].get("id") for h in history]
    assert event_ids.count("pickup-once") == event_ids.count("delivery-once") == 1
    kinds = [h["kind"] for h in history]
    assert kinds.index("assignment_committed") < kinds.index("simulated_pickup") < kinds.index("simulated_delivery")
    assert len(repo.snapshot("i1").events) == 3  # source evidence remains retrievable


@pytest.mark.parametrize("body", [[], {"usage": ["unexpected"], "choices": []}, {"choices": [{"message": []}]}])
def test_malformed_provider_objects_use_sanitized_error(settings, body):
    from logistics_recovery.model import ModelContext
    live = settings.model_copy(update={"model_id": "test/model"})
    from pydantic import SecretStr
    live = live.model_copy(update={"provider_key": SecretStr("private-test-sentinel")})
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))) as client:
        adapter = OpenRouterModel(live, client)
        with pytest.raises(DomainError, match="^invalid_model_response$"):
            adapter.next_turn(ModelContext(incident_id="i1", call_index=1, messages=()), [])


def test_malformed_provider_shapes_use_bounded_workflow_errors(settings, workflow_factory, repo):
    from pydantic import SecretStr
    live = settings.model_copy(update={"model_id": "test/model", "provider_key": SecretStr("private-test-sentinel")})
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))) as client:
        result = workflow_factory(OpenRouterModel(live, client)).start("i1")
    assert result.status == "escalated"
    assert repo.stats("i1")["model_calls"] == 6
    errors = [h for h in repo.history("i1") if h["kind"] == "model_error"]
    assert len(errors) == 6
    assert all(h["payload"]["code"] == "invalid_model_response" for h in errors)
    assert "private-test-sentinel" not in json.dumps(repo.history("i1"))
