"""A deterministic dispatcher for the local demo; no model inference."""
import json

from .baseline import choose_baseline
from .domain import Snapshot
from .model import ModelTurn, ToolCall

READS = ("get_order", "get_couriers", "get_quotes", "get_policy", "get_events")


class CurrentReplayModel:
    def next_turn(self, context, tools) -> ModelTurn:
        if context.messages[-1]["role"] != "tool":
            return ModelTurn(kind="tools", tool_calls=tuple(ToolCall(id=f"read-{name}", name=name, arguments={}) for name in READS))
        names, results = {}, {}
        for message in context.messages:
            if message["role"] == "assistant":
                names.update({call["id"]: call["function"]["name"] for call in message.get("tool_calls", ())})
            elif message["role"] == "tool":
                results[names[message["tool_call_id"]]] = json.loads(message["content"])
        if not all(name in results and "records" in results[name] for name in READS):
            return ModelTurn(kind="escalate", reason="Required evidence is unavailable.")
        order = results["get_order"]
        snapshot = Snapshot.model_validate({"incident_id": context.incident_id, "incident_version": order["incident_version"], "now_min": order["now_min"], "job": order["records"][0], "couriers": results["get_couriers"]["records"], "quotes": results["get_quotes"]["records"], "policy": results["get_policy"]["records"][0], "events": results["get_events"]["records"]})
        candidate = choose_baseline(snapshot)
        if candidate is None: return ModelTurn(kind="escalate", reason="No feasible recovery from the retrieved records.")
        return ModelTurn(kind="proposal", candidate=candidate)
