import secrets

from .config import Settings
from .domain import DomainError, Operator


def authenticate(username: str, password: str, settings: Settings) -> Operator:
    valid_username = secrets.compare_digest(username.encode("utf-8"), settings.dispatcher_username.encode("utf-8"))
    valid_password = secrets.compare_digest(password.encode("utf-8"), settings.dispatcher_password.get_secret_value().encode("utf-8"))
    if not (valid_username and valid_password): raise DomainError("authentication_failed")
    return Operator(id="dispatcher")
