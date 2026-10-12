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

Including the earlier cases and one separate Google diagnostic, there were 28 chat requests: seven Google HTTP 429 responses and 21 Cohere HTTP 200 responses. The diagnostic is not another evaluated scenario. No observed billed usage or cash spend occurred; coding-assistant account usage is not measured here.

## Feedback correction and next check

Source inspection found no corrective context on malformed output and only generic feedback on failed feasibility. Three controlled provider regressions reproduced safe but unhelpful escalation. Fixed schema guidance and allowlisted policy error codes now support useful revisions without replaying rejected provider text or changing approval, request or output limits. Full suite: 136 passed; [RED evidence](evidence/agent-010-red.txt), [GREEN evidence](evidence/agent-010-green.txt).

A separate feedback-fix phase starts with stale-development-01, permits at most three development cases / 18 free attempts, and preserves the previous cohort. Retest pending. Its purpose is to test a specific correction, not to search until a model happens to pass. No held-out tuning, new architecture or paid model purchase is authorized by this record.
