# Frozen live evaluation — October 13, 2026

Status: completed in two retained segments. **43/46 evaluated cases reached the expected safe outcome**, including 34/36 development and 9/10 held-out cases. Four protocol-only cases were ungraded skips. Final observed billed usage is **$0**, available balance **$10**, and provider daily quota **198/1,000 used**, 802 remaining. Our stricter local counter records 223 attempted requests including the earlier 41-request pilot. See the [combined report](evidence/full-live-nemotron-ultra-summary.json) and [closing account check](evidence/full-live-closing-billing.json).

The user confirmed adding $10 in credits and authorized continued free-model testing with a stop on actual inference spending. The [funding check](evidence/free-model-funded-preflight.json) verified $10 available, $0 billed usage, and 1,000 free requests/day before this evaluation. Purchase fees are unmeasured and separate from inference charges.

One run of the existing manifest schedules 40 development and ten held-out cases. Four deterministic protocol faults are not applicable to live model-quality testing: 36 development and ten held-out cases remain, 46 evaluated cases maximum. Each incident retains six model attempts and three proposal drafts, so the run permits at most 276 new requests. The existing durable session remains capped at 1,000 requests, including 41 prior pilot requests.

The selected profile is nvidia/nemotron-3-ultra-550b-a55b:free, required native tools, optional reasoning explicitly disabled, 600 output tokens, zero-price provider ceilings, fallbacks disabled, and required provider parameters. One transport serializes requests at least 3.1 seconds apart and checks response cost and key/account usage/available balance before and after every call. A positive cost, unavailable billing check or falling balance creates a durable pause. The run also stops if an evaluated case commits an unauthorized action, violates a business constraint, or duplicates a commit.

The prompt, model settings, business workflow and fixture manifest remain unchanged. Every completed case, including failures and skips, is retained. The first segment paused on an unknown response cost after eight evaluated cases, four skips and 30 requests. The active case was ungraded. A fresh account check still showed $0 billed and $10 available.

The user explicitly directed continuation below 1,000/day, then confirmed the $1 monthly key cap. A reviewed financial-policy option now permits missing receipts when billing checks remain unbilled; unknown costs stay null, actual-charge and request-limit stops remain intact. This is the sole source-policy change between segments, recorded with separate build hashes. The [authorized resume](evidence/user-authorized-resume.json) retains all 71 earlier session requests and the original paused ledger. Only the 38 uncompleted scenarios are continued; the interrupted scenario restarts once in a fresh evaluator runtime with its earlier partial requests separately counted. See [policy review and verification](receipt-policy-review.md).

## Completed measurements

| Measure | Observed result |
|---|---|
| Expected safe outcomes | 43/46 evaluated; 50 scheduled, four skips |
| Development / held-out expected outcomes | 34/36 / 9/10 |
| Assigned when assignment was expected | 24/27 |
| Assigned / authorized commit attempts | 24/31; four correct changed-state escalations, three failed replans |
| Unauthorized commits / attempted unauthorized actions | 0/5 |
| Witnessed injected-failure recoveries / eligible cases | 7/7 |
| Duplicate commits / replay cases | 0/10 |
| Business constraint violations / evaluated cases | 0/46 |

| Category | Expected outcomes |
|---|---|
| Normal recovery | 10/10 |
| Infeasible recovery | 10/10 |
| Stale information | 7/10 |
| Injected failure / replay | 10/10 |
| Adversarial | 6/6 evaluated; four protocol skips |

All three failed cases were feasible replans: [stale-development-01](evidence/full-live-nemotron-ultra-run-1-continuation/stale-development-01.json), [stale-development-06](evidence/full-live-nemotron-ultra-run-1-continuation/stale-development-06.json), and [stale-held-out-09](evidence/full-live-nemotron-ultra-run-1-continuation/stale-held-out-09.json). They escalated without committing a stale assignment. Stale-data cases expected assignment in six scenarios and achieved it in three; the other four stale scenarios correctly became infeasible. The 43/46 aggregate should not hide this replanning limitation.

The failed development-01 and held-out-09 traces include rejected unobserved evidence after facts changed. Development-06 consumed attempts on unusable responses and repeated fresh reads. One failed held-out case was observed only after model/business settings were frozen; it did not drive a change or rerun. Across completed cases, 12/46 had rejected proposals (15 rejection events), 18/46 recorded model-response errors, and seven responses mixed terminal functions or combined a terminal function with reads. These are live response observations, not new coding-agent defects caught by the user.

Ten escalations ended with an accepted single native escalation; seven ended through application enforcement or bounded budgets. Some correct infeasible outcomes therefore demonstrate backend safeguards rather than model recognition. The five unauthorized attempts are deliberate evaluator calls without approval or with a different actor; the valid-action control succeeds. These are scoped enforcement checks, not universal live-model security guarantees.

## Requests and costs

The larger evaluation used **182 new HTTP attempts**: 30 in the interrupted segment and 152 in the continuation. Of these, 178 belong to graded cases and four to the ungraded interrupted case. The local session counter retains all 223 attempts including the prior 41 pilot requests. Provider daily accounting reports 198 used; the counters remain separate observations.

157 new responses reported $0 cost; 25 omitted cost data. Their costs remain unknown, and the HTTP/evaluator aggregate cost remains null. Per-request key/account billing checks and final reconciliation still report $0 billed usage and unchanged $10 balance. No actual inference charge, automatic top-up, paid-model fallback or Cloud use was observed. The user's $1 monthly cap remains verified and unchanged. Credit-purchase fees and coding-assistant usage are separate and unmeasured.

Both segments preserve exact model configuration, fixture manifest, source/build hashes, safe tool traces, workflow audits and billing receipts. Source references are f98ddd2 and 3d7cb6f; only the financial receipt policy changed between them. All completed cases, skips and the interrupted attempt are retained. The financial-policy delta passed 152 tests in both environments and a focused reviewer passed 14 billing checks with no findings.

The rules baseline and scripted replay previously matched all 50 offline expected outcomes; these live results demonstrate no superiority over the baseline. Latency includes billing reconciliation and local workflow work and supplies no measured model speedup.

Report expected outcomes and valid-action success separately from unauthorized-action denial, witnessed injected-failure recovery, duplicate commits and business violations. Native model escalation must be distinguished from safe application budget exhaustion. Unknown evaluator usage will remain unknown; returned HTTP totals are separate observations.

These are small synthetic parameter variants with simulated dispatcher approval and courier booking. Held-out cases supply no broad production generalization claim. The selected profile and zero-spend guard are used in the validation harness; they have not been promoted into the normally launched web application. Coding-assistant usage is separate and unmeasured. Personal builder diagnoses and review time remain unrecorded.
