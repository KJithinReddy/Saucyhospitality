from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    submitted = "submitted"
    triaged = "triaged"
    matching = "matching"
    accepted = "accepted"
    en_route = "en_route"
    in_progress = "in_progress"
    completed = "completed"
    confirmed = "confirmed"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Urgency(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Category(str, Enum):
    commercial_refrigeration = "commercial_refrigeration"
    hvac = "hvac"
    plumbing = "plumbing"
    electrical = "electrical"
    cooking_equipment = "cooking_equipment"
    dishwashing = "dishwashing"
    general_maintenance = "general_maintenance"


class Specialty(str, Enum):
    refrigeration = "refrigeration"
    hvac = "hvac"
    plumbing = "plumbing"
    electrical = "electrical"
    cooking_equipment = "cooking_equipment"
    dishwashing = "dishwashing"
    general_facilities = "general_facilities"


CATEGORY_LABELS = {
    Category.commercial_refrigeration: "Commercial Refrigeration",
    Category.hvac: "HVAC",
    Category.plumbing: "Plumbing",
    Category.electrical: "Electrical",
    Category.cooking_equipment: "Cooking Equipment",
    Category.dishwashing: "Dishwashing Equipment",
    Category.general_maintenance: "General Maintenance",
}

SPECIALTY_LABELS = {
    Specialty.refrigeration: "Commercial Refrigeration Technician",
    Specialty.hvac: "Commercial HVAC Technician",
    Specialty.plumbing: "Restaurant Plumbing Specialist",
    Specialty.electrical: "Commercial Electrician",
    Specialty.cooking_equipment: "Cooking Equipment Technician",
    Specialty.dishwashing: "Warewashing Equipment Technician",
    Specialty.general_facilities: "General Facilities Technician",
}

CATEGORY_TO_SPECIALTY = {
    Category.commercial_refrigeration: Specialty.refrigeration,
    Category.hvac: Specialty.hvac,
    Category.plumbing: Specialty.plumbing,
    Category.electrical: Specialty.electrical,
    Category.cooking_equipment: Specialty.cooking_equipment,
    Category.dishwashing: Specialty.dishwashing,
    Category.general_maintenance: Specialty.general_facilities,
}

STATUS_LABELS = {
    TicketStatus.submitted: "Reported",
    TicketStatus.triaged: "Assessed",
    TicketStatus.matching: "Matching contractors",
    TicketStatus.accepted: "Technician assigned",
    TicketStatus.en_route: "En route",
    TicketStatus.in_progress: "Repair in progress",
    TicketStatus.completed: "Repair completed",
    TicketStatus.confirmed: "Confirmed complete",
}


class RestaurantOut(BaseModel):
    id: str
    name: str
    address: str
    city: str
    neighborhood: str
    contact_name: str

    model_config = {"from_attributes": True}


class ContractorOut(BaseModel):
    id: str
    name: str
    company: str
    specialty: str
    specialty_label: str
    secondary_specialty: Optional[str] = None
    city: str
    service_area: str
    available: bool
    emergency_available: bool
    rating: float
    jobs_completed: int
    eta_minutes: int
    distance_miles: float
    photo_initials: str
    blurb: str

    model_config = {"from_attributes": True}


class AssessmentOut(BaseModel):
    category: str
    category_label: str
    severity: Severity
    possible_issue: str
    recommended_specialty: str
    recommended_specialty_label: str
    observations: list[str]
    immediate_action: str
    source: Literal["openrouter", "fallback"]
    model_id: Optional[str] = None


class CandidateMatchOut(BaseModel):
    id: str
    contractor: ContractorOut
    score: float
    reasons: list[str]
    rank: int


class StatusEventOut(BaseModel):
    id: str
    status: TicketStatus
    status_label: str
    actor_role: str
    actor_name: str
    note: Optional[str] = None
    created_at: datetime


class TicketOut(BaseModel):
    id: str
    status: TicketStatus
    status_label: str
    title: str
    description: str
    location_note: str
    urgency: Urgency
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    completion_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    restaurant: RestaurantOut
    assessment: Optional[AssessmentOut] = None
    matches: list[CandidateMatchOut] = Field(default_factory=list)
    assigned_contractor: Optional[ContractorOut] = None
    events: list[StatusEventOut] = Field(default_factory=list)


class TicketListOut(BaseModel):
    tickets: list[TicketOut]


class StatusUpdateIn(BaseModel):
    status: TicketStatus
    contractor_id: str
    note: Optional[str] = None


class AcceptIn(BaseModel):
    contractor_id: str


class ConfirmIn(BaseModel):
    note: Optional[str] = None


class HealthOut(BaseModel):
    status: str
    runtime_writable: bool
    openrouter_configured: bool
    ticket_count: int
