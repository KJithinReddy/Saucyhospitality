from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.models import CandidateMatch, Contractor, Ticket
from app.schemas import CATEGORY_TO_SPECIALTY, Category, Severity, Specialty


def _score_contractor(contractor: Contractor, specialty: Specialty, severity: Severity) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    if contractor.specialty == specialty.value:
        score += 80
        reasons.append("Primary specialty match")
    elif contractor.secondary_specialty == specialty.value:
        score += 45
        reasons.append("Secondary specialty match")
    else:
        return 0.0, []

    if not contractor.available:
        return 0.0, []

    if contractor.service_area == "manhattan":
        score += 10
        reasons.append("Covers Midtown service area")

    score += max(0, 15 - contractor.eta_minutes / 8)
    reasons.append(f"ETA about {contractor.eta_minutes} min")

    if severity in {Severity.critical, Severity.high} and contractor.emergency_available:
        score += 12
        reasons.append("Available for emergency dispatch")

    score += contractor.rating
    return round(score, 2), reasons


def match_contractors(db: Session, ticket: Ticket, category: Category, severity: Severity) -> list[CandidateMatch]:
    specialty = CATEGORY_TO_SPECIALTY[category]
    contractors = db.query(Contractor).all()
    scored: list[tuple[Contractor, float, list[str]]] = []
    for contractor in contractors:
        score, reasons = _score_contractor(contractor, specialty, severity)
        if score > 0:
            scored.append((contractor, score, reasons))

    scored.sort(key=lambda item: (-item[1], item[0].eta_minutes, item[0].distance_miles))
    matches: list[CandidateMatch] = []
    for rank, (contractor, score, reasons) in enumerate(scored[:3], start=1):
        match = CandidateMatch(
            id=f"match_{uuid.uuid4().hex[:12]}",
            ticket_id=ticket.id,
            contractor_id=contractor.id,
            score=score,
            reasons_json=json.dumps(reasons),
            rank=rank,
        )
        db.add(match)
        matches.append(match)
    return matches
