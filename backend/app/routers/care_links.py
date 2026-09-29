"""CareLink pairing router: 6-digit invite code .
"""

import logging
import secrets
import string
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CareLink, User
from app.routers.notifications import broadcast_mutation
from app.schemas import (
    CareLinkGenerate,
    CareLinkGenerateResponse,
    CareLinkPair,
    CareLinkResponse,
    PatientSummary,
)
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/care-links", tags=["care-links"])

_CODE_ALPHABET: str = string.digits  # 6-digit numeric code as per blueprint
_CODE_LENGTH: int = 6


def _generate_invite_code(db: Session) -> str:
    """Generate a unique 6-digit code not currently used by a pending link."""
    for _ in range(50):
        code: str = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
        exists: CareLink | None = (
            db.query(CareLink).filter(CareLink.invite_code == code).first()
        )
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate unique invite code")


@router.post("/generate-code", response_model=CareLinkGenerateResponse)
def generate_code(
    body: CareLinkGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareLinkGenerateResponse:
    """Patient (or a caretaker acting on behalf of a paired patient) requests a code."""
    try:
        patient_id: str = body.patient_id if body.patient_id else current_user.id

        if current_user.id != patient_id and current_user.role != "caretaker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the patient or a linked caretaker can generate a code",
            )

        patient: User | None = db.query(User).filter(User.id == patient_id).first()
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.role != "patient":
            raise HTTPException(status_code=400, detail="Target user is not a patient")

        # Invalidate any stale pending links for this patient
        stale: List[CareLink] = (
            db.query(CareLink)
            .filter(CareLink.patient_id == patient_id, CareLink.status == "pending")
            .all()
        )
        for link in stale:
            db.delete(link)

        code: str = _generate_invite_code(db)
        link: CareLink = CareLink(
            patient_id=patient_id,
            caretaker_id=current_user.id if current_user.role == "caretaker" and current_user.id != patient_id else patient_id,
            invite_code=code,
            status="pending",
        )
        # caretaker_id is filled properly on pair; use the patient's own id as a
        # placeholder to satisfy the NOT NULL constraint until pairing completes.
        link.caretaker_id = patient_id
        db.add(link)
        db.commit()
        db.refresh(link)

        logger.info("Invite code generated for patient %s", patient_id)
        return CareLinkGenerateResponse(invite_code=code, patient_id=patient_id)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("generate-code failed")
        raise HTTPException(status_code=400, detail=f"Could not generate code: {exc}")


@router.post("/pair", response_model=CareLinkResponse)
def pair(
    body: CareLinkPair,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareLinkResponse:
    """Caretaker submits a 6-digit code to establish an active care link."""
    try:
        if current_user.role != "caretaker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only caretakers can pair via an invite code",
            )

        link: CareLink | None = (
            db.query(CareLink).filter(CareLink.invite_code == body.invite_code).first()
        )
        if link is None:
            raise HTTPException(status_code=404, detail="Invalid invite code")
        if link.status == "active":
            raise HTTPException(status_code=400, detail="Invite code already used")

        link.caretaker_id = current_user.id
        link.status = "active"
        db.commit()
        db.refresh(link)

        logger.info(
            "CareLink %s activated: patient=%s caretaker=%s",
            link.id, link.patient_id, current_user.id,
        )
        # Realtime push: tell the patient their caretaker just connected.
        broadcast_mutation(
            link.patient_id,
            "CARE_LINK_ACTIVATED",
            {"caretaker_id": current_user.id, "caretaker_name": current_user.name},
        )
        return CareLinkResponse.model_validate(link)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("pair failed")
        raise HTTPException(status_code=400, detail=f"Pairing failed: {exc}")


@router.get("/my-patients", response_model=List[PatientSummary])
def my_patients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PatientSummary]:
    """Return active patients linked to the authenticated caretaker."""
    try:
        if current_user.role != "caretaker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only caretakers have linked patients",
            )

        links: List[CareLink] = (
            db.query(CareLink)
            .filter(CareLink.caretaker_id == current_user.id, CareLink.status == "active")
            .all()
        )
        results: List[PatientSummary] = []
        for link in links:
            patient: User | None = (
                db.query(User).filter(User.id == link.patient_id).first()
            )
            if patient is not None:
                results.append(
                    PatientSummary(
                        id=patient.id,
                        name=patient.name,
                        email=patient.email,
                        preferred_language=patient.preferred_language,
                    )
                )
        return results
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("my-patients failed")
        raise HTTPException(status_code=400, detail=f"Could not list patients: {exc}")
