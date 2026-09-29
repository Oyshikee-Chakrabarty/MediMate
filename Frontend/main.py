"""MediMate — Milestone 1 + 2 standalone app, FRONTEND entrypoint (flet 1.0).

This app is split into two halves:

    medimate_standalone/
    ├── frontend/               # this folder — the Flet UI
    │   ├── main.py             # entry point: page setup + routing (this file)
    │   ├── config.py           # colors & sizes shared by all views
    │   ├── components/common.py    # centered(), safe_update(), toast()
    │   ├── services/api_client.py  # REST client (JWT, care-links, medications)
    │   ├── services/event_socket.py# realtime push channel (no polling)
    │   └── views/              # one file per screen (auth, patient, caretaker)
    └── backend/                # the FastAPI API it talks to (see ../backend/)

It demonstrates the first two milestones:

  Milestone 1 : register & login (JWT auth)                    -> views/auth_view.py
  Milestone 2 : 6-digit care-link pairing + medication CRUD    -> views/patient_view.py
                                                                views/caretaker_view.py

Run it:
    uv run uvicorn app.main:app --app-dir medimate_standalone/backend --reload  # terminal 1
    uv run flet run medimate_standalone/frontend/main.py                        # terminal 2

Dashboards refresh in realtime without any polling: the backend pushes
MEDICATION_* / CARE_LINK_* events over WS /ws/events/{user_id} the moment
data changes (services/event_socket.py), and the mounted view reloads
itself. Each signed-in user gets exactly one EventSocket; it is stopped
on logout and replaced on the next login.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import flet as ft

from components.common import centered
from services.api_client import Api
from services.event_socket import EventSocket
from views.auth_view import AuthView
from views.caretaker_view import CaretakerView
from views.patient_view import PatientView

# Point the app at a different backend (e.g. a phone on your LAN) without
# editing code:  MEDIMATE_API_URL=http://192.168.1.50:8000 flet run main.py
API_BASE: str = os.getenv("MEDIMATE_API_URL", "http://127.0.0.1:8000")


def main(page: ft.Page) -> None:
    """flet 1.0 entrypoint — called once per app session with a fresh Page."""
    page.title = "MediMate"
    page.window.width = 440
    page.window.height = 920
    page.window.resizable = True
    page.padding = 0
    page.spacing = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#F4FAFF"

    api: Api = Api(API_BASE)
    # The realtime push socket of the currently signed-in user (None on auth).
    current_socket: list[EventSocket | None] = [None]

    def show_auth() -> None:
        """Render the login/register screen."""
        if current_socket[0] is not None:
            current_socket[0].stop()  # logout: drop the event channel
            current_socket[0] = None
        page.clean()
        page.add(centered([AuthView(page, api, on_logged_in=show_home)]))

    def show_home(role: str, user: Dict[str, Any]) -> None:
        """Route to the dashboard matching the signed-in user's role."""
        if current_socket[0] is not None:  # defensive: never stack two sockets
            current_socket[0].stop()
            current_socket[0] = None
        page.clean()

        view: PatientView | CaretakerView
        if role == "caretaker":
            view = CaretakerView(page, api, user, on_logout=show_auth)
        else:
            view = PatientView(page, api, user, on_logout=show_auth)

        # The socket is bound to THIS view via closure: events it receives are
        # delivered to this view's handle_event() on the UI loop. Binding at
        # creation (instead of looking up "the current view") keeps events
        # correct even if the view is swapped mid-flight.
        def handle_event(event_type: str, payload: Dict[str, Any]) -> None:
            view.handle_event(event_type, payload)

        socket: EventSocket = EventSocket(
            page, API_BASE, user["id"], api.token or "", on_event=handle_event
        )
        socket.start()
        current_socket[0] = socket

        page.add(centered([view]))

    show_auth()


# flet 1.0: ft.app(target=...) is gone — ft.run() starts the app.
if __name__ == "__main__":
    ft.run(main)
