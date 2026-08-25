from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Assessment, CandidateMatch, StatusEvent, Ticket, utcnow
from app.schemas import AcceptIn, ConfirmIn, StatusUpdateIn, TicketListOut, TicketOut, TicketStatus
from app.seed import RESTAURANT, seed_core
from app.serializers import ticket_out
from app.services.matching import match_contractors
from app.services.media import encode_photo_for_triage, save_upload
from app.services.triage import analyze_issue
from app.services.workflow import add_event, advance_contractor_status

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _ticket_query(db: Session):
    return db.query(Ticket).options(
        joinedload(Ticket.restaurant),
        joinedload(Ticket.assigned_contractor),
        joinedload(Ticket.assessment),
        joinedload(Ticket.matches),
        joinedload(Ticket.events),
    )


def _get_ticket(db: Session, ticket_id: str) -> Ticket:
    ticket = _ticket_query(db).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _image_data_url(photo_path: str | None) -> str | None:
    return encode_photo_for_triage(photo_path)


@router.post("", response_model=TicketOut)
async def create_ticket(
    description: str = Form(...),
    urgency: str = Form("high"),
    location_note: str = Form("Walk-in cooler, kitchen back line"),
    photo: UploadFile | None = File(default=None),
    video: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    cleaned = description.strip()
    if len(cleaned) < 10:
        raise HTTPException(status_code=400, detail="Please describe the issue in a bit more detail.")

    ticket_id = f"tkt_{uuid.uuid4().hex[:10]}"
    photo_path = await save_upload(ticket_id, photo, "photo")
    video_path = await save_upload(ticket_id, video, "video")
    title = cleaned.split(".")[0][:80] or "Maintenance issue"

    ticket = Ticket(
        id=ticket_id,
        restaurant_id=RESTAURANT.id,
        status=TicketStatus.submitted.value,
        title=title,
        description=cleaned,
        location_note=location_note.strip() or "Kitchen",
        urgency=urgency,
        photo_path=photo_path,
        video_path=video_path,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(ticket)
    add_event(db, ticket, TicketStatus.submitted, "restaurant", "Maya Chen", "Issue reported by kitchen staff.")
    db.commit()
    return ticket_out(_get_ticket(db, ticket_id))


@router.get("", response_model=TicketListOut)
def list_tickets(view: str = "restaurant", contractor_id: str | None = None, db: Session = Depends(get_db)):
    query = _ticket_query(db).order_by(Ticket.created_at.desc())
    tickets = query.all()
    if view == "contractor":
        if not contractor_id:
            raise HTTPException(status_code=400, detail="contractor_id is required for contractor view")
        filtered = []
        for ticket in tickets:
            is_assigned = ticket.assigned_contractor_id == contractor_id
            is_candidate = ticket.status == TicketStatus.matching.value and any(
                match.contractor_id == contractor_id for match in ticket.matches
            )
            if is_assigned or is_candidate:
                filtered.append(ticket)
        tickets = filtered
    return TicketListOut(tickets=[ticket_out(ticket) for ticket in tickets])


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    return ticket_out(_get_ticket(db, ticket_id))


@router.post("/{ticket_id}/triage", response_model=TicketOut)
async def triage_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = _get_ticket(db, ticket_id)
    if ticket.status not in {TicketStatus.submitted.value, TicketStatus.triaged.value, TicketStatus.matching.value}:
        return ticket_out(ticket)

    result = await analyze_issue(
        ticket.description,
        ticket.urgency,
        ticket.location_note,
        _image_data_url(ticket.photo_path),
    )
    if ticket.assessment:
        db.delete(ticket.assessment)
        db.flush()
    for match in list(ticket.matches):
        db.delete(match)
    db.flush()

    assessment = Assessment(
        id=f"asm_{uuid.uuid4().hex[:12]}",
        ticket_id=ticket.id,
        category=result.category.value,
        severity=result.severity.value,
        possible_issue=result.possible_issue,
        recommended_specialty=result.recommended_specialty.value,
        observations_json=json.dumps(result.observations),
        immediate_action=result.immediate_action,
        source=result.source,
        model_id=result.model_id,
    )
    db.add(assessment)
    add_event(
        db,
        ticket,
        TicketStatus.triaged,
        "system",
        "Saucy triage",
        f"Advisory assessment: {result.category.value.replace('_', ' ')}.",
    )
    match_contractors(db, ticket, result.category, result.severity)
    add_event(
        db,
        ticket,
        TicketStatus.matching,
        "system",
        "Saucy matching",
        "Qualified contractors identified for this repair.",
    )
    db.commit()
    return ticket_out(_get_ticket(db, ticket_id))


@router.post("/{ticket_id}/accept", response_model=TicketOut)
def accept_ticket(ticket_id: str, payload: AcceptIn, db: Session = Depends(get_db)):
    ticket = _get_ticket(db, ticket_id)
    if ticket.status != TicketStatus.matching.value:
        raise HTTPException(status_code=409, detail="This job is no longer available.")
    match = next((item for item in ticket.matches if item.contractor_id == payload.contractor_id), None)
    if match is None:
        raise HTTPException(status_code=403, detail="This contractor is not a match for the job.")
    ticket.assigned_contractor_id = payload.contractor_id
    contractor = match.contractor
    add_event(
        db,
        ticket,
        TicketStatus.accepted,
        "contractor",
        contractor.name,
        f"{contractor.company} accepted the job.",
    )
    db.commit()
    return ticket_out(_get_ticket(db, ticket_id))


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_status(ticket_id: str, payload: StatusUpdateIn, db: Session = Depends(get_db)):
    ticket = _get_ticket(db, ticket_id)
    if ticket.assigned_contractor_id != payload.contractor_id:
        raise HTTPException(status_code=403, detail="Only the assigned contractor can update this job.")
    next_status = advance_contractor_status(ticket, payload.status)
    if next_status == TicketStatus.completed:
        ticket.completion_note = payload.note or "Repair completed. Equipment restored to service."
    notes = {
        TicketStatus.en_route: "Technician is traveling to the restaurant.",
        TicketStatus.in_progress: "Onsite diagnosis and repair started.",
        TicketStatus.completed: ticket.completion_note,
    }
    add_event(
        db,
        ticket,
        next_status,
        "contractor",
        ticket.assigned_contractor.name if ticket.assigned_contractor else "Contractor",
        payload.note or notes[next_status],
    )
    db.commit()
    return ticket_out(_get_ticket(db, ticket_id))


@router.post("/{ticket_id}/confirm", response_model=TicketOut)
def confirm_ticket(ticket_id: str, payload: ConfirmIn | None = None, db: Session = Depends(get_db)):
    ticket = _get_ticket(db, ticket_id)
    if ticket.status != TicketStatus.completed.value:
        raise HTTPException(status_code=409, detail="The restaurant can confirm only after the repair is completed.")
    add_event(
        db,
        ticket,
        TicketStatus.confirmed,
        "restaurant",
        ticket.restaurant.contact_name,
        (payload.note if payload else None) or "Kitchen confirmed the repair is complete.",
    )
    db.commit()
    return ticket_out(_get_ticket(db, ticket_id))


@router.post("/demo/reset")
def reset_demo(x_demo_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    if x_demo_token != settings.demo_reset_token:
        raise HTTPException(status_code=401, detail="Invalid demo reset token")
    db.query(StatusEvent).delete()
    db.query(CandidateMatch).delete()
    db.query(Assessment).delete()
    db.query(Ticket).delete()
    db.commit()
    seed_core(db)
    upload_root = settings.upload_path
    if upload_root.exists():
        for child in upload_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            elif child.name != ".write_probe":
                child.unlink(missing_ok=True)
    return {"ok": True}
