import copy

import pytest
from pydantic import ValidationError


def check(data, candidate):
    from logistics_recovery.domain import Snapshot
    from logistics_recovery.policy import validate_candidate
    return validate_candidate(candidate, Snapshot.model_validate(data))


def test_valid_candidate(snapshot_data, valid_candidate):
    assert check(snapshot_data, valid_candidate).valid


@pytest.mark.parametrize("change,error", [
    ("capacity", "capacity"), ("availability", "availability"),
    ("deadline", "deadline"), ("budget", "budget"),
    ("expired", "quote_expired"), ("wrong_job", "quote_job"),
    ("unknown_custody", "custody"), ("conflicting_custody", "custody"),
])
def test_unsafe_candidate_rejected(snapshot_data, valid_candidate, change, error):
    data = copy.deepcopy(snapshot_data)
    if change == "capacity": data["couriers"][0]["free_capacity"] = 2
    if change == "availability": data["couriers"][0]["available"] = False
    if change == "deadline": data["job"]["deadline_min"] = 29
    if change == "budget": data["policy"]["max_cost_cents"] = 1199
    if change == "expired": data["now_min"] = 10
    if change == "wrong_job": data["quotes"][0]["job_id"] = "j2"
    if change == "unknown_custody": data["job"]["custody"] = "unknown"
    if change == "conflicting_custody": data["events"][0]["custody"] = "in_transit"
    report = check(data, valid_candidate)
    assert not report.valid
    assert error in report.errors


def test_arrival_exactly_at_deadline_allowed(snapshot_data, valid_candidate):
    snapshot_data["job"]["deadline_min"] = 30
    assert check(snapshot_data, valid_candidate).valid


def test_missing_and_invented_evidence_rejected(snapshot_data, valid_candidate):
    for evidence in [("quote:q1@1",), (*valid_candidate.evidence_ids, "quote:made-up@1")]:
        report = check(snapshot_data, valid_candidate.model_copy(update={"evidence_ids": evidence}))
        assert not report.valid
        assert "evidence" in report.errors


@pytest.mark.parametrize("value", [-1, 1200.5, True])
def test_invalid_money_rejected(snapshot_data, value):
    from logistics_recovery.domain import Snapshot
    snapshot_data["quotes"][0]["cost_cents"] = value
    with pytest.raises(ValidationError):
        Snapshot.model_validate(snapshot_data)


def test_frozen_records_and_extra_fields(snapshot_data):
    from logistics_recovery.domain import Snapshot
    snapshot = Snapshot.model_validate(snapshot_data)
    with pytest.raises(ValidationError): snapshot.job.parcel_count = 10
    snapshot_data["job"]["approved"] = True
    with pytest.raises(ValidationError): Snapshot.model_validate(snapshot_data)


def test_baseline_cheapest_feasible(snapshot_data):
    from logistics_recovery.domain import Snapshot
    from logistics_recovery.baseline import choose_baseline
    assert choose_baseline(Snapshot.model_validate(snapshot_data)).quote_id == "q1"
    snapshot_data["couriers"][0]["available"] = False
    assert choose_baseline(Snapshot.model_validate(snapshot_data)).quote_id == "q2"
    snapshot_data["couriers"][1]["available"] = False
    assert choose_baseline(Snapshot.model_validate(snapshot_data)) is None
