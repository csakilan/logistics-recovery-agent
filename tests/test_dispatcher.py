"""Dispatcher decisions must reflect recorded facts and backend case state."""
import json
from contextlib import contextmanager
from html.parser import HTMLParser
from threading import Event, Thread, current_thread

import pytest
from fastapi.testclient import TestClient

from logistics_recovery.web import build_application
from logistics_recovery.presentation import incident_view


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sections = {}
        self.stack = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            label = dict(attrs).get("aria-label")
            self.stack.append(label)
            if label:
                self.sections.setdefault(label, [])

    def handle_endtag(self, tag):
        if tag == "section":
            self.stack.pop()

    def handle_data(self, data):
        for label in self.stack:
            if label:
                self.sections[label].append(data)

    def text(self, label):
        return " ".join(" ".join(self.sections.get(label, [])).split())


def test_proposal_review_uses_quote_records_instead_of_model_claims(client, auth, service, valid_candidate, repo):
    # A plausible explanation must never become the displayed price or ETA.
    service.propose("i1", valid_candidate.model_copy(update={"summary": "Courier c2 costs $1.00 and arrives at minute 5."}))
    history, stats = repo.history("i1"), repo.stats("i1")
    html = client.get("/incidents/i1", auth=auth).text
    page = Page(html)
    facts = page.text("Recorded quote facts")
    assert "c1" in facts and "q1" in facts
    assert "$12.00" in facts and "minute 30" in facts
    assert "minute 10" in facts and "$15.00" in facts
    assert "$1.00" not in facts and "c2" not in facts
    assert "$1.00" in page.text("Agent explanation")
    assert "Awaiting approval" in page.text("Recovery status")
    assert 'name="decision" value="approve"' in html
    assert repo.assignment("i1") is None and repo.approval(repo.latest_proposal("i1").id) is None
    assert repo.history("i1") == history and repo.stats("i1") == stats


@pytest.mark.parametrize("change", ["availability", "expiry", "quote"])
def test_changed_facts_hide_old_approval_and_quote_facts(client, auth, proposal, repo, change):
    if change == "availability":
        repo.change_courier("c1", available=False)
    elif change == "expiry":
        repo.advance_clock("i1", 10)
    else:
        with repo.transaction() as connection:
            quote = repo._snapshot(connection, "i1").quotes[0]
            connection.execute("UPDATE quotes SET payload=? WHERE id=?", (quote.model_copy(update={"cost_cents": 1300, "version": 2}).model_dump_json(), "q1"))
    history, stats = repo.history("i1"), repo.stats("i1")
    html = client.get("/incidents/i1", auth=auth).text
    assert 'name="decision" value="approve"' not in html
    assert "Needs fresh investigation" in Page(html).text("Recovery status")
    assert Page(html).text("Recorded quote facts") == ""
    assert "$13.00" not in html  # A changed quote is not the old proposal's price.
    assert '/incidents/i1/investigate"' in html
    assert "Needs fresh investigation" in client.get("/", auth=auth).text
    assert repo.history("i1") == history and repo.stats("i1") == stats
    assert repo.approval(proposal.id) is None and repo.assignment("i1") is None


@pytest.mark.parametrize("terminal", ["rejected", "escalated"])
def test_terminal_cases_have_no_misleading_decision_controls(client, auth, proposal, service, repo, operator, terminal):
    if terminal == "rejected":
        service.reject(proposal.id, operator)
    else:
        repo.set_terminal("i1", "escalated", "Model-attempt budget exhausted")
    html = client.get("/incidents/i1", auth=auth).text
    assert 'name="decision" value="approve"' not in html
    assert terminal.capitalize() in Page(html).text("Recovery status")
    assert terminal.capitalize() in client.get("/", auth=auth).text
    assert 'action="/incidents/i1/investigate"' not in html
    assert repo.assignment("i1") is None
    if terminal == "escalated":
        assert "Model-attempt budget exhausted" in Page(html).text("Incident history")
        assert "No feasible courier" not in Page(html).text("Recovery status")


@pytest.mark.parametrize("state,label,custody", [("assigned", "Assigned", "At depot"), ("picked_up", "Picked up", "In transit"), ("delivered", "Delivered", "Delivered")])
def test_assignment_progress_is_distinct_from_approval_and_delivery(client, auth, approved, service, operator, repo, state, label, custody):
    service.commit(approved.proposal_id, operator)
    if state != "assigned":
        service.record_event("i1", "pickup-1", "pickup", operator)
    if state == "delivered":
        service.record_event("i1", "delivery-1", "delivery", operator)
    html = client.get("/incidents/i1", auth=auth).text
    assert 'action="/incidents/i1/investigate"' not in html
    status = Page(html).text("Recovery status")
    assert label in status and custody in status
    assert label in client.get("/", auth=auth).text
    assert "Needs fresh investigation" not in status
    assert 'name="decision" value="approve"' not in html
    assert "Simulate pickup" in html if state == "assigned" else "Simulate pickup" not in html
    assert "Simulate delivery" in html if state == "picked_up" else "Simulate delivery" not in html
    assert repo.stats("i1")["commit_events"] == 1


def test_existing_approval_is_visible_before_assignment(client, auth, approved, repo):
    html = client.get("/incidents/i1", auth=auth).text
    assert "Complete approved recovery" in html
    assert "Approved" in Page(html).text("Recovery status")
    assert "assignment pending" in Page(html).text("Recovery status")
    assert repo.assignment("i1") is None


def test_reinvestigation_of_stale_approved_proposal_still_needs_new_approval(settings, repo, auth, origin, operator):
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        first = client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()["proposal"]
        client.app.state.service.approve(first["id"], 1, operator)
        repo.change_courier("c1", available=False)
        stale = client.get("/incidents/i1", auth=auth).text
        assert 'name="decision" value="approve"' not in stale
        assert "Needs fresh investigation" in Page(stale).text("Recovery status")
        second = client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()["proposal"]
        assert second["id"] != first["id"] and repo.approval(second["id"]) is None
        page = Page(client.get("/incidents/i1", auth=auth).text)
        assert "Awaiting approval" in page.text("Recovery status")
        assert "c2" in page.text("Recorded quote facts") and "$14.00" in page.text("Recorded quote facts")
        assert repo.assignment("i1") is None
        response = client.post("/incidents/i1/decision", auth=auth, headers=origin, data={"proposal_id": second["id"], "incident_version": str(second["incident_version"]), "decision": "approve"})
        assert response.status_code == 200 and repo.assignment("i1").courier_id == "c2"
        assert repo.stats("i1")["commit_events"] == 1


def test_assigned_case_does_not_present_changed_quote_as_booked_facts(client, auth, service, approved, operator, repo):
    service.commit(approved.proposal_id, operator)
    with repo.transaction() as connection:
        quote = repo._snapshot(connection, "i1").quotes[0]
        connection.execute("UPDATE quotes SET payload=? WHERE id=?", (quote.model_copy(update={"cost_cents": 1300, "version": 2}).model_dump_json(), "q1"))
    html = client.get("/incidents/i1", auth=auth).text
    assert "Assigned" in Page(html).text("Recovery status")
    assert "$13.00" not in Page(html).text("Recorded quote facts")
    assert "c1" in Page(html).text("Recovery status")


def test_business_history_preserves_order_and_escaped_notes(client, auth, service, approved, operator, repo):
    service.commit(approved.proposal_id, operator)
    service.record_event("i1", "pickup-1", "pickup", operator)
    service.record_event("i1", "delivery-1", "delivery", operator)
    with repo.transaction() as connection:
        event = json.loads(connection.execute("SELECT payload FROM source_events WHERE id='e1'").fetchone()[0])
        event["note"] = "<script>attack</script>"
        connection.execute("UPDATE source_events SET payload=? WHERE id='e1'", (json.dumps(event),))
    html = client.get("/incidents/i1", auth=auth).text
    history = Page(html).text("Incident history")
    labels = ("Cancellation", "Replacement proposed", "Dispatcher approved", "Courier assigned", "Simulated pickup", "Simulated delivery")
    positions = [history.find(label) for label in labels]
    assert all(position >= 0 for position in positions) and positions == sorted(positions)
    assert "<script>attack</script>" not in html and "&lt;script&gt;attack" in html
    assert "assignment committed" in html  # The complete audit remains inspectable.


@pytest.mark.parametrize("action", ["commit", "pickup"])
def test_concurrent_action_cannot_mix_assignment_and_snapshot(service, approved, operator, repo, monkeypatch, action):
    if action == "pickup":
        service.commit(approved.proposal_id, operator)
    write_at_commit, write_done, triggered = Event(), Event(), Event()
    errors = []
    original_connection, original_snapshot, original_assignment = repo.connection, repo._snapshot, repo.assignment

    def write():
        try:
            if action == "commit":
                service.commit(approved.proposal_id, operator)
            else:
                service.record_event("i1", "concurrent-pickup", "pickup", operator)
        except Exception as error:
            errors.append(error)
        finally:
            write_done.set()

    writer = Thread(target=write)

    @contextmanager
    def traced_connection():
        with original_connection() as connection:
            def trace(sql):
                if sql == "COMMIT" and current_thread() is writer:
                    write_at_commit.set()
            connection.set_trace_callback(trace)
            yield connection

    def interleaved_snapshot(connection, incident_id):
        snapshot = original_snapshot(connection, incident_id)
        if not triggered.is_set():
            triggered.set()
            writer.start()
            assert write_at_commit.wait(5), "Concurrent real write never reached commit"
        return snapshot

    def later_assignment(incident_id):
        # Force the old separate-transaction implementation to see the new write.
        assert write_done.wait(5)
        return original_assignment(incident_id)

    monkeypatch.setattr(repo, "connection", traced_connection)
    monkeypatch.setattr(repo, "_snapshot", interleaved_snapshot)
    monkeypatch.setattr(repo, "assignment", later_assignment)
    try:
        view = incident_view(service, "i1")
    finally:
        writer.join(6)
    assert not writer.is_alive() and not errors and write_done.is_set()
    actual = original_assignment("i1")
    assert actual.status == ("assigned" if action == "commit" else "picked_up")
    if view["assignment"]:
        assert view["snapshot"].incident_version >= 2
        if view["assignment"].status == "picked_up":
            assert view["snapshot"].job.custody == "in_transit"
    else:
        assert view["status"] == "approved" and view["snapshot"].incident_version == 1


def test_action_after_view_read_cannot_change_that_pages_history(client, auth, service, proposal, operator, repo, monkeypatch):
    from logistics_recovery import web
    original_view = web.incident_view
    errors = []

    def write():
        try:
            service.approve(proposal.id, 1, operator)
            service.commit(proposal.id, operator)
        except Exception as error:
            errors.append(error)

    def interleaved_view(*args):
        view = original_view(*args)
        writer = Thread(target=write)
        writer.start()
        writer.join(6)
        assert not writer.is_alive() and not errors
        return view

    monkeypatch.setattr(web, "incident_view", interleaved_view)
    page = Page(client.get("/incidents/i1", auth=auth).text)
    assert "Awaiting approval" in page.text("Recovery status")
    assert "Courier assigned" not in page.text("Incident history")
    assert "Dispatcher approved" not in page.text("Incident history")
    assert repo.assignment("i1").status == "assigned" and repo.stats("i1")["commit_events"] == 1
