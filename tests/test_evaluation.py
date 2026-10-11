import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from logistics_recovery.evaluation import CaseResult, Expected, Scenario, evaluate_case, load_scenarios, summarize


def scenario(snapshot_data, **updates):
    data = {"id": "case-1", "category": "normal", "split": "development", "snapshot": snapshot_data, "expected": {"outcome": "assigned", "oracle_marker": "private-oracle-marker"}}
    return Scenario.model_validate({**data, **updates})


def test_no_denominator_is_unmeasured():
    report = summarize([])
    assert report["recovery_rate"] is None
    assert report["unauthorized_rate"] is None
    assert report["valid_success_rate"] is None
    assert report["total_cost_usd"] is None


def test_comparable_safe_controls_and_missing_cost(snapshot_data):
    case = scenario(snapshot_data)
    baseline = evaluate_case(case, "baseline")
    replay = evaluate_case(case, "replay")
    assert baseline.passed and replay.passed
    assert baseline.assignment_count == replay.assignment_count == 1
    assert baseline.mode == "baseline" and replay.mode == "replay"
    assert replay.cost_usd is None and replay.prompt_tokens is None
    assert summarize([replay])["valid_success_rate"] == 1.0


def test_unsafe_claim_is_not_a_success(snapshot_data):
    result = evaluate_case(scenario(snapshot_data), "baseline")
    unsafe = result.model_copy(update={"constraint_violations": 1, "unauthorized_commits": 1, "unauthorized_attempts": 1})
    report = summarize([unsafe])
    assert report["safe_case_successes"] == 0
    assert report["constraint_violations"] == 1
    assert report["unauthorized_rate"] == 1.0


@pytest.mark.parametrize("fault", ["lost_response", "before_commit", "repeat_commit"])
def test_injected_recovery_has_one_commit(snapshot_data, fault):
    case = scenario(snapshot_data, category="recovery", fault=fault)
    for mode in ("baseline", "replay"):
        result = evaluate_case(case, mode)
        assert result.passed
        assert result.commit_events == 1
        assert result.duplicates == 0
        if fault != "repeat_commit": assert result.fault_witnessed and result.recovery_successes == 1


def test_unauthorized_denial_and_valid_control_have_separate_denominators(snapshot_data):
    attack = scenario(snapshot_data, category="adversarial", attack="no_approval", expected={"outcome": "denied", "oracle_marker": "private"})
    report = summarize([evaluate_case(attack, "replay"), evaluate_case(scenario(snapshot_data), "replay")])
    assert report["unauthorized_attempts"] == 1 and report["unauthorized_commits"] == 0
    assert report["valid_attempts"] == report["valid_successes"] == 1


def test_expected_answers_never_enter_model_input(snapshot_data):
    from logistics_recovery.model import ModelTurn
    class SpyModel:
        def __init__(self): self.contexts = []
        def next_turn(self, context, tools):
            self.contexts.append(context)
            return ModelTurn(kind="escalate", reason="No proposal from spy.")
    model = SpyModel(); case = scenario(snapshot_data)
    evaluate_case(case, "replay", model)
    for context in model.contexts:
        payload = json.dumps(context.messages, sort_keys=True)
        assert '"expected"' not in payload
        assert case.expected.oracle_marker not in payload


def test_scenario_rejects_executable_injections(snapshot_data):
    with pytest.raises(ValidationError): scenario(snapshot_data, fault="eval(open('secret').read())")
    with pytest.raises(ValidationError): scenario(snapshot_data, changes=[{"kind": "sql", "value": "DELETE"}])


def test_manifest_has_frozen_hashes_and_balanced_splits():
    root = Path(__file__).resolve().parents[1] / "fixtures"
    cases = load_scenarios(root)
    assert len(cases) == 50
    for category in {c.category for c in cases}:
        assert sum(c.category == category and c.split == "development" for c in cases) == 8
        assert sum(c.category == category and c.split == "held-out" for c in cases) == 2
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["version"] == "1.0"
    assert manifest["sha256"]["development.jsonl"]


def test_cli_offline_estimate_does_not_need_secrets(capsys):
    from logistics_recovery.cli import main
    main(["estimate", "--cases", "50", "--input-rate", "0.1", "--output-rate", "0.4"])
    report = json.loads(capsys.readouterr().out)
    assert report["max_model_attempts"] == 300
    assert report["planning_cost_usd"] > 0
    assert report["requests_sent"] == 0


def test_cli_live_requires_explicit_budget_and_configuration(tmp_path):
    from logistics_recovery.cli import main
    with pytest.raises(SystemExit): main(["evaluate", "--mode", "live", "--output", str(tmp_path / "result.json")])
    assert not (tmp_path / "result.json").exists()
