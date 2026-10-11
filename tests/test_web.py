import json

import pytest
from pydantic import ValidationError


def test_incident_requires_authentication(client):
    assert client.get("/incidents/i1").status_code == 401


def test_invalid_credentials_rejected(client):
    assert client.get("/", auth=("dispatcher", "wrong")).status_code == 401


def test_authenticated_views(client, auth):
    response = client.get("/incidents/i1", auth=auth)
    assert response.status_code == 200
    assert "Driver cancelled before pickup" in response.text
    assert "Scripted replay" in response.text
    assert client.get("/", auth=auth).status_code == 200
    assert client.get("/incidents/unknown", auth=auth).status_code == 404


def test_direct_commit_cannot_bypass_approval(client, auth, origin, proposal, repo):
    response = client.post("/incidents/i1/commit", json={"proposal_id": proposal.id}, auth=auth, headers=origin)
    assert response.status_code == 409
    assert response.json()["code"] == "approval_required"
    assert repo.assignment("i1") is None


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://attacker.invalid"}, {"Origin": "null"}])
def test_write_requires_configured_origin(client, auth, proposal, repo, headers):
    response = client.post("/incidents/i1/decision", json={"proposal_id": proposal.id, "incident_version": 1, "decision": "approve"}, auth=auth, headers=headers)
    assert response.status_code == 403
    assert repo.approval(proposal.id) is None


def test_forged_approval_field_rejected(client, auth, origin, proposal, repo):
    response = client.post("/incidents/i1/commit", json={"proposal_id": proposal.id, "approved": True}, auth=auth, headers=origin)
    assert response.status_code == 422
    assert repo.assignment("i1") is None


def test_valid_decision_then_commit(client, auth, origin, proposal, repo):
    decision = client.post("/incidents/i1/decision", json={"proposal_id": proposal.id, "incident_version": 1, "decision": "approve"}, auth=auth, headers=origin)
    assert decision.status_code == 200
    committed = client.post("/incidents/i1/commit", json={"proposal_id": proposal.id}, auth=auth, headers=origin)
    assert committed.status_code == 200
    assert committed.json()["status"] == "assigned"
    assert repo.stats("i1")["assignments"] == 1


def test_form_decision_and_commit(client, auth, origin, proposal, repo):
    response = client.post("/incidents/i1/decision", data={"proposal_id": proposal.id, "incident_version": "1", "decision": "approve"}, auth=auth, headers=origin, follow_redirects=False)
    assert response.status_code == 303
    response = client.post("/incidents/i1/commit", data={"proposal_id": proposal.id}, auth=auth, headers=origin, follow_redirects=False)
    assert response.status_code == 303
    assert repo.assignment("i1").status == "assigned"


def test_html_notes_are_escaped(client, auth, repo):
    with repo.transaction() as connection:
        row = connection.execute("SELECT payload FROM source_events WHERE incident_id=?", ("i1",)).fetchone()
        event = json.loads(row[0]); event["note"] = "<script>alert('attack')</script>"
        connection.execute("UPDATE source_events SET payload=? WHERE incident_id=?", (json.dumps(event), "i1"))
    response = client.get("/incidents/i1", auth=auth)
    assert "<script>alert" not in response.text
    assert "&lt;script&gt;" in response.text


def test_json_boolean_version_not_coerced(client, auth, origin, proposal):
    response = client.post("/incidents/i1/decision", json={"proposal_id": proposal.id, "incident_version": True, "decision": "approve"}, auth=auth, headers=origin)
    assert response.status_code == 422


def test_configuration_requires_https_for_remote_host(tmp_path):
    from logistics_recovery.config import Settings
    with pytest.raises(ValidationError):
        Settings(data_dir=tmp_path, origin="http://example.com", dispatcher_username="dispatcher", dispatcher_password="test-password")


def test_configuration_repr_does_not_expose_secrets(settings):
    assert "test-password" not in repr(settings)
