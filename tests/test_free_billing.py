"""Billing faults are deliberately injected; no real money is spent here."""
import json
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from logistics_recovery.model import OpenRouterModel


MODEL = "test/verified:free"
CHAT = "https://openrouter.ai/api/v1/chat/completions"


def guarded_model(settings, tmp_path, valid_candidate, *, cost=0, increase_usage=False, decrease_credits=False, limit=1000, **guard_options):
    from logistics_recovery.free_billing import BillingSnapshot, ZeroCostTransport

    calls = []
    billed = [Decimal("0")]
    balance = [Decimal("10")]

    def billing():
        return BillingSnapshot(key_usage=billed[0], account_usage=billed[0], credits=balance[0], free_remaining=1000)

    def provider(request):
        body = json.loads(request.content)
        calls.append(body)
        retrieved = any(message["role"] == "tool" for message in body["messages"])
        names = ("propose_recovery",) if retrieved else ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")
        tools = [{"id": f"call-{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(valid_candidate.model_dump() if retrieved else {})}} for name in names]
        if increase_usage: billed[0] = Decimal("0.001")
        if decrease_credits: balance[0] = Decimal("9.999")
        # A real boundary requirement: omitting the outbound zero-price ceiling
        # would make even the successful control pause instead of recover.
        outgoing = body.get("provider", {})
        protected = outgoing.get("max_price") == {"prompt": 0, "completion": 0, "request": 0} and outgoing.get("allow_fallbacks") is False
        returned_cost = cost if protected else 0.01
        usage = {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        if returned_cost is not None: usage["cost"] = returned_cost
        return httpx.Response(200, json={"id": "test-generation", "object": "chat.completion", "created": 0, "model": MODEL, "choices": [{"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": tools}, "finish_reason": "tool_calls"}], "usage": usage})

    guard = ZeroCostTransport(MODEL, httpx.MockTransport(provider), billing, tmp_path / "billing-state.json", {"prompt": "0", "completion": "0"}, request_limit=limit, minimum_interval_seconds=0, **guard_options)
    client = httpx.Client(transport=guard)
    config = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": MODEL})
    return OpenRouterModel(config, client), guard, calls, client


@pytest.mark.parametrize("cost,increase_usage,reason", [(0.001, False, "reported_charge"), (0, True, "billing_increase"), (None, False, "cost_unknown")])
def test_charge_or_unknown_cost_stops_the_real_workflow_after_one_request(cost, increase_usage, reason, settings, tmp_path, valid_candidate, workflow_factory, repo):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, cost=cost, increase_usage=increase_usage)
    with client:
        with pytest.raises(BillingPause) as paused:
            workflow_factory(model).start("i1")
        assert paused.value.reason == reason
        assert len(calls) == 1
        assert repo.stats("i1")["model_calls"] == 1
        assert repo.assignment("i1") is None
        state = json.loads((tmp_path / "billing-state.json").read_text())
        assert state["status"] == "paused"
        assert state["reason"] == reason
        assert "private-test-sentinel" not in json.dumps(state)
        # The graph's normal DomainError retry path must not swallow this stop.
        with pytest.raises(BillingPause):
            client.post(CHAT, json=calls[0])
        assert len(calls) == 1


def test_zero_cost_control_reaches_approval_and_commits_once(settings, tmp_path, valid_candidate, workflow_factory, repo, service, operator):
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate)
    with client:
        workflow = workflow_factory(model)
        view = workflow.start("i1")
        assert view.status == "awaiting_approval"
        assert repo.assignment("i1") is None
        assert len(calls) == 2
        service.approve(view.proposal.id, view.proposal.incident_version, operator)
        assert workflow.resume("i1", view.proposal.id).status == "assigned"
        assert repo.stats("i1")["commit_events"] == 1
        assert guard.state["status"] == "active"


def test_credit_balance_drop_stops_even_when_usage_counters_lag(settings, tmp_path, valid_candidate, workflow_factory, repo):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, decrease_credits=True)
    with client:
        with pytest.raises(BillingPause, match="credit_balance_decreased"):
            workflow_factory(model).start("i1")
        assert len(calls) == 1
        assert repo.stats("i1")["model_calls"] == 1
        assert repo.assignment("i1") is None
        assert guard.state["status"] == "paused"


def test_global_request_budget_stops_before_another_network_request(settings, tmp_path, valid_candidate, workflow_factory, repo):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, limit=1)
    with client:
        with pytest.raises(BillingPause, match="request_budget_exhausted"):
            workflow_factory(model).start("i1")
        assert len(calls) == 1
        assert repo.assignment("i1") is None


def test_a_paused_session_stays_paused_after_reconstruction(settings, tmp_path, valid_candidate):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, cost=0.001)
    with client:
        with pytest.raises(BillingPause):
            client.post(CHAT, json={"model": MODEL, "max_tokens": 600, "messages": []})
    with pytest.raises(BillingPause, match="session_already_paused"):
        guarded_model(settings, tmp_path, valid_candidate)
    assert len(calls) == 1


@pytest.mark.parametrize("model_id,pricing", [("test/paid", {"prompt": "0", "completion": "0"}), (MODEL, {"prompt": "0.000001", "completion": "0"})])
def test_nonfree_model_or_price_is_rejected_before_inference(model_id, pricing, tmp_path):
    from logistics_recovery.free_billing import BillingPause, BillingSnapshot, ZeroCostTransport
    def never_send(request): pytest.fail("Unsafe request reached provider")
    with pytest.raises(BillingPause):
        ZeroCostTransport(model_id, httpx.MockTransport(never_send), lambda: BillingSnapshot(Decimal(0), Decimal(0), Decimal(10), 1000), tmp_path / "state.json", pricing, minimum_interval_seconds=0)


def test_missing_receipt_policy_can_reach_approval_without_inventing_cost(settings, tmp_path, valid_candidate, workflow_factory, repo, service, operator):
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, cost=None, pause_on_unknown_cost=False)
    with client:
        workflow = workflow_factory(model)
        view = workflow.start("i1")
        assert view.status == "awaiting_approval"
        assert repo.assignment("i1") is None
        service.approve(view.proposal.id, view.proposal.incident_version, operator)
        assert workflow.resume("i1", view.proposal.id).status == "assigned"
        assert repo.stats("i1")["commit_events"] == 1
        assert len(calls) == 2
        assert guard.state["status"] == "active"
        assert [e["reported_cost_usd"] for e in guard.state["events"]] == [None, None]


@pytest.mark.parametrize("cost,increase_usage,decrease_credits,reason", [
    (0.001, False, False, "reported_charge"),
    (None, True, False, "billing_increase"),
    (None, False, True, "credit_balance_decreased"),
])
def test_missing_receipt_policy_still_stops_real_spending(cost, increase_usage, decrease_credits, reason, settings, tmp_path, valid_candidate, workflow_factory, repo):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, cost=cost, increase_usage=increase_usage, decrease_credits=decrease_credits, pause_on_unknown_cost=False)
    with client:
        with pytest.raises(BillingPause, match=reason):
            workflow_factory(model).start("i1")
        assert len(calls) == 1
        assert repo.assignment("i1") is None
        assert guard.state["status"] == "paused"
        with pytest.raises(BillingPause):
            client.post(CHAT, json=calls[0])
        assert len(calls) == 1


def test_missing_receipt_policy_preserves_request_ceiling(settings, tmp_path, valid_candidate, workflow_factory, repo):
    from logistics_recovery.free_billing import BillingPause
    model, guard, calls, client = guarded_model(settings, tmp_path, valid_candidate, cost=None, limit=1, pause_on_unknown_cost=False)
    with client:
        with pytest.raises(BillingPause, match="request_budget_exhausted"):
            workflow_factory(model).start("i1")
        assert len(calls) == 1
        assert repo.assignment("i1") is None
