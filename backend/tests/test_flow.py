from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import TicketStatus
from app.services.matching import match_contractors
from app.services.triage import fallback_triage
from app.schemas import Category, Severity, Specialty


client = TestClient(app)


def test_list_restaurants():
    response = client.get("/api/restaurants")
    assert response.status_code == 200
    restaurants = response.json()["restaurants"]
    assert restaurants
    assert restaurants[0]["name"]
    assert restaurants[0]["neighborhood"]


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


def test_mismatched_photo_does_not_keep_trade_match():
    from app.services.triage import apply_photo_evidence

    parsed = {
        "category": "plumbing",
        "severity": "critical",
        "possible_issue": "Possible rodent trapped in a drainage vent",
        "recommended_specialty": "plumbing",
        "observations": ["Rat observed in the kitchen drain."],
        "immediate_action": "Isolate the area and wait for a technician.",
        "photo_matches_report": False,
    }
    result = apply_photo_evidence(parsed, has_photo=True)
    assert result["category"] == "general_maintenance"
    assert result["severity"] == "medium"
    assert "photo" in result["observations"][0].lower()


def test_matching_photo_keeps_reported_trade():
    from app.services.triage import apply_photo_evidence

    parsed = {
        "category": "plumbing",
        "severity": "high",
        "possible_issue": "Possible drain blockage",
        "recommended_specialty": "plumbing",
        "observations": ["Photo shows standing water near a floor drain."],
        "immediate_action": "Keep the area clear.",
        "photo_matches_report": True,
    }
    result = apply_photo_evidence(parsed, has_photo=True)
    assert result["category"] == "plumbing"
    assert result["severity"] == "high"


def test_hint_match_maps_messy_openrouter_labels():
    from app.services.triage import CATEGORY_HINTS, SPECIALTY_HINTS, _hint_match

    assert _hint_match("Commercial Refrigeration", CATEGORY_HINTS, Category.general_maintenance) == Category.commercial_refrigeration
    assert _hint_match("Commercial Refrigeration Technician", SPECIALTY_HINTS, Specialty.general_facilities) == Specialty.refrigeration
    assert _hint_match("unknown trade", CATEGORY_HINTS, Category.general_maintenance) == Category.general_maintenance


def test_normalize_parsed_keeps_valid_openrouter_json():
    from app.services.triage import _normalize_parsed

    result = _normalize_parsed(
        {
            "category": "commercial_refrigeration",
            "severity": "critical",
            "possible_issue": "Possible failed evaporator fan",
            "recommended_specialty": "refrigeration",
            "observations": ["Walk-in is warm.", "Water is pooling near the door."],
            "immediate_action": "Keep the door closed and wait for a technician.",
        },
        "critical",
    )
    assert result["category"] == "commercial_refrigeration"
    assert result["recommended_specialty"] == "refrigeration"
    assert result["severity"] == "critical"


def test_analyze_issue_uses_openrouter_success_payload():
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.services import triage

    payload = {
        "category": "commercial_refrigeration",
        "severity": "critical",
        "possible_issue": "Possible failed evaporator fan motor",
        "recommended_specialty": "refrigeration",
        "observations": ["Walk-in is warm.", "Water is pooling near the door."],
        "immediate_action": "Keep the door closed and wait for a technician.",
        "photo_matches_report": True,
    }

    async def run():
        with patch.object(triage.settings, "openrouter_api_key", "test-key"):
            with patch.object(triage, "_call_openrouter", AsyncMock(return_value=(payload, "test-model"))):
                return await triage.analyze_issue(
                    "The walk-in refrigerator isn't getting cold.",
                    "critical",
                    "Walk-in cooler",
                    None,
                )

    result = asyncio.run(run())
    assert result.source == "openrouter"
    assert result.model_id == "test-model"
    assert result.category == Category.commercial_refrigeration
    assert result.recommended_specialty == Specialty.refrigeration


def test_analyze_issue_falls_back_on_unexpected_openrouter_error():
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.services import triage

    async def run():
        with patch.object(triage.settings, "openrouter_api_key", "test-key"):
            with patch.object(triage, "_call_openrouter", AsyncMock(side_effect=RuntimeError("boom"))):
                return await triage.analyze_issue(
                    "The walk-in refrigerator isn't getting cold.",
                    "critical",
                    "Walk-in cooler",
                    None,
                )

    result = asyncio.run(run())
    assert result.source == "fallback"
    assert result.category == Category.commercial_refrigeration
