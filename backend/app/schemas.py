"""Pydantic validation schemas for the MediMate backend."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(patient|caretaker)$")
    preferred_language: str = Field(default="en", max_length=5)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    preferred_language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class MedicationCreate(BaseModel):
    patient_id: Optional[str] = None  # caretakers may supply the paired patient's id
    name: str = Field(min_length=1, max_length=160)
    dosage: Optional[str] = None
    form: Optional[str] = "Tablet"
    disease: Optional[str] = None
    body_part: Optional[str] = None
    notes: Optional[str] = None
    stock_qty: int = Field(default=0, ge=0)
    restock_notify_days: int = Field(default=7, ge=0, le=90)


class MedicationUpdate(BaseModel):
    patient_id: Optional[str] = None  # caretakers must supply the paired patient's id
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    dosage: Optional[str] = None
    form: Optional[str] = None
    disease: Optional[str] = None
    body_part: Optional[str] = None
    notes: Optional[str] = None
    stock_qty: Optional[int] = Field(default=None, ge=0)
    restock_notify_days: Optional[int] = Field(default=None, ge=0, le=90)


class MedicationResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    dosage: Optional[str] = None
    form: Optional[str] = "Tablet"
    disease: Optional[str] = None
    body_part: Optional[str] = None
    notes: Optional[str] = None
    stock_qty: int
    restock_notify_days: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    medication_id: str
    due_time: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")
    days_of_week: str = Field(default="daily", max_length=30)

    @field_validator("due_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        hh, mm, ss = value.split(":")
        if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59 and 0 <= int(ss) <= 59):
            raise ValueError("due_time must be a valid HH:MM:SS time")
        return value

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, value: str) -> str:
        if value == "daily":
            return value
        days = [d.strip().upper() for d in value.split(",")]
        valid = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
        if not days or any(d not in valid for d in days):
            raise ValueError("days_of_week must be 'daily' or comma-separated MON..SUN")
        return ",".join(days)


class ScheduleResponse(BaseModel):
    id: str
    medication_id: str
    due_time: str
    days_of_week: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoseEventResponse(BaseModel):
    id: str
    schedule_id: str
    due_timestamp: datetime
    status: str
    taken_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoseEventUpdate(BaseModel):
    status: str = Field(pattern="^(taken|skipped|missed)$")


class CareLinkGenerate(BaseModel):
    """Patient requests a pairing code. patient_id defaults to the caller."""

    patient_id: Optional[str] = None


class CareLinkGenerateResponse(BaseModel):
    invite_code: str
    patient_id: str


class CareLinkPair(BaseModel):
    invite_code: str = Field(min_length=4, max_length=12)


class CareLinkResponse(BaseModel):
    id: str
    patient_id: str
    caretaker_id: str
    invite_code: str
    status: str

    model_config = {"from_attributes": True}


class PatientSummary(BaseModel):
    id: str
    name: str
    email: EmailStr
    preferred_language: str


# ---------------------------------------------------------------------------
# Sync schemas (delta payload, Last-Write-Wins)
# ---------------------------------------------------------------------------


class SyncMedication(BaseModel):
    id: str
    patient_id: str
    name: str
    dosage: Optional[str] = None
    form: Optional[str] = "Tablet"
    disease: Optional[str] = None
    body_part: Optional[str] = None
    notes: Optional[str] = None
    stock_qty: int
    restock_notify_days: int
    updated_at: datetime


class SyncSchedule(BaseModel):
    id: str
    medication_id: str
    due_time: str
    days_of_week: str
    updated_at: datetime


class SyncDoseEvent(BaseModel):
    id: str
    schedule_id: str
    due_timestamp: datetime
    status: str
    taken_at: Optional[datetime] = None
    updated_at: datetime


class SyncPayload(BaseModel):
    medications: List[SyncMedication] = Field(default_factory=list)
    schedules: List[SyncSchedule] = Field(default_factory=list)
    dose_events: List[SyncDoseEvent] = Field(default_factory=list)


class SyncResult(BaseModel):
    """Server -> client delta: authoritative records the client should apply."""

    medications: List[SyncMedication] = Field(default_factory=list)
    schedules: List[SyncSchedule] = Field(default_factory=list)
    dose_events: List[SyncDoseEvent] = Field(default_factory=list)
    server_time: datetime


class WebSocketMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
