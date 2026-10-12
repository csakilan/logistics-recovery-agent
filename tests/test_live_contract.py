"""Regression for a provider that validly defaults to prose in auto mode."""
import json

import httpx
from pydantic import SecretStr

from logistics_recovery.model import OpenRouterModel


def test_live_workflow_requires_native_tool_output(settings, workflow_factory, valid_candidate, service, repo, operator):
    def provider(request):
        body = json.loads(request.content)
        if body.get("tool_choice") != "required":
            message = {"role": "assistant", "content": "Here is my recommended recovery plan."}
        else:
            retrieved = any(message["role"] == "tool" for message in body["messages"])
            names = ("propose_recovery",) if retrieved else ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")
            calls = [{"id": f"call-{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(valid_candidate.model_dump() if retrieved else {})}} for name in names]
            message = {"role": "assistant", "content": None, "tool_calls": calls}
        return httpx.Response(200, json={"id": "test-generation", "object": "chat.completion", "created": 0, "model": "test/model", "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20, "cost": 0}})

    live = settings.model_copy(update={"mode": "live", "provider_key": SecretStr("private-test-sentinel"), "model_id": "test/model"})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workflow = workflow_factory(OpenRouterModel(live, client))
        paused = workflow.start("i1")
        assert paused.status == "awaiting_approval"
        assert repo.assignment("i1") is None
        assert repo.stats("i1")["model_calls"] == 2
        service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
        assert workflow.resume("i1", paused.proposal.id).status == "assigned"
        assert repo.stats("i1")["commit_events"] == 1
