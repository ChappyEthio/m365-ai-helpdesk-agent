import pytest
from fastapi.testclient import TestClient

from src.ticket_api.main import app, store

KEY = "test-key"
H = {"x-api-key": KEY}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HELPDESK_API_KEY", KEY)
    store.reset()


client = TestClient(app)


def _payload(**overrides):
    body = {
        "requester_upn": "Abebe@Contoso.org",
        "title": "Printer on floor 2 not printing",
        "description": "Jobs stay in the queue since this morning.",
        "category": "Device",
    }
    body.update(overrides)
    return body


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_rejects_missing_api_key():
    assert client.post("/tickets", json=_payload()).status_code == 401


def test_create_normal_ticket_is_open_and_upn_normalised():
    r = client.post("/tickets", json=_payload(), headers=H)
    assert r.status_code == 201
    t = r.json()
    assert t["status"] == "Open" and t["requires_approval"] is False
    assert t["requester_upn"] == "abebe@contoso.org"


def test_high_risk_ticket_waits_for_approval():
    r = client.post("/tickets", json=_payload(category="Account", title="Need mailbox access",
                                              description="Please give me access to the finance mailbox."), headers=H)
    assert r.json()["status"] == "PendingApproval"


def test_idempotency_prevents_duplicates_on_retry():
    h = {**H, "Idempotency-Key": "run-123"}
    a = client.post("/tickets", json=_payload(), headers=h).json()
    b = client.post("/tickets", json=_payload(), headers=h).json()
    assert a["id"] == b["id"]
    assert client.get("/health").json()["tickets"] == 1


def test_validation_errors_fail_fast():
    assert client.post("/tickets", json=_payload(requester_upn="no-at-sign"), headers=H).status_code == 422
    assert client.post("/tickets", json=_payload(title="hi"), headers=H).status_code == 422


def test_cannot_open_high_risk_ticket_without_approval():
    t = client.post("/tickets", json=_payload(category="Security", title="Disable MFA for travel",
                                              description="Please disable MFA while I travel."), headers=H).json()
    r = client.patch(f"/tickets/{t['id']}", json={"status": "Open"}, headers=H)
    assert r.status_code == 409
    r = client.patch(f"/tickets/{t['id']}", json={"status": "Open", "approval_id": "APR-42"}, headers=H)
    assert r.status_code == 200 and r.json()["status"] == "Open"


def test_get_unknown_ticket_404():
    assert client.get("/tickets/HD-NOPE", headers=H).status_code == 404
