# Fresh investigation after changed evidence

October 13, 2026. Assistant-discovered and assistant-corrected; no personal user diagnosis or review time is inferred.

The development failure `stale-development-01` refreshed only courier/quote data after a rejected old approval, then had a proposal rejected as `unobserved_evidence`. The workflow cleared `seen_evidence` but kept every previous model-visible tool result and error. This exposed evidence that was no longer authorized for the new investigation. The saved trace is consistent with reusing old citations; exact rejected arguments were not retained, so it does not prove which reference the model reused.

A separate development failure, `stale-development-06`, spent two attempts on unusable HTTP200 responses, then repeated fresh reads instead of proposing within the six-attempt budget. The original response error bodies were not retained. Context isolation addresses the application's stale-context mismatch; it does not establish the cause of those external responses or promise to remove all inefficient model behavior.

The correction resets the model conversation when replanning, retaining trusted initial instructions and a new incident-specific request. It explicitly asks for all five fresh evidence reads and states the remaining durable model/draft budgets. Old results, errors, proposals and approvals remain in the business audit and historical checkpoints. Citation observation, feasibility checks, total six attempts, total three drafts and fresh approval remain enforced. Raising limits or accepting old citations would conceal the mismatch instead of resolving it.

Two controlled regressions failed first because old assistant/tool messages reached the new model request. With the correction, the real adapter, graph and business store complete a replacement with one new approval and one assignment, including the variant with two prior unusable provider responses. These are boundary regressions with a controlled external provider, not measurements of a real model's response to the prompt. The full suite passed154 checks in development and in a clean locked environment. See [verification evidence](evidence/replan-context-verification.json).

Independent read-only review found no issues in the correction, passed31 focused checks and four temporary route/reconstruction variants. A separate bounded free-model development check is pending. The original43/46 full evaluation and its failures remain unchanged. No held-out failure informed this correction.
