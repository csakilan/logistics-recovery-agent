# Free-model selection and spending controls

The user completed a $10 credit top-up and requires testing to stay on free models and pause on actual inference spending. The [funding check](evidence/free-model-funded-preflight.json) verifies $10 available, $0 billed usage and a 1,000/day allowance. The earlier pilot was completed before the top-up, when the account had $0 credits and a 50/day allowance. No purchase was made by the assistant; checkout fees are unmeasured. The larger evaluation and user-directed receipt policy are recorded in [full live results](full-live-results.md).

OpenRouter's [official usage guidance](https://openrouter.ai/blog/tutorials/any-coding-agent/) says purchasing $10 in credits raises the free-model allowance to 1,000 requests **per day**, with a 20/minute limit. The same source describes a separate 5.5% credit-purchase fee, minimum $0.80. $10 in credits would therefore normally mean $10.80 before taxes or payment-specific differences; the user should verify the checkout total. Adding credits is cash spending even if subsequent inference remains free.

## Research shortlist

| Candidate | Why investigate it | Current verification |
|---|---|---|
| nvidia/nemotron-3-ultra-550b-a55b:free | First candidate: strongest reported agentic index among the eligible tool-capable free entries with an index in the inspected catalog; NVIDIA publishes agentic evaluations. | Free endpoint, tools/tool_choice/max_tokens/reasoning supported. |
| nvidia/nemotron-3-super-120b-a12b:free | Comparison candidate: NVIDIA specifically documents agent workflows/tool use and configurable reasoning; endpoint also advertises structured outputs. | Free endpoint, required parameters supported. |

The catalog ranking nominated candidates; it did not prove a universal best model. The project pilot below supports choosing Ultra's tested profile for the next evaluation. Sources: [current OpenRouter catalog](https://openrouter.ai/api/v1/models), [Ultra free endpoint](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-ultra-550b-a55b:free/endpoints), [Super free endpoint](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-super-120b-a12b:free/endpoints), [NVIDIA Ultra model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4/raw/main/README.md), [NVIDIA Super model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16). Public metadata and sanitized account fields are retained in evidence/free-model-preflight.json and evidence/free-model-endpoints.json.

## Test plan

1. Pilot normal, infeasible and stale development-01 cases with each candidate, at most 36 requests across six cases. Publish failures and native escalation behavior as well as assigned jobs.
2. Select by expected outcomes and business safety, then request count and latency. Freeze the configuration and check repeatability before the reserved held-out evaluation. A three-case pilot alone establishes no broad reliability rate.
3. Use at most 1,000 serial requests in this testing session and the actual account's current daily allowance. This is a ceiling, not a target to exhaust. Broader testing requires verifying the top-up and increased allowance first.

The existing application, fixture manifest, six model attempts, three proposal drafts, 600 output tokens and approval/commit checks remain unchanged. The explicitly named profile disables optional reasoning, supported by both candidates, to leave the bounded output available for native tool calls. This changes model and generation configuration compared with earlier Cohere runs; no model-only causal gain is claimed. API metadata does not guarantee correct schema generation or provider availability.

## Completed pilot and unchanged repeat

All runs used source build **2f775ab**, the same fixture manifest and the profile above. The first comparison used 31 of its 36 permitted requests. Ultra's unchanged repeat used ten additional requests, for **41 total**. No held-out scenario was used.

| Candidate / run | Expected outcomes | Feasible case assignments | Requests | Constraint violations |
|---|---|---|---|---|
| Ultra, first pilot | 3/3 | 2/2 | 13 | 0/3 |
| Super, comparison | 1/3 | 0/2 | 18 | 0/3 |
| Ultra, unchanged repeat | 3/3 | 2/2 | 10 | 0/3 |

| Case | Ultra first result / requests | Super result / requests | Ultra repeat result / requests |
|---|---|---|---|
| Normal recovery | Assigned / 3 | Escalated / 6, failed | Assigned / 2 |
| No feasible courier | Escalated / 6 | Escalated / 6, budget stop | Escalated / 4 |
| Availability changed after approval | Assigned / 4 | Escalated / 6, failed | Assigned / 4 |

Choose **nvidia/nemotron-3-ultra-550b-a55b:free with optional reasoning disabled** for the next evaluation. It completed both feasible cases twice, and the stale cases required a new proposal and simulated fresh approval before committing once. This is six Ultra case-runs across **three unique synthetic development cases**, not six independent samples or a broad reliability rate.

The failures matter. Ultra's first normal run submitted two terminal proposals in one response; the adapter rejected that response and a later single proposal succeeded. Both infeasible runs proposed an invalid plan before backend rejection and eventual native escalation. The first infeasible run also repeatedly retrieved the same records and used all six requests. Super repeatedly fetched records, never produced a proposal or native escalation, and exhausted the six-attempt budget in all three cases. Its infeasible passing grade comes from the application safely stopping, not demonstrated model recognition of infeasibility.

All 41 HTTP responses reported $0 cost. The per-request ledger, before/after case checks and final read-only reconciliation report $0 key/account billed usage and unchanged $0 balance; **no billing pause occurred**. Raw HTTP usage totals are 60,923 prompt tokens and 2,906 completion tokens, including rejected output. Evaluator usage remains null in Ultra's first normal case after a malformed response; HTTP totals are separate measurements. Recorded case latency includes billing checks and local workflow work, so it is not bare model latency.

The [summary](evidence/free-model-pilot-summary.json) links all nine immutable case reports, including failures, configuration, source hashes, safe tool traces, workflow audits and billing receipts. The [closing account check](evidence/free-model-closing-preflight.json) confirms 41/50 used and nine remaining. These cases contain no live unauthorized-action, replay or lost-response attempts; those outcomes remain verified offline only.

Funding and the increased allowance are verified. The [completed larger evaluation](full-live-results.md) matched 43/46 expected outcomes using the same generation/business profile, with separate financial-policy segments. The 1,000-request session limit is a ceiling, not a requirement to spend every request. The selected generation profile and money guard have **not** been promoted into the normally launched web application.

## Spending stop

ZeroCostTransport is used by the evaluation runner, not automatically by every manually launched app instance. It pins one catalog :free entry; verifies zero prompt/completion/request prices; rejects paid plugins, alternate model lists and other extras; and sends a [provider maximum price](https://openrouter.ai/docs/guides/routing/provider-selection) of zero with fallbacks disabled.

Before and after **each** inference request it checks key usage, account usage and available credit balance, and checks the returned response cost. A positive cost, rising usage, declining balance or failed billing check creates a durable pause. Unknown cost also pauses by default; after one such pause, the user authorized continuation under the request limit, so the continuation opts into keeping missing receipts unknown while using billing checks to detect spending. BillingPause bypasses the application's normal retry handler. A paused session cannot silently resume: the user-directed resume preserves the counter and all receipts. No automatic top-up or paid-model fallback is used.

Account changes can originate outside this run, so a balance change triggers conservative investigation without automatically attributing it to this project's inference. Checks cover OpenRouter accounting, not the coding assistant's separate account usage. This harness is for one serial evaluation process; it is not distributed spending coordination.

## Verification

Nine injected billing/control checks passed. Full suite: 147 passed in development and clean locked environments before these source-matched pilot runs. Simulated charge amounts in tests are not actual spending. The focused review found a missing balance-decrease rule; its failing reproduction and passing correction are preserved as AGENT-011. See [review](free-billing-review.md), [RED](evidence/agent-011-red.txt), [GREEN](evidence/agent-011-green.txt), and [clean suite](evidence/free-billing-clean-suite.txt).
