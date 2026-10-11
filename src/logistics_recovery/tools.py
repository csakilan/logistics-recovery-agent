from pydantic import ValidationError, Field

from .domain import Candidate, DomainError, Identifier, Record
from .model import EscalateRequest, ToolCall
from .repository import Repository


class EmptyArguments(Record):
    pass


class QuoteArguments(Record):
    courier_ids: tuple[Identifier, ...] | None = Field(default=None, max_length=100)


class ToolRegistry:
    def __init__(self, repository: Repository):
        self.repository = repository

    def schemas(self) -> list[dict]:
        tools = [("get_order", EmptyArguments), ("get_couriers", EmptyArguments), ("get_quotes", QuoteArguments), ("get_policy", EmptyArguments), ("get_events", EmptyArguments), ("propose_recovery", Candidate), ("escalate", EscalateRequest)]
        return [{"type": "function", "function": {"name": name, "description": "Return incident-scoped evidence" if name.startswith("get_") else "Submit a proposal for validation" if name == "propose_recovery" else "Request dispatcher escalation", "parameters": schema.model_json_schema()}} for name, schema in tools]

    def execute(self, incident_id: str, call: ToolCall) -> dict:
        if call.name not in {"get_order", "get_couriers", "get_quotes", "get_policy", "get_events"}:
            raise DomainError("tool_not_allowed")
        try:
            args = (QuoteArguments if call.name == "get_quotes" else EmptyArguments).model_validate(call.arguments)
        except ValidationError:
            raise DomainError("invalid_tool_arguments") from None
        snapshot = self.repository.snapshot(incident_id)
        kind, records = {
            "get_order": ("job", (snapshot.job,)),
            "get_couriers": ("courier", snapshot.couriers),
            "get_quotes": ("quote", snapshot.quotes),
            "get_policy": ("policy", (snapshot.policy,)),
            "get_events": ("event", snapshot.events),
        }[call.name]
        if call.name == "get_quotes" and args.courier_ids is not None:
            records = tuple(record for record in records if record.courier_id in args.courier_ids)
        return {"records": [record.model_dump(mode="json") for record in records], "evidence_ids": [f"{kind}:{record.id}@{record.version}" for record in records], "incident_version": snapshot.incident_version, "now_min": snapshot.now_min}
