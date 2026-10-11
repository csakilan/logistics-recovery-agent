# Employer expectations and project review priorities

Research date: October 11, 2026. This mapping interprets published hiring guidance and engineering practices; it is not an employer-issued scoring rubric. It informs the approved project without expanding the one-week scope.

| Principle | Primary evidence | Project evidence to preserve |
|---|---|---|
| Correctness under imperfect inputs | Microsoft's interview guidance asks candidates to test boundary, error, and security conditions. [Microsoft technical interviewing](https://careers.microsoft.com/v2/global/en/hiring-tips/technical-interviewing) | Invalid approvals, expired quotes, unknown custody, and infeasible plans are rejected; valid requests still work. |
| Reliability and recovery | Amazon's SDE II preparation identifies robust tested code and reliable design as evaluation criteria. This is broader SWE guidance, not an internship-specific requirement. [Amazon SDE II preparation](https://www.amazon.jobs/content/en/how-we-hire/sde-ii-interview-prep) | Lost responses and restarts recover without another reservation or assignment. |
| Sound design and appropriate simplicity | Google's published review standards examine component interactions and unnecessary complexity. [Google code-review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | Explain the single-application choice, separation of model decisions from business writes, and each component's responsibility. |
| Useful tests and concurrency reasoning | Google's guidance asks whether tests would detect broken behavior and whether parallel work can introduce races. [Google code-review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | Verify a test catches an unsafe implementation; two competing bookings cannot exceed one courier's capacity. |
| Ownership and explainable decisions | Amazon's U.S. SDE internship description discusses owning code through design, deployment and operations; its interview guidance asks for the reasons behind decisions and evidence where applicable. [U.S. internship example](https://prod.gamma.amazon.jobs/en-gb/jobs/3116030/software-development-engineer-internship-fall-2026-us), [interview guidance](https://www.amazon.jobs/content/en/how-we-hire/sde-ii-interview-prep) | Record who diagnosed the problem, alternatives considered, the remedy, and verification. Approval alone does not establish authorship or diagnosis. |
| Maintainability and communication | Google's guidance includes understandable code, naming and documentation that matches changed behavior. [Google code-review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | Small focused modules, reproducible setup, clear error states, and a builder explanation of limitations. |

These signals support prioritizing engineering outcomes over counts of agents, prompts, generated lines, or caught trivial mistakes. AI-specific roles can add requirements beyond this general software foundation.

## Recommended first showcase case

The strongest first case study is a booking that commits successfully but loses its response. It exercises ambiguous failure, durable state, atomic transactions, repeat-safe operations, and tests beyond the successful path. Stripe publishes this same failure pattern as motivation for idempotent APIs; this is a production engineering example, not a hiring requirement. [Stripe engineering explanation](https://stripe.com/blog/idempotency).

Security enforcement remains a required release gate. Review approval bypass next, showing the backend denies unauthorized changes even when the interface or model requests them. Review stale courier availability next, showing that earlier approval cannot authorize a plan whose assumptions have changed. These priorities are the assistant's recommendation from the sources; the user requested research-based prioritization and has not independently supplied the diagnosis.

Metrics: committed duplicates / replayed cases; successful recoveries / eligible injected failures; unauthorized commits / unauthorized attempts, paired with valid-action controls; corrected defects still passing their checks; and confirmed human decisions with before/after evidence. Publish sample sizes and test scope. A clean test suite is supporting evidence, not a universal security or reliability guarantee.

The personal engineering story is how the builder reasoned about a failure, evaluated the implementation, and verified a defensible correction. The project can supply that evidence only for contributions actually observed or confirmed.
