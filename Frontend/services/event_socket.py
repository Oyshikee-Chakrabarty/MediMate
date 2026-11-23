"""Realtime event socket (frontend side of the push channel).

No polling anywhere: the server pushes MEDICATION_* / CARE_LINK_* events
over WS /ws/events/{user_id} the moment data changes, and this client
forwards them into the flet UI.

Threading model (flet 1.0):
- run_loop() runs in its own OS thread (page.run_thread) and uses the
  *sync* websockets client, so it never touches the UI loop's asyncio.
- Every incoming message is handed to the UI with page.run_task(...) —
  internally asyncio.run_coroutine_threadsafe, the blessed thread→loop
  bridge — so the on_event callback executes ON the UI loop and can
  mutate controls directly, exactly like an on_click handler.
- On disconnect it reconnects with capped backoff (1s→2s→4s→8s→max 10s),
  so a backend restart mid-session heals itself.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.sync.client import ClientConnection, connect

logger = logging.getLogger(__name__)

# Capped reconnect backoff: the probe loop burns no CPU while idle.
_RECONNECT_DELAYS = (1.0, 2.0, 4.0, 8.0, 10.0)


class EventSocket:
    """Owns one WS /ws/events/{user_id} connection for a signed-in user."""

    def __init__(
        self,
        page: Any,
        base_url: str,
        user_id: str,
        token: str,
        on_event: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        self._page: Any = page
        self._url: str = (
            f"{base_url.rstrip('/').replace('http', 'ws', 1)}/ws/events/{user_id}"
        )
        self._token: str = token
        self._on_event: Callable[[str, Dict[str, Any]], None] = on_event
        self._ws: Optional[ClientConnection] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # lifecycle (UI-thread API)
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Spawn the listener thread. Safe to call twice; no-op once started."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread: threading.Thread = threading.Thread(
            target=self._run, name=f"events-{self._url.rsplit('/', 1)[-1]}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread to exit and close the socket (UI thread)."""
        self._stop.set()
        ws: Optional[ClientConnection] = self._ws
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        self._ws = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ #
    # listener thread
    # ------------------------------------------------------------------ #
    def _run(self) -> None:
        """Blocking receive loop; reconnects with backoff until stopped."""
        attempts: int = 0
        while not self._stop.is_set():
            try:
                with connect(
                    self._url,
                    additional_headers={"Authorization": f"Bearer {self._token}"},
                    open_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    self._ws = ws
                    logger.info("Event socket connected: %s", self._url)
                    attempts = 0  # healthy connection resets backoff
                    for raw in ws:
                        if self._stop.is_set():
                            break
                        self._dispatch(raw)
            except Exception as exc:  # noqa: BLE001 - any failure -> backoff
                if self._stop.is_set():
                    break
                delay: float = _RECONNECT_DELAYS[
                    min(attempts, len(_RECONNECT_DELAYS) - 1)
                ]
                attempts += 1
                logger.warning("Event socket down (%s); retry in %.0fs", exc, delay)
                if self._stop.wait(delay):
                    break
            finally:
                self._ws = None

    def _dispatch(self, raw: str) -> None:
        """Parse one server frame and marshal the callback onto the UI loop."""
        try:
            message: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Non-JSON frame: %r", raw[:120])
            return
        event_type: str = str(message.get("type", ""))
        payload: Dict[str, Any] = message.get("payload", {}) or {}

        if not event_type:
            return
        try:
            # page.run_task is thread-safe (asyncio.run_coroutine_threadsafe
            # under the hood): the handler runs on the UI loop.
            self._page.run_task(self._emit, event_type, payload)
        except Exception:  # noqa: BLE001 - page may be shutting down
            logger.exception("Could not marshal event %s to UI loop", event_type)

    async def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Runs ON the UI loop: invoke the view's event callback."""
        try:
            self._on_event(event_type, payload)
        except Exception:  # noqa: BLE001 - a broken view must not kill the socket
            logger.exception("on_event handler failed for %s", event_type)
