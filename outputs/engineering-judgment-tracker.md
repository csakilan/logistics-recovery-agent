# Engineering judgment tracker

Started: October 11, 2026

Purpose: collect evidence that the builder can direct coding agents, identify flawed work, make engineering decisions, and verify corrections. The user has made this the primary résumé priority for the proposed logistics project. Budget: $35 cash plus $300 in active Google Cloud credits, available for 90 days. First résumé-ready milestone: a working prototype within one week; ordinary weekly capacity is 15 hours, with 45–50 hours confirmed for the first week on October 11, 2026.

Status: implementation started October 11, 2026 after the user approved the written implementation plan and Native execution. Eight naturally occurring implementation defects have been verified and corrected by the assistant and independent assistant reviewer; no user-attributable correction is recorded yet. Empty logs mean no observations recorded, not a measured zero. This tracker records work; it does not approve the application design or authorize deployment.

## Metrics to collect

| Measure | Definition and evidence required | Current result |
|---|---|---|
| Verified corrections attributable to the user | Count distinct, naturally occurring agent defects identified by the user or corrected through a specific user-directed diagnosis. Require attribution evidence, a reproducible failure, and verification after the fix. Break down by security, reliability, business rules, and maintainability. | Not measured |
| Engineering decisions attributable to the user | Count substantive choices with the user's reasoning, the alternatives considered, and evidence supporting the chosen approach. Keep these separate from defect corrections. | Not measured |
| Security outcomes | Unauthorized actions committed / unauthorized action attempts in a named test suite. Also record rejection of a valid action, so blocking everything cannot look successful. | Offline scenarios: 0/5 per mode; authorized assignments 27/31, with four safe stale-state escalations |
| Reliability outcomes | Duplicate committed assignments / replayed incident cases; successful recoveries / eligible injected-failure cases; business constraint violations / evaluated cases. Record each separately. | Offline scenarios per mode: duplicates 0/10; recoveries 7/7; constraint violations 0/50 |
| Fixes that remain correct | Previously verified fixes passing their relevant checks / previously verified fixes retested at a later checkpoint. | 8/8 defect regressions passed in the later clean-environment checkpoint |
| Human oversight effort | Actual active review minutes and agent revision rounds for a meaningful decision or correction. Unknown time stays blank. Revision counts describe effort, not engineering quality. | Not measured |

Runtime, inference cost, and baseline task success can be supporting measurements once the application exists. Track application inference separately from coding-assistant usage, and cash spending separately from Cloud credits. No speedup claim without a comparable measured baseline.

## Event record

Use [engineering-judgment-events.csv](engineering-judgment-events.csv) for one row per substantive decision or defect, with a stable event ID. Record:

- What the agent proposed or implemented, and why it was inadequate.
- Who identified the problem, who decided the correction, and who implemented it. These can be different people or agents.
- Evidence for attribution: a message reference, short user-confirmed account, review comment, or saved decision note.
- The impact and engineering reasoning, including a relevant tradeoff.
- A reproducible check before the fix and its result after the fix, plus evidence references such as test output and commit IDs.
- Status: observed, reproduced, fix proposed, verified, or reopened. Mark a decision documented once its attribution and reasoning are recorded; record whether its outcome has been evaluated.

For defects, label origin as naturally occurring or deliberately injected. Injected defects validate the test harness and never count as real agent mistakes caught. Deduplicate the same root cause; do not count every failing test as another correction. Record severity only when the impact supports it.

Do not credit the user for an agent-discovered issue merely because the user approved continuing. Record contributions precisely, such as user selected the constraint, agent found the defect, user chose the remedy, agent implemented it. If attribution is unclear, mark it unconfirmed and exclude it from personal résumé claims. Retain agent-discovered issues because they still demonstrate the review process.

## Checkpoints and comparisons

Use [project-metrics.csv](project-metrics.csv) for observations at the first runnable version, a meaningful security or reliability change, and the résumé-ready milestone. Use the same suite version and case set for before/after comparisons; record build and model configuration. Distinguish rules-baseline comparisons, changes to the agent workflow, and corrections to an agent-written implementation.

Always publish counts with rates: for example, 0 unauthorized actions in 25 tested attempts, rather than an unqualified security guarantee. Preserve valid-action controls, limitations, and held-out case labels. A passing adversarial suite supports claims about those cases, not universal security.

## Update routine

During project work in this workspace, update these records after substantive reviews, verified corrections, and measurement checkpoints. Logging should stay brief and proportionate; ordinary formatting edits and every prompt do not need entries. At a milestone, summarize observations here with links to evidence. Reopen a correction if later verification fails.

When the implementation moves into a repository, carry this tracker, both logs, and the tracking instructions into that repository. Cross-workspace continuity requires those files to be available; no background monitoring is configured.

## Résumé evidence gate

Before making a personal accomplishment claim, require confirmed attribution and linked evidence. Before quoting an improvement, require comparable before/after measurements and their sample sizes. Prefer a few defensible case studies over a large count of trivial fixes. Do not manufacture mistakes, retrospectively invent review time, or claim estimated improvements as measured results.

Verified offline case studies include approval enforcement, lost-response recovery, stale courier availability, conflicting custody and hostile-note tool boundaries. Their verification is attributed to agents; personal builder reasoning is still unrecorded.

Current milestone summary: all nine implementation tasks and the independent review/fix pass are complete offline. Both environments passed 132 checks. Eight natural defects were identified by agents and corrected by the assistant; personal user review and live inference remain unmeasured.

Planning update, October 11, 2026: [week-one approved design and delivery roadmap](week-one-logistics-plan.md) uses 43 scheduled hours plus 2–7 hours of contingency after the user confirmed 45–50 first-week hours. Ten of the scheduled hours are reserved for the builder's reviews, diagnosis, analysis, and evidence notes. The user approved the written scope by replying "yes" and asking for an explanation of the agentic setup. The agent proposed the technical scope and allocations; approval does not attribute those decisions or any defect diagnosis to the user. Availability and approval are planning records, not measured engineering contributions. No implementation metrics or verified defect corrections are added by writing or approving this roadmap. Implementation-plan review and execution-method selection remain pending.

Implementation planning, October 11, 2026: the user said "alright we can begin." The assistant prepared and self-reviewed [the implementation plan](logistics-implementation-plan.md), containing nine tasks totaling the approved 43 scheduled hours. Planned test examples and task structure were checked; no product tests have run and no product code exists. The user's instruction authorizes progress, while the written-plan review and execution-method requirements remain pending under the selected Superpowers workflow. Preparing this document creates no personal engineering metric or verified correction entry.

Execution approval, October 11, 2026: user said "yes approved lets continue." Native execution is authorized. Generic approval is excluded from personal engineering-decision/correction counts. The implementation repository now holds the canonical tracker and logs.

Task 1 checkpoint: business records, feasibility validation and the cheapest-feasible baseline implemented; 16 policy checks passed. No human diagnosis or defect correction is inferred from planned implementation steps. No model/cloud usage.

Task 2 checkpoint: 27 tests passed, including approval denial, actor mismatch, rollback, replay, and competing-incident capacity checks. Agent-discovered SQL INSERT arity error is recorded as AGENT-001 with reproducible before/after output. Its diagnosis and correction are attributed to the assistant, not the user.

Task 3 checkpoint: 41 tests passed, including HTTP authentication, origin checks, forged approval rejection, successful authorized actions, and escaped HTML notes. Personal review preference/reasoning requested from the user; no response is inferred or recorded yet.

Task 4 checkpoint: 62 tests passed. Read-only tool dispatch, provider parsing/error sanitization, context limits, and incident-indexed replay adapter implemented. Live requests remain unrun. The user requested that review priorities be grounded in employers’ published software-engineering expectations rather than choosing an edge case personally; this steering is recorded without attributing a technical diagnosis or decision to the user.

Task 5 checkpoint: 73 tests passed. Persistent approval, incident-scoped retrieval, unobserved-evidence rejection, concurrency guard and durable six-attempt/three-draft budgets verified offline. AGENT-002 records the status-display correction. Employer-guidance research recommends the lost-response recovery case as the first case study; source mapping is in docs/employer-principles.md. No live inference or paid usage has been measured.

Task 6 checkpoint: 85 tests passed. Lost-response recovery witnessed the injected failure after a real commit and returned the original assignment with one commit event and one capacity reservation. Stale availability and quote expiry block old approvals; simulated pickup/delivery are ordered, authenticated, idempotent and accurately update custody. AGENT-003 documents the naturally occurring ambiguous-custody validation error and its correction. Injected response loss is a recovery test, not a natural defect or user diagnosis.

Task 7 checkpoint: all 19 adversarial checks passed; combined security/HTTP/recovery run passed 45 checks. Valid-action control succeeded and the isolated faulty approval-bypass double was detected. No new natural implementation defect was observed. These test counts are not rates across distinct attack cases; scenario denominators will be computed in Task 8. Protected assets, privilege boundaries and remaining limitations are recorded in docs/threat-model.md.

Task 8 checkpoint: 116 tests passed. Both rules baseline and scripted agent matched expected outcomes in 50/50 synthetic cases, with 0 unauthorized commits in 5 attempted cases, 7/7 eligible injected recoveries and 0 duplicate commits in 10 replay cases per mode. Four changed-state cases safely escalated; assigned authorized cases were 27/31. Results, hashes, build/configuration and limitations are in docs/results.md and the metric CSV. No live model, cost advantage or user-attributable defect diagnosis is claimed.

Task 9 checkpoint: full suite 118 passed. A fresh Python 3.14.8 environment installed the pinned dependencies and editable package, passed both factory smoke checks, and completed seeding, protected views, investigation, blocked unapproved booking, authorized approval, simulated pickup/delivery and infeasible escalation. One commit event remained. All three natural defect regressions passed at this checkpoint. README, demo script and case studies are available; no credentials, live calls, recording, cloud deployment or personal diagnosis are implied. Fresh whole-branch review remains pending.

Final review checkpoint: a fresh assistant reviewer verified the original 118-check suite and found three Important and two Minor defects. The implementer regraded misleading history and malformed-provider failure handling as Important for this project’s evidence/reliability requirements. All five defects were reproduced and corrected in one fix pass; 132 checks passed in both the development and fresh locked environments. AGENT-004 through AGENT-008 preserve reviewer attribution and before/after checks. Live protocol-only cases are now explicitly skipped with separate scheduled/evaluated/skipped counts; no live requests occurred. The 50-case offline reruns retained the previous counts; changes were driven by review reproductions, not held-out failures.

Local handoff: final full suite 132 passed in 2.97s. Corrected code is committed; final per-case source digests match correction build d4107c0 and retain original run metadata. The local branch is preserved because this repository has no separate merge destination or remote. Eight assistant-made scope/design decisions are recorded separately from eight natural defect corrections; none are attributed to the user. Full execution rulings and limits are saved in docs/execution-record.md. No deferred minors remain after regrading; no live inference, public hosting or personal builder diagnosis is claimed.

Live-validation preparation: the user requested the next step. Anonymous official metadata confirmed advertised tool support for google/gemini-2.5-flash-lite; standard-rate three-development-case planning estimate is $0.02592 for at most 18 attempts. The assistant recommends a one-case start and a dedicated $1 lifetime key cap. No credentials are configured in this workspace; account/key readiness was requested. DECISION-009 records the assistant’s choice, not the user’s diagnosis. No inference, purchase, cloud usage or personal reasoning was recorded. See docs/live-validation.md.

Credential setup checkpoint: the user supplied an API credential in chat. Its value was not copied into project files, logs or tool commands and no provider request was made with it. The assistant recommended revoking it and replacing it with a dedicated $1 lifetime-limit key saved privately. An owner-only local credential file was prepared outside the repository; rotation and replacement remain unverified. This is credential handling, not a natural implementation defect or a personal engineering accomplishment.
