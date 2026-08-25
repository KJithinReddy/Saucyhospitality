from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    neighborhood: Mapped[str] = mapped_column(String, nullable=False)
    contact_name: Mapped[str] = mapped_column(String, nullable=False)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="restaurant")


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    specialty: Mapped[str] = mapped_column(String, nullable=False)
    secondary_specialty: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=False)
    service_area: Mapped[str] = mapped_column(String, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    emergency_available: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Float, default=4.8)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=120)
    eta_minutes: Mapped[int] = mapped_column(Integer, default=45)
    distance_miles: Mapped[float] = mapped_column(Float, default=4.2)
    photo_initials: Mapped[str] = mapped_column(String, default="CT")
    blurb: Mapped[str] = mapped_column(Text, default="")

    matches: Mapped[list["CandidateMatch"]] = relationship(back_populates="contractor")
    assigned_tickets: Mapped[list["Ticket"]] = relationship(back_populates="assigned_contractor")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    assigned_contractor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("contractors.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="submitted", index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_note: Mapped[str] = mapped_column(String, default="")
    urgency: Mapped[str] = mapped_column(String, default="high")
    photo_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completion_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    restaurant: Mapped[Restaurant] = relationship(back_populates="tickets")
    assigned_contractor: Mapped[Optional[Contractor]] = relationship(back_populates="assigned_tickets")
    assessment: Mapped[Optional["Assessment"]] = relationship(back_populates="ticket", uselist=False)
    matches: Mapped[list["CandidateMatch"]] = relationship(back_populates="ticket")
    events: Mapped[list["StatusEvent"]] = relationship(back_populates="ticket", order_by="StatusEvent.created_at")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    possible_issue: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_specialty: Mapped[str] = mapped_column(String, nullable=False)
    observations_json: Mapped[str] = mapped_column(Text, default="[]")
    immediate_action: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, default="fallback")
    model_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="assessment")


class CandidateMatch(Base):
    __tablename__ = "candidate_matches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    contractor_id: Mapped[str] = mapped_column(ForeignKey("contractors.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    rank: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="matches")
    contractor: Mapped[Contractor] = relationship(back_populates="matches")


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    actor_role: Mapped[str] = mapped_column(String, nullable=False)
    actor_name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="events")
