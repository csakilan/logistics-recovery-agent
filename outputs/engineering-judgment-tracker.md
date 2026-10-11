# Engineering judgment tracker

Started: October 11, 2026

Purpose: collect evidence that the builder can direct coding agents, identify flawed work, make engineering decisions, and verify corrections. The user has made this the primary résumé priority for the proposed logistics project. Budget: $35 cash plus $300 in active Google Cloud credits, available for 90 days. First résumé-ready milestone: a working prototype within one week; ordinary weekly capacity is 15 hours, with 45–50 hours confirmed for the first week on October 11, 2026.

Status: implementation started October 11, 2026 after the user approved the written implementation plan and Native execution. No verified implementation corrections or performance measurements have been recorded. Empty logs mean no observations recorded, not a measured zero. This tracker records work; it does not approve the application design or authorize deployment.

## Metrics to collect

| Measure | Definition and evidence required | Current result |
|---|---|---|
| Verified corrections attributable to the user | Count distinct, naturally occurring agent defects identified by the user or corrected through a specific user-directed diagnosis. Require attribution evidence, a reproducible failure, and verification after the fix. Break down by security, reliability, business rules, and maintainability. | Not measured |
| Engineering decisions attributable to the user | Count substantive choices with the user's reasoning, the alternatives considered, and evidence supporting the chosen approach. Keep these separate from defect corrections. | Not measured |
| Security outcomes | Unauthorized actions committed / unauthorized action attempts in a named test suite. Also record rejection of a valid action, so blocking everything cannot look successful. | Not measured |
| Reliability outcomes | Duplicate committed assignments / replayed incident cases; successful recoveries / eligible injected-failure cases; business constraint violations / evaluated cases. Record each separately. | Not measured |
| Fixes that remain correct | Previously verified fixes passing their relevant checks / previously verified fixes retested at a later checkpoint. | Not measured |
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

Potential case studies, currently unverified: bypassing approval through the backend, creating duplicate assignments after a retry, accepting stale courier availability, and following malicious instructions embedded in courier notes. These are investigation targets, not completed accomplishments.

Current milestone summary: no implementation evidence recorded yet.

Planning update, October 11, 2026: [week-one approved design and delivery roadmap](week-one-logistics-plan.md) uses 43 scheduled hours plus 2–7 hours of contingency after the user confirmed 45–50 first-week hours. Ten of the scheduled hours are reserved for the builder's reviews, diagnosis, analysis, and evidence notes. The user approved the written scope by replying "yes" and asking for an explanation of the agentic setup. The agent proposed the technical scope and allocations; approval does not attribute those decisions or any defect diagnosis to the user. Availability and approval are planning records, not measured engineering contributions. No implementation metrics or verified defect corrections are added by writing or approving this roadmap. Implementation-plan review and execution-method selection remain pending.

Implementation planning, October 11, 2026: the user said "alright we can begin." The assistant prepared and self-reviewed [the implementation plan](logistics-implementation-plan.md), containing nine tasks totaling the approved 43 scheduled hours. Planned test examples and task structure were checked; no product tests have run and no product code exists. The user's instruction authorizes progress, while the written-plan review and execution-method requirements remain pending under the selected Superpowers workflow. Preparing this document creates no personal engineering metric or verified correction entry.

Execution approval, October 11, 2026: user said "yes approved lets continue." Native execution is authorized. Generic approval is excluded from personal engineering-decision/correction counts. The implementation repository now holds the canonical tracker and logs.

Task 1 checkpoint: business records, feasibility validation and the cheapest-feasible baseline implemented; 16 policy checks passed. No human diagnosis or defect correction is inferred from planned implementation steps. No model/cloud usage.
