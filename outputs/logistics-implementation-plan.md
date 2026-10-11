# Logistics Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended by the skill) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved one-week logistics recovery prototype and preserve evidence of the builder's engineering judgment.

**Architecture:** One Python web application hosts a dispatcher interface and a bounded LangGraph recovery agent. Read-only tools retrieve synthetic logistics records; a separate application service validates proposals and commits approved assignments transactionally in SQLite. Persistent graph checkpoints and authoritative business records support restart and repeat-safe recovery.

**Tech Stack:** Python, FastAPI, Jinja2, Uvicorn, Pydantic, LangGraph, langgraph-checkpoint-sqlite, HTTPX, SQLite, pytest, python-multipart. Use a replay model for deterministic tests and an explicitly configured OpenRouter adapter for live inference. Resolve and lock compatible dependency versions in the isolated environment; the available local Python runtime is 3.14.8.

**Spec:** [Approved weekly design](week-one-logistics-plan.md). Copy it into the implementation repository as `outputs/week-one-logistics-plan.md`; copy this plan alongside it. Executors read both.

**Status:** Written for review on October 11, 2026. Design is approved; implementation-plan review and execution-method selection remain pending. This document contains planned tests, not passing test results.

## Global Constraints

- $35 total personal spending; $300 in currently active Google Cloud credits available for 90 days.
- 15 hours in ordinary weeks and 45–50 hours in the first week.
- Schedule 43 active builder hours, leaving 2–7 hours of contingency within the confirmed range.
- Reserve 10 of the 43 scheduled hours for the builder's own design review, diagnosis, results analysis, and evidence notes.
- One dispatcher, one depot, cancellation before pickup, one delivery job per incident, and one replacement courier for the complete job.
- Each incident allows at most six model calls and two revised proposals before escalation.
- Monetary values use integer cents; synthetic scenario time uses integer minutes from a fixed scenario start.
- The model cannot approve its own plan, write an assignment, issue arbitrary SQL, access credentials, or make arbitrary network requests.
- A changed quote, courier state, or proposal requires revalidation and a fresh approval.
- Approval consumption, capacity reservation, assignment creation, and the commit audit event share one business-database transaction.
- Initial model-credit checkout ceiling: $12 including fees, within the $35 overall ceiling; no automatic top-ups.
- Target 50 versioned synthetic cases across five groups, with 10 held out from prompt/workflow iteration. Report actual completed counts.
- Hosting is optional. No cloud resources, purchases, live courier integration, or account-registration system are required for the local milestone.
- Attribution, naturally occurring versus injected defects, before/after evidence, and sample sizes follow `AGENTS.md` and the engineering judgment tracker.

## Review Focus

1. Concurrent approved requests must neither duplicate an incident's assignment nor overbook a shared courier. Task 2 owns these tests.
2. Missing/foreign origins and forged approval fields must not authorize browser writes, while a valid authenticated request still works. Tasks 3 and 7 own these tests.
3. A quote for another job, invented evidence, or conflicting custody records must fail validation rather than be accepted because the model chose it. Tasks 1 and 4 own these tests.
4. Repeated or out-of-order pickup/delivery events must preserve an accurate history and never turn assignment into a false delivery claim. Task 6 owns these tests.
5. A restart, lost model response, or new graph invocation must not reset request limits, reuse stale approval, or repeat a committed reservation. Tasks 5 and 6 own these tests.

## Workspace and file boundaries

Proposed implementation root, created only after plan review: `outputs/logistics-recovery/` in this chat workspace. This is a new standalone Git repository; the chat directory currently has no repository. Invoke using-git-worktrees at execution time to assess isolation; do not attempt to create a managed worktree from a nonexistent parent repository. Keep the virtual environment and runtime databases in the chat's `work/` directory, outside user-facing outputs.

All paths in tasks are relative to the new repository. Verification commands assume its virtual environment is active and the working directory is the repository root. The executor must use that environment's interpreter, not install into the global Python environment. Set `LOGISTICS_DATA_DIR` to the private runtime directory; ignore `.env`, credentials, databases, generated caches, and machine-local paths in Git.

| Files | Responsibility |
|---|---|
| `pyproject.toml`, `requirements.lock`, `.gitignore` | Packaging, tested dependency versions, private-file exclusions |
| `src/logistics_recovery/domain.py`, `policy.py`, `baseline.py` | Typed records, pure feasibility rules, cheapest-feasible baseline |
| `src/logistics_recovery/repository.py`, `assignments.py` | Authoritative records, approvals, atomic writes and event transitions |
| `src/logistics_recovery/config.py`, `auth.py`, `web.py` | Private configuration, authenticated requests, routes and rendering |
| `src/logistics_recovery/templates/list.html`, `detail.html` | Two escaped dispatcher views |
| `src/logistics_recovery/tools.py`, `model.py`, `workflow.py` | Read-only tool dispatch, model adapters, bounded persistent graph |
| `src/logistics_recovery/evaluation.py`, `cli.py` | Scenario loading, replay/live runs, counts, exports and demo setup |
| `tests/conftest.py`, task-specific test files | Synthetic factories, isolated storage, HTTP/model fakes, behavioral checks |
| `fixtures/development.jsonl`, `heldout.jsonl`, `manifest.json` | Versioned scenarios and expected outcomes, never model context |
| `outputs/engineering-judgment-tracker.md`, both tracking CSVs | Canonical project evidence, carried from this chat |
| `outputs/week-one-logistics-plan.md`, `logistics-implementation-plan.md`, `AGENTS.md` | Approved design, executable plan, tracking rules |
| `README.md`, `docs/threat-model.md`, `docs/results.md`, `docs/case-studies.md` | Setup, scope, measured evidence, confirmed contributions |

After migration, repository tracking files are canonical. Mirror them back to the chat's original outputs at meaningful milestones. Do not maintain two independently edited logs.

## Contracts used by the tasks

Define the following immutable Pydantic records in Task 1. Reject extra fields; IDs are nonempty strings. Integer fields are strict integers: bools and floats must not silently become money, time, capacity, or versions. Counts, costs, travel time and versions are nonnegative; `parcel_count` is positive.

- `Job(id, parcel_count, deadline_min, custody, version)`; custody is `depot`, `unknown`, or `in_transit`.
- `Courier(id, free_capacity, available, version)`.
- `Quote(id, job_id, courier_id, cost_cents, travel_min, expires_at_min, version)`.
- `Policy(id, max_cost_cents, version)`.
- `IncidentEvent(id, job_id, kind, at_min, custody, version, note)`; note is untrusted text, limited to 1,000 characters.
- `Snapshot(incident_id, incident_version, now_min, job, couriers, quotes, policy, events)`; courier, quote and event collections are tuples.
- `Candidate(quote_id, evidence_ids, summary)`; evidence IDs are a tuple and summary is limited to 1,000 characters. Referenced records use `kind:id@version`, such as `quote:q1@1`.
- `ValidationReport(valid, errors)`; errors is a tuple of stable codes.
- `Proposal(id, incident_id, incident_version, candidate, observed_versions, revision)`; observed versions are immutable `(record_id, version)` pairs. Its server-generated ID and stored payload are immutable.
- `Approval(id, proposal_id, incident_version, operator_id, consumed)`.
- `Assignment(id, incident_id, proposal_id, courier_id, operation_id, status)`; status is `assigned`, `picked_up`, or `delivered`.
- `Operator(id)` is obtained from server authentication, never client-supplied identity.
- `DomainError(code, message)` is the service error contract; its string includes the stable code and a sanitized message, with no credentials or model keys.
- `RunView(status, proposal, assignment, model_calls, revisions, detail)`; status is `awaiting_approval`, `assigned`, `rejected`, or `escalated`.
- `WorkflowRunner` protocol has `start(incident_id: str) -> RunView` and `resume(incident_id: str, proposal_id: str) -> RunView`. It lives with the shared contracts so web does not import workflow implementation.

Additional records defined in Task 4: `ToolCall(id, name, arguments)`, `ModelTurn(kind, tool_calls, candidate, reason, usage)`, `ModelContext(incident_id, call_index, messages)`, and `Usage(prompt_tokens, completion_tokens, cost_usd)`. Call index is the one-based request-attempt counter reserved in business storage. Missing billed cost is null, not zero. Turn kind is `tools`, `proposal`, or `escalate`; a terminal proposal cannot be mixed with read-tool calls in one turn. JSON messages and arguments must be bounded and validated before use.

Task 8 defines `ExpectedOutcome(status, allowed_courier_ids, oracle_marker)`, `Injection(kind, trigger, payload)`, `Scenario(id, category, split, initial_snapshot, scripted_turns, injections, expected: ExpectedOutcome)` and `CaseResult(case_id, mode, status, constraint_violations, unauthorized_attempts, unauthorized_commits, valid_attempts, valid_successes, replay_cases, duplicate_assignments, eligible_recoveries, successful_recoveries, model_calls, usage, latency_ms)`. Expected status is `assigned`, `escalated`, or `rejected`; the oracle marker is an expected-answer-only sentinel. Injection kind is one of `courier_unavailable`, `advance_clock`, `lose_commit_response`, `replay_commit`, `pickup`, `delivery`, `http_unauthorized`, or `tamper_proposal`; validate each kind's payload fields and apply it only within the isolated scenario runner.

Shared fixture values: incident `i1`, version 1, scenario time 0; job `j1` has 3 parcels, deadline 60 and custody `depot`; courier `c1` has capacity 3 and is available; quote `q1` costs 1,200 cents, takes 30 minutes, and expires at minute 10; policy `p1` maximum is 1,500 cents. All record versions are 1. Cancellation event `e1` confirms depot custody. `q2` is a valid 1,400-cent alternative using available courier `c2`, capacity 3, travel time 30 and expiry 10. `valid_candidate` references q1 and all five current evidence records; `full_snapshot` sets c1 capacity to 2. Repository reads order couriers by ID. These are test data, not universal business policy defaults. Every scenario supplies its own policy.

## Task 1: Rules, typed records and fair baseline — 6 hours, Day 1

**Files:** Create packaging files, `domain.py`, `policy.py`, `baseline.py`, `tests/conftest.py`, `tests/test_policy.py`, and initial `fixtures/development.jsonl`. Copy the design, plan, tracking files, and AGENTS instructions into the repository during setup.

**Interfaces:** Produces `validate_candidate(candidate: Candidate, snapshot: Snapshot) -> ValidationReport` and `choose_baseline(snapshot: Snapshot) -> Candidate | None`. The baseline receives the same records and uses the same feasibility rules as the agent.

- [ ] Prepare the isolated repository and project environment under the approved execution method; resolve dependencies and capture their exact working versions. No paid model calls.
- [ ] Write the policy tests using the shared fixture. Include these assertions, plus rejection of negative/float/bool money, expired quotes at minute 10, quote/job mismatch, unknown or conflicting custody, and invented/missing evidence IDs.

```python
def test_valid_candidate(feasible_snapshot, valid_candidate):
    assert validate_candidate(valid_candidate, feasible_snapshot).valid

def test_insufficient_capacity(full_snapshot, valid_candidate):
    report = validate_candidate(valid_candidate, full_snapshot)
    assert not report.valid
    assert "capacity" in report.errors

def test_baseline_is_cheapest_feasible(feasible_snapshot):
    assert choose_baseline(feasible_snapshot).quote_id == "q1"
```

- [ ] Run `python -m pytest tests/test_policy.py -q`; confirm a missing implementation or the intended behavioral failure, not an unrelated environment error.
- [ ] Implement the records and pure rules. Arrival is `now_min + travel_min`; arrival equal to the deadline is allowed, but a quote is expired when `now_min >= expires_at_min`. Require job and current custody evidence to agree that parcels remain at the depot. Require current job, courier, quote, policy and relevant event evidence. Break equal-cost baseline ties by quote ID.
- [ ] Run `python -m pytest tests/test_policy.py -q`; expected all policy tests pass. Record the builder's actual reasoning about authoritative evidence if supplied.
- [ ] Commit: `git add pyproject.toml requirements.lock .gitignore src tests fixtures outputs AGENTS.md` then `git commit -m "feat: define logistics policy and baseline"`.

## Task 2: Approval and atomic assignment service — 4 hours, Day 2

**Files:** Create `repository.py`, `assignments.py`, and `tests/test_assignments.py`.

**Interfaces:** Consumes Task 1 records/rules. Produces `Repository(path: Path)` with `seed(snapshot: Snapshot) -> None`, `snapshot(incident_id: str) -> Snapshot`, `assignment(incident_id: str) -> Assignment | None`, `history(incident_id: str) -> list[dict]`, and `stats(incident_id: str) -> dict[str, int]`. Produces `AssignmentService(repository: Repository, fault_hook: Callable[[str], None] | None = None)` with `propose(incident_id: str, candidate: Candidate, revision: int = 0) -> Proposal`, `approve(proposal_id: str, expected_version: int, operator: Operator) -> Approval`, `reject(proposal_id: str, operator: Operator) -> None`, and `commit(proposal_id: str, operator: Operator) -> Assignment`. Fault hooks are test-only callbacks at `after_capacity_update` and `after_commit`; never expose them through configuration, model tools, or HTTP. Repository owns its connections; request threads do not share an unguarded SQLite connection.

- [ ] Write tests for missing approval, proposal immutability, version change, replay, transaction rollback, and two concurrent incidents competing for one courier. Use separate repository instances and a bounded barrier for concurrency. Pin these outcomes:

```python
def test_assignment_requires_approval(service, proposal, operator):
    with pytest.raises(DomainError, match="approval_required"):
        service.commit(proposal.id, operator)

def test_replay_does_not_reserve_twice(service, approved, operator, repo):
    first = service.commit(approved.proposal_id, operator)
    assert service.commit(approved.proposal_id, operator).id == first.id
    assert repo.stats(first.incident_id)["assignments"] == 1
    assert repo.stats(first.incident_id)["commit_events"] == 1
    assert repo.snapshot(first.incident_id).couriers[0].free_capacity == 0
```

- [ ] Run `python -m pytest tests/test_assignments.py -q`; confirm the expected red tests.
- [ ] Implement parameterized SQL, foreign keys, immutable proposals, recorded approvals, unique incident assignments, and a stable operation ID derived from the incident. Use a transaction that takes the write lock before rechecking facts. On a repeated commit for the same proposal, return its existing assignment; a different proposal for an already assigned incident returns `assignment_conflict`. A failed transaction reserves no capacity, consumes no approval, and leaves no commit audit event.
- [ ] Run `python -m pytest tests/test_policy.py tests/test_assignments.py -q`; expected all pass, including exactly one winner for the shared-capacity race. Preserve actual defect findings with their finder and evidence.
- [ ] Commit: `git add src/logistics_recovery/repository.py src/logistics_recovery/assignments.py tests/test_assignments.py` then `git commit -m "feat: enforce approval and atomic assignment"`.

## Task 3: Authenticated dispatcher interface — 3 hours, Day 2

**Files:** Create `config.py`, `auth.py`, `web.py`, both templates, and `tests/test_web.py`.

**Interfaces:** Consumes Task 1 WorkflowRunner and RunView contracts. Produces `Settings.from_env() -> Settings` with data directory, configured origin, dispatcher username/password, mode (`replay` or `live`), optional provider key/model, request timeout and context/output limits. Produces `authenticate(username: str, password: str, settings: Settings) -> Operator` and `create_app(settings: Settings, service: AssignmentService, workflow: WorkflowRunner | None = None) -> FastAPI`. Task 5 supplies the runner implementation. Before that integration, investigation is unavailable, while approved baseline proposals can be demonstrated.

- [ ] Write HTTP tests: unauthenticated incident access is 401; an approved, authenticated commit from the configured origin succeeds; missing/foreign Origin is 403; unknown incident is 404; a forged `approved=true` field is 422; service conflicts are 409. Include invalid credential controls and an HTML note containing `<script>` that renders escaped.

```python
def test_direct_commit_cannot_bypass_approval(client, auth, origin, proposal):
    response = client.post(
        f"/incidents/{proposal.incident_id}/commit",
        json={"proposal_id": proposal.id}, auth=auth, headers=origin,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "approval_required"
```

- [ ] Run `python -m pytest tests/test_web.py -q`; confirm red behavior.
- [ ] Implement authenticated `GET /`, `GET /incidents/{id}`, and protected POST routes `/incidents/{id}/investigate`, `/decision`, and `/commit`. Decision fields are only `proposal_id`, `incident_version`, and `decision` (`approve` or `reject`); commit accepts only `proposal_id`. Check that proposal and URL incident match. Support equivalent typed form/JSON input for these same routes. State-changing requests require the exact configured Origin and server-derived Operator. Render autoescaped templates, compare UTF-8 credential bytes in constant time, return sanitized errors, and keep secrets out of views and logs. Serve locally on loopback with one worker; remote operation requires HTTPS and explicit private configuration.
- [ ] Run `python -m pytest tests/test_web.py tests/test_assignments.py -q`; expected all pass with both denied and successful action controls.
- [ ] Commit: `git add src/logistics_recovery/config.py src/logistics_recovery/auth.py src/logistics_recovery/web.py src/logistics_recovery/templates tests/test_web.py` then `git commit -m "feat: add protected dispatcher review interface"`.

## Task 4: Read-only tools and model adapters — 3 hours, Day 3

**Files:** Create `tools.py`, `model.py`, and `tests/test_tools.py`, `tests/test_model.py`.

**Interfaces:** Consumes Repository and Task 1 records. Produces `ToolRegistry(repository: Repository).execute(incident_id: str, call: ToolCall) -> dict`, `ModelAdapter.next_turn(context: ModelContext, tools: list[dict]) -> ModelTurn`, `ReplayModel(scripts: dict[str, tuple[ModelTurn, ...]])`, and `OpenRouterModel(settings: Settings, client: httpx.Client)`. Replay scripts are keyed by incident and indexed by the persisted request-attempt counter; they do not share a mutable global turn queue between incidents. Define the model records and protocol in `model.py`; web only depends on Task 1 WorkflowRunner/RunView, avoiding circular imports.

- [ ] Write tests proving the allowed names are exactly `get_order`, `get_couriers`, `get_quotes`, `get_policy`, and `get_events`; reject an unknown tool, extra arguments, another incident's quote, and inputs that attempt SQL/file/network access. Test provider response parsing with mocked HTTP, no live network, and fake key sentinels.

```python
def test_agent_cannot_dispatch_commit(registry, tool_call):
    call = tool_call(name="commit_assignment", arguments={})
    with pytest.raises(DomainError, match="tool_not_allowed"):
        registry.execute("i1", call)
```

- [ ] Run `python -m pytest tests/test_tools.py tests/test_model.py -q`; confirm intended failures.
- [ ] Implement incident-scoped reads and schemas. `get_quotes` can optionally select courier IDs but cannot select another job. Parse real provider tool calls; terminal `propose_recovery` and `escalate` declarations create typed model output and never enter the business tool dispatcher. Reject mixed terminal/read responses, malformed arguments, invented fields, and absent usage values without assuming success. Use fixed OpenRouter endpoint, 30-second timeout, no automatic HTTP retries, at most five read calls in a turn, 24,000 characters of serialized model context, and 600 requested output tokens. Escalate on oversized context instead of silently discarding evidence. Record summaries, tool results and usage, not hidden chain-of-thought. Display replay/live mode explicitly.
- [ ] Run `python -m pytest tests/test_tools.py tests/test_model.py -q`; expected all pass. Live mode remains disabled until an actual key/model and verified budget/capability settings are available.
- [ ] Commit: `git add src/logistics_recovery/tools.py src/logistics_recovery/model.py src/logistics_recovery/domain.py tests/test_tools.py tests/test_model.py` then `git commit -m "feat: add restricted tools and model adapters"`.

## Task 5: Bounded LangGraph workflow — 4 hours, Day 3

**Files:** Create `workflow.py`, `tests/test_workflow.py`; integrate `web.py` with WorkflowRunner. Extend repository with budget methods.

**Interfaces:** Consumes ModelAdapter, ToolRegistry and AssignmentService. Produces `Workflow(repository: Repository, service: AssignmentService, model: ModelAdapter, checkpoint_path: Path)`, implementing `start(incident_id: str) -> RunView`, `resume(incident_id: str, proposal_id: str) -> RunView`, and `recover(incident_id: str) -> RunView`. Repository adds `reserve_model_call(incident_id: str, limit: int = 6) -> int` and `reserve_proposal_attempt(incident_id: str, limit: int = 3) -> int`; exhausted budgets raise `budget_exhausted`. Counters persist in business storage before the corresponding external attempt, so crashes cannot reset them.

- [ ] Write scripted-model tests for conditional tool retrieval, a valid proposal pausing without assignment, resume after app recreation, rejected proposals, malformed model output, six failed calls, and three unsuccessful draft attempts. Assert an unknown/missing fact leads to retrieval or escalation, never a fabricated assignment.

```python
def test_pause_survives_restart(workflow_factory, repo, operator):
    paused = workflow_factory().start("i1")
    assert paused.status == "awaiting_approval"
    assert repo.assignment("i1") is None
    service = workflow_factory().service
    service.approve(paused.proposal.id, paused.proposal.incident_version, operator)
    result = workflow_factory().resume("i1", paused.proposal.id)
    assert result.status == "assigned"

def test_call_limit_survives_restart(failing_workflow_factory, repo):
    failing_workflow_factory().start("i1")
    result = failing_workflow_factory().recover("i1")
    assert result.status == "escalated"
    assert repo.stats("i1")["model_calls"] == 6
```

- [ ] Run `python -m pytest tests/test_workflow.py -q`; confirm intended failures.
- [ ] Implement investigate/tools/validate/interrupt/recheck/commit routing with a durable SQLite saver and stable incident thread ID. Count six model attempts including failed requests; allow the initial draft plus two revisions. Approval/resume input carries a proposal reference, not a trusted boolean. The commit service rereads the recorded approval and current versions. Start/resume/recover first return the authoritative existing assignment when already committed. Reject route mismatches and concurrent workflow invocations for the same incident; the SQLite budget and assignment protections remain authoritative. Graph nodes perform no unguarded side effects before an interrupt. Hook approved/rejected decisions into the interface and display calls, evidence, validation errors, and status.
- [ ] Run `python -m pytest tests/test_workflow.py tests/test_web.py -q`; expected all pass with no network. Demonstrate one complete replay case while labeling it a scripted simulation.
- [ ] Commit: `git add src/logistics_recovery/workflow.py src/logistics_recovery/repository.py src/logistics_recovery/domain.py src/logistics_recovery/web.py tests/test_workflow.py tests/test_web.py` then `git commit -m "feat: add bounded persistent recovery workflow"`.

## Task 6: Failure recovery and honest event state — 6 hours, Day 4

**Files:** Extend repository, service, workflow, and web; create `tests/test_recovery.py`.

**Interfaces:** Service adds `record_event(incident_id: str, event_id: str, kind: Literal['pickup', 'delivery'], operator: Operator) -> Assignment`. Repository adds `change_courier(courier_id: str, available: bool) -> None` and `advance_clock(incident_id: str, now_min: int) -> None`; related record versions increase, and simulated time cannot move backward. Use the Task 2 fault hook for transaction/response-loss tests. Clock advancement is controlled by the scenario runner, not the model or a public API; label the interface's displayed time as simulated. Simulated event POST `/incidents/{id}/events` accepts only `event_id` and `kind`, with the same authentication/origin protections. It is labeled simulation in the detail view.

- [ ] Write tests for state change after approval, failure before transaction commit, response loss after commit but before graph checkpoint, duplicate resume, repeated pickup/delivery, and delivery-before-pickup. Inject faults in isolated tests only.

```python
def test_stale_approval_cannot_book(service, approved, repo, operator):
    repo.change_courier("c1", available=False)
    with pytest.raises(DomainError, match="stale_proposal"):
        service.commit(approved.proposal_id, operator)
    assert repo.assignment("i1") is None

def test_lost_response_recovers_once(crashed_after_commit, workflow, repo):
    result = workflow.recover("i1")
    assert result.status == "assigned"
    assert repo.stats("i1")["assignments"] == 1
    assert repo.stats("i1")["commit_events"] == 1
```

- [ ] Run `python -m pytest tests/test_recovery.py -q`; verify the injected fault actually occurs and the checks detect incorrect behavior.
- [ ] Implement reconciliation from authoritative assignment records, stale-proposal invalidation and fresh-approval requirements. Event transitions are `assigned -> picked_up -> delivered`; a repeated event ID returns the existing state without another event or capacity mutation. A new out-of-order event raises `invalid_transition`. Assignment must not be labeled delivered before the valid delivery event. Graph restart must not repeat a successful business commit.
- [ ] Run `python -m pytest tests/test_assignments.py tests/test_workflow.py tests/test_recovery.py -q`; expected all pass. Record failures before and after a real correction; clearly label injected faults and agent-discovered findings.
- [ ] Commit: `git add src/logistics_recovery tests/test_recovery.py tests/test_web.py outputs` then `git commit -m "feat: recover safely from replay and interrupted commits"`.

## Task 7: Adversarial checks and threat model — 7 hours, Day 5

**Files:** Create `tests/test_adversarial.py`, `docs/threat-model.md`; modify only components implicated by a reproduced failure.

**Interfaces:** Uses existing HTTP routes, tool registry, service and model contracts. Adds no new privileges or production endpoints.

- [ ] Write attacks against the isolated application: no credentials, bad credentials, approval bypass, forged proposal/courier/policy fields, another incident's proposal, replayed stale approval, credential-like notes, prompt injection, escaped HTML, and secret-sentinel exposure in logs. Include valid authorized requests as controls. Use both a normal replay model and a deliberately adversarial model that proposes forbidden actions; do not call the latter a natural implementation mistake.

```python
def test_hostile_note_cannot_grant_approval(hostile_workflow, repo):
    result = hostile_workflow.start("i1")
    assert result.status in {"awaiting_approval", "escalated"}
    assert repo.assignment("i1") is None

def test_secret_sentinels_absent_from_logs(secret_config, exercised_app, caplog):
    assert secret_config.provider_key not in caplog.text
    assert secret_config.dispatcher_password not in caplog.text
```

- [ ] Run `python -m pytest tests/test_adversarial.py -q`; for attacks that already fail safely, confirm a known faulty test double would be caught. Never introduce an unsafe production implementation just to generate a red test.
- [ ] Correct only reproducible gaps; use systematic-debugging for unexpected failures. Document protected assets, entry points, read/write privileges, local/HTTPS scope, credential handling, and remaining limitations. Sanitized logs must omit authorization headers, private configuration and raw provider errors containing request secrets. Never treat prompt instructions as approval enforcement.
- [ ] Run `python -m pytest tests/test_adversarial.py tests/test_web.py tests/test_recovery.py -q`; expected all pass, with valid controls succeeding. Update attribution/event records only with observed findings and verification references.
- [ ] Commit: `git add src tests/test_adversarial.py docs/threat-model.md outputs` then `git commit -m "test: verify security boundaries and document threats"`.

## Task 8: Evaluation and comparable evidence — 6 hours, Day 6

**Files:** Create `evaluation.py`, `cli.py`, `tests/test_evaluation.py`, final fixture manifest and `docs/results.md`.

**Interfaces:** Produces `load_scenarios(path: Path) -> list[Scenario]`, `evaluate_case(case: Scenario, mode: Literal['baseline', 'replay', 'live'], model: ModelAdapter | None) -> CaseResult`, and `summarize(results: list[CaseResult]) -> dict`. The CLI entry point `logistics-recovery` supports `seed-demo`, `evaluate`, and `estimate`; export results to private runtime files first, then publish sanitized results in `docs/results.md` and the metric CSV.

- [ ] Write evaluator tests for known unsafe/safe runs, zero eligible denominators, missing cost, mode labeling, valid controls, comparison equality, and expected-answer exclusion from ModelContext. Add schema validation for Scenario injections: only named changes/faults, never executable code. For each category create 8 development cases; after workflow/prompt freeze create 2 held-out cases per category. Record manifest version and hashes.

```python
def test_no_denominator_is_unmeasured(empty_results):
    assert summarize(empty_results)["recovery_rate"] is None

def test_expected_answers_never_enter_model_input(spy_model, scenario):
    evaluate_case(scenario, "replay", spy_model)
    for context in spy_model.contexts:
        payload = json.dumps(context.messages, sort_keys=True)
        assert '"expected"' not in payload
        assert scenario.expected.oracle_marker not in payload
```

- [ ] Run `python -m pytest tests/test_evaluation.py -q`; confirm intended failures.
- [ ] Implement isolated per-case storage and the same read data, action service and deterministic constraints for baseline/replay/live. Count committed events rather than model claims. Export recovery, constraint violations, unauthorized commits/attempts, valid successes/attempts, replay duplicates, token usage, latency, and costs with their case set and mode. Snapshot build revision, model ID/configuration, manifest, raw counts and sample sizes. Measure active review time only from actual recorded input; never derive it from tool elapsed time.
- [ ] Run `python -m pytest tests/test_evaluation.py -q`, then `logistics-recovery evaluate --mode baseline --split development` and `logistics-recovery evaluate --mode replay --split development`; expected truthful reports for all completed cases. Before live runs, verify model capabilities, current rates, key credit limit and batch estimate; stop if the key is missing or budget is insufficient, while completing offline verification. No purchase or live call is implicit in the estimate command. Run held-out evaluation once frozen; if its failures drive changes, relabel those cases as development and create a new held-out set before further held-out claims.
- [ ] Commit: `git add src/logistics_recovery/evaluation.py src/logistics_recovery/cli.py tests/test_evaluation.py fixtures docs/results.md outputs` then `git commit -m "feat: evaluate recovery and safety with reproducible cases"`.

## Task 9: Reproducible delivery and résumé evidence — 4 hours, Day 7

**Files:** Create `README.md`, `docs/case-studies.md`, `docs/demo-script.md`; update packaging, results and tracking documents only as evidence requires.

**Interfaces:** CLI `seed-demo` initializes synthetic incidents and the private runtime paths; `python -m uvicorn logistics_recovery.web:build_application --factory --host 127.0.0.1 --port 8000 --workers 1` launches the configured app. Define `build_application(settings: Settings | None = None) -> FastAPI` in `web.py`; when settings is omitted, use Settings.from_env. Wire repository, service, selected model and checkpointed workflow to create_app. Importing modules must not make network calls or write business records; private storage/schema initialization belongs to explicit demo setup or application startup.

- [ ] Write `tests/test_smoke.py` proving app construction causes no network requests and does not commit assignments. Its replay demonstration must reach approved assignment and show accurate history. Use fake/private test credentials, never a committed real configuration.

```python
def test_app_factory_wires_replay_without_business_effects(settings, repo, auth, no_network):
    app = build_application(settings)
    with TestClient(app) as client:
        response = client.get("/incidents/i1", auth=auth)
    assert response.status_code == 200
    assert "Scripted replay" in response.text
    assert repo.assignment("i1") is None
    assert repo.stats("i1")["commit_events"] == 0
```
- [ ] Run that smoke test with `python -m pytest tests/test_smoke.py -q`; confirm the intended red condition before wiring the entry point.
- [ ] Implement the application factory and write clean-environment installation, locked dependencies, configuration, commands, tests, schema limitations, and safe local demonstration instructions. Mode labels are `Scripted replay` and `Live model`; never label scripted behavior as actual LLM inference. Document how to create private credentials without publishing them. Prepare a 3-minute script showing investigation, approval, a blocked action or replay, and evidence. Store a recording only if a recording tool is available and authorized; the runnable demo and script remain deliverables. Draft résumé wording from actual results and confirmed user contributions, with missing claims omitted.
- [ ] Run `python -m pytest -q` once against the final state. Perform installation and replay smoke run from a fresh environment with the lock file, confirming the interface and history. Inspect sanitized outputs and the contribution ledger. Record exact commands/results; if a check fails, resolve it before declaring the milestone complete. Cloud hosting is optional and requires a current estimate, credit coverage, spending controls and teardown plan before provisioning; do not spend the week's final hours on it while required checks remain open.
- [ ] Commit: `git add README.md docs src/logistics_recovery/web.py tests/test_smoke.py pyproject.toml requirements.lock outputs` then `git commit -m "docs: deliver reproducible demo and portfolio evidence"`.

## Execution and evidence checkpoints

The task allocations total 43 hours; they include 10 hours of builder review/evidence work and leave 2–7 hours of buffer. Tasks 1/2/3 map to Days 1/2; Tasks 4/5 to Day 3; Tasks 6–9 to Days 4–7. These are planned allocations, not already spent hours.

At each consequential boundary, summarize what changed and its verification. Invite a specific builder review when personal judgment is relevant, rather than crediting generic continuation as diagnosis. Record confirmed reasoning and actual corrections, including before/after test output and revision links. No quota of caught defects, no invented review time, and no unqualified security or synthetic business-impact claims.

## Self-review record

- Spec coverage: core workflow and constraints map to Tasks 1–6; authentication and adversarial checks to 3/7; baseline, held-out cases and cost reporting to 1/8; reproducibility and résumé evidence to 9. Optional hosting has an explicit pre-provision gate.
- Interfaces: task-owned contracts are defined above or in their Interfaces blocks. Task 1 owns shared RunView and WorkflowRunner, Task 4 owns the model protocol, and imports do not cycle through the web layer. Test hooks are isolated from production entry points.
- Review Focus: all five named failure classes have owning test tasks. Valid-action controls accompany security rejection tests.
- Proportion: bodies are left to implementation; examples pin outcomes. This plan defines work and planned checks, not completed implementation evidence.

## Review and execution selection

Please review this plan before implementation. Recommended for this budget and tightly connected application: **Native**, where the assistant implements tasks here and a fresh reviewer checks the completed branch. Alternative: **Subagent-driven**, with a fresh implementer and reviewer for each task plus a final branch review; this uses more context and coordination.

After the user approves this written plan and selects a method, invoke the corresponding Superpowers execution skill and start Task 1. No repository, dependencies, product code, paid model calls, or cloud resources have been created by writing this plan.

## Primary implementation references

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): persistent pauses, resume behavior and repeat-safe node work.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpoint storage and workflow state.
- [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling): the client validates and executes requested tools.
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs): provider/model capability must be checked; local validation remains required.
- [FastAPI HTTP Basic](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/): credential dependency and constant-time comparison.
- [Uvicorn settings](https://www.uvicorn.org/settings/): application-factory launch with a loopback host and one worker.
