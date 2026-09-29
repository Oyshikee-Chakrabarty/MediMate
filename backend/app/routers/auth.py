"""Authentication router: register and login endpoints."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserLogin, UserResponse
from app.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Register a new patient or caretaker and return a bearer token."""
    try:
        existing: User | None = db.query(User).filter(User.email == user_in.email).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user: User = User(
            name=user_in.name,
            email=user_in.email,
            password_hash=hash_password(user_in.password),
            role=user_in.role,
            preferred_language=user_in.preferred_language,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token_payload: Dict[str, Any] = {"sub": user.id, "role": user.role}
        return Token(
            access_token=create_access_token(token_payload),
            user=UserResponse.model_validate(user),
        )
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Register integrity error: %s", exc)
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as exc:
        db.rollback()
        logger.exception("Register failed")
        raise HTTPException(status_code=400, detail=f"Registration failed: {exc}")


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Validate credentials and return a JWT bearer token."""
    try:
        user: User | None = db.query(User).filter(User.email == credentials.email).first()
        if user is None or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_payload: Dict[str, Any] = {"sub": user.id, "role": user.role}
        return Token(
            access_token=create_access_token(token_payload),
            user=UserResponse.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Login failed")
        raise HTTPException(status_code=400, detail=f"Login failed: {exc}")
