"""WebSocket escalation router and connection manager.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CareLink, Medication, Schedule, User
from app.security import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


class ConnectionManager:
    """Maps user IDs to their active WebSocket connections.

    Two kinds of sockets live here:
    - escalation sockets: WS /ws/caretaker/{caretaker_id}  (missed-dose alerts)
    - event sockets:      WS /ws/events/{user_id}          (generic data pushes:
                          medication changes, care-link activation, ...)
    """

    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def register_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the running loop so plain endpoints can schedule sends."""
        self._loop = loop

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self._loop

    def connect(self, user_id: str, websocket: WebSocket) -> None:
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info("WS connect: user=%s (total=%d)", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        logger.info("WS disconnect: user=%s", user_id)

    def has_connections(self, caretaker_id: str) -> bool:
        return bool(self._connections.get(caretaker_id))

    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send a JSON message to all sockets of one user."""
        dead: List[WebSocket] = []
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    # Backwards-compatible alias (caretaker escalation path).
    send_to_caretaker = send_to_user

    async def broadcast(self, message: Dict[str, Any]) -> None:
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)


manager = ConnectionManager()


def _get_paired_caretaker_ids(patient_id: str) -> List[str]:
    """Query PostgreSQL for caretakers actively linked to a patient."""
    db: Session = SessionLocal()
    try:
        links: List[CareLink] = (
            db.query(CareLink)
            .filter(CareLink.patient_id == patient_id, CareLink.status == "active")
            .all()
        )
        return [link.caretaker_id for link in links]
    except Exception:
        logger.exception("Failed to resolve paired caretakers")
        return []
    finally:
        db.close()


def _get_patient_name(patient_id: str) -> str:
    db: Session = SessionLocal()
    try:
        user: User | None = db.query(User).filter(User.id == patient_id).first()
        return user.name if user else patient_id
    except Exception:
        return patient_id
    finally:
        db.close()


def _get_linked_user_ids(user_id: str) -> List[str]:
    """IDs of users sharing an active care link with `user_id` (both directions)."""
    db: Session = SessionLocal()
    try:
        links: List[CareLink] = (
            db.query(CareLink)
            .filter(
                CareLink.status == "active",
                (CareLink.patient_id == user_id) | (CareLink.caretaker_id == user_id),
            )
            .all()
        )
        ids: List[str] = []
        for link in links:
            other = link.caretaker_id if link.patient_id == user_id else link.patient_id
            if other not in ids:
                ids.append(other)
        return ids
    except Exception:
        logger.exception("Failed to resolve linked users for %s", user_id)
        return []
    finally:
        db.close()


def broadcast_mutation(user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """Push a data-change event to `user_id`, their linked users, and admins.

    Fire-and-forget, safe from sync endpoints and worker threads: never
    raises, silently no-ops when nobody is connected or the loop is down.
    Used for MEDICATION_* / CARE_LINK_* realtime UI updates.
    """
    targets: List[str] = [user_id]
    targets.extend(_get_linked_user_ids(user_id))

    message: Dict[str, Any] = {
        "type": event_type,
        "payload": {**payload, "about_user_id": user_id,
                    "emitted_at": datetime.now(timezone.utc).isoformat()},
    }

    loop: Optional[asyncio.AbstractEventLoop] = manager.loop
    if loop is None or not loop.is_running():
        logger.warning("WS manager loop not ready; %s dropped", event_type)
        return

    def _dispatch() -> None:
        # A set() de-dupes when user_id is also among the linked ids.
        for uid in dict.fromkeys(targets):
            if manager.has_connections(uid):
                asyncio.run_coroutine_threadsafe(
                    manager.send_to_user(uid, message), loop
                )

    try:
        try:
            running: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            _dispatch()
        else:
            loop.call_soon_threadsafe(_dispatch)
    except Exception:
        logger.exception("broadcast_mutation(%s) failed", event_type)


def broadcast_missed_dose_alert(patient_id: str, med_name: str, due_time: str = "") -> None:
    """Notify all paired caretakers that a dose was missed.

    Safe to call from sync FastAPI endpoints (schedules on the shared loop)
    and from worker threads alike.
    """
    message: Dict[str, Any] = {
        "type": "MISSED_DOSE_ALERT",
        "payload": {
            "patient_id": patient_id,
            "patient_name": _get_patient_name(patient_id),
            "medication_name": med_name,
            "due_time": due_time,
            "alerted_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    caretaker_ids: List[str] = _get_paired_caretaker_ids(patient_id)
    if not caretaker_ids:
        logger.info("No paired caretakers online for patient %s", patient_id)
        return

    loop: Optional[asyncio.AbstractEventLoop] = manager.loop

    def _dispatch() -> None:
        for cid in caretaker_ids:
            if manager.has_connections(cid):
                asyncio.run_coroutine_threadsafe(
                    manager.send_to_caretaker(cid, message), loop
                )

    if loop is not None and loop.is_running():
        # We are (likely) on a worker thread: hop onto the event loop.
        try:
            running: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            _dispatch()
        else:
            loop.call_soon_threadsafe(_dispatch)
    else:
        logger.warning("WS manager loop not ready; alert for patient %s dropped", patient_id)


@router.websocket("/ws/caretaker/{caretaker_id}")
async def caretaker_socket(websocket: WebSocket, caretaker_id: str) -> None:
    """Realtime escalation channel for a caretaker client."""
    await websocket.accept()
    manager.register_loop(asyncio.get_running_loop())
    manager.connect(caretaker_id, websocket)
    try:
        # Keepalive receive loop; client messages are ignored but tracked.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(caretaker_id, websocket)
    except Exception:
        logger.exception("WS error for caretaker %s", caretaker_id)
        manager.disconnect(caretaker_id, websocket)


@router.websocket("/ws/events/{user_id}")
async def user_event_socket(websocket: WebSocket, user_id: str) -> None:
    """Generic realtime data-change channel (any authenticated role).

    The client identifies itself with its user id; the JWT is verified from
    the handshake headers before the socket is registered.
    """
    token: str = websocket.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user: User | None = get_current_user_from_token(token)
    except Exception:
        await websocket.close(code=4401)
        return
    if user is None or user.id != user_id:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    manager.register_loop(asyncio.get_running_loop())
    manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # client pings; ignored
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        logger.exception("WS event error for user %s", user_id)
        manager.disconnect(user_id, websocket)
