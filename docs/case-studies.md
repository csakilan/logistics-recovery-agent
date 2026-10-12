# Engineering evidence and personal review

These examples map to employers' published priorities: sound design, tested behavior, security boundaries, failure reasoning and clear tradeoffs. See employer-principles.md for primary sources. All diagnosis and implementation below were performed by the assistant. The builder's own reasoning is still to be recorded; approving continued work does not establish personal diagnosis.

## Lost response after booking

A database commit can succeed while the caller never receives its response. Blindly booking again would create another assignment or reserve capacity twice. The test wraps the real commit, records its assignment ID and deliberately raises a connection error after it succeeds. A fresh workflow recovers the original assignment from business storage. The test checks one assignment, one commit event and one capacity deduction, and witnesses that the injected failure occurred.

Reproduce: `python -m pytest tests/test_recovery.py::test_lost_response_recovers_once -q`. This is a deliberately injected failure demonstrating recovery, not an agent bug that the builder caught. Tradeoff: SQLite and one process simplify this prototype; multi-process graph execution needs additional coordination. A stable operation ID and unique assignment are independent of checkpoint progress.

## Ambiguous parcel custody — AGENT-003

The initial validator broke a timestamp tie by record ID. A depot cancellation record and an in-transit pickup record at the same time could therefore be treated as known depot custody. IDs are not evidence of chronology. A test supplied both records and reproduced unsafe acceptance; the corrected validator requires all latest-time custody records to agree and cites the complete group. Ambiguity escalates rather than authorizing another pickup.

Reproduce: `python -m pytest tests/test_recovery.py::test_contradictory_same_time_custody_not_resolved_by_id -q`. Before/after outputs are in evidence/agent-003-red.txt and evidence/agent-003-green.txt. This naturally occurring defect was identified, diagnosed and corrected by the assistant. The user has not yet supplied a personal diagnosis. Tradeoff: conservative escalation can require human investigation when timestamps are too coarse.

## Approval authority and stale facts

A model or caller saying "approved" cannot create a stored dispatcher approval. The HTTP layer rejects extra fields; the service independently checks the authenticated actor and approval record. An availability change or quote expiry invalidates the original plan. Replanning produces another immutable proposal and requires another approval. Tests verify denial and successful authorized controls, so rejecting every request cannot pass as useful security.

Reproduce: `python -m pytest tests/test_adversarial.py tests/test_recovery.py -q`. A known insecure test double deliberately grants approval and proves the attack assertion catches a violation. That double is test-only and excluded from natural-defect counts.

## Résumé wording gate

Current evidence supports a project description: “Logistics recovery prototype with LangGraph, FastAPI and SQLite; approval-bound assignments, replay recovery and a 50-case synthetic safety evaluation.” It also supports “0 duplicate commits across 10 replay scenarios; recovered 7/7 injected failures in offline evaluation.” These are synthetic project results, not production savings or personal discoveries.

A first-person bullet about engineering judgment should wait until the builder can explain and demonstrate the implementation. For each chosen example, record the failing behavior, your diagnosis, alternatives, chosen correction or critique, and the verification you ran. Do not claim that you personally caught the recorded agent defects: all ten currently recorded natural defects were assistant findings. Personal active review time is unknown.

The final independent review found and corrected five further agent-written defects, including a stale-before-approval recovery dead end and startup-frozen replay choices. See [review and regressions](final-review.md). These are additional examples for the builder to study, not evidence of personal diagnosis.
