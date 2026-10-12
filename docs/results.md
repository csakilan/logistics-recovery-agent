# Offline results — October 11, 2026

Synthetic manifest 1.0: 40 development cases and 10 held-out parameter variants across normal, infeasible, stale, recovery and adversarial categories. Workflow/prompt freeze is recorded in fixtures/manifest.json. Held-out results did not drive changes to workflow or prompt. These cases are small synthetic variants, not representative production traffic.

The scripted agent uses deterministic retrieval/proposal scripts built from structured records; it does not measure an LLM’s ability to plan. The rules baseline and replay share business records, constraints, approval service, faults and action boundaries. The runner supplies simulated authorized dispatcher approval, including a new approval after stale data. Named protocol attacks are refused by the baseline without model calls; their model behavior is exercised only in replay.

| Measurement | Rules baseline | Scripted agent |
|---|---:|---:|
| Expected safe case outcome | 50 / 50 | 50 / 50 |
| Unauthorized commits / attempts | 0 / 5 | 0 / 5 |
| Recovered injected failures / eligible cases | 7 / 7 | 7 / 7 |
| Duplicate commit events / replay cases | 0 / 10 | 0 / 10 |
| Assigned / authorized commit cases | 27 / 31 | 27 / 31 |
| Constraint violations / evaluated cases | 0 / 50 | 0 / 50 |

Four of the 31 authorized commit cases changed to an infeasible state after approval and correctly escalated. Thus 50/50 expected outcomes does not mean all jobs were assigned. The baseline matched the scripted workflow; there is no demonstrated agent advantage or speedup. Replay executed 131 adapter attempts, not paid requests.

At this offline checkpoint, costs and tokens were null because the replay adapter supplies no usage and live inference had not run. Application API spend and Cloud consumption were $0; coding-assistant account usage is a separate unmeasured cost. Later live observations are documented separately in [live results](live-results.md). Production throughput and personal review minutes remain unmeasured.

Evidence includes per-case results, exact manifest hashes, code digest, pre-task build revision and dirty-tree flag in [baseline development](evidence/final-baseline-development.json), [baseline held-out](evidence/final-baseline-held-out.json), [replay development](evidence/final-replay-development.json), and [replay held-out](evidence/final-replay-held-out.json). Final rerun source digests were matched to committed correction build d4107c0. Original parent revisions and dirty flags remain in the reports; verified_commit_ref records the later hash match. The earlier Task 8 reports are retained as historical evidence. Latencies are local timings affected by concurrent runs, startup, SQLite and machine load; no comparative performance claim is made.

No live batch was attempted at this offline checkpoint. Later bounded development checks verified model metadata and the configured key limit before inference; see [live results](live-results.md). Cloud credits are unnecessary for local checks.

Independent review and fix verification: all five reported findings were corrected; 132 tests passed in both environments. The final offline rerun retained the table above. The four deterministic protocol-only fault cases are now explicitly not applicable to live model-quality comparison: scheduled, evaluated and skipped counts are separate, skips are neither passes nor failures, and those cases make no provider request. Adapter/replay tests still cover their enforcement. No held-out failure drove a workflow/prompt revision. See [review evidence](final-review.md).
