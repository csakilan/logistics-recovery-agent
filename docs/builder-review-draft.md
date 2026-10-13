# Builder review preparation: approval after changed availability

Assistant-written draft requested by the builder on October13,2026: “make it for now I will come back to this later.” This is preparation, not the builder's own reasoning, diagnosis or review time. Personal contribution remains unrecorded until the builder reviews the case and provides their own assessment.

The approval authorizes a particular proposal using particular facts: courier, price, parcel capacity, estimated arrival, custody and record versions. If that courier becomes unavailable, the basis for the approval has changed. Silently switching couriers could change price or arrival time without the dispatcher agreeing to those terms. Even a feasible alternative needs a new proposal and approval.

Keep the model's recommendation separate from authority. The model can retrieve fresh evidence and recommend an alternative. The backend checks feasibility and current versions, and the authenticated dispatcher supplies approval. The commit rechecks the facts because they can change between review and submission. UI buttons help the person understand the case; they do not provide the security boundary.

Verification should include a valid control and a changed-state case. Start with a feasible proposal, approve it, then make its courier unavailable. The old approval must not commit an assignment. Investigate again, check that the new proposal uses fresh records and a different proposal ID, and confirm no assignment appears before its new approval. After approval, verify exactly one assignment, one commit event and one capacity reservation. Also test quote expiry, rejection and repeated requests. Read-only page visits must not approve or change the case.

The latest independent review found another issue: overlapping requests could combine pickup status with older depot custody or show committed history beside an awaiting-approval status. One read transaction now presents a coherent snapshot; the later write still checks the latest facts. A consistent screen is evidence for a review decision, not authorization to reuse stale data.

Evidence to inspect: dispatcher-interface.md, dispatcher-review.md, tests/test_recovery.py, tests/test_dispatcher.py, and docs/evidence/dispatcher-browser-run-2/{stale-proposal.png,fresh-proposal.png,summary.json}. These diagnoses are agent-attributed. The builder can review the existing cases and record a substantive design assessment; they cannot retrospectively claim discovery from this draft.

Builder's own review: not yet supplied.
Actual active review time: unmeasured.
