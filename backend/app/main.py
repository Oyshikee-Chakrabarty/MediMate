"""MediMate FastAPI application entrypoint."""

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
    return {"response": "MediMate API. See docs at /docs or /redoc"}

