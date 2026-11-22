"""Insulin and Blood Sugar Level router.

Provides endpoints to:
- POST /insulin : record a sugar level and time for a date
- GET /insulin : list readings for a date (ordered by time)
- GET /insulin/dates : list dates with readings for a given month
- DELETE /insulin/{id} : delete a reading
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InsulinReading, User
from app.routers.medicines import _resolve_patient_id
from app.routers.notifications import broadcast_mutation
from app.schemas import InsulinReadingCreate, InsulinReadingResponse
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insulin", tags=["insulin"])


@router.post("", response_model=InsulinReadingResponse, status_code=status.HTTP_201_CREATED)
def add_reading(
    body: InsulinReadingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsulinReadingResponse:
    """Record a sugar level reading with time for a specific day."""
    try:
        pid: str = _resolve_patient_id(body.patient_id, current_user, db)

        # Standardize reading_time to HH:MM:SS
        r_time = body.reading_time
        if len(r_time) == 5:
            r_time = f"{r_time}:00"

        reading = InsulinReading(
            patient_id=pid,
            reading_date=body.reading_date,
            reading_time=r_time,
            sugar_level=round(float(body.sugar_level), 2),
            insulin_units=body.insulin_units,
            notes=body.notes,
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)

        try:
            broadcast_mutation(
                pid,
                "INSULIN_READING_CREATED",
                {
                    "id": reading.id,
                    "date": reading.reading_date,
                    "time": reading.reading_time,
                    "sugar_level": reading.sugar_level,
                },
            )
        except Exception:
            pass

        return InsulinReadingResponse.model_validate(reading)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("add_reading failed")
        raise HTTPException(status_code=400, detail=f"Could not add insulin reading: {exc}")


@router.get("", response_model=List[InsulinReadingResponse])
def list_readings_for_date(
    date: str,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[InsulinReadingResponse]:
    """List all sugar level readings for a given date, ordered by time."""
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        rows: List[InsulinReading] = (
            db.query(InsulinReading)
            .filter(
                and_(
                    InsulinReading.patient_id == pid,
                    InsulinReading.reading_date == date,
                )
            )
            .order_by(InsulinReading.reading_time)
            .all()
        )
        return [InsulinReadingResponse.model_validate(r) for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_readings_for_date failed")
        raise HTTPException(status_code=400, detail=f"Could not list readings: {exc}")


@router.get("/dates", response_model=List[str])
def list_dates_with_readings(
    year: int,
    month: int,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[str]:
    """List unique date strings ('YYYY-MM-DD') that have readings in a given month."""
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        prefix = f"{year:04d}-{month:02d}-"
        rows = (
            db.query(InsulinReading.reading_date)
            .filter(
                and_(
                    InsulinReading.patient_id == pid,
                    InsulinReading.reading_date.like(f"{prefix}%"),
                )
            )
            .distinct()
            .order_by(InsulinReading.reading_date)
            .all()
        )
        return [r[0] for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_dates_with_readings failed")
        raise HTTPException(status_code=400, detail=f"Could not list reading dates: {exc}")


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(
    reading_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an insulin/sugar level reading."""
    try:
        reading: Optional[InsulinReading] = (
            db.query(InsulinReading).filter(InsulinReading.id == reading_id).first()
        )
        if reading is None:
            raise HTTPException(status_code=404, detail="Reading not found")

        _resolve_patient_id(reading.patient_id, current_user, db)
        pid = reading.patient_id
        db.delete(reading)
        db.commit()

        try:
            broadcast_mutation(pid, "INSULIN_READING_DELETED", {"id": reading_id})
        except Exception:
            pass
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("delete_reading failed")
        raise HTTPException(status_code=400, detail=f"Could not delete reading: {exc}")
