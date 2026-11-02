"""MediMate FastAPI application entrypoint."""

import sys
from pathlib import Path

# Ensure the parent backend directory is in sys.path so 'import app...'
# resolves properly even when launched as 'uvicorn main:app' from inside 'backend/app'
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.database import init_db
from app.routers import (
    auth,
    care_links,
    dose_events,
    medicines,
    notifications,
    schedules,
    sync,
)
from app.routers.notifications import manager as ws_manager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Init tables on startup; hand the running loop to the WS manager."""
    init_db()
    ws_manager.register_loop(asyncio.get_running_loop())
    logger.info("WS manager bound to running event loop.")
    yield


app = FastAPI(
    title="MediMate API",
    description="Medication adherence and caretaker escalation backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(care_links.router)
app.include_router(medicines.router)
app.include_router(schedules.router)
app.include_router(dose_events.router)
app.include_router(sync.router)
app.include_router(notifications.router)

@app.get("/")
def root() -> dict:
    return {"response": "MediMate API.\nSee docs at /docs or /redoc"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
