# SDD ledger — plan: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/outputs/logistics-recovery/outputs/logistics-implementation-plan.md

Execution approved October 11, 2026: Native. Initial branch base: e0af590.
Isolation: new standalone repository on feature/week-one as approved; no parent repository or worktree existed.

Pre-flight: Task 1 → 2: immutable records and validation match service contracts.
Pre-flight: Task 1 → 3: RunView/WorkflowRunner live in shared domain contracts; no web/workflow cycle.
Pre-flight: Task 2 → 3: service approval/commit signatures match routes.
Pre-flight: Tasks 1/2 → 4: snapshot and scoped repository match tool dispatch.
Pre-flight: Tasks 2/4 → 5: request counters are business-storage authority; replay index is persisted.
Pre-flight: Tasks 2/5 → 6: commit is authoritative when checkpoints lag; fault-injection interface conflicts with test-only-method rule.
Pre-flight: Tasks 3/4/6 → 7: adversarial tests operate on the same routes/tools/service; no production attack hooks.
Pre-flight: Tasks 1/4/5/6 → 8: baseline and replay/live share policy/action service; oracle fields stay outside ModelContext.
Pre-flight: Tasks 3/5/8 → 9: factory wires approved interfaces; all network work is explicit.

Ruling: Use test-side connection/service wrappers for fault injection instead of adding fault_hook to production classes — the testing skill prohibits test-only production methods and the spec requires only observable recovery — cost if wrong: an injected fault may not represent the intended crash point; tests will witness the failure and verify database effects.

Task 1: in_progress.
Task 1: process correction: artifact generation used the global interpreter, which lacked pytest. A premature task-done line was removed; generation rerun with the project interpreter before commit. Identified/corrected by assistant, not user.
Task 1: complete (commits e0af590..0093ec8, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 16 passed in 0.02s)
Task 2: complete (commits 0093ec8..bb32c08, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 27 passed in 0.15s)
Task 3: complete (commits bb32c08..b42ecee, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 41 passed in 0.43s)
Task 4: complete (commits b42ecee..886645b, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 62 passed in 0.89s)
Task 5: complete (commits 886645b..c7048d1, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 73 passed in 1.33s)
Task 6: Ruling: Extend custody with delivered — valid simulated delivery needs an accurate final state required by the approved design — cost if wrong: callers expecting the original three-value enum must support one additional value.
Task 6: complete (commits c7048d1..261b348, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 85 passed in 1.57s)
Task 7: complete (commits 261b348..c0cdabb, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 104 passed in 2.01s)
Task 8: complete (commits c0cdabb..5bee21e, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 116 passed in 2.79s)
Task 9: complete (commits 5bee21e..63b0596, tests: /Users/ak/Documents/Codex/2026-10-09/a-lot-of-companies-are-now/work/venvs/logistics-recovery/bin/python -m pytest -q → 118 passed in 2.85s)
Final review: initial reviewer invocation interrupted by turn cancellation before any findings/report were returned; no reviewer remains active. Restarting the same required whole-branch review, not adding a second review/fix pass. Implementation HEAD unchanged at 63b0596.
Paused at the user's explicit request on October 11, 2026. All nine task commits are saved through 63b0596; working tree was clean at the pause checkpoint. Latest full verification: 118 passed. Required final independent review remains pending; interrupted reviewer returned no report, and its replacement has not been dispatched. No live requests, cloud resources or demo server are running from this work. Resume with final review; do not redo completed tasks.
Resumed at the user's explicit request on October 11, 2026. Fresh reviewer completed a read-only whole-branch review of e0af590..63b0596; 118 tests passed. Three Important findings accepted: stale-before-approval dead end, factory replay startup-state decisions, live protocol-case applicability. Re-grade: duplicate/misordered history is Important for the promised accurate incident evidence; malformed-provider AttributeError is Important for bounded sanitized failure handling. All five enter one regression-backed fix pass. No remaining Minor items after re-grade. No re-review will be dispatched.
Final: Ruling: Distributed workers, production authentication/TLS, migrations and real courier delivery guarantees remain outside this local one-worker prototype — the documented deployment does not provide them — cost if wrong: deploying as a production service without another review could break coordination or expose data.
Final: Ruling: Actual OpenRouter quality, compatibility and billed cost remain unmeasured — live credentials, model compatibility and provider spending controls have not been verified in this run — cost if wrong: a chosen live model may fail capability or budget expectations.
Final: Ruling: Deliver the verified editable repository installation without standalone wheel fixture bundling — this is the supported README setup — cost if wrong: a wheel-only installation will not find the external fixture files.
Final: Ruling: External/future-dated event ingestion remains outside the supported controlled simulator — generated events use the incident clock and no external feed is exposed — cost if wrong: unvetted external or synthetic fixtures could encode impossible chronology and require additional validation.
Final: Ruling: Exclude deterministic protocol-only fault cases from live model-quality evaluation instead of fabricating live model faults — these cases exercise client enforcement and a compliant provider may choose a valid plan — cost if wrong: skipped cases give no evidence of live-model robustness to adversarial output; separate adapter/replay checks are still necessary.
Final: fixed stale-before-approval dead end — test_stale_before_approval_can_reinvestigate RED→GREEN, suite 132/132.
Final: fixed startup-state replay decisions — test_factory_replay_uses_current_shared_capacity RED→GREEN, suite 132/132.
Final: fixed misleading live protocol grading — test_live_protocol_fault_cases_are_explicitly_not_applicable RED→GREEN, suite 132/132; skipped-case mode and denominator regression also RED→GREEN.
Final: fixed duplicate/misordered history — test_incident_history_has_one_event_in_operational_order RED→GREEN, suite 132/132.
Final: fixed malformed-provider response escape — test_malformed_provider_objects_use_sanitized_error and bounded workflow regression RED→GREEN, suite 132/132.
Final verification: fresh locked environment full suite 132 passed; four offline evaluation runs retained 50/50 expected outcomes per mode. No held-out result drove corrections. No live requests or cloud resources. All findings attributed to agents, not user.

Final: Ruling: Preserve feature/week-one locally without an integration menu — this new standalone repository has no separate base branch or configured remote and the user authorized a local prototype — cost if wrong: a later publication/integration request will need its own destination and setup.
Final handoff: full suite 132 passed in 2.97s after all corrections; both code and evidence retained. No deferred minors. All nine tasks, one completed independent review and its one fix pass are complete. No live inference or personal user diagnosis is claimed.
