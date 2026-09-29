"""Dose event router: record dose outcomes and trigger escalation alerts.
"""

import logging
from datetime import datetime, time, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DoseEvent, Medication, Schedule, User
from app.routers.medicines import _resolve_patient_id
from app.routers.notifications import broadcast_missed_dose_alert
from app.schemas import DoseEventResponse, DoseEventUpdate
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dose-events", tags=["dose-events"])


def _apply_status(db: Session, dose: DoseEvent, new_status: str) -> DoseEvent:
    """Shared status-transition logic (also reused by the sync router)."""
    dose.status = new_status
    dose.updated_at = datetime.now(timezone.utc)

    if new_status == "taken":
        dose.taken_at = datetime.now(timezone.utc)
        med: Medication | None = (
            db.query(Medication)
            .join(Schedule, Schedule.medication_id == Medication.id)
            .filter(Schedule.id == dose.schedule_id)
            .first()
        )
        if med is not None and med.stock_qty > 0:
            med.stock_qty -= 1
            med.updated_at = datetime.now(timezone.utc)
            logger.info("Stock decremented for med %s (now %d)", med.id, med.stock_qty)
    elif new_status in ("skipped", "missed"):
        dose.taken_at = None

    if new_status == "missed":
        schedule: Schedule | None = (
            db.query(Schedule).filter(Schedule.id == dose.schedule_id).first()
        )
        med_name: str = "Unknown medication"
        patient_id: Optional[str] = None
        due_time: str = ""
        if schedule is not None:
            med: Medication | None = (
                db.query(Medication).filter(Medication.id == schedule.medication_id).first()
            )
            if med is not None:
                med_name = med.name
                patient_id = med.patient_id
                due_time = schedule.due_time
        if patient_id is not None:
            try:
                broadcast_missed_dose_alert(patient_id, med_name, due_time)
            except Exception:
                logger.exception("Failed broadcasting missed-dose alert")

    return dose


@router.post("/{dose_event_id}/status", response_model=DoseEventResponse)
def set_dose_status(
    dose_event_id: str,
    body: DoseEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DoseEventResponse:
    """Set dose status; decrement stock on 'taken', escalate on 'missed'."""
    try:
        dose: DoseEvent | None = (
            db.query(DoseEvent).filter(DoseEvent.id == dose_event_id).first()
        )
        if dose is None:
            raise HTTPException(status_code=404, detail="Dose event not found")

        schedule: Schedule | None = (
            db.query(Schedule).filter(Schedule.id == dose.schedule_id).first()
        )
        med: Medication | None = None
        if schedule is not None:
            med = db.query(Medication).filter(Medication.id == schedule.medication_id).first()
        if med is None:
            raise HTTPException(status_code=404, detail="Parent medication not found")

        _resolve_patient_id(med.patient_id, current_user, db)
        _apply_status(db, dose, body.status)
        db.commit()
        db.refresh(dose)
        return DoseEventResponse.model_validate(dose)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("set_dose_status failed")
        raise HTTPException(status_code=400, detail=f"Could not update dose: {exc}")


@router.get("/today", response_model=List[DoseEventResponse])
def todays_doses(
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DoseEventResponse]:
    """List today's dose events for the resolved patient, sorted by due time."""
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        now: datetime = datetime.now(timezone.utc)
        day_start: datetime = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        day_end: datetime = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

        rows: List[DoseEvent] = (
            db.query(DoseEvent)
            .join(Schedule, DoseEvent.schedule_id == Schedule.id)
            .join(Medication, Schedule.medication_id == Medication.id)
            .filter(
                and_(
                    Medication.patient_id == pid,
                    DoseEvent.due_timestamp >= day_start,
                    DoseEvent.due_timestamp <= day_end,
                )
            )
            .order_by(DoseEvent.due_timestamp)
            .all()
        )
        return [DoseEventResponse.model_validate(d) for d in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("todays_doses failed")
        raise HTTPException(status_code=400, detail=f"Could not list doses: {exc}")
