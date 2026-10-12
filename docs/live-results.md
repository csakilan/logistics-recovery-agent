# Bounded live-model validation

October 12, 2026. Development cases only; approval is simulated by the evaluator. Repeated runs are tuning observations, not independent samples. No credit purchase or Cloud usage occurred. The configured key has a $1 monthly limit, not the initially recommended lifetime limit; no provider settings were changed.

## Retained runs

| Configuration | Case | Expected / actual | Calls | Assignments / commits |
|---|---|---|---|---|
| Gemma free, original contract | normal-development-01 | assigned / escalated | 6 HTTP 429 | 0 / 0 |
| Cohere free, original contract | normal-development-01 | assigned / escalated | 6 HTTP 200 | 0 / 0 |
| Cohere free, required tools + batched-read prompt | normal-development-01 | assigned / assigned | 3 | 1 / 1 |
| Same | infeasible-development-01 | escalated / escalated | 6 | 0 / 0 |
| Same | stale-development-01 | assigned / escalated | 6 | 0 / 0 |

Each corrected-cohort report retains the exact model configuration, source hash, build reference, fixture manifest, sanitized HTTP trace and before/after quota readings under [evidence](evidence/). Build: db30cb0. Endpoint: cohere/north-mini-code:free; native tool choice required; six model attempts, three proposal attempts, 600 output tokens per call.

The corrected cohort matched expected outcomes in **2/3 cases**, with **1/2 successful authorized case attempts**, one actual assignment/commit and **0 constraint violations in three cases**. These cases contain no unauthorized-action attempt, replay or lost-response injection, so they supply no live denominators for those guarantees.

The infeasible case tried invalid plans and exhausted its budget without a native escalation call. Backend enforcement produced the expected safe outcome; do not credit the model with recognizing infeasibility. In the stale case, current evidence was retrieved after the old plan became invalid, but the final two responses reached the 600-token output limit without usable native calls. The application safely escalated instead of committing the stale plan.

## Cost and measurement

All 15 corrected-cohort HTTP responses reported zero cost: 12,730 prompt tokens and 5,724 completion tokens in the returned HTTP usage. These include rejected responses. Key and account usage deltas were also zero. The evaluator's aggregated token/cost fields remain null whenever parsing fails; HTTP trace totals are a separate observation, not a repaired evaluator result. Free endpoint availability and small-sample success do not establish production reliability.

Before the feedback retest, including earlier cases and one separate Google diagnostic, there were 28 chat requests: seven Google HTTP 429 responses and 21 Cohere HTTP 200 responses. The diagnostic is not another evaluated scenario. No observed billed usage or cash spend occurred; coding-assistant account usage is not measured here.

## Feedback correction and next check

Source inspection found no corrective context on malformed output and only generic feedback on failed feasibility. Three controlled provider regressions reproduced safe but unhelpful escalation. Fixed schema guidance and allowlisted policy error codes now support useful revisions without replaying rejected provider text or changing approval, request or output limits. Full suite: 136 passed; [RED evidence](evidence/agent-010-red.txt), [GREEN evidence](evidence/agent-010-green.txt).

A separate feedback-fix phase permitted at most three development cases / 18 free attempts and used 14 attempts. Build: f71a98b; same model, fixture manifest, six-attempt/three-draft/600-token bounds and simulated approval. Only the revision feedback changed. Reports also retain sanitized workflow audit events. Results:

| Case | Expected / actual | Calls | Assignments / commits |
|---|---|---|---|
| stale-development-01 | assigned / assigned | 6 | 1 / 1 |
| normal-development-01 | assigned / escalated | 4 | 0 / 0 |
| infeasible-development-01 | escalated / escalated | 4 | 0 / 0 |

Expected outcomes remain **2/3**, and feasible-case assignments are **1/2**. There were **0 constraint violations in three evaluated cases**. In the stale case the audit records q1 proposal/approval, stale-plan replanning, rejected unobserved evidence, a malformed response, then q2 proposal/approval and exactly one assignment to c2. In the normal case a malformed response was followed by a proposal with invalid evidence, then an unnecessary native escalation. In the infeasible case the model used a native escalation that correctly cited both couriers' zero capacity.

The 14 HTTP responses reported 11,643 prompt tokens, 5,638 completion tokens and $0 cost. Key/account usage deltas were zero. Evaluator usage totals remain null because each case included a malformed response; HTTP usage totals are separate evidence. This brings all attempted chat requests to **42**, including the single diagnostic: seven Google HTTP 429 responses and 35 Cohere HTTP 200 responses. Observed billed usage and cash purchases remain $0.

The feedback correction is verified as client behavior, including 136 checks in both development and clean locked environments and a focused read-only assistant review with no findings. **A reliable live demo is not established:** the same feasible case succeeded in one cohort and failed in the next. No aggregate live-quality gain is claimed, and no further requests were made to search for a passing run. The reproducible offline demonstration remains the stable portfolio walkthrough; live quality is a documented next milestone. No held-out case was used for tuning.

## Citation investigation and refinement

The failed stable normal case passed the observed-reference guard before policy returned an evidence error. Since no facts changed and all retrieved references were current, this narrows the class to missing mandatory citations. The exact historical omitted reference was not saved and is not asserted here.

One unchanged instrumented diagnostic recovered in two calls with all five required citations and one approved commit. Its [report](evidence/live-citation-diagnostic-cohere-north-mini-code-free-normal-development-01.json) preserves safe reference comparisons and response-size counts, with no reasoning text or credential. It reported $0 cost and zero key/account usage deltas. It demonstrates variation, not a correction. Total chat attempts through this diagnostic: 44 including the earlier separate provider diagnostic.

A controlled missing-citation regression failed before the refinement while four controls passed. Proposal feedback now names omitted current required citations only when already in the model's retrieved evidence. It neither supplies unseen evidence nor fills in the candidate. All 138 checks passed; [focused review](citation-feedback-review.md) found no issues. This refines AGENT-010 rather than counting a new root cause.

Correction retest pending: normal, stale and infeasible development-01 cases, at most 18 free attempts, same provider and six-attempt/three-draft/600-token incident limits. Default model reasoning and the prompt/schema are unchanged. All older cohorts remain preserved; no held-out tuning or additional feature is introduced.
