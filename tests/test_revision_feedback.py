"""Controlled provider faults exercise the real adapter, graph and business store.

These regressions prove client feedback behavior, not a live model's response to it.
Removing actionable feedback must make the useful recovery assertions fail.
"""
import json

import httpx
import pytest
from pydantic import SecretStr

from logistics_recovery.model import OpenRouterModel


def provider_response(names, arguments):
    calls = [{"id": f"call-{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments if name == "propose_recovery" else {})}} for name in names]
    return httpx.Response(200, json={"id": "test-generation", "object": "chat.completion", "created": 0, "model": "test/model", "choices": [{"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": calls}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20, "cost": 0}})


READS = ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")


@pytest.mark.parametrize("fault", ("prose", "invalid_arguments"))
def test_rejected_model_output_gets_feedback_and_recovers_within_budget(fault, settings, workflow_factory, valid_candidate, service, repo, operator):
    def provider(request):
        body = json.loads(request.content)
        messages = body["messages"]
        if not any(message["role"] == "tool" for message in messages):
            return provider_response(READS, {})
        if any(message["role"] == "user" and "invalid_model_response" in message["content"] for message in messages):
            return provider_response(("propose_recovery",), valid_candidate.model_dump())
        if fault == "prose":
            return httpx.Response(200, json={"id": "test-generation", "object": "chat.completion", "created": 0, "model": "test/model", "choices": [{"index": 0, "message": {"role": "assistant", "content": "untrusted-provider-detail"}, "finish_reason": "length"}], "usage": {"prompt_tokens": 10, "completion_tokens": 600, "total_tokens": 610, "cost": 0}})
        return provider_response(("propose_recovery",), {**valid_candidate.model_dump(), "extra": "untrusted-provider-detail"})

    live = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": "test/model"})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workflow = workflow_factory(OpenRouterModel(live, client))
        paused = workflow.start("i1")
        assert paused.status == "awaiting_approval"
        assert repo.assignment("i1") is None
        assert repo.stats("i1")["model_calls"] == 3
        saved = workflow.graph.get_state(workflow._config("i1")).values
        assert "untrusted-provider-detail" not in json.dumps(saved["messages"])
        assert "private-test-sentinel" not in json.dumps(saved["messages"])
        service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
        assert workflow.resume("i1", paused.proposal.id).status == "assigned"
        assert repo.stats("i1")["commit_events"] == 1


def test_constraint_feedback_allows_replacing_an_infeasible_quote(settings, workflow_factory, valid_candidate, service, repo, operator):
    repo.change_courier("c1", available=False)
    alternative = {"quote_id": "q2", "evidence_ids": ["job:j1@1", "courier:c2@1", "quote:q2@1", "policy:p1@1", "event:e1@1"], "summary": "Courier c2 has capacity."}
    # q1 evidence must match the changed courier, so availability is the only error.
    invalid = {**valid_candidate.model_dump(), "evidence_ids": ["job:j1@1", "courier:c1@2", "quote:q1@1", "policy:p1@1", "event:e1@1"]}

    def provider(request):
        messages = json.loads(request.content)["messages"]
        if not any(message["role"] == "tool" for message in messages):
            return provider_response(READS, {})
        corrected = any(message["role"] == "user" and "availability" in message["content"] for message in messages)
        return provider_response(("propose_recovery",), alternative if corrected else invalid)

    live = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": "test/model"})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workflow = workflow_factory(OpenRouterModel(live, client))
        paused = workflow.start("i1")
        assert paused.status == "awaiting_approval"
        assert paused.proposal.candidate.quote_id == "q2"
        assert repo.assignment("i1") is None
        assert repo.stats("i1")["model_calls"] == 3
        service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
        assert workflow.resume("i1", paused.proposal.id).assignment.courier_id == "c2"
        assert repo.stats("i1")["commit_events"] == 1


def test_missing_citation_feedback_repairs_a_feasible_plan(settings, workflow_factory, valid_candidate, service, repo, operator):
    """Without precise citation feedback the provider escalates a feasible job."""
    incomplete = {**valid_candidate.model_dump(), "evidence_ids": ["job:j1@1", "courier:c1@1", "quote:q1@1", "policy:p1@1"]}

    def provider(request):
        messages = json.loads(request.content)["messages"]
        if not any(message["role"] == "tool" for message in messages):
            return provider_response(READS, {})
        feedback = [message["content"] for message in messages if message["role"] == "user" and "invalid_proposal" in message["content"]]
        if not feedback:
            return provider_response(("propose_recovery",), incomplete)
        if "event:e1@1" in feedback[-1]:
            return provider_response(("propose_recovery",), valid_candidate.model_dump())
        return httpx.Response(200, json={"id": "test-generation", "object": "chat.completion", "created": 0, "model": "test/model", "choices": [{"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": [{"id": "call-escalate", "type": "function", "function": {"name": "escalate", "arguments": json.dumps({"reason": "Required evidence unavailable."})}}]}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20, "cost": 0}})

    live = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": "test/model"})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workflow = workflow_factory(OpenRouterModel(live, client))
        paused = workflow.start("i1")
        assert paused.status == "awaiting_approval"
        assert paused.proposal.candidate.evidence_ids == valid_candidate.evidence_ids
        assert repo.stats("i1")["model_calls"] == 3
        assert repo.assignment("i1") is None
        service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
        assert workflow.resume("i1", paused.proposal.id).status == "assigned"
        assert repo.stats("i1")["commit_events"] == 1


def test_citation_feedback_never_supplies_unretrieved_evidence(workflow_factory, valid_candidate, repo):
    from logistics_recovery.model import ModelTurn, ReplayModel, ToolCall
    incomplete = valid_candidate.model_copy(update={"evidence_ids": ("job:j1@1",)})
    read_order = ModelTurn(kind="tools", tool_calls=(ToolCall(id="read-order", name="get_order", arguments={}),))
    invalid = ModelTurn(kind="proposal", candidate=incomplete)
    workflow = workflow_factory(ReplayModel({"i1": (read_order, invalid, invalid, invalid)}))
    assert workflow.start("i1").status == "escalated"
    saved = workflow.graph.get_state(workflow._config("i1")).values
    feedback = json.dumps([message for message in saved["messages"] if message["role"] == "user"])
    for unseen in ("courier:c1@1", "quote:q1@1", "policy:p1@1", "event:e1@1"):
        assert unseen not in feedback
    assert repo.assignment("i1") is None


@pytest.mark.parametrize("prior_provider_faults", (0, 2))
def test_replanning_hides_invalidated_context_without_resetting_audit_or_budgets(
    prior_provider_faults, settings, workflow_factory, valid_candidate, service, repo, operator
):
    """Old tool results must not cross the fresh-investigation model boundary.

    This checks the actual outgoing adapter payload and persisted business state;
    the controlled provider does not claim to predict a live model's behavior.
    """
    from logistics_recovery.domain import DomainError

    requests = []
    replacement = {"quote_id": "q2", "evidence_ids": ["job:j1@1", "courier:c2@1", "quote:q2@1", "policy:p1@1", "event:e1@1"], "summary": "Use the available alternative courier."}

    def provider(request):
        requests.append(json.loads(request.content))
        attempt = len(requests)
        if attempt in (1, 3 + prior_provider_faults):
            return provider_response(READS, {})
        if 2 <= attempt <= 1 + prior_provider_faults:
            return httpx.Response(200, json={"choices": []})
        candidate = valid_candidate.model_dump() if attempt == 2 + prior_provider_faults else replacement
        return provider_response(("propose_recovery",), candidate)

    live = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": "test/model"})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workflow = workflow_factory(OpenRouterModel(live, client))
        first = workflow.start("i1")
        service.approve(first.proposal.id, first.proposal.incident_version, operator)
        repo.change_courier("c1", available=False)
        second = workflow.resume("i1", first.proposal.id)

        fresh_messages = requests[2 + prior_provider_faults]["messages"]
        assert not any(message["role"] in {"tool", "assistant"} for message in fresh_messages)
        assert "invalid_model_response" not in json.dumps(fresh_messages)
        assert "i1" in json.dumps(fresh_messages)
        for citation in valid_candidate.evidence_ids:
            assert citation not in json.dumps(fresh_messages)
        assert second.status == "awaiting_approval"
        assert second.proposal.id != first.proposal.id
        assert second.proposal.candidate.quote_id == "q2"
        assert repo.assignment("i1") is None
        assert repo.stats("i1")["model_calls"] == 4 + prior_provider_faults
        assert repo.stats("i1")["proposal_attempts"] == 2
        history = repo.history("i1")
        assert len([event for event in history if event["kind"] == "tool_result"]) == 10
        assert len([event for event in history if event["kind"] == "model_error"]) == prior_provider_faults
        with pytest.raises(DomainError, match="approval_mismatch"):
            workflow.resume("i1", first.proposal.id)
        with pytest.raises(DomainError, match="approval_required"):
            workflow.resume("i1", second.proposal.id)
        service.approve(second.proposal.id, second.proposal.incident_version, operator)
        assert workflow.resume("i1", second.proposal.id).assignment.courier_id == "c2"
        assert repo.stats("i1")["commit_events"] == 1
