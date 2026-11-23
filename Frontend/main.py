from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import flet as ft

from components.common import centered
from services.api_client import Api
from services.event_socket import EventSocket
from views.add_medicine_view import AddMedicineView
from views.auth_view import AuthView
from views.caretaker_view import CaretakerView
from views.medicines_view import MedicinesView
from views.patient_view import PatientView
from views.schedule_view import ScheduleView

API_BASE: str = os.getenv("MEDIMATE_API_URL", "http://127.0.0.1:8000")
ASSETS_DIR: str = str(Path(__file__).resolve().parent / "assets")
os.environ.setdefault("FLET_ASSETS_DIR", ASSETS_DIR)


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
    page.theme_mode = ft.ThemeMode.LIGHT

    api: Api = Api(API_BASE)
    current_socket: list[EventSocket | None] = [None]

    def show_auth() -> None:
        """Render the login/register screen."""
        from services.alarm_service import AlarmRinger
        AlarmRinger.stop_all()
        if current_socket[0] is not None:
            current_socket[0].stop()  # logout: drop the event channel
            current_socket[0] = None
        page.clean()
        page.add(centered([AuthView(page, api, on_logged_in=show_home)], scroll=True))

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

        page.add(centered([view], scroll=False))

    show_auth()


# flet 1.0: ft.app(target=...) is gone — ft.run() starts the app.
if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
