# User-directed receipt policy — October 13, 2026

The user clarified that testing should continue below the 1,000/day request allowance after a response omitted its cost receipt, then confirmed a $1 monthly provider key cap. The earlier requirement to use free models and stop on actual spending remains. Account checks showed $0 billed usage and the full $10 balance. The omitted receipt remains unknown; it is not replaced with a measured zero.

ZeroCostTransport now accepts an opt-in pause_on_unknown_cost=False. Its default still pauses on missing cost data. The opt-in evaluation still verifies zero-price routing and checks key/account usage and available credit balance before and after every request. Positive reported cost, usage increase, balance decrease, unavailable billing, empty free quota or exhausted session budget still stops calls. This does not change the application's business workflow, model prompt or normally launched web application.

Five new feature/control cases failed before the option existed, then the full suite passed 152 checks in development and 152 in the clean locked environment. These tests use deliberately injected billing data; no actual money was spent by them. The independent assistant reviewer reported no Critical, Important or Minor findings and passed all 14 focused billing checks. No live provider accounting or model quality was inferred from that review.

The original paused ledger and response will be preserved. User-authorized continuation retains the existing counter and previous receipts, including the unknown value, and only resumes after read-only billing reconciliation. Completed cases will not be repeated. The interrupted synthetic case must restart in a fresh evaluator runtime because its temporary databases were closed; that partial attempt remains ungraded and separately counted.

Evidence: [RED](evidence/receipt-policy-red.txt), [GREEN](evidence/receipt-policy-green.txt), [clean suite](evidence/receipt-policy-clean.txt), and [paused segment](evidence/full-live-nemotron-ultra-run-1/summary.json).
