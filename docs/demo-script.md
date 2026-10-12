# Three-minute walkthrough

0:00–0:30 — State the business problem: a driver cancels before pickup; the dispatcher must recover the job without guessing parcel custody, overspending or double booking. Point out Scripted replay and simulated time. Explain that the latest live development check matched 2/3 expected outcomes and that live reliability remains a limitation; the walkthrough uses reproducible replay.

0:30–1:15 — Open demo-1 and investigate. Show the cited order, courier, quote, policy and custody evidence. Before approval, there is no assignment. Explain that the model has read-only tools and cannot grant itself approval. Approve and show one committed assignment in the history.

1:15–1:50 — Restart the app with the same runtime directory or repeat the investigation. Show the same assignment and one commit event. Explain the automated lost-response test: it commits, deliberately loses the response, then recovers from the business database without reserving capacity again.

1:50–2:20 — Simulate pickup and delivery. Show that assigned, picked up and delivered are distinct states. Open demo-2, investigate and show safe escalation when no quote fits the spending limit.

2:20–3:00 — Open results and the custody case study. Report 0 duplicate commits in 10 replay cases and 7/7 injected recoveries per mode, with a successful authorized control. Both the rules baseline and replay matched the 50 synthetic outcomes. Explain the custody root cause and failing/passing evidence. Attribute the assistant's diagnosis accurately; add your own recorded reasoning only after personally reviewing it.

If displaying commands, use the private runtime and credentials from the README. Do not record passwords, provider keys or private environment files. No recording has been created.
