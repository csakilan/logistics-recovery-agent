# Interview preparation: choosing a remedy for the failed live run

Assistant-written draft requested by the builder on October 12, 2026. This is a proposed engineering assessment, not a record of a personal diagnosis or contribution. Use it only after understanding and reviewing the implementation and evidence.

## Suggested answer

“I would first separate a request-budget problem from a broken response contract. Here, the model spent five calls retrieving independent records and then returned prose, while the application required a structured proposal. Increasing the budget would leave that mismatch in place.

“My preferred remedy is to require native tool calls, batch the independent reads, and give useful validation feedback within the existing budget. The model can recommend a plan; the backend must still enforce feasibility and require dispatcher approval before booking.

“I would verify that with a regression that fails before the fix, a valid recovery that commits exactly once after approval, and cases where infeasible or stale plans are rejected. Then I would repeat a small live evaluation under the same limits and publish failures as well as successes. A safe escalation is useful protection, but it is not evidence that the model solved the task.”

## Evidence behind this answer

- Before the native-output correction, one live normal case exhausted six calls and escalated; after it, the same development case assigned successfully in three calls. This is one repeated case, not a measured general reliability improvement.
- The corrected three-case cohort matched expected outcomes in 2/3 cases. The infeasible case matched by guarded escalation after invalid proposals, not by a correct model escalation. The stale case failed to complete recovery.
- Three controlled regressions reproduce missing revision feedback. With fixed schema guidance and allowlisted feasibility error codes, they reach approval in three calls; no assignment exists before approval, and one commit exists afterward. These are controlled provider faults, not live-model performance.
- The full suite passed 136 checks after the feedback change. The additional live retest is tracked separately in [live results](live-results.md).

This demonstrates contract design, bounded resource use, separation of authority, regression testing and honest evaluation. Avoid claiming that you personally discovered the problem until your own review and reasoning are recorded.
