"""The approved free model and persistent spending controls for the local app."""
import json
import threading

import httpx

from .config import Settings
from .free_billing import BillingPause, BillingSnapshot, ZeroCostTransport, amount
from .model import ModelContext, OpenRouterModel


FREE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
PAUSE_MESSAGES = {
    "free_quota_exhausted": "The provider's free request allowance is exhausted.",
    "request_budget_exhausted": "The persistent 1,000-request session limit has been reached.",
    "reported_charge": "The provider reported an inference charge. Further model requests are stopped.",
    "billing_increase": "Billed usage increased. Further model requests are stopped.",
    "credit_balance_decreased": "The credit balance decreased. Further model requests are stopped.",
    "billed_usage_present": "The account reports billed usage. Review it before making more model requests.",
    "billing_check_failed": "Billing or account limits could not be verified.",
    "nonfree_model": "Live mode requires the approved free Nemotron model.",
    "nonzero_pricing": "The selected model no longer has verified zero pricing.",
    "pricing_unknown": "The model's current prices could not be verified.",
    "model_profile_unavailable": "The approved free model's required capabilities could not be verified.",
    "request_failed_cost_unknown": "A provider request failed and its cost could not be verified.",
    "cost_unknown": "A response's cost could not be verified.",
    "session_already_paused": "Live requests were previously paused and require review.",
    "session_state_unknown": "The persistent request record could not be verified.",
    "request_limit_changed": "The persistent request limit changed and requires review.",
    "request_not_free_scoped": "A request did not match the approved free-model configuration.",
    "unexpected_endpoint": "An unexpected provider endpoint was blocked.",
}


def safe_pause_reason(reason):
    return reason if reason in PAUSE_MESSAGES else "session_already_paused"


class FreeLiveModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.billing_state_path or settings.data_dir / "free-model-requests.json"
        self.control = httpx.Client(timeout=20, follow_redirects=False)
        self.delegate = httpx.HTTPTransport(retries=0)
        self.lock = threading.Lock()
        self.client = self.guard = self.model = None
        self.profile_verified = False
        self.paused_reason = ""
        try:
            # Zero is the required price contract. Current catalogue/endpoint
            # prices are independently verified before any inference is sent.
            self.guard = ZeroCostTransport(settings.model_id, self.delegate, self._billing, self.path,
                                           {"prompt": "0", "completion": "0", "request": "0"},
                                           disable_reasoning=True, pause_on_unknown_cost=False)
            self.client = httpx.Client(transport=self.guard)
            self.model = OpenRouterModel(settings, self.client)
        except BillingPause as error:
            self.paused_reason = safe_pause_reason(error.reason)

    def _get(self, path, *, authenticated=False):
        headers = {"Authorization": "Bearer " + self.settings.provider_key.get_secret_value()} if authenticated else {}
        response = self.control.get("https://openrouter.ai/api/v1/" + path, headers=headers)
        response.raise_for_status()
        return response.json()["data"]

    @staticmethod
    def _zero_pricing(pricing):
        return all(amount(pricing[field]) == 0 for field in ("prompt", "completion")) and amount(pricing.get("request", "0")) == 0

    def _verify_profile(self):
        try:
            if self.settings.model_id != FREE_MODEL: raise BillingPause("model_profile_unavailable")
            model = next(row for row in self._get("models") if row["id"] == FREE_MODEL)
            if not self._zero_pricing(model["pricing"]): raise BillingPause("nonzero_pricing")
            if model.get("reasoning", {}).get("mandatory"): raise BillingPause("model_profile_unavailable")
            endpoints = self._get("models/" + FREE_MODEL + "/endpoints")["endpoints"]
            required = {"tools", "tool_choice", "reasoning"}
            if not any(self._zero_pricing(endpoint["pricing"]) and required.issubset(endpoint["supported_parameters"]) for endpoint in endpoints):
                raise BillingPause("model_profile_unavailable")
        except BillingPause as error:
            self.guard._pause(safe_pause_reason(error.reason))
        except (httpx.HTTPError, KeyError, TypeError, ValueError, StopIteration, AttributeError):
            self.guard._pause("pricing_unknown")
        self.profile_verified = True

    def _billing(self):
        key, credits = self._get("key", authenticated=True), self._get("credits", authenticated=True)
        if key.get("limit") is None or not 0 < amount(key["limit"]) <= 1:
            raise BillingPause("billing_check_failed")
        quota = key["free_model_daily_requests"]
        if type(quota["limit"]) is not int or quota["limit"] < 1:
            raise BillingPause("billing_check_failed")
        return BillingSnapshot(amount(key["usage"]), amount(credits["total_usage"]),
                               amount(credits["total_credits"]) - amount(credits["total_usage"]), quota["remaining"])

    def next_turn(self, context: ModelContext, tools: list[dict]):
        with self.lock:
            if self.paused_reason: raise BillingPause(self.status()["reason"])
            if self.guard.state["status"] != "active": raise BillingPause(self.status()["reason"])
            if not self.profile_verified: self._verify_profile()
            return self.model.next_turn(context, tools)

    def status(self):
        # Views read the atomic local record; opening a page never calls a model
        # or sends a billing request. Only safe, selected fields reach the UI.
        result = {"paused": False, "reason": "", "message": "", "requests": 0, "billing": None}
        try:
            state = json.loads(self.path.read_text())
            count = state["requests"]
            if type(count) is not int or count < 0 or state["status"] not in {"active", "paused"}: raise ValueError()
            result["requests"] = count
            if state["status"] == "paused":
                result["paused"] = True
                result["reason"] = safe_pause_reason(state.get("reason", ""))
                result["message"] = PAUSE_MESSAGES[result["reason"]]
            events = state.get("events", [])
            snapshot = events[-1]["after"] if events else state.get("last_before")
            if snapshot:
                result["billing"] = BillingSnapshot(snapshot["key_usage_usd"], snapshot["account_usage_usd"],
                                                    snapshot["credit_balance_usd"], snapshot["free_remaining"]).safe_dict()
        except (OSError, KeyError, TypeError, ValueError, IndexError, BillingPause):
            result.update(paused=True, reason="session_state_unknown", message=PAUSE_MESSAGES["session_state_unknown"])
        return result

    def close(self):
        if self.client: self.client.close()
        else: self.delegate.close()
        self.control.close()
