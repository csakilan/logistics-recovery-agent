import json

import httpx
import pytest

from logistics_recovery.domain import DomainError


def response_for(calls, usage=None):
    return {"id": "test-generation", "object": "chat.completion", "created": 0, "model": "test-model", "choices": [{"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": calls}, "finish_reason": "tool_calls"}], "usage": usage}


def provider_call(name, arguments):
    return {"id": "call-1", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


def model_for(settings, payload, status=200):
    from logistics_recovery.model import OpenRouterModel
    config = settings.model_copy(update={"mode": "live", "provider_key": __import__('pydantic').SecretStr("fake-key-not-real"), "model_id": "test-model"})
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
    return OpenRouterModel(config, httpx.Client(transport=transport))


def context(messages=None, index=1):
    from logistics_recovery.model import ModelContext
    return ModelContext(incident_id="i1", call_index=index, messages=messages or ({"role": "user", "content": "Investigate incident i1"},))


def test_provider_tool_response_parsed(settings):
    result = model_for(settings, response_for([provider_call("get_order", {})], {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001})).next_turn(context(), [])
    assert result.kind == "tools"
    assert result.tool_calls[0].name == "get_order"
    assert result.usage.prompt_tokens == 10
    assert str(result.usage.cost_usd) == "0.0001"


def test_provider_proposal_parsed(settings, valid_candidate):
    result = model_for(settings, response_for([provider_call("propose_recovery", valid_candidate.model_dump())])).next_turn(context(), [])
    assert result.kind == "proposal"
    assert result.candidate.quote_id == "q1"
    assert result.usage.cost_usd is None


def test_mixed_terminal_and_read_response_rejected(settings, valid_candidate):
    payload = response_for([provider_call("get_order", {}), provider_call("propose_recovery", valid_candidate.model_dump())])
    with pytest.raises(DomainError, match="invalid_model_response"):
        model_for(settings, payload).next_turn(context(), [])


def test_malformed_arguments_rejected(settings):
    malformed = provider_call("get_order", {}); malformed["function"]["arguments"] = "not json"
    with pytest.raises(DomainError, match="invalid_model_response"):
        model_for(settings, response_for([malformed])).next_turn(context(), [])


def test_context_limit_prevents_request(settings):
    with pytest.raises(DomainError, match="context_too_large"):
        model_for(settings, {}).next_turn(context(({"role": "user", "content": "x" * 24001},)), [])


def test_provider_error_sanitized_without_retry(settings):
    from logistics_recovery.model import OpenRouterModel
    from pydantic import SecretStr
    requests = []
    def fail(request):
        requests.append(request)
        return httpx.Response(500, json={"error": "private fake-key-not-real"})
    config = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("fake-key-not-real"), "model_id": "test-model"})
    model = OpenRouterModel(config, httpx.Client(transport=httpx.MockTransport(fail)))
    with pytest.raises(DomainError, match="provider_unavailable") as error:
        model.next_turn(context(), [])
    assert "fake-key-not-real" not in str(error.value)
    assert len(requests) == 1


def test_replay_index_is_incident_specific(valid_candidate):
    from logistics_recovery.model import ModelTurn, ReplayModel
    first = ModelTurn(kind="escalate", reason="Missing evidence")
    second = ModelTurn(kind="proposal", candidate=valid_candidate)
    replay = ReplayModel({"i1": (first, second)})
    assert replay.next_turn(context(index=2), []).candidate.quote_id == "q1"
    assert replay.next_turn(context(index=1), []).kind == "escalate"
