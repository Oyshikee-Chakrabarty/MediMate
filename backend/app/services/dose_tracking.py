"""Dose tracking and reschedule calculation service.

Calculates:
- Medication daily/weekly consumption rate based on active schedules.
- Remaining supply duration in days (how long until stock runs out).
- Projected reschedule due date and warning notification date.
- Realtime notification triggers for both patient and linked caretakers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import DoseEvent, Medication, Schedule, User

logger = logging.getLogger(__name__)


def calculate_medication_tracking(db: Session, medication: Medication) -> Dict[str, Any]:
    """Calculate dose frequency, remaining supply duration, and reschedule status."""
    schedules: List[Schedule] = (
        db.query(Schedule).filter(Schedule.medication_id == medication.id).all()
    )

    doses_per_week: float = 0.0
    for s in schedules:
        days_str = (s.days_of_week or "daily").strip().lower()
        if days_str == "daily":
            doses_per_week += 7.0
        else:
            days = [d.strip() for d in s.days_of_week.split(",") if d.strip()]
            doses_per_week += float(len(days))

    doses_per_day: float = doses_per_week / 7.0 if doses_per_week > 0 else 0.0

    # Human-readable frequency summary
    if len(schedules) == 0:
        freq_summary = "No schedule set"
    elif doses_per_day == 1.0 and len(schedules) == 1 and schedules[0].days_of_week.lower() == "daily":
        t = schedules[0].due_time[:5]
        freq_summary = f"Once daily ({t})"
    elif doses_per_day == 2.0 and len(schedules) == 2 and all(s.days_of_week.lower() == "daily" for s in schedules):
        freq_summary = "Twice daily"
    elif doses_per_day > 0 and all(s.days_of_week.lower() == "daily" for s in schedules):
        freq_summary = f"{len(schedules)} times daily ({doses_per_day:.0f} doses/day)"
    elif doses_per_day > 0:
        freq_summary = f"{doses_per_week:.0f} doses/week"
    else:
        freq_summary = "As needed"

    # Supply and reschedule calculation
    now = datetime.now()
    stock = medication.stock_qty

    if stock <= 0:
        days_supply_remaining = 0.0
        reschedule_due_date = now
        reschedule_status = "reschedule_now"
    elif doses_per_day > 0:
        days_supply_remaining = round(stock / doses_per_day, 1)
        reschedule_due_date = now + timedelta(days=days_supply_remaining)
        if days_supply_remaining <= float(medication.restock_notify_days):
            reschedule_status = "reschedule_soon"
        else:
            reschedule_status = "healthy"
    else:
        days_supply_remaining = 999.0
        reschedule_due_date = None
        reschedule_status = "healthy"

    reschedule_warning_date: Optional[datetime] = None
    if reschedule_due_date and doses_per_day > 0:
        warn_days = max(0.0, days_supply_remaining - float(medication.restock_notify_days))
        reschedule_warning_date = now + timedelta(days=warn_days)

    # Adherence metrics
    dose_events: List[DoseEvent] = (
        db.query(DoseEvent)
        .join(Schedule, DoseEvent.schedule_id == Schedule.id)
        .filter(Schedule.medication_id == medication.id)
        .all()
    )
    total_taken = sum(1 for d in dose_events if d.status == "taken")
    total_missed = sum(1 for d in dose_events if d.status == "missed")
    total_skipped = sum(1 for d in dose_events if d.status == "skipped")
    total_scheduled = len(dose_events)

    past_due_count = sum(1 for d in dose_events if d.status in ("taken", "missed", "skipped"))
    adherence_pct = (
        round((total_taken / past_due_count * 100), 1) if past_due_count > 0 else 100.0
    )

    patient = db.query(User).filter(User.id == medication.patient_id).first()
    patient_name = patient.name if patient else "Patient"

    is_alert_active = reschedule_status in ("reschedule_soon", "reschedule_now")

    return {
        "medication_id": medication.id,
        "medication_name": medication.name,
        "patient_id": medication.patient_id,
        "patient_name": patient_name,
        "dosage": medication.dosage,
        "form": medication.form or "Tablet",
        "disease": medication.disease,
        "stock_qty": medication.stock_qty,
        "restock_notify_days": medication.restock_notify_days,
        "doses_per_day": round(doses_per_day, 2),
        "doses_per_week": round(doses_per_week, 1),
        "frequency_summary": freq_summary,
        "days_supply_remaining": days_supply_remaining,
        "reschedule_due_date": reschedule_due_date.isoformat() if reschedule_due_date else None,
        "reschedule_warning_date": (
            reschedule_warning_date.isoformat() if reschedule_warning_date else None
        ),
        "reschedule_status": reschedule_status,
        "is_reschedule_alert_active": is_alert_active,
        "total_doses_taken": total_taken,
        "total_doses_missed": total_missed,
        "total_doses_skipped": total_skipped,
        "total_doses_scheduled": total_scheduled,
        "adherence_pct": adherence_pct,
    }


def check_and_broadcast_reschedule_alert(
    db: Session, medication: Medication
) -> Optional[Dict[str, Any]]:
    """Broadcast RESCHEDULE_ALERT to patient and paired caretakers if supply is low or out."""
    tracking = calculate_medication_tracking(db, medication)
    if tracking["is_reschedule_alert_active"]:
        from app.routers.notifications import broadcast_mutation

        status = tracking["reschedule_status"]
        days = tracking["days_supply_remaining"]
        med_name = tracking["medication_name"]
        patient_name = tracking["patient_name"]

        if status == "reschedule_now":
            msg = (
                f"Alert: {med_name} is OUT OF STOCK for {patient_name}. "
                f"Immediate rescheduling required!"
            )
            urgency = "critical"
        else:
            msg = (
                f"Reschedule Alert: {med_name} for {patient_name} has only "
                f"{days:.0f} day(s) of doses left ({tracking['stock_qty']} doses remaining). "
                f"Please reschedule soon."
            )
            urgency = "warning"

        payload = {
            **tracking,
            "message": msg,
            "urgency": urgency,
            "alerted_at": datetime.now(timezone.utc).isoformat(),
        }
        broadcast_mutation(medication.patient_id, "RESCHEDULE_ALERT", payload)
        logger.info(
            "Broadcast RESCHEDULE_ALERT for med %s (patient %s, status %s)",
            medication.id,
            medication.patient_id,
            status,
        )
        return payload
    return None


def reschedule_medication(
    db: Session,
    medication: Medication,
    added_stock: int,
    new_due_times: Optional[List[str]] = None,
    new_days_of_week: Optional[str] = None,
    extend_days: int = 30,
) -> Dict[str, Any]:
    """Restock medication, optionally update schedule frequency, and generate extended dose events."""
    from app.routers.notifications import broadcast_mutation
    from app.routers.schedules import generate_dose_events

    medication.stock_qty += added_stock
    medication.updated_at = datetime.now(timezone.utc)
    db.flush()

    # If new schedule times are provided, update or create schedules
    if new_due_times:
        days_code = new_days_of_week or "daily"
        # Remove old schedules or add new ones
        for st in new_due_times:
            # Check if this due_time already exists
            existing = (
                db.query(Schedule)
                .filter(
                    Schedule.medication_id == medication.id,
                    Schedule.due_time == st,
                )
                .first()
            )
            if existing is None:
                new_sched = Schedule(
                    medication_id=medication.id,
                    due_time=st,
                    days_of_week=days_code,
                )
                db.add(new_sched)
                db.flush()
                generate_dose_events(db, new_sched, medication, days=extend_days)
            else:
                existing.days_of_week = days_code
                db.flush()
                generate_dose_events(db, existing, medication, days=extend_days)
    else:
        # Extend existing schedules with fresh pending dose events
        schedules = db.query(Schedule).filter(Schedule.medication_id == medication.id).all()
        for s in schedules:
            generate_dose_events(db, s, medication, days=extend_days)

    db.commit()
    db.refresh(medication)

    tracking = calculate_medication_tracking(db, medication)

    # Broadcast MEDICATION_UPDATED and RESCHEDULE_COMPLETED to patient and caretakers
    broadcast_mutation(
        medication.patient_id,
        "MEDICATION_UPDATED",
        {
            "medication_id": medication.id,
            "name": medication.name,
            "stock_qty": medication.stock_qty,
            "dosage": medication.dosage,
            "form": medication.form,
            "disease": medication.disease,
            "restock_notify_days": medication.restock_notify_days,
            "actor": "system",
        },
    )
    broadcast_mutation(
        medication.patient_id,
        "RESCHEDULE_COMPLETED",
        {
            **tracking,
            "added_stock": added_stock,
            "new_stock": medication.stock_qty,
            "message": f"Successfully rescheduled {medication.name}! Stock increased by {added_stock}.",
        },
    )

    return tracking
