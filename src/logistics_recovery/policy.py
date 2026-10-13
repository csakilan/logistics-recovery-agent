from .domain import Candidate, Proposal, Quote, Snapshot, ValidationReport


def evidence_records(snapshot: Snapshot) -> dict[str, int]:
    records = {f"job:{snapshot.job.id}": snapshot.job.version, f"policy:{snapshot.policy.id}": snapshot.policy.version}
    for kind, values in (("courier", snapshot.couriers), ("quote", snapshot.quotes), ("event", snapshot.events)):
        records.update({f"{kind}:{r.id}": r.version for r in values})
    return records


def proposal_is_current(proposal: Proposal, snapshot: Snapshot) -> bool:
    current = evidence_records(snapshot)
    return (
        snapshot.incident_version == proposal.incident_version
        and all(current.get(name) == version for name, version in proposal.observed_versions)
        and validate_candidate(proposal.candidate, snapshot).valid
    )


def required_evidence(snapshot: Snapshot, quote: Quote) -> tuple[str, ...]:
    records = evidence_records(snapshot)
    names = [f"job:{snapshot.job.id}", f"policy:{snapshot.policy.id}", f"quote:{quote.id}", f"courier:{quote.courier_id}"]
    events = [e for e in snapshot.events if e.job_id == snapshot.job.id]
    if events:
        latest_time = max(e.at_min for e in events)
        names.extend(f"event:{e.id}" for e in events if e.at_min == latest_time)
    return tuple(f"{name}@{records[name]}" for name in names if name in records)


def validate_candidate(candidate: Candidate, snapshot: Snapshot) -> ValidationReport:
    errors = []
    quote = next((q for q in snapshot.quotes if q.id == candidate.quote_id), None)
    if quote is None:
        return ValidationReport(valid=False, errors=("quote_missing",))
    courier = next((c for c in snapshot.couriers if c.id == quote.courier_id), None)
    if quote.job_id != snapshot.job.id: errors.append("quote_job")
    if courier is None:
        errors.append("courier_missing")
    else:
        if not courier.available: errors.append("availability")
        if courier.free_capacity < snapshot.job.parcel_count: errors.append("capacity")
    if snapshot.now_min >= quote.expires_at_min: errors.append("quote_expired")
    if snapshot.now_min + quote.travel_min > snapshot.job.deadline_min: errors.append("deadline")
    if quote.cost_cents > snapshot.policy.max_cost_cents: errors.append("budget")
    events = [e for e in snapshot.events if e.job_id == snapshot.job.id]
    latest_time = max((e.at_min for e in events), default=None)
    latest = [e for e in events if e.at_min == latest_time]
    if snapshot.job.custody != "depot" or not latest or any(e.custody != "depot" for e in latest): errors.append("custody")
    known = {f"{name}@{version}" for name, version in evidence_records(snapshot).items()}
    supplied = set(candidate.evidence_ids)
    if not set(required_evidence(snapshot, quote)).issubset(supplied) or not supplied.issubset(known): errors.append("evidence")
    return ValidationReport(valid=not errors, errors=tuple(errors))
