"""SQLAlchemy ORM models for MediMate backend database.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    name: str = Column(String(120), nullable=False)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)
    role: str = Column(String(20), nullable=False, default="patient")  # 'patient' | 'caretaker'
    preferred_language: str = Column(String(5), nullable=False, default="en")
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_now)

    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    links_as_patient = relationship(
        "CareLink", foreign_keys="CareLink.patient_id", back_populates="patient"
    )
    links_as_caretaker = relationship(
        "CareLink", foreign_keys="CareLink.caretaker_id", back_populates="caretaker"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class CareLink(Base):
    __tablename__ = "care_links"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    patient_id: str = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    caretaker_id: str = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    # 6-digit alphanumeric invite code; unique among *pending* links
    invite_code: str = Column(String(12), unique=True, nullable=False, index=True)
    status: str = Column(String(20), nullable=False, default="pending")  # 'pending' | 'active'

    patient = relationship("User", foreign_keys=[patient_id], back_populates="links_as_patient")
    caretaker = relationship("User", foreign_keys=[caretaker_id], back_populates="links_as_caretaker")

    def __repr__(self) -> str:
        return f"<CareLink id={self.id} patient={self.patient_id} caretaker={self.caretaker_id} status={self.status}>"


class Medication(Base):
    __tablename__ = "medications"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    patient_id: str = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: str = Column(String(160), nullable=False)
    dosage: str = Column(String(80), nullable=True)
    form: str = Column(String(50), nullable=True, default="Tablet")
    disease: str = Column(String(100), nullable=True)
    body_part: str = Column(String(100), nullable=True)
    notes: str = Column(String(255), nullable=True)
    stock_qty: int = Column(Integer, nullable=False, default=0)
    restock_notify_days: int = Column(Integer, nullable=False, default=7)
    updated_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
    # SQLite local-only column; kept for schema parity with the client DB
    is_dirty: int = Column(Integer, nullable=False, default=0)

    patient = relationship("User", back_populates="medications")
    schedules = relationship("Schedule", back_populates="medication", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name} stock={self.stock_qty}>"


class Schedule(Base):
    __tablename__ = "schedules"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    medication_id: str = Column(String(36), ForeignKey("medications.id"), nullable=False, index=True)
    due_time: str = Column(String(8), nullable=False)  # "HH:MM:SS"
    days_of_week: str = Column(String(30), nullable=False, default="daily")  # "daily" | "MON,WED,FRI"
    updated_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    medication = relationship("Medication", back_populates="schedules")
    dose_events = relationship(
        "DoseEvent", back_populates="schedule", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Schedule id={self.id} med={self.medication_id} due_time={self.due_time}>"


class DoseEvent(Base):
    __tablename__ = "dose_events"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    schedule_id: str = Column(String(36), ForeignKey("schedules.id"), nullable=False, index=True)
    due_timestamp: datetime = Column(DateTime(timezone=True), nullable=False)
    status: str = Column(String(15), nullable=False, default="pending")  # 'pending'|'taken'|'skipped'|'missed'
    taken_at: datetime = Column(DateTime(timezone=True), nullable=True)
    updated_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
    # SQLite local-only column; kept for schema parity with the client DB
    is_dirty: int = Column(Integer, nullable=False, default=0)

    schedule = relationship("Schedule", back_populates="dose_events")

    def __repr__(self) -> str:
        return f"<DoseEvent id={self.id} status={self.status} due={self.due_timestamp}>"
