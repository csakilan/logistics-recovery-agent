# Week-one logistics project: approved design and delivery roadmap

Prepared October 11, 2026. Status: the user approved the written design and weekly scope on October 11, 2026, replying "yes" and asking for an explanation of the agentic setup. Implementation has not started. This is the weekly delivery roadmap and approved design brief, not the later task-by-task implementation plan. Start the seven-day schedule after implementation-plan review and execution-method selection.

## Outcome and constraints

Build a runnable logistics recovery prototype that shows both an adaptive agent workflow and the builder's judgment while directing coding agents. The primary résumé evidence is confirmed human decisions, verified corrections, and measured security and reliability results.

Confirmed constraints: $35 total personal spending; $300 in currently active Google Cloud credits available for 90 days; one résumé-ready milestone within a week; 15 hours in ordinary weeks and 45–50 hours in the first week. Schedule 43 active builder hours, leaving 2–7 hours of contingency within the confirmed range. Agent execution time is separate from the builder's active time. Existing development-assistant charges, if any, must also be considered before claiming the entire project stayed under the cash ceiling.

Success means a complete runnable workflow, reproducible tests, a measured report, a recorded demonstration, and defensible résumé wording. A hosted URL is optional. No financial savings, real delivery improvement, production security, or faster development claim can be inferred from synthetic cases or estimated effort.

## Approaches considered

| Approach | Benefit | Main cost | Choice |
|---|---|---|---|
| One Python web application with a small interface, LangGraph, and SQLite | A visible working product with a backend that can be tested directly | More work than a command-line demo | Recommended |
| Command-line agent and evaluation suite first | Leaves the most time for evaluation | Weaker demonstration of a usable product | Fallback if first-week availability is lower |
| Separate frontend, several services, and live courier integrations | Broader infrastructure experience | Setup dominates the available week | Defer |

## Proposed product and architecture

User: one dispatcher at a fictional local parcel operator. Workflow: a driver cancels before pickup; all parcels for the delivery job remain at the depot. Each incident covers one delivery job, possibly containing multiple parcels. One replacement courier handles the complete job. Synthetic quotes include travel estimates, so this version does not calculate or optimize multi-stop routes.

The dispatcher opens the incident, reviews the agent's proposed replacement and its evidence, approves or rejects it, and sees the resulting assignment and event history. Simulated pickup and delivery events must be distinguishable from assignment; the application cannot claim delivery merely because it assigned a courier.

Proposed stack: Python, FastAPI, a minimal server-rendered interface, LangGraph, SQLite business storage and persistent graph checkpoints, pytest, and a configurable OpenRouter model. One application serves the interface and backend. Two principal views are sufficient: incident list and incident detail with proposal, approval controls, and history. Development starts locally; a small Cloud VM is optional after the local milestone passes.

The model can retrieve orders, courier availability, quotes, policy, and incident events through typed read-only tools. It can investigate missing evidence, propose a candidate, or escalate; it cannot issue arbitrary SQL, access credentials, make arbitrary network requests, approve its own plan, or write an assignment. Deterministic code validates deadlines, capacity, quote freshness, custody, and spending. Monetary values use integer cents; synthetic scenario time uses integer minutes from a fixed scenario start.

Graph flow: investigate -> validate proposal -> wait for dispatcher -> recheck current state -> commit assignment or return for review -> record simulated outcome. Missing or conflicting evidence leads to another bounded retrieval or escalation. Each incident allows at most six model calls and two revised proposals before escalation. These limits are proposed application defaults, not observed request counts.

An approval is a server-side record tied to an immutable proposal and incident version. A changed quote, courier state, or proposal requires revalidation and a fresh approval. The simulated commit consumes the approval, reserves capacity, creates the assignment, and records its audit event in one business-database transaction. A unique incident assignment and stable operation ID make repeat requests return the existing result. Business records are authoritative if the graph checkpoint and commit disagree after a crash. This guarantees only the behavior implemented in the local simulator, not exactly-once effects at a real courier API.

Security scope: one authenticated dispatcher account; no registration or multi-tenant account system this week. Use a framework-supported HTTP Basic dependency with credentials supplied through private configuration and constant-time credential comparison. Local development binds to loopback; remote access requires HTTPS. State-changing browser requests must validate the configured origin and reject missing or mismatched origins, as well as authenticate the operator. The model never receives dispatcher credentials. The backend enforces approval independently of UI visibility or model output. Notes render as escaped text; inputs and logs must not expose secrets. These choices still require implementation and testing.

Checkpointing alone does not authorize actions or make business commits atomic. LangGraph documents persistent interrupts and warns that an interrupted node restarts on resume, making repeat-safe work necessary. [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence). The proposed minimal authentication approach follows the framework's documented recipe. [FastAPI HTTP Basic](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/).

## Seven-day schedule

Hours are planning allocations, not measured work or a delivery guarantee. Implementation tasks will be decomposed after the written design is reviewed.

| Day | Hours | Deliverable and acceptance check | Builder review to preserve |
|---|---:|---|---|
| 1 | 6 | Define the custody, capacity, deadline, quote, and approval rules; create initial synthetic cases and a cheapest-feasible-courier rules baseline. A feasible case assigns correctly; an infeasible or insufficient-evidence case escalates. | Explain which facts are authoritative, why arithmetic stays in code, and what would make the model useful beyond the baseline. |
| 2 | 7 | Build the authenticated incident interface, business storage, validated proposals, and approval-controlled simulated assignment service. A direct backend request cannot assign without the matching recorded approval; a valid approved request succeeds and produces history. | Review the approval boundary and data model before accepting the implementation. |
| 3 | 7 | Connect LangGraph tools, bounded investigation, persistent pause/resume, and structured proposals. Demonstrate an evidence-dependent tool call and resume a paused incident after restarting the application. | Inspect one complete trace; challenge unsupported facts or unnecessary model calls. |
| 4 | 6 | Verify repeat-safe assignment, stale-state rejection, and recovery after a commit followed by a lost response. Replaying the operation produces one assignment and one capacity reservation. | Reason through the crash timing and the database/checkpoint distinction; preserve any natural defect and its correction evidence. |
| 5 | 7 | Run adversarial and negative tests against the isolated prototype: unauthorized requests, approval bypass, proposal tampering, malicious courier notes, escaped content, and secret exposure. Valid requests must still work. Fix failures and verify the same attack no longer succeeds. | Choose the threat model, inspect the failing behavior, and decide the remedy. Do not manufacture agent mistakes to create a case study. |
| 6 | 6 | Freeze the evaluation suite and run the rules baseline and agent workflow using the same case inputs and business-action service. Report raw counts, safety violations, escalation correctness, successful recoveries, model usage, and latency. | Review failures and explain where the agent adds value, adds cost, or fails to improve on the baseline. |
| 7 | 4 | Produce reproducible setup instructions, a 3-minute demonstration, a results report, and evidence-supported résumé wording. Run setup from a fresh environment. Include cloud hosting only if all required checks pass and buffer remains. | Explain the design and tradeoffs without agent assistance; verify that each personal claim has attribution evidence. |
| Contingency | 7 | Resolve unexpected failures or unfamiliar tooling. Preserve testing and documentation time. Use only the buffer that fits the user's actual 45–50-hour availability. | Record actual effort; do not treat this allocation as measured time saved. |

Planned work: 43 hours. With contingency, the allowance is 45–50 hours, capped at 50. Reserve 10 of the 43 scheduled hours for the builder's own design review, diagnosis, results analysis, and evidence notes; this is included in the daily allocations, not additional time. The larger first-week commitment strengthens review and evaluation while preserving one workflow. If time runs short, cut visual polish, remote hosting, and simulator variety first. Keep backend authorization, repeat-safe writes, recovery verification, and honest evaluation. If availability later falls to 20–25 hours, rescope before execution to the command-line workflow and smaller controlled demonstration; do not promise the full web product in that allocation.

## Evaluation and security evidence

Target 50 versioned synthetic cases: 10 normal replacements, 10 infeasible or insufficient-evidence cases, 10 stale-state cases, 10 failure/replay cases, and 10 adversarial or malformed-input cases. Hold 10 of the 50 out of prompt and workflow iteration, with cases drawn from all five groups. Keep expected outcomes outside the model's inputs. This is a development target, not a claim of 50 completed tests; report the suite actually completed.

The baseline selects the cheapest candidate that passes the same deterministic constraints and escalates when required evidence is missing. It gets the same available data and backend safeguards; do not intentionally weaken it to make the agent appear better. Identical decision performance with added agent cost is a valid result. Any information-gathering comparison must document which retrieval steps each approach is allowed to perform.

At minimum, verify these observable outcomes, including applicable valid-action controls:

- An unauthenticated request or request without the matching approval cannot create an assignment.
- A submitted proposal cannot change the candidate or spending authority after approval.
- Courier availability changing after approval cannot cause an invalid reservation.
- A duplicated event or lost commit response cannot create another assignment or reserve capacity twice.
- Restarting the application preserves a paused case and reconciles an already committed assignment.
- Malicious courier text cannot grant approval or bypass deterministic policy; rendered text cannot execute in the review interface.
- Infeasible cases escalate, and valid approved cases can complete the simulated workflow.

Use [the tracker](engineering-judgment-tracker.md) and both CSV logs for attribution and results. Separate deterministic test runs from live model runs, development cases from held-out cases, and naturally occurring agent defects from injected test faults. For repeat model runs, record model/configuration and case-level results rather than hiding variability in an average. Security rates must include denominators and the relevant case set.

## Human judgment and coding-agent workflow

For each consequential component, the builder states the invariant and acceptance criteria, the coding assistant proposes or implements a small change, the builder reviews its behavior, and tests establish whether it should be accepted. Preserve meaningful corrections with the failing example, user diagnosis or specific direction, fix, and verification references. A generic approval of agent work is not a personal diagnosis.

Aim to leave the week with a few explainable decision or correction case studies. There is no required count of agent mistakes; if the implementation is correct, document actual design decisions and reviews instead. Counts of prompts, generated lines, or agents used are not headline résumé metrics. No independent subagent work is authorized by this roadmap; select the execution method when reviewing the implementation plan.

## Spending controls

Use free local development and deterministic tests first. Before the first paid model run, check the selected model's current capabilities, prices, and checkout fees. Initial model-credit checkout ceiling: $12 including fees, within the $35 overall ceiling; no automatic top-ups. Configure a provider key limit and application request/token limits, and estimate each evaluation batch before running it. Choose a cheaper or smaller batch if it does not fit the remaining budget.

Cloud credits are optional for this milestone. Prior allocation of up to $120 of credits is a planning ceiling, not a verified service quote. Confirm current credit eligibility, estimated resources, spending controls, and teardown before provisioning. Preserve the local runnable version and video regardless of hosting. No domain, managed database, paid LangGraph service, or new subscription is required.

## Résumé formats after verification

These are draft formats, not current accomplishments. Replace placeholders only from recorded evidence, and omit a claim if its condition was not achieved.

- Designed and built a LangGraph logistics recovery prototype with evidence-backed proposals, persistent dispatcher approval, and transactional simulated courier assignments.
- Directed AI-assisted development and verified [N] naturally occurring implementation corrections across [documented categories], using reproducible failure tests and regression checks.
- Evaluated recovery behavior across [N] synthetic scenarios; recorded [A/B] successful eligible recoveries and [C/D] unauthorized actions in the named test suite.

If no user-attributable defects were found, replace the second format with a specific supported decision, such as designing the approval/commit boundary and verifying its behavior across replay and restart tests. Do not describe synthetic results as business impact, unqualified security, or production deployment. The strongest final bullets may differ from these templates.

## Week-one completion gate and review

The local workflow runs from a documented clean setup; the dispatcher can approve a valid plan; invalid actions cannot bypass backend checks; the application resumes after restart; replay does not duplicate committed assignments; actual evaluation results and limitations are published; and personal résumé claims are linked to confirmed contributions. Remote hosting is not part of the required gate.

Written-design review is complete. The user approved this scope on October 11, 2026. Next, use Superpowers writing-plans to turn it into exact files, interfaces, tests, and task checklists. Review that implementation plan and select execution before creating the application repository or writing product code. No repository or cloud resource has been created by this planning step. Scope approval is not evidence that the user personally diagnosed an agent defect or independently selected every technical choice.
