import httpx
from fastapi.testclient import TestClient

from logistics_recovery.web import build_application


def test_app_factory_wires_replay_without_business_effects(settings, repo, auth, monkeypatch):
    def no_network(*args, **kwargs): raise AssertionError("Unexpected network request")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        response = client.get("/incidents/i1", auth=auth)
        assert response.status_code == 200
        assert "Scripted replay" in response.text
    assert repo.assignment("i1") is None
    assert repo.stats("i1")["commit_events"] == 0


def test_factory_replay_demo_reaches_approved_assignment(settings, repo, auth, origin):
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        response = client.post("/incidents/i1/investigate", auth=auth, headers=origin)
        assert response.status_code == 200
        proposal = response.json()["proposal"]
        assert response.json()["status"] == "awaiting_approval"
        assert repo.assignment("i1") is None
        response = client.post("/incidents/i1/decision", auth=auth, headers=origin, json={"proposal_id": proposal["id"], "incident_version": proposal["incident_version"], "decision": "approve"})
        assert response.status_code == 200
        assert response.json()["assignment"]["status"] == "assigned"
        detail = client.get("/incidents/i1", auth=auth).text
        assert "assignment committed" in detail and "proposal approved" in detail
        client.post("/incidents/i1/commit", auth=auth, headers=origin, json={"proposal_id": proposal["id"]})
        assert repo.stats("i1")["commit_events"] == 1
    # Restart resumes authoritative state without inference or another booking.
    with TestClient(build_application(settings), base_url=settings.origin) as client:
        assert client.post("/incidents/i1/investigate", auth=auth, headers=origin).json()["assignment"]["status"] == "assigned"
    assert repo.stats("i1")["model_calls"] == 2
