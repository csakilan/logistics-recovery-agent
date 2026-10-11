import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import httpx

from .config import Settings
from .domain import DomainError, Snapshot
from .evaluation import evaluate_case, load_scenarios, summarize
from .model import OpenRouterModel
from .repository import Repository


def planning_estimate(cases: int, input_rate: float, output_rate: float, input_tokens: int = 12000) -> dict:
    attempts = cases * 6
    return {"cases": cases, "max_model_attempts": attempts, "assumed_input_tokens_per_attempt": input_tokens, "max_output_tokens_per_attempt": 600, "input_usd_per_million": input_rate, "output_usd_per_million": output_rate, "planning_cost_usd": round(attempts*(input_tokens*input_rate+600*output_rate)/1000000, 6), "requests_sent": 0, "limitation": "Planning assumption, not a provider quote or guaranteed bill. Verify current tool support, rates and provider spending limit before live use."}


def seed_demo(repository: Repository, fixtures: Path):
    cases = load_scenarios(fixtures)
    chosen = [next(c for c in cases if c.category == name) for name in ("normal", "infeasible")]
    for i, case in enumerate(chosen, 1):
        data = case.snapshot.model_dump(mode="json")
        data["incident_id"] = f"demo-{i}"; data["job"]["id"] = f"job-demo-{i}"
        for quote in data["quotes"]:
            quote["id"] += f"-demo-{i}"; quote["job_id"] = data["job"]["id"]
        for event in data["events"]: event["job_id"] = data["job"]["id"]
        # The infeasible demo uses its own spending limit, while couriers share depot capacity.
        if i == 2:
            data["policy"]["id"] = "policy-demo-2"; data["policy"]["max_cost_cents"] = 100
        if data["incident_id"] not in repository.list_incidents(): repository.seed(Snapshot.model_validate(data))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synthetic logistics recovery demo and evaluation")
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).resolve().parents[2]/"fixtures")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed-demo")
    estimate = commands.add_parser("estimate")
    estimate.add_argument("--cases", type=int, default=50)
    estimate.add_argument("--input-rate", type=float, required=True)
    estimate.add_argument("--output-rate", type=float, required=True)
    estimate.add_argument("--input-tokens", type=int, default=12000)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--mode", choices=("baseline", "replay", "live"), required=True)
    evaluation.add_argument("--split", choices=("development", "held-out", "all"), default="development")
    evaluation.add_argument("--output", type=Path, default=Path(os.environ.get("LOGISTICS_DATA_DIR", "work/runtime"))/"evaluation.json")
    evaluation.add_argument("--live-budget-usd", type=float)
    evaluation.add_argument("--input-rate", type=float)
    evaluation.add_argument("--output-rate", type=float)
    evaluation.add_argument("--confirmed-provider-settings", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "estimate":
        if min(args.cases, args.input_tokens, args.input_rate, args.output_rate) < 0: parser.error("Use nonnegative planning inputs")
        print(json.dumps(planning_estimate(args.cases, args.input_rate, args.output_rate, args.input_tokens), indent=2)); return
    if args.command == "seed-demo":
        settings = Settings.from_env(); seed_demo(Repository(settings.data_dir/"business.sqlite"), args.fixtures)
        print("Synthetic demo incidents seeded; existing incidents retained."); return
    cases = [c for c in load_scenarios(args.fixtures) if args.split == "all" or c.split == args.split]
    settings = None; client = None; model = None
    try:
        if args.mode == "live":
            if not args.confirmed_provider_settings or args.live_budget_usd is None or not 0 < args.live_budget_usd <= 35 or args.input_rate is None or args.output_rate is None or min(args.input_rate, args.output_rate) < 0:
                parser.error("Live evaluation requires verified provider settings, rates and an explicit remaining budget of at most $35")
            estimate = planning_estimate(len(cases), args.input_rate, args.output_rate)
            if estimate["planning_cost_usd"] > args.live_budget_usd: parser.error("Planning estimate exceeds remaining live budget")
            try: settings = Settings.from_env()
            except (DomainError, ValueError): parser.error("Private live model configuration is missing or invalid")
            if settings.mode != "live": parser.error("Explicitly set LOGISTICS_MODE=live")
            client = httpx.Client(); model = OpenRouterModel(settings, client)
        results = [evaluate_case(case, args.mode, model) for case in cases]
        try:
            build = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
        except (OSError, subprocess.CalledProcessError): build, dirty = "unknown", None
        source_root = Path(__file__).parent
        source_hash = hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in sorted(source_root.glob("*.py")))).hexdigest()
        report = {"build_ref": build, "working_tree_dirty": dirty, "source_sha256": source_hash, "manifest": json.loads((args.fixtures/"manifest.json").read_text()), "split": args.split, "model_config": {"mode": args.mode, "model_id": settings.model_id if settings else None, "max_attempts": 6, "max_drafts": 3, "max_output_tokens": 600}, "summary": summarize(results), "cases": [r.model_dump(mode="json") for r in results]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps({"output": str(args.output), **report["summary"]}, indent=2))
    finally:
        if client: client.close()


if __name__ == "__main__": main()
