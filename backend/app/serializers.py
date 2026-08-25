from __future__ import annotations

import json
from typing import Optional

from app.models import Assessment, CandidateMatch, Contractor, StatusEvent, Ticket
from app.schemas import (
    CATEGORY_LABELS,
    SPECIALTY_LABELS,
    STATUS_LABELS,
    AssessmentOut,
    CandidateMatchOut,
    Category,
    ContractorOut,
    Severity,
    Specialty,
    StatusEventOut,
    TicketOut,
    TicketStatus,
    Urgency,
)


def media_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"/uploads/{path}"


def contractor_out(contractor: Contractor) -> ContractorOut:
    specialty = Specialty(contractor.specialty)
    return ContractorOut(
        id=contractor.id,
        name=contractor.name,
        company=contractor.company,
        specialty=contractor.specialty,
        specialty_label=SPECIALTY_LABELS[specialty],
        secondary_specialty=contractor.secondary_specialty,
        city=contractor.city,
        service_area=contractor.service_area,
        available=contractor.available,
        emergency_available=contractor.emergency_available,
        rating=contractor.rating,
        jobs_completed=contractor.jobs_completed,
        eta_minutes=contractor.eta_minutes,
        distance_miles=contractor.distance_miles,
        photo_initials=contractor.photo_initials,
        blurb=contractor.blurb,
    )


def assessment_out(assessment: Assessment) -> AssessmentOut:
    category = Category(assessment.category)
    specialty = Specialty(assessment.recommended_specialty)
    return AssessmentOut(
        category=assessment.category,
        category_label=CATEGORY_LABELS[category],
        severity=Severity(assessment.severity),
        possible_issue=assessment.possible_issue,
        recommended_specialty=assessment.recommended_specialty,
        recommended_specialty_label=SPECIALTY_LABELS[specialty],
        observations=json.loads(assessment.observations_json or "[]"),
        immediate_action=assessment.immediate_action,
        source=assessment.source,  # type: ignore[arg-type]
        model_id=assessment.model_id,
    )


def match_out(match: CandidateMatch) -> CandidateMatchOut:
    return CandidateMatchOut(
        id=match.id,
        contractor=contractor_out(match.contractor),
        score=match.score,
        reasons=json.loads(match.reasons_json or "[]"),
        rank=match.rank,
    )


def event_out(event: StatusEvent) -> StatusEventOut:
    status = TicketStatus(event.status)
    return StatusEventOut(
        id=event.id,
        status=status,
        status_label=STATUS_LABELS[status],
        actor_role=event.actor_role,
        actor_name=event.actor_name,
        note=event.note,
        created_at=event.created_at,
    )


def ticket_out(ticket: Ticket) -> TicketOut:
    status = TicketStatus(ticket.status)
    matches = sorted(ticket.matches, key=lambda item: item.rank)
    return TicketOut(
        id=ticket.id,
        status=status,
        status_label=STATUS_LABELS[status],
        title=ticket.title,
        description=ticket.description,
        location_note=ticket.location_note,
        urgency=Urgency(ticket.urgency),
        photo_url=media_url(ticket.photo_path),
        video_url=media_url(ticket.video_path),
        completion_note=ticket.completion_note,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        restaurant=ticket.restaurant,
        assessment=assessment_out(ticket.assessment) if ticket.assessment else None,
        matches=[match_out(match) for match in matches],
        assigned_contractor=contractor_out(ticket.assigned_contractor) if ticket.assigned_contractor else None,
        events=[event_out(event) for event in sorted(ticket.events, key=lambda item: item.created_at)],
    )
