"""Dose event router: record dose outcomes and trigger escalation alerts.

Phase 3, Task 3.1:
- POST /dose-events/{id}/status : set status to taken|skipped|missed;
  decrement medication stock_qty when status is 'taken'; broadcast a
  MISSED_DOSE_ALERT to paired caretakers when status is 'missed'
- GET /dose-events/today : list today's dose events for a patient
"""

import calendar
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DoseEvent, Medication, Schedule, User
from app.routers.medicines import _resolve_patient_id
from app.routers.notifications import broadcast_missed_dose_alert
from app.routers.schedules import _schedule_runs_today
from app.schemas import (
    DoseDetailItem,
    DoseEventResponse,
    DoseEventUpdate,
    DoseHistoryDaySummary,
    DoseHistoryResponse,
)
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
        try:
            from app.routers.notifications import broadcast_mutation
            broadcast_mutation(
                med.patient_id,
                "DOSE_STATUS_CHANGED",
                {
                    "dose_id": dose.id,
                    "schedule_id": dose.schedule_id,
                    "status": dose.status,
                    "medication_id": med.id,
                },
            )
        except Exception:
            pass

        if body.status == "taken" and med is not None:
            try:
                from app.services.dose_tracking import check_and_broadcast_reschedule_alert
                check_and_broadcast_reschedule_alert(db, med)
            except Exception:
                logger.exception("Failed checking reschedule alert after dose taken")
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
        now: datetime = datetime.now()
        day_start: datetime = datetime.combine(now.date(), time.min)
        day_end: datetime = datetime.combine(now.date(), time.max)

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


@router.get("/history", response_model=DoseHistoryResponse)
def dose_history(
    year: int,
    month: int,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DoseHistoryResponse:
    """Return calendar adherence history for a given year and month.

    Status color rules:
    - 'blue': all medications are taken
    - 'red': none of the medication is taken (past date)
    - 'hollow': one or few medication missed, but some taken
    - 'green_dot': scheduled medication date in the future
    - 'normal': no scheduled medications
    """
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        num_days: int = calendar.monthrange(year, month)[1]
        m_start: datetime = datetime(year, month, 1, 0, 0, 0)
        m_end: datetime = datetime(year, month, num_days, 23, 59, 59)
        today_d = date.today()

        # Query all dose events for patient in this month
        events: List[DoseEvent] = (
            db.query(DoseEvent)
            .join(Schedule, DoseEvent.schedule_id == Schedule.id)
            .join(Medication, Schedule.medication_id == Medication.id)
            .filter(
                and_(
                    Medication.patient_id == pid,
                    DoseEvent.due_timestamp >= m_start,
                    DoseEvent.due_timestamp <= m_end,
                )
            )
            .order_by(DoseEvent.due_timestamp)
            .all()
        )

        events_by_date: Dict[date, List[DoseEvent]] = {}
        for ev in events:
            ev_date = ev.due_timestamp.date() if isinstance(ev.due_timestamp, datetime) else ev.due_timestamp
            events_by_date.setdefault(ev_date, []).append(ev)

        # Query active schedules for checking future days if dose events aren't pre-generated
        active_schedules: List[Schedule] = (
            db.query(Schedule)
            .join(Medication, Schedule.medication_id == Medication.id)
            .filter(Medication.patient_id == pid)
            .all()
        )

        day_summaries: List[DoseHistoryDaySummary] = []
        for d in range(1, num_days + 1):
            cur_d = date(year, month, d)
            cur_str = cur_d.strftime("%Y-%m-%d")
            day_evs = events_by_date.get(cur_d, [])

            total = len(day_evs)
            taken = sum(1 for e in day_evs if e.status == "taken")
            missed = sum(1 for e in day_evs if e.status == "missed")
            skipped = sum(1 for e in day_evs if e.status == "skipped")
            pending = sum(1 for e in day_evs if e.status == "pending")

            # If no persisted dose events yet and date is future, check recurring schedules
            if total == 0 and cur_d >= today_d:
                for s in active_schedules:
                    if _schedule_runs_today(s.days_of_week, cur_d):
                        total += 1
                        pending += 1

            has_sched = total > 0

            # Determine color coding based on user specification:
            # - blue marked date: all medications are taken
            # - red: none of the medication is taken
            # - hollow circle: one or few medication missed, but some taken
            # - green dotted date: scheduled medication date in the future
            if cur_d > today_d:
                color = "green_dot" if has_sched else "normal"
            elif not has_sched:
                color = "normal"
            else:
                if taken > 0 and taken == total:
                    color = "blue"
                elif taken == 0:
                    color = "red"
                else:
                    color = "hollow"

            day_summaries.append(
                DoseHistoryDaySummary(
                    date=cur_str,
                    day=d,
                    has_schedule=has_sched,
                    total_doses=total,
                    taken_doses=taken,
                    missed_doses=missed,
                    skipped_doses=skipped,
                    pending_doses=pending,
                    status_color=color,
                )
            )

        return DoseHistoryResponse(
            year=year,
            month=month,
            days=day_summaries,
            today=today_d.strftime("%Y-%m-%d"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("dose_history failed")
        raise HTTPException(status_code=400, detail=f"Could not load dose history: {exc}")


@router.get("/by-date", response_model=List[DoseDetailItem])
def doses_by_date(
    date_str: str,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DoseDetailItem]:
    """Return all scheduled doses for a specific day with medication details."""
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

        d_start = datetime.combine(target_date, time.min)
        d_end = datetime.combine(target_date, time.max)

        rows = (
            db.query(DoseEvent, Schedule, Medication)
            .join(Schedule, DoseEvent.schedule_id == Schedule.id)
            .join(Medication, Schedule.medication_id == Medication.id)
            .filter(
                and_(
                    Medication.patient_id == pid,
                    DoseEvent.due_timestamp >= d_start,
                    DoseEvent.due_timestamp <= d_end,
                )
            )
            .order_by(DoseEvent.due_timestamp)
            .all()
        )

        results: List[DoseDetailItem] = []
        seen_schedule_ids = set()
        for dose, sched, med in rows:
            seen_schedule_ids.add(sched.id)
            results.append(
                DoseDetailItem(
                    id=dose.id,
                    schedule_id=sched.id,
                    medication_id=med.id,
                    medication_name=med.name,
                    dosage=med.dosage,
                    form=med.form,
                    disease=med.disease,
                    due_time=sched.due_time,
                    due_timestamp=dose.due_timestamp,
                    status=dose.status,
                    taken_at=dose.taken_at,
                )
            )

        # For future dates or dates where events weren't instantiated in DB, also pull matching active schedules
        if target_date >= date.today():
            active_scheds = (
                db.query(Schedule, Medication)
                .join(Medication, Schedule.medication_id == Medication.id)
                .filter(Medication.patient_id == pid)
                .order_by(Schedule.due_time)
                .all()
            )
            for sched, med in active_scheds:
                if sched.id not in seen_schedule_ids and _schedule_runs_today(sched.days_of_week, target_date):
                    try:
                        hh, mm, ss = [int(x) for x in sched.due_time.split(":")]
                    except Exception:
                        hh, mm, ss = 9, 0, 0
                    due_dt = datetime.combine(target_date, time(hh, mm, ss))
                    results.append(
                        DoseDetailItem(
                            id=f"sched_{sched.id}_{date_str}",
                            schedule_id=sched.id,
                            medication_id=med.id,
                            medication_name=med.name,
                            dosage=med.dosage,
                            form=med.form,
                            disease=med.disease,
                            due_time=sched.due_time,
                            due_timestamp=due_dt,
                            status="pending",
                            taken_at=None,
                        )
                    )

        results.sort(key=lambda item: item.due_time)
        return results
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("doses_by_date failed")
        raise HTTPException(status_code=400, detail=f"Could not list doses by date: {exc}")
