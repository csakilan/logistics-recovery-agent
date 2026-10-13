"""Read-only dispatcher views; action authorization remains in the service."""
from .assignments import AssignmentService
from .policy import proposal_is_current


def money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def incident_view(service: AssignmentService, incident_id: str) -> dict:
    state = service.repository.read_incident(incident_id)
    snapshot, assignment, proposal = state["snapshot"], state["assignment"], state["proposal"]
    terminal, approval = state["terminal"], state["approval"]
    quote = None
    if assignment:
        status = assignment.status
    elif terminal in {"rejected", "escalated"}:
        status = terminal
    elif proposal:
        if not proposal_is_current(proposal, snapshot):
            status = "stale"
        else:
            quote = next(q for q in snapshot.quotes if q.id == proposal.candidate.quote_id)
            status = "approved" if approval else "awaiting_approval"
    else:
        status = "needs_review"
    labels = {
        "needs_review": "Needs review", "awaiting_approval": "Awaiting approval",
        "approved": "Approved · assignment pending", "stale": "Needs fresh investigation",
        "rejected": "Rejected", "escalated": "Escalated", "assigned": "Assigned",
        "picked_up": "Picked up", "delivered": "Delivered",
    }
    guidance = {
        "needs_review": "Investigate the cancellation to gather facts and prepare a replacement.",
        "awaiting_approval": "Review the recorded facts below. No courier has been assigned yet.",
        "approved": "Approval is recorded. Complete the recovery to create the assignment.",
        "stale": "The recorded facts changed or the quote expired. Investigate again; the new proposal needs a fresh approval.",
        "rejected": "The dispatcher rejected this recovery. No courier was assigned.",
        "escalated": "This investigation stopped and requires manual review. No courier was assigned.",
        "assigned": "The courier is assigned. Pickup has not occurred yet.",
        "picked_up": "Simulated pickup is recorded. The parcels are in transit.",
        "delivered": "Simulated delivery is recorded. The reserved courier capacity has been released.",
    }
    return {
        **state, "quote": quote, "status": status,
        "status_label": labels[status], "guidance": guidance[status],
        "custody_label": {"depot": "At depot", "unknown": "Unknown", "in_transit": "In transit", "delivered": "Delivered"}[snapshot.job.custody],
        "can_investigate": status in {"needs_review", "stale"},
        "can_decide": status in {"awaiting_approval", "approved"},
        "arrival_min": snapshot.now_min + quote.travel_min if quote else None,
    }


def business_history(history: list[dict]) -> list[dict]:
    """Summarize business events without changing or omitting the full audit."""
    activity = []
    for item in history:
        kind, payload = item["kind"], item["payload"]
        if kind == "source_event":
            title = payload["kind"].replace("_", " ").capitalize()
            detail = f"Simulated minute {payload['at_min']}. {payload['note']}"
        elif kind == "proposal_created":
            title, detail = "Replacement proposed", f"Quote {payload['quote_id']} submitted for review."
        elif kind == "proposal_approved":
            title, detail = "Dispatcher approved", "Approval recorded for this proposal."
        elif kind == "proposal_rejected":
            title, detail = "Dispatcher rejected", "No assignment was created."
        elif kind == "replanning_required":
            title, detail = "Fresh investigation required", "Previous facts became stale; a new proposal and approval are required."
        elif kind == "assignment_committed":
            title, detail = "Courier assigned", f"Courier {payload['courier_id']}. Pickup had not occurred at assignment."
        elif kind in {"simulated_pickup", "simulated_delivery"}:
            title = kind.replace("_", " ").capitalize()
            detail = f"Dispatcher-triggered simulation at minute {payload['at_min']}."
        elif kind == "case_escalated":
            title, detail = "Investigation escalated", payload["detail"]
        else:
            continue
        activity.append({"title": title, "detail": detail})
    return activity
