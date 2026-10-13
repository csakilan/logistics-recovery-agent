"""Controlled provider/billing responses exercise the real application factory.

Billing faults are injected; no requests leave this test process and no real
spend or live-model performance is measured.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from logistics_recovery.web import build_application


MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
READS = ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")


class ControlledRouter:
    def __init__(self, candidate, fault="none", cost=0):
        self.candidate, self.fault, self.cost = candidate, fault, cost
        self.requests = []
        self.chat_requests = []

    def respond(self, request):
        self.requests.append(request)
        path = request.url.path
        pricing = {"prompt": "0", "completion": "0", "request": "0"}
        if path == "/api/v1/models":
            if self.fault == "catalog_price": pricing["prompt"] = "0.01"
            reasoning = None if self.fault == "malformed_profile" else {"mandatory": False}
            return httpx.Response(200, json={"data": [{"id": MODEL, "pricing": pricing, "reasoning": reasoning}]})
        if path == "/api/v1/models/" + MODEL + "/endpoints":
            if self.fault == "endpoint_price": pricing["completion"] = "0.01"
            parameters = [] if self.fault == "unsupported_tools" else ["tools", "tool_choice", "reasoning"]
            return httpx.Response(200, json={"data": {"endpoints": [{"provider_name": "Nvidia", "pricing": pricing, "supported_parameters": parameters}]}})
        if path == "/api/v1/key":
            if self.fault == "billing_unavailable":
                return httpx.Response(503, text="private-test-sentinel must not reach the page")
            used = 0.001 if self.fault == "usage_increase" and self.chat_requests else 0
            remaining = 0 if self.fault == "quota" else 1000 - len(self.chat_requests)
            limit = None if self.fault == "missing_key_limit" else 2 if self.fault == "excess_key_limit" else 1
            return httpx.Response(200, json={"data": {"usage": used, "limit": limit, "limit_reset": "monthly", "free_model_daily_requests": {"limit": 1000, "remaining": remaining}}})
        if path == "/api/v1/credits":
            balance = 9.999 if self.fault == "balance_drop" and self.chat_requests else 10
            return httpx.Response(200, json={"data": {"total_credits": balance, "total_usage": 0}})
        assert request.method == "POST" and path == "/api/v1/chat/completions"
        body = json.loads(request.content)
        self.chat_requests.append(body)
        retrieved = any(message["role"] == "tool" for message in body["messages"])
        names = ("propose_recovery",) if retrieved else READS
        calls = [{"id": "call-" + name, "type": "function", "function": {"name": name, "arguments": json.dumps(self.candidate.model_dump() if retrieved else {})}} for name in names]
        usage = {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        if self.cost is not None: usage["cost"] = self.cost
        if self.fault == "reported_charge" or (self.fault == "charge_after_control" and len(self.chat_requests) > 2): usage["cost"] = 0.001
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": calls}, "finish_reason": "tool_calls"}], "usage": usage})


@pytest.fixture
def router_factory(monkeypatch, valid_candidate):
    def factory(fault="none", cost=0):
        router = ControlledRouter(valid_candidate, fault, cost)
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: router.respond(request))
        return router
    return factory


def live_settings(settings, model=MODEL):
    return settings.model_copy(update={"mode": "live", "model_id": model, "provider_key": SecretStr("private-test-sentinel")})


@pytest.mark.parametrize("cost", (0, None))
def test_live_factory_uses_free_profile_and_preserves_counts_and_approval_after_restart(cost, settings, router_factory, repo, auth, origin):
    router = router_factory(cost=cost)
    settings = live_settings(settings)
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        assert client.get("/incidents/i1").status_code == 401
        assert client.post("/incidents/i1/investigate", auth=auth).status_code == 403
        assert router.requests == []
        result = client.post("/incidents/i1/investigate", auth=auth, headers=origin)
        assert result.status_code == 200
        proposal = result.json()["proposal"]
        assert result.json()["status"] == "awaiting_approval"
        assert repo.assignment("i1") is None
        assert client.post("/incidents/i1/commit", auth=auth, headers=origin, json={"proposal_id": proposal["id"]}).status_code == 409
        assert (settings.data_dir / "free-model-requests.json").is_file()
        ledger = json.loads((settings.data_dir / "free-model-requests.json").read_text())
        assert ledger["requests"] == 2
        assert [event["reported_cost_usd"] for event in ledger["events"]] == (["0", "0"] if cost == 0 else [None, None])
        for body in router.chat_requests:
            assert body["model"] == MODEL
            assert body["provider"] == {"max_price": {"prompt": 0, "completion": 0, "request": 0}, "allow_fallbacks": False, "require_parameters": True}
            assert body["reasoning"] == {"enabled": False}
            assert body["tool_choice"] == "required" and body["max_tokens"] == 600
            assert "private-test-sentinel" not in json.dumps(body)

    with TestClient(build_application(settings), base_url=settings.origin) as client:
        assert "2 / 1,000" in client.get("/incidents/i1", auth=auth).text
        approved = client.post("/incidents/i1/decision", auth=auth, headers=origin, json={"proposal_id": proposal["id"], "incident_version": proposal["incident_version"], "decision": "approve"})
        assert approved.status_code == 200 and approved.json()["assignment"]["status"] == "assigned"
        client.post("/incidents/i1/commit", auth=auth, headers=origin, json={"proposal_id": proposal["id"]})
        assert repo.stats("i1")["commit_events"] == 1
        assert len(router.chat_requests) == 2
        assert json.loads((settings.data_dir / "free-model-requests.json").read_text())["requests"] == 2


@pytest.mark.parametrize("fault,expected_chats", [
    ("quota", 0), ("billing_unavailable", 0), ("catalog_price", 0),
    ("endpoint_price", 0), ("reported_charge", 1), ("usage_increase", 1),
    ("balance_drop", 1), ("paid_model", 0), ("unsupported_tools", 0),
    ("missing_key_limit", 0), ("excess_key_limit", 0),
    ("malformed_profile", 0),
])
def test_live_web_pause_is_visible_and_durable_without_approval_or_extra_requests(fault, expected_chats, settings, router_factory, repo, auth, origin):
    router = router_factory(fault)
    settings = live_settings(settings, "example/paid" if fault == "paid_model" else MODEL)
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        result = client.post("/incidents/i1/investigate", auth=auth, headers=origin)
        assert result.status_code == 503
        assert result.json()["status"] == "paused"
        assert len(router.chat_requests) == expected_chats
        assert repo.assignment("i1") is None
        page = client.get("/incidents/i1", auth=auth)
        assert page.status_code == 200 and "Live investigations paused" in page.text
        assert "private-test-sentinel" not in page.text + result.text
        assert json.loads((settings.data_dir / "free-model-requests.json").read_text())["status"] == "paused"
        attempts_before_retry = repo.stats("i1")["model_calls"]
    # Correcting the external condition cannot silently clear a persisted stop.
    router.fault = "none"
    settings = live_settings(settings)
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        assert "Live investigations paused" in client.get("/", auth=auth).text
        result = client.post("/incidents/i1/investigate", auth=auth, headers={**origin, "Content-Type": "application/x-www-form-urlencoded"}, content="", follow_redirects=False)
        assert result.status_code == 303
        assert len(router.chat_requests) == expected_chats
        assert repo.stats("i1")["model_calls"] == attempts_before_retry
        assert repo.assignment("i1") is None


@pytest.mark.parametrize("shared_ledger", (False, True))
def test_live_web_persisted_request_cap_stops_before_the_next_model_send(shared_ledger, settings, router_factory, repo, auth, origin):
    router = router_factory()
    settings = live_settings(settings)
    ledger_path = settings.data_dir / ("shared-evaluation-ledger.json" if shared_ledger else "free-model-requests.json")
    if shared_ledger:
        settings = settings.model_copy(update={"billing_state_path": ledger_path})
    ledger_path.write_text(json.dumps({"status": "active", "reason": "", "requests": 999, "request_limit": 1000, "events": []}))
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        result = client.post("/incidents/i1/investigate", auth=auth, headers=origin)
        assert result.status_code == 503 and result.json()["status"] == "paused"
        assert len(router.chat_requests) == 1
        assert json.loads(ledger_path.read_text())["requests"] == 1000
        assert repo.assignment("i1") is None
        assert "1,000 / 1,000" in client.get("/incidents/i1", auth=auth).text
        if shared_ledger:
            assert not (settings.data_dir / "free-model-requests.json").exists()


@pytest.fixture
def cli_runner(monkeypatch, settings, snapshot_data, tmp_path):
    """Two independently isolated cases; expected outcomes stay evaluator-only."""
    import hashlib
    from logistics_recovery.cli import main

    fixtures = tmp_path / "cli-fixtures"
    fixtures.mkdir()
    cases = [{"id": f"cli-control-{i}", "category": "normal", "split": "development", "snapshot": snapshot_data,
              "expected": {"outcome": "assigned", "oracle_marker": "evaluation-only"}} for i in (1, 2)]
    development = fixtures / "development.jsonl"
    development.write_text("\n".join(json.dumps(case) for case in cases) + "\n")
    (fixtures / "manifest.json").write_text(json.dumps({"sha256": {"development.jsonl": hashlib.sha256(development.read_bytes()).hexdigest()}}))
    for name, value in {"LOGISTICS_DATA_DIR": str(settings.data_dir), "LOGISTICS_USERNAME": "dispatcher", "LOGISTICS_PASSWORD": "test-password", "LOGISTICS_MODE": "live", "OPENROUTER_API_KEY": "private-test-sentinel", "OPENROUTER_MODEL": MODEL}.items():
        monkeypatch.setenv(name, value)

    def run(model=MODEL):
        monkeypatch.setenv("OPENROUTER_MODEL", model)
        output = tmp_path / "cli-result.json"
        main(["--fixtures", str(fixtures), "evaluate", "--mode", "live", "--split", "development", "--confirmed-provider-settings", "--live-budget-usd", "1", "--input-rate", "0", "--output-rate", "0", "--output", str(output)])
        return json.loads(output.read_text())
    return run


def test_live_cli_uses_the_same_free_profile_and_persistent_guard(cli_runner, router_factory, settings):
    router = router_factory()
    report = cli_runner()
    assert report.get("status") == "completed"
    assert len(report["cases"]) == 2 and all(case["passed"] for case in report["cases"])
    assert json.loads((settings.data_dir / "free-model-requests.json").read_text())["requests"] == 4
    assert all(body.get("provider") == {"max_price": {"prompt": 0, "completion": 0, "request": 0}, "allow_fallbacks": False, "require_parameters": True} for body in router.chat_requests)


@pytest.mark.parametrize("fault,model,expected_chats", [("none", "example/paid", 0), ("reported_charge", MODEL, 1)])
def test_live_cli_blocks_paid_models_and_stops_on_reported_spending(fault, model, expected_chats, cli_runner, router_factory, settings):
    router = router_factory(fault)
    report = cli_runner(model)
    assert report.get("status") == "paused"
    assert len(router.chat_requests) == expected_chats
    assert report["cases"] == []
    assert report["interrupted_case_id"] == "cli-control-1"
    assert json.loads((settings.data_dir / "free-model-requests.json").read_text())["status"] == "paused"


def test_live_cli_retains_completed_cases_when_the_next_case_pauses(cli_runner, router_factory):
    router = router_factory("charge_after_control")
    report = cli_runner()
    assert report.get("status") == "paused"
    assert len(report["cases"]) == 1 and report["cases"][0]["passed"]
    assert report["interrupted_case_id"] == "cli-control-2"
    assert len(router.chat_requests) == 3
