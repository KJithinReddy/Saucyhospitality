from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import TicketStatus
from app.services.matching import match_contractors
from app.services.triage import fallback_triage
from app.schemas import Category, Severity


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["runtime_writable"] is True


def test_create_ticket_and_fallback_triage():
    response = client.post(
        "/api/tickets",
        data={
            "description": "The walk-in refrigerator isn't getting cold and water is leaking near the unit.",
            "urgency": "critical",
            "location_note": "Walk-in cooler, kitchen back line",
        },
        files={"photo": ("walk-in.jpg", b"demo-jpeg-content", "image/jpeg")},
    )
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["status"] == TicketStatus.submitted.value
    assert ticket["photo_url"]
    media_response = client.get(ticket["photo_url"])
    assert media_response.status_code == 200
    ticket_id = ticket["id"]

    triaged = client.post(f"/api/tickets/{ticket_id}/triage")
    assert triaged.status_code == 200
    body = triaged.json()
    assert body["assessment"]["category"] == "commercial_refrigeration"
    assert body["status"] == TicketStatus.matching.value
    assert len(body["matches"]) >= 1
    assert body["matches"][0]["contractor"]["specialty"] == "refrigeration"

    listed = client.get("/api/tickets")
    assert any(item["id"] == ticket_id for item in listed.json()["tickets"])


def test_status_transitions():
    created = client.post(
        "/api/tickets",
        data={
            "description": "The walk-in refrigerator isn't getting cold and water is leaking near the unit.",
            "urgency": "critical",
            "location_note": "Walk-in cooler",
        },
    ).json()
    ticket_id = created["id"]
    ticket = client.post(f"/api/tickets/{ticket_id}/triage").json()
    contractor_id = ticket["matches"][0]["contractor"]["id"]

    accepted = client.post(f"/api/tickets/{ticket_id}/accept", json={"contractor_id": contractor_id})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    blocked = client.patch(
        f"/api/tickets/{ticket_id}/status",
        json={"status": "completed", "contractor_id": contractor_id},
    )
    assert blocked.status_code == 409

    for status in ("en_route", "in_progress", "completed"):
        updated = client.patch(
            f"/api/tickets/{ticket_id}/status",
            json={"status": status, "contractor_id": contractor_id, "note": "Updated from test"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == status

    confirmed = client.post(f"/api/tickets/{ticket_id}/confirm", json={"note": "Looks good"})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"


def test_fallback_triage_keywords():
    result = fallback_triage("The walk-in refrigerator isn't getting cold and water is leaking near the unit.", "critical")
    assert result.category == Category.commercial_refrigeration
    assert result.severity == Severity.critical
    assert result.source == "fallback"
