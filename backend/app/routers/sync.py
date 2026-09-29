"""Delta synchronization router implementing Last-Write-Wins (LWW).
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DoseEvent, Medication, Schedule, User
from app.routers.dose_events import _apply_status
from app.routers.notifications import broadcast_missed_dose_alert
from app.schemas import (
    SyncDoseEvent,
    SyncMedication,
    SyncPayload,
    SyncResult,
    SyncSchedule,
)
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


def _naive(dt: datetime) -> datetime:
    """Normalize datetimes for comparison (SQLite rows are naive)."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _sync_medications(db: Session, user: User, items: List[SyncMedication], result: SyncResult) -> None:
    for item in items:
        try:
            med: Medication | None = db.query(Medication).filter(Medication.id == item.id).first()
            if med is None:
                # New record from client: insert if it belongs to this user.
                if item.patient_id != user.id:
                    continue
                med = Medication(
                    id=item.id,
                    patient_id=item.patient_id,
                    name=item.name,
                    stock_qty=item.stock_qty,
                    restock_notify_days=item.restock_notify_days,
                    updated_at=item.updated_at,
                )
                db.add(med)
                result.medications.append(item)
                continue

            if med.patient_id != user.id:
                continue  # never touch other users' rows

            if _naive(item.updated_at) > _naive(med.updated_at):
                med.name = item.name
                med.stock_qty = item.stock_qty
                med.restock_notify_days = item.restock_notify_days
                med.updated_at = item.updated_at
                result.medications.append(item)
            else:
                # Server row is authoritative; hand it back to the client.
                result.medications.append(
                    SyncMedication(
                        id=med.id,
                        patient_id=med.patient_id,
                        name=med.name,
                        stock_qty=med.stock_qty,
                        restock_notify_days=med.restock_notify_days,
                        updated_at=med.updated_at,
                    )
                )
        except Exception:
            logger.exception("LWW sync failed for medication %s", item.id)


def _sync_schedules(db: Session, user: User, items: List[SyncSchedule], result: SyncResult) -> None:
    for item in items:
        try:
            sched: Schedule | None = db.query(Schedule).filter(Schedule.id == item.id).first()
            if sched is None:
                med: Medication | None = (
                    db.query(Medication).filter(Medication.id == item.medication_id).first()
                )
                if med is None or med.patient_id != user.id:
                    continue
                sched = Schedule(
                    id=item.id,
                    medication_id=item.medication_id,
                    due_time=item.due_time,
                    days_of_week=item.days_of_week,
                    updated_at=item.updated_at,
                )
                db.add(sched)
                result.schedules.append(item)
                continue

            med = db.query(Medication).filter(Medication.id == sched.medication_id).first()
            if med is None or med.patient_id != user.id:
                continue

            if _naive(item.updated_at) > _naive(sched.updated_at):
                sched.due_time = item.due_time
                sched.days_of_week = item.days_of_week
                sched.updated_at = item.updated_at
                result.schedules.append(item)
            else:
                result.schedules.append(
                    SyncSchedule(
                        id=sched.id,
                        medication_id=sched.medication_id,
                        due_time=sched.due_time,
                        days_of_week=sched.days_of_week,
                        updated_at=sched.updated_at,
                    )
                )
        except Exception:
            logger.exception("LWW sync failed for schedule %s", item.id)


def _sync_dose_events(db: Session, user: User, items: List[SyncDoseEvent], result: SyncResult) -> None:
    for item in items:
        try:
            dose: DoseEvent | None = db.query(DoseEvent).filter(DoseEvent.id == item.id).first()
            if dose is None:
                sched: Schedule | None = (
                    db.query(Schedule).filter(Schedule.id == item.schedule_id).first()
                )
                if sched is None:
                    continue
                med: Medication | None = (
                    db.query(Medication).filter(Medication.id == sched.medication_id).first()
                )
                if med is None or med.patient_id != user.id:
                    continue
                dose = DoseEvent(
                    id=item.id,
                    schedule_id=item.schedule_id,
                    due_timestamp=item.due_timestamp,
                    status=item.status,
                    taken_at=item.taken_at,
                    updated_at=item.updated_at,
                )
                db.add(dose)
                result.dose_events.append(item)
                continue

            sched = db.query(Schedule).filter(Schedule.id == dose.schedule_id).first()
            med = None
            if sched is not None:
                med = db.query(Medication).filter(Medication.id == sched.medication_id).first()
            if med is None or med.patient_id != user.id:
                continue

            if _naive(item.updated_at) > _naive(dose.updated_at):
                # Reuse endpoint semantics (stock decrement + escalation) for
                # transitions that actually change status.
                if item.status != dose.status:
                    _apply_status(db, dose, item.status)
                    dose.updated_at = item.updated_at
                    if item.taken_at is not None:
                        dose.taken_at = item.taken_at
                else:
                    dose.updated_at = item.updated_at
                    dose.taken_at = item.taken_at
                result.dose_events.append(item)
            else:
                result.dose_events.append(
                    SyncDoseEvent(
                        id=dose.id,
                        schedule_id=dose.schedule_id,
                        due_timestamp=dose.due_timestamp,
                        status=dose.status,
                        taken_at=dose.taken_at,
                        updated_at=dose.updated_at,
                    )
                )
        except Exception:
            logger.exception("LWW sync failed for dose event %s", item.id)


@router.post("", response_model=SyncResult)
def sync_payload(
    payload: SyncPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResult:
    """LWW delta sync: apply newer client rows, return authoritative server rows."""
    try:
        result: SyncResult = SyncResult(server_time=datetime.now(timezone.utc))

        _sync_medications(db, current_user, payload.medications, result)
        _sync_schedules(db, current_user, payload.schedules, result)
        _sync_dose_events(db, current_user, payload.dose_events, result)

        db.commit()
        logger.info(
            "Sync for user %s: %d meds, %d schedules, %d doses processed",
            current_user.id,
            len(payload.medications),
            len(payload.schedules),
            len(payload.dose_events),
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("sync failed")
        raise HTTPException(status_code=400, detail=f"Sync failed: {exc}")
