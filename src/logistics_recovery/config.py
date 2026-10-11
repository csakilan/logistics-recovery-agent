import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from .domain import DomainError, Identifier


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    data_dir: Path
    origin: str = "http://127.0.0.1:8000"
    dispatcher_username: Identifier
    dispatcher_password: SecretStr = Field(repr=False)
    mode: Literal["replay", "live"] = "replay"
    provider_key: SecretStr | None = Field(default=None, repr=False)
    model_id: str | None = None
    timeout_seconds: int = Field(default=30, gt=0, le=30)
    max_context_chars: int = Field(default=24000, gt=0, le=24000)
    max_output_tokens: int = Field(default=600, gt=0, le=600)

    @model_validator(mode="after")
    def validate_configuration(self):
        origin = urlsplit(self.origin)
        if origin.scheme not in {"http", "https"} or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username:
            raise ValueError("Configure an origin without path or credentials")
        if origin.scheme == "http" and origin.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Remote access requires HTTPS")
        if not self.dispatcher_password.get_secret_value(): raise ValueError("Private dispatcher password required")
        if self.mode == "live" and (not self.provider_key or not self.model_id): raise ValueError("Live mode requires explicitly configured key and model")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        needed = {name: os.environ.get(name) for name in ("LOGISTICS_DATA_DIR", "LOGISTICS_USERNAME", "LOGISTICS_PASSWORD")}
        if not all(needed.values()): raise DomainError("configuration_missing", "Set private application configuration")
        return cls(data_dir=needed["LOGISTICS_DATA_DIR"], dispatcher_username=needed["LOGISTICS_USERNAME"], dispatcher_password=needed["LOGISTICS_PASSWORD"], origin=os.environ.get("LOGISTICS_ORIGIN", "http://127.0.0.1:8000"), mode=os.environ.get("LOGISTICS_MODE", "replay"), provider_key=os.environ.get("OPENROUTER_API_KEY") or None, model_id=os.environ.get("OPENROUTER_MODEL") or None)
