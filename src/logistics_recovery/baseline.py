from .domain import Candidate, Snapshot
from .policy import required_evidence, validate_candidate


def choose_baseline(snapshot: Snapshot) -> Candidate | None:
    for quote in sorted(snapshot.quotes, key=lambda q: (q.cost_cents, q.id)):
        candidate = Candidate(quote_id=quote.id, evidence_ids=required_evidence(snapshot, quote), summary="Cheapest feasible quote using structured records.")
        if validate_candidate(candidate, snapshot).valid:
            return candidate
    return None
