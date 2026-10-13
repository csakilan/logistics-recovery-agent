# Free-model selection and spending controls

The builder offers a $10 OpenRouter credit top-up to enable larger free-model testing and requires evaluation to pause if inference uses money. This resumes the previously paused model-selection work. No purchase has been made by the assistant. The latest read-only preflight still reports $0 credits, $0 key/account billed usage and a 50/day free-model allowance.

OpenRouter's [official usage guidance](https://openrouter.ai/blog/tutorials/any-coding-agent/) says purchasing $10 in credits raises the free-model allowance to 1,000 requests **per day**, with a 20/minute limit. The same source describes a separate 5.5% credit-purchase fee, minimum $0.80. $10 in credits would therefore normally mean $10.80 before taxes or payment-specific differences; the user should verify the checkout total. Adding credits is cash spending even if subsequent inference remains free.

## Research shortlist

| Candidate | Why investigate it | Current verification |
|---|---|---|
| nvidia/nemotron-3-ultra-550b-a55b:free | First candidate: strongest reported agentic index among the eligible tool-capable free entries with an index in the inspected catalog; NVIDIA publishes agentic evaluations. | Free endpoint, tools/tool_choice/max_tokens/reasoning supported. |
| nvidia/nemotron-3-super-120b-a12b:free | Comparison candidate: NVIDIA specifically documents agent workflows/tool use and configurable reasoning; endpoint also advertises structured outputs. | Free endpoint, required parameters supported. |

The ranking is a nomination, not proof that Ultra is universally best or best for this project. Sources: [current OpenRouter catalog](https://openrouter.ai/api/v1/models), [Ultra free endpoint](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-ultra-550b-a55b:free/endpoints), [Super free endpoint](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-super-120b-a12b:free/endpoints), [NVIDIA Ultra model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4/raw/main/README.md), [NVIDIA Super model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16). Public metadata and sanitized account fields are retained in evidence/free-model-preflight.json and evidence/free-model-endpoints.json.

## Test plan

1. Pilot normal, infeasible and stale development-01 cases with each candidate, at most 36 requests across six cases. Publish failures and native escalation behavior as well as assigned jobs.
2. Select by expected outcomes and business safety, then request count and latency. Freeze the configuration and check repeatability before the reserved held-out evaluation. A three-case pilot alone establishes no broad reliability rate.
3. Use at most 1,000 serial requests in this testing session and the actual account's current daily allowance. This is a ceiling, not a target to exhaust. Broader testing requires verifying the top-up and increased allowance first.

The existing application, fixture manifest, six model attempts, three proposal drafts, 600 output tokens and approval/commit checks remain unchanged. The explicitly named profile disables optional reasoning, supported by both candidates, to leave the bounded output available for native tool calls. This changes model and generation configuration compared with earlier Cohere runs; no model-only causal gain is claimed. API metadata does not guarantee correct schema generation or provider availability.

## Spending stop

ZeroCostTransport is used by the evaluation runner, not automatically by every manually launched app instance. It pins one catalog :free entry; verifies zero prompt/completion/request prices; rejects paid plugins, alternate model lists and other extras; and sends a [provider maximum price](https://openrouter.ai/docs/guides/routing/provider-selection) of zero with fallbacks disabled.

Before and after **each** inference request it checks key usage, account usage and available credit balance, and checks the returned response cost. A positive cost, rising usage, declining balance, failed billing check or unverifiable cost creates a durable pause. BillingPause bypasses the application's normal retry handler. Another script invocation cannot silently resume a paused session. The user receives the pause reason and can choose an activity/billing review, a revised free configuration, or stopping the experiment. No automatic top-up or paid-model fallback is used.

Account changes can originate outside this run, so a balance change triggers conservative investigation without automatically attributing it to this project's inference. Checks cover OpenRouter accounting, not the coding assistant's separate account usage. This harness is for one serial evaluation process; it is not distributed spending coordination.

## Verification

Nine injected billing/control checks passed. Full suite: 147 passed in development and clean locked environments. Simulated charge amounts in tests are not actual spending. The focused review found a missing balance-decrease rule; its failing reproduction and passing correction are preserved as AGENT-011. See [review](free-billing-review.md), [RED](evidence/agent-011-red.txt), [GREEN](evidence/agent-011-green.txt), and [clean suite](evidence/free-billing-clean-suite.txt). Live candidate pilot pending.
