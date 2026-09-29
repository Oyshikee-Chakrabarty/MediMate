"""Schedule router: create dose schedules with 30-day dose event generation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DoseEvent, Medication, Schedule, User
from app.routers.medicines import _resolve_patient_id
from app.schemas import ScheduleCreate, ScheduleResponse
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])

DAYS_AHEAD: int = 30
WEEKDAY_MAP: dict = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"}


def _schedule_runs_today(days_of_week: str, day: datetime) -> bool:
    if days_of_week.strip().lower() == "daily":
        return True
    wanted: set = {d.strip().upper() for d in days_of_week.split(",")}
    return WEEKDAY_MAP.get(day.weekday()) in wanted


def generate_dose_events(
    db: Session, schedule: Schedule, medication: Medication, days: int = DAYS_AHEAD
) -> List[DoseEvent]:
    """Generate `days` days of pending DoseEvents for a schedule."""
    now: datetime = datetime.now(timezone.utc)
    events: List[DoseEvent] = []
    hh, mm, ss = (int(p) for p in schedule.due_time.split(":"))

    for offset in range(days):
        day: datetime = (now + timedelta(days=offset)).replace(
            hour=hh, minute=mm, second=ss, microsecond=0
        )
        if not _schedule_runs_today(schedule.days_of_week, day):
            continue
        events.append(
            DoseEvent(
                schedule_id=schedule.id,
                due_timestamp=day,
                status="pending",
            )
        )
    db.add_all(events)
    return events


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    body: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Create a schedule attached to a medication; auto-generate 30-day doses."""
    try:
        med: Medication | None = (
            db.query(Medication).filter(Medication.id == body.medication_id).first()
        )
        if med is None:
            raise HTTPException(status_code=404, detail="Medication not found")
        _resolve_patient_id(med.patient_id, current_user, db)

        schedule: Schedule = Schedule(
            medication_id=med.id,
            due_time=body.due_time,
            days_of_week=body.days_of_week,
        )
        db.add(schedule)
        db.flush()  # assign schedule.id before generating dose events

        events: List[DoseEvent] = generate_dose_events(db, schedule, med)
        db.commit()
        db.refresh(schedule)

        logger.info(
            "Schedule %s created for med %s with %d dose events",
            schedule.id, med.id, len(events),
        )
        return ScheduleResponse.model_validate(schedule)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("create_schedule failed")
        raise HTTPException(status_code=400, detail=f"Could not create schedule: {exc}")


@router.get("", response_model=List[ScheduleResponse])
def list_schedules(
    medication_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ScheduleResponse]:
    """List schedules filtered by medication or patient."""
    try:
        if medication_id is not None:
            med: Medication | None = (
                db.query(Medication).filter(Medication.id == medication_id).first()
            )
            if med is None:
                raise HTTPException(status_code=404, detail="Medication not found")
            _resolve_patient_id(med.patient_id, current_user, db)
            rows: List[Schedule] = (
                db.query(Schedule).filter(Schedule.medication_id == medication_id).all()
            )
        else:
            pid: str = _resolve_patient_id(patient_id, current_user, db)
            rows = (
                db.query(Schedule)
                .join(Medication, Schedule.medication_id == Medication.id)
                .filter(Medication.patient_id == pid)
                .all()
            )
        return [ScheduleResponse.model_validate(s) for s in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_schedules failed")
        raise HTTPException(status_code=400, detail=f"Could not list schedules: {exc}")


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a schedule and all of its dose events."""
    try:
        schedule: Schedule | None = (
            db.query(Schedule).filter(Schedule.id == schedule_id).first()
        )
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        med: Medication | None = (
            db.query(Medication).filter(Medication.id == schedule.medication_id).first()
        )
        if med is not None:
            _resolve_patient_id(med.patient_id, current_user, db)

        db.query(DoseEvent).filter(DoseEvent.schedule_id == schedule_id).delete()
        db.delete(schedule)
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("delete_schedule failed")
        raise HTTPException(status_code=400, detail=f"Could not delete schedule: {exc}")
