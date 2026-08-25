from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import StatusEvent, Ticket, utcnow
from app.schemas import TicketStatus


CONTRACTOR_TRANSITIONS = {
    TicketStatus.accepted: TicketStatus.en_route,
    TicketStatus.en_route: TicketStatus.in_progress,
    TicketStatus.in_progress: TicketStatus.completed,
}

CONTRACTOR_ALLOWED = set(CONTRACTOR_TRANSITIONS.values())


def add_event(
    db: Session,
    ticket: Ticket,
    status: TicketStatus,
    actor_role: str,
    actor_name: str,
    note: str | None = None,
) -> StatusEvent:
    event = StatusEvent(
        id=f"evt_{uuid.uuid4().hex[:12]}",
        ticket_id=ticket.id,
        status=status.value,
        actor_role=actor_role,
        actor_name=actor_name,
        note=note,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    ticket.status = status.value
    ticket.updated_at = utcnow()
    return event


def advance_contractor_status(ticket: Ticket, next_status: TicketStatus) -> TicketStatus:
    current = TicketStatus(ticket.status)
    expected = CONTRACTOR_TRANSITIONS.get(current)
    if expected != next_status:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move from {current.value} to {next_status.value}.",
        )
    return next_status
