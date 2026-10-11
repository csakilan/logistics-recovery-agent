from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

Nonnegative = Annotated[StrictInt, Field(ge=0)]
Positive = Annotated[StrictInt, Field(gt=0)]
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")]
Custody = Literal["depot", "unknown", "in_transit", "delivered"]


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Job(Record):
    id: Identifier
    parcel_count: Positive
    deadline_min: Nonnegative
    custody: Custody
    version: Nonnegative


class Courier(Record):
    id: Identifier
    free_capacity: Nonnegative
    available: StrictBool
    version: Nonnegative


class Quote(Record):
    id: Identifier
    job_id: Identifier
    courier_id: Identifier
    cost_cents: Nonnegative
    travel_min: Nonnegative
    expires_at_min: Nonnegative
    version: Nonnegative


class Policy(Record):
    id: Identifier
    max_cost_cents: Nonnegative
    version: Nonnegative


class IncidentEvent(Record):
    id: Identifier
    job_id: Identifier
    kind: Annotated[str, Field(min_length=1, max_length=40)]
    at_min: Nonnegative
    custody: Custody
    version: Nonnegative
    note: Annotated[str, Field(max_length=1000)] = ""


class Snapshot(Record):
    incident_id: Identifier
    incident_version: Nonnegative
    now_min: Nonnegative
    job: Job
    couriers: tuple[Courier, ...]
    quotes: tuple[Quote, ...]
    policy: Policy
    events: tuple[IncidentEvent, ...]


class Candidate(Record):
    quote_id: Identifier
    evidence_ids: tuple[Annotated[str, Field(max_length=120)], ...]
    summary: Annotated[str, Field(max_length=1000)]


class ValidationReport(Record):
    valid: bool
    errors: tuple[str, ...] = ()


class Proposal(Record):
    id: Identifier
    incident_id: Identifier
    incident_version: Nonnegative
    candidate: Candidate
    observed_versions: tuple[tuple[str, Nonnegative], ...]
    revision: Nonnegative = 0


class Approval(Record):
    id: Identifier
    proposal_id: Identifier
    incident_version: Nonnegative
    operator_id: Identifier
    consumed: bool = False


class Assignment(Record):
    id: Identifier
    incident_id: Identifier
    proposal_id: Identifier
    courier_id: Identifier
    operation_id: Identifier
    status: Literal["assigned", "picked_up", "delivered"] = "assigned"


class Operator(Record):
    id: Identifier


class DomainError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}" if message else code)


class RunView(Record):
    status: Literal["awaiting_approval", "assigned", "rejected", "escalated"]
    proposal: Proposal | None = None
    assignment: Assignment | None = None
    model_calls: Nonnegative = 0
    revisions: Nonnegative = 0
    detail: str = ""


class WorkflowRunner(Protocol):
    def start(self, incident_id: str) -> RunView: ...
    def resume(self, incident_id: str, proposal_id: str) -> RunView: ...
