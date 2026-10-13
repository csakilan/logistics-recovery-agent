# Local portfolio handoff

The technical prototype is ready locally. It investigates a cancelled delivery, checks available couriers and quotes, presents recorded facts, waits for dispatcher approval, creates one simulated assignment, and tracks simulated pickup/delivery. Changed facts require a fresh proposal and approval. Restart or repeated requests do not create another booking.

## What to inspect first

1. Watch the three-minute captioned replay video in demo/final/replay-walkthrough.mp4. It is an actual automated browser recording with simulated operator actions and no narrated builder voice. Captions identify replay, synthetic data and the limits of the demonstration.
2. Read final-validation-results.md. Baseline and replay matched12/12 fresh outcomes; the live model matched10/12. A feasible replacement escalated, and one denial-check case never produced a proposal. These failures remain visible.
3. Read dispatcher-interface.md and case-studies.md for approval, changed facts, coherent display and repeat-safe commit examples. Full audit records remain inspectable.
4. Follow the README to run locally in replay without a provider key. Live mode is optional and uses the approved free model, verified pricing/limits, per-request billing checks and a persistent private request record.
5. Review builder-review-draft.md, then provide your own reasoning when ready. It is assistant-written preparation; personal diagnosis, decisions and review minutes remain unmeasured.

## Verified checkpoint

A new Python3.14.8 environment installed the pinned dependencies and editable package, passed the dependency-consistency check and all190 tests. Actual Chrome exercised the workflow, approval denial, restart identity, pickup/delivery and infeasible replay escalation. Prior browser tests also cover stale approval requiring a fresh proposal and approval. Independent reviews and their reproduced/corrected findings are recorded; no material finding is hidden as a “pass.”

The fresh live evaluation used45 requests within a72-request cap. Thirty-five receipts report zero cost and10 omit it, so aggregate receipt cost remains unknown. Account/key checks observed zero billed usage and unchanged10-dollar available balance. Local session307 and provider daily268/1000 are separate measured counters. The existing1-dollar monthly key cap remains intact. No paid fallback, new subscription or Cloud resource was used.

## What remains

The builder explicitly deferred their own review. Complete that before making personal engineering-judgment claims. Adding the builder's own narration is optional for the captioned demonstration, and may make an interview walkthrough stronger. Choose repository destination and visibility before publication; files and setup are prepared locally but no public remote exists. These outstanding human actions prevent claiming the entire portfolio handoff is finished.

This is a local one-worker simulator with one dispatcher and one complete job per incident. There is no real courier integration, routing optimizer, production deployment or universal security/reliability guarantee. The rules baseline performed at least as well as the live model on the fresh set. Safe application enforcement and honest model evaluation are the project's evidence.
