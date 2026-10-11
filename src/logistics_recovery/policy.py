from .domain import Candidate, Quote, Snapshot, ValidationReport


def evidence_records(snapshot: Snapshot) -> dict[str, int]:
    records = {f"job:{snapshot.job.id}": snapshot.job.version, f"policy:{snapshot.policy.id}": snapshot.policy.version}
    for kind, values in (("courier", snapshot.couriers), ("quote", snapshot.quotes), ("event", snapshot.events)):
        records.update({f"{kind}:{r.id}": r.version for r in values})
    return records


def required_evidence(snapshot: Snapshot, quote: Quote) -> tuple[str, ...]:
    records = evidence_records(snapshot)
    names = [f"job:{snapshot.job.id}", f"policy:{snapshot.policy.id}", f"quote:{quote.id}", f"courier:{quote.courier_id}"]
    events = [e for e in snapshot.events if e.job_id == snapshot.job.id]
    if events:
        latest = max(events, key=lambda e: (e.at_min, e.id))
        names.append(f"event:{latest.id}")
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
    latest = max(events, key=lambda e: (e.at_min, e.id)) if events else None
    if snapshot.job.custody != "depot" or latest is None or latest.custody != "depot": errors.append("custody")
    known = {f"{name}@{version}" for name, version in evidence_records(snapshot).items()}
    supplied = set(candidate.evidence_ids)
    if not set(required_evidence(snapshot, quote)).issubset(supplied) or not supplied.issubset(known): errors.append("evidence")
    return ValidationReport(valid=not errors, errors=tuple(errors))
