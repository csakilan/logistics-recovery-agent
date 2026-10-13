"""Zero-cost transport for explicitly authorized, serial evaluation runs.

This is a validation harness component, not the normal application's transport.
BillingPause deliberately bypasses the workflow's retryable DomainError handler.
"""
import json
import os
import threading
import time
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from pathlib import Path
from typing import Callable

import httpx


class BillingPause(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def amount(value) -> Decimal:
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed < 0: raise ValueError()
        return parsed
    except (DecimalException, ValueError, TypeError):
        raise BillingPause("billing_value_unknown") from None


@dataclass(frozen=True)
class BillingSnapshot:
    """credits is the available credit balance, not lifetime purchased credits."""
    key_usage: Decimal
    account_usage: Decimal
    credits: Decimal
    free_remaining: int

    def __post_init__(self):
        for field in ("key_usage", "account_usage", "credits"):
            object.__setattr__(self, field, amount(getattr(self, field)))
        if type(self.free_remaining) is not int or self.free_remaining < 0:
            raise BillingPause("quota_unknown")

    def safe_dict(self):
        return {"key_usage_usd": str(self.key_usage), "account_usage_usd": str(self.account_usage), "credit_balance_usd": str(self.credits), "free_remaining": self.free_remaining}


class ZeroCostTransport(httpx.BaseTransport):
    def __init__(self, model_id: str, transport: httpx.BaseTransport,
                 billing_reader: Callable[[], BillingSnapshot], state_path: Path,
                 pricing: dict, *, request_limit: int = 1000,
                 minimum_interval_seconds: float = 3.1,
                 disable_reasoning: bool = False):
        self.model_id, self.transport, self.billing_reader = model_id, transport, billing_reader
        self.path = Path(state_path)
        self.interval, self.disable_reasoning = minimum_interval_seconds, disable_reasoning
        self.lock = threading.Lock()
        self.last_started = 0.0
        self.state = {"status": "active", "reason": "", "requests": 0, "request_limit": request_limit, "events": []}
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text())
                if not isinstance(saved, dict) or type(saved.get("requests")) is not int or saved["requests"] < 0 or not isinstance(saved.get("events"), list): raise ValueError()
                self.state = saved
            except (ValueError, OSError):
                self._pause("session_state_unknown")
            if self.state.get("status") != "active": raise BillingPause("session_already_paused")
            if self.state.get("request_limit") != request_limit: self._pause("request_limit_changed")
        if type(request_limit) is not int or not 1 <= request_limit <= 1000: self._pause("invalid_request_limit")
        if not model_id.endswith(":free"): self._pause("nonfree_model")
        try:
            prices = [amount(pricing[field]) for field in ("prompt", "completion")]
            prices.append(amount(pricing.get("request", "0")))
        except (KeyError, TypeError, BillingPause):
            self._pause("pricing_unknown")
        if any(prices): self._pause("nonzero_pricing")
        self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(self.state, indent=2) + "\n")
        os.replace(temporary, self.path)

    def _pause(self, reason):
        self.state.update(status="paused", reason=reason)
        self._save()
        raise BillingPause(reason)

    def _snapshot(self):
        try:
            snapshot = self.billing_reader()
            if not isinstance(snapshot, BillingSnapshot): raise ValueError()
            return snapshot
        except Exception:
            self._pause("billing_check_failed")

    def handle_request(self, request):
        with self.lock:
            if self.state["status"] != "active": raise BillingPause("session_already_paused")
            if request.method != "POST" or str(request.url) != "https://openrouter.ai/api/v1/chat/completions": self._pause("unexpected_endpoint")
            try:
                body = json.loads(request.content)
                allowed = {"model", "messages", "tools", "tool_choice", "max_tokens"}
                if not isinstance(body, dict) or set(body) - allowed or body.get("model") != self.model_id: raise ValueError()
                if type(body.get("max_tokens")) is not int or not 1 <= body["max_tokens"] <= 600: raise ValueError()
                secret = request.headers.get("Authorization", "").removeprefix("Bearer ")
                if secret and secret.encode() in request.content: raise ValueError()
            except (ValueError, TypeError):
                self._pause("request_not_free_scoped")
            if self.state["requests"] >= self.state["request_limit"]: self._pause("request_budget_exhausted")
            before = self._snapshot()
            self.state["last_before"] = before.safe_dict()
            if before.key_usage or before.account_usage: self._pause("billed_usage_present")
            if before.free_remaining < 1: self._pause("free_quota_exhausted")
            body["provider"] = {"max_price": {"prompt": 0, "completion": 0, "request": 0}, "allow_fallbacks": False, "require_parameters": True}
            if self.disable_reasoning: body["reasoning"] = {"enabled": False}
            headers = dict(request.headers)
            headers.pop("content-length", None)
            protected = httpx.Request(request.method, request.url, headers=headers, json=body, extensions=request.extensions)
            delay = self.interval - (time.monotonic() - self.last_started)
            if delay > 0: time.sleep(delay)
            self.last_started = time.monotonic()
            self.state["requests"] += 1
            self._save()
            try:
                response = self.transport.handle_request(protected)
                response.read()
            except httpx.HTTPError:
                self._pause("request_failed_cost_unknown")
            after = self._snapshot()
            cost = None
            try:
                data = response.json()
                cost = amount(data["usage"]["cost"])
            except (ValueError, KeyError, TypeError, BillingPause):
                pass
            event = {"request": self.state["requests"], "model": self.model_id, "http_status": response.status_code,
                     "reported_cost_usd": str(cost) if cost is not None else None,
                     "before": before.safe_dict(), "after": after.safe_dict()}
            self.state["events"].append(event)
            self._save()
            if cost is not None and cost > 0: self._pause("reported_charge")
            if after.key_usage > before.key_usage or after.account_usage > before.account_usage: self._pause("billing_increase")
            if after.credits < before.credits: self._pause("credit_balance_decreased")
            if cost is None: self._pause("cost_unknown")
            return response

    def close(self):
        self.transport.close()
