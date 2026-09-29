"""Database engine and session management for the MediMate backend.
"""

import os
import logging
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

logger = logging.getLogger(__name__)

# The SQLite fallback path is anchored to backend/ so the same physical DB is
# used no matter which directory uvicorn was launched from (a CWD-relative
# './fallback.db' silently created two databases and "lost" data on logout).
_FALLBACK_DB: str = str(Path(__file__).resolve().parent.parent / "fallback.db")
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_FALLBACK_DB}")

# For SQLite (dev fallback) we must enable check_same_thread=False and rely on
# SerializeMixin semantics; for PostgreSQL we can pool connections normally.
connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables from ORM metadata (idempotent)."""
    from app import models  # noqa: F401  (ensure models are registered)

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized.")
    except Exception as exc:  # pragma: no cover - startup safety
        logger.exception("Failed to initialize database tables: %s", exc)
        raise
