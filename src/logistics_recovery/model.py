import json
from decimal import Decimal
from typing import Annotated, Any, Literal, Protocol

import httpx
from pydantic import Field, ValidationError, model_validator

from .config import Settings
from .domain import Candidate, DomainError, Identifier, Nonnegative, Positive, Record


class ToolCall(Record):
    id: Annotated[str, Field(min_length=1, max_length=120)]
    name: Annotated[str, Field(min_length=1, max_length=80)]
    arguments: dict[str, Any]


class Usage(Record):
    prompt_tokens: Nonnegative | None = None
    completion_tokens: Nonnegative | None = None
    cost_usd: Annotated[Decimal, Field(ge=0)] | None = None


class ModelContext(Record):
    incident_id: Identifier
    call_index: Positive
    messages: tuple[dict[str, Any], ...]


class EscalateRequest(Record):
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class ModelTurn(Record):
    kind: Literal["tools", "proposal", "escalate"]
    tool_calls: tuple[ToolCall, ...] = ()
    candidate: Candidate | None = None
    reason: Annotated[str, Field(max_length=1000)] = ""
    usage: Usage = Field(default_factory=Usage)

    @model_validator(mode="after")
    def validate_turn(self):
        if self.kind == "tools" and (not 1 <= len(self.tool_calls) <= 5 or self.candidate is not None): raise ValueError("Invalid read turn")
        if self.kind == "proposal" and (self.candidate is None or self.tool_calls): raise ValueError("Invalid proposal turn")
        if self.kind == "escalate" and (not self.reason or self.tool_calls or self.candidate is not None): raise ValueError("Invalid escalation turn")
        return self


class ModelAdapter(Protocol):
    def next_turn(self, context: ModelContext, tools: list[dict]) -> ModelTurn: ...


class ReplayModel:
    def __init__(self, scripts: dict[str, tuple[ModelTurn, ...]]):
        self.scripts = scripts

    def next_turn(self, context: ModelContext, tools: list[dict]) -> ModelTurn:
        turns = self.scripts.get(context.incident_id, ())
        if context.call_index > len(turns): raise DomainError("replay_exhausted")
        return turns[context.call_index - 1]


class OpenRouterModel:
    def __init__(self, settings: Settings, client: httpx.Client):
        if not settings.provider_key or not settings.model_id: raise DomainError("model_not_configured")
        self.settings, self.client = settings, client

    def next_turn(self, context: ModelContext, tools: list[dict]) -> ModelTurn:
        payload = {"model": self.settings.model_id, "messages": list(context.messages), "tools": tools, "tool_choice": "required", "max_tokens": self.settings.max_output_tokens}
        if len(json.dumps(payload, ensure_ascii=False)) > self.settings.max_context_chars:
            raise DomainError("context_too_large")
        try:
            response = self.client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {self.settings.provider_key.get_secret_value()}"}, timeout=self.settings.timeout_seconds, follow_redirects=False)
            response.raise_for_status()
        except httpx.HTTPError:
            raise DomainError("provider_unavailable") from None
        try:
            data = response.json()
            if not isinstance(data, dict): raise ValueError("Invalid response object")
            raw_usage = data.get("usage")
            if raw_usage is None: raw_usage = {}
            if not isinstance(raw_usage, dict): raise ValueError("Invalid usage object")
            usage = Usage(prompt_tokens=raw_usage.get("prompt_tokens"), completion_tokens=raw_usage.get("completion_tokens"), cost_usd=raw_usage.get("cost"))
            message = data["choices"][0]["message"]
            if not isinstance(message, dict): raise ValueError("Invalid message object")
            calls = tuple(ToolCall(id=call["id"], name=call["function"]["name"], arguments=json.loads(call["function"]["arguments"])) for call in message.get("tool_calls", []))
            terminal = [call for call in calls if call.name in {"propose_recovery", "escalate"}]
            if terminal:
                if len(calls) != 1: raise ValueError("Mixed terminal response")
                call = terminal[0]
                if call.name == "propose_recovery":
                    return ModelTurn(kind="proposal", candidate=Candidate.model_validate(call.arguments), usage=usage)
                return ModelTurn(kind="escalate", reason=EscalateRequest.model_validate(call.arguments).reason, usage=usage)
            return ModelTurn(kind="tools", tool_calls=calls, usage=usage)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError):
            raise DomainError("invalid_model_response") from None
