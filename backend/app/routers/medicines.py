"""Medication CRUD router.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import CareLink, Medication, User
from app.routers.notifications import broadcast_mutation
from app.schemas import MedicationCreate, MedicationResponse, MedicationUpdate
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/medications", tags=["medications"])


def _resolve_patient_id(
    requested: Optional[str], current_user: User, db: Session
) -> str:
    """Patients act on their own meds; caretakers may act for linked patients."""
    if current_user.role == "patient":
        if requested is not None and requested != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only manage their own medications",
            )
        return current_user.id

    # caretaker path
    if requested is None:
        raise HTTPException(
            status_code=400,
            detail="patient_id is required when acting as a caretaker",
        )
    linked: CareLink | None = (
        db.query(CareLink)
        .filter(
            CareLink.caretaker_id == current_user.id,
            CareLink.patient_id == requested,
            CareLink.status == "active",
        )
        .first()
    )
    if linked is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not linked to this patient",
        )
    return requested


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
def create_medication(
    body: MedicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Add a new medication with initial stock and restock threshold."""
    try:
        patient_id: str = _resolve_patient_id(body.patient_id, current_user, db)
        med: Medication = Medication(
            patient_id=patient_id,
            name=body.name,
            dosage=body.dosage,
            form=body.form or "Tablet",
            disease=body.disease,
            body_part=body.body_part,
            notes=body.notes,
            stock_qty=body.stock_qty,
            restock_notify_days=body.restock_notify_days,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(med)
        db.flush()

        # Auto-create daily 9:00 AM schedule so dose events are generated for today
        from app.models import Schedule
        from app.routers.schedules import generate_dose_events
        schedule = Schedule(
            medication_id=med.id,
            due_time="09:00:00",
            days_of_week="daily",
        )
        db.add(schedule)
        db.flush()
        generate_dose_events(db, schedule, med)

        db.commit()
        db.refresh(med)
        logger.info("Medication created: %s for patient %s", med.id, patient_id)
        # Realtime push: let the patient's (and linked caretakers') UI reload.
        broadcast_mutation(
            patient_id,
            "MEDICATION_CREATED",
            {"medication_id": med.id, "name": med.name, "stock_qty": med.stock_qty,
             "dosage": med.dosage, "form": med.form, "disease": med.disease,
             "restock_notify_days": med.restock_notify_days,
             "actor": current_user.name, "actor_id": current_user.id},
        )
        return MedicationResponse.model_validate(med)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("create_medication failed")
        raise HTTPException(status_code=400, detail=f"Could not create medication: {exc}")


@router.get("", response_model=List[MedicationResponse])
def list_medications(
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MedicationResponse]:
    """Fetch all medications belonging to the (resolved) patient."""
    try:
        pid: str = _resolve_patient_id(patient_id, current_user, db)
        meds: List[Medication] = (
            db.query(Medication)
            .options(joinedload(Medication.patient))
            .filter(Medication.patient_id == pid)
            .order_by(Medication.name)
            .all()
        )
        return [MedicationResponse.model_validate(m) for m in meds]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_medications failed")
        raise HTTPException(status_code=400, detail=f"Could not list medications: {exc}")


@router.get("/{medication_id}", response_model=MedicationResponse)
def get_medication(
    medication_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Fetch a single medication by id."""
    try:
        med: Medication | None = (
            db.query(Medication).filter(Medication.id == medication_id).first()
        )
        if med is None:
            raise HTTPException(status_code=404, detail="Medication not found")
        _resolve_patient_id(med.patient_id, current_user, db)
        return MedicationResponse.model_validate(med)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_medication failed")
        raise HTTPException(status_code=400, detail=f"Could not fetch medication: {exc}")


@router.put("/{medication_id}", response_model=MedicationResponse)
def update_medication(
    medication_id: str,
    body: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Edit medication details or update stock count."""
    try:
        med: Medication | None = (
            db.query(Medication).filter(Medication.id == medication_id).first()
        )
        if med is None:
            raise HTTPException(status_code=404, detail="Medication not found")
        # caretakers may pass patient_id in the body to authorize the edit
        _resolve_patient_id(body.patient_id or med.patient_id, current_user, db)

        if body.name is not None:
            med.name = body.name
        if body.dosage is not None:
            med.dosage = body.dosage
        if body.form is not None:
            med.form = body.form
        if body.disease is not None:
            med.disease = body.disease
        if body.body_part is not None:
            med.body_part = body.body_part
        if body.notes is not None:
            med.notes = body.notes
        if body.stock_qty is not None:
            med.stock_qty = body.stock_qty
        if body.restock_notify_days is not None:
            med.restock_notify_days = body.restock_notify_days
        med.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(med)
        broadcast_mutation(
            med.patient_id,
            "MEDICATION_UPDATED",
            {"medication_id": med.id, "name": med.name, "stock_qty": med.stock_qty,
             "dosage": med.dosage, "form": med.form, "disease": med.disease,
             "restock_notify_days": med.restock_notify_days,
             "actor": current_user.name, "actor_id": current_user.id},
        )
        return MedicationResponse.model_validate(med)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("update_medication failed")
        raise HTTPException(status_code=400, detail=f"Could not update medication: {exc}")


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medication(
    medication_id: str,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove a medication record (cascades to schedules and dose events)."""
    try:
        med: Medication | None = (
            db.query(Medication).filter(Medication.id == medication_id).first()
        )
        if med is None:
            raise HTTPException(status_code=404, detail="Medication not found")
        # caretakers pass ?patient_id=... to authorize the delete
        _resolve_patient_id(patient_id or med.patient_id, current_user, db)

        patient_id: str = med.patient_id
        med_name: str = med.name
        db.delete(med)
        db.commit()
        logger.info("Medication deleted: %s", medication_id)
        broadcast_mutation(
            patient_id,
            "MEDICATION_DELETED",
            {"medication_id": medication_id, "name": med_name,
             "actor": current_user.name, "actor_id": current_user.id},
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("delete_medication failed")
        raise HTTPException(status_code=400, detail=f"Could not delete medication: {exc}")
