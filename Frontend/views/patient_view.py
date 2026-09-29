"""PatientView — Patient Dashboard matching PNG 3."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from components.common import build_bottom_nav, get_asset_path, safe_update, toast
from config import (
    BLUE,
    CARD_BG_BLUE,
    CARD_BORDER_BLUE,
    CARD_WIDTH,
    CYAN,
    FONT,
    GREEN,
    MUTED,
    RED,
    SCHEDULE_NAVY,
    TEXT,
    TITLE_NAVY,
    WHITE,
    YELLOW,
)
from services.api_client import Api, ApiError
from views.add_medicine_view import AddMedicineView
from views.medicines_view import MedicinesView


class PatientView(ft.Column):
    """Patient dashboard styled identically to PNG 3."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        user: Dict[str, Any],
        on_logout: Callable[[], None],
    ) -> None:
        super().__init__(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=380,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._user: Dict[str, Any] = user
        self._on_logout: Callable[[], None] = on_logout

        # Navigation state: "dashboard", "medicines", "add_medicine"
        self._current_subview: str = "dashboard"

        # ---- Smoke Test Compatibility Fields --------------------------- #
        self.code_display: ft.Text = ft.Text(
            "— no active code —",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=SCHEDULE_NAVY,
            text_align=ft.TextAlign.CENTER,
        )
        self.med_name: ft.TextField = ft.TextField(label="Medication name", value="")
        self.med_stock: ft.TextField = ft.TextField(label="Stock", value="10")
        self.med_threshold: ft.TextField = ft.TextField(label="Restock alert", value="7")
        self.med_list: ft.Column = ft.Column(spacing=6)

        # ---- Top Green Header (PNG 3) ---------------------------------- #
        patient_name: str = user.get("name", "User").split()[0]
        today_date_str: str = datetime.now().strftime("%A, %B %d")

        self.header: ft.Container = ft.Container(
            bgcolor=GREEN,
            padding=ft.Padding(20, 28, 20, 24),
            border_radius=ft.BorderRadius(0, 0, 36, 0),
            width=380,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"Good Morning, {patient_name}",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=WHITE,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.KEY_ROUNDED,
                                icon_color=WHITE,
                                tooltip="Pairing Code",
                                on_click=lambda _e: self.show_pairing_dialog(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT,
                                icon_color=WHITE,
                                tooltip="Log out",
                                on_click=self.on_logout,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        bgcolor=SCHEDULE_NAVY,
                        border_radius=20,
                        padding=ft.Padding(16, 6, 16, 6),
                        content=ft.Text(
                            today_date_str,
                            size=13,
                            italic=True,
                            weight=ft.FontWeight.BOLD,
                            color=WHITE,
                        ),
                    ),
                ],
                spacing=8,
            ),
        )

        # ---- TODAY'S MEDICINES Section --------------------------------- #
        self.today_title: ft.Text = ft.Text(
            "TODAY'S MEDICINES",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )

        self.today_meds_col: ft.Column = ft.Column(spacing=12, width=360)

        # ---- TODAY'S PROGRESS Card ------------------------------------- #
        self.progress_subtitle: ft.Text = ft.Text(
            "0 / 0 Doses Taken",
            size=13,
            color=WHITE,
        )
        self.progress_pct: ft.Text = ft.Text("0%", size=13, color=WHITE, weight=ft.FontWeight.BOLD)
        self.progress_fill: ft.Container = ft.Container(
            bgcolor=YELLOW,
            border_radius=8,
            height=14,
            width=0,  # dynamic width
        )
        self.progress_bar_track: ft.Container = ft.Container(
            bgcolor=WHITE,
            border_radius=8,
            height=14,
            expand=True,
            content=self.progress_fill,
            alignment=ft.Alignment.CENTER_LEFT,
        )
        self.remaining_badge_text: ft.Text = ft.Text(
            "0 medicine remaining",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )

        self.progress_card: ft.Container = ft.Container(
            bgcolor=CYAN,
            border_radius=20,
            padding=ft.Padding(18, 16, 18, 16),
            width=360,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "TODAY'S PROGRESS",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=WHITE,
                    ),
                    self.progress_subtitle,
                    ft.Row(
                        controls=[
                            self.progress_bar_track,
                            self.progress_pct,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        bgcolor=SCHEDULE_NAVY,
                        border_radius=14,
                        padding=ft.Padding(14, 6, 14, 6),
                        content=self.remaining_badge_text,
                    ),
                ],
                spacing=10,
            ),
        )

        # ---- Bottom Nav ------------------------------------------------ #
        self.nav_bar: ft.Container = build_bottom_nav(
            role="patient",
            on_medicines=self.nav_to_medicines,
            on_schedule=self.show_schedule_dialog,
            on_alerts_or_history=self.show_history_dialog,
            on_profile=self.show_profile_dialog,
        )

        # ---- Subview Container (swapped when navigating to Medicines) --- #
        self.subview_slot: ft.Container = ft.Container(content=None, visible=False)

        # ---- Main Dashboard Body --------------------------------------- #
        self.main_body: ft.Column = ft.Column(
            controls=[
                ft.Container(height=12),
                ft.Container(
                    content=self.today_title,
                    width=360,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(0, 6, 0, 4),
                ),
                self.today_meds_col,
                ft.Container(height=8),
                self.progress_card,
                ft.Container(height=8),
                self.nav_bar,
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=380,
        )

        self.controls.extend([self.header, self.main_body, self.subview_slot])

    def did_mount(self) -> None:
        self.page.run_task(self.load_data)

    async def load_data(self, *_args: Any) -> None:
        await self.load_medications()
        await self.load_todays_doses()

    # -- Subview Navigation --------------------------------------------- #
    def nav_to_medicines(self) -> None:
        meds_view = MedicinesView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=None,
            on_back=self.nav_to_dashboard,
            on_add_click=self.nav_to_add_medicine,
            on_schedule=self.show_schedule_dialog,
            on_alerts_or_history=self.show_history_dialog,
            on_profile=self.show_profile_dialog,
        )
        self.header.visible = False
        self.main_body.visible = False
        self.subview_slot.content = meds_view
        self.subview_slot.visible = True
        if getattr(self, "page", None) and hasattr(self.page, "run_task"):
            try:
                self.page.run_task(meds_view.load_medications)
            except Exception:
                pass
        safe_update(self)

    def nav_to_add_medicine(self) -> None:
        add_view = AddMedicineView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=None,
            on_back=self.nav_to_medicines,
            on_saved=self._on_med_saved,
        )
        self.header.visible = False
        self.main_body.visible = False
        self.subview_slot.content = add_view
        self.subview_slot.visible = True
        safe_update(self)

    def _on_med_saved(self) -> None:
        self.nav_to_medicines()
        self.page.run_task(self.load_data)

    def nav_to_dashboard(self) -> None:
        self.subview_slot.visible = False
        self.subview_slot.content = None
        self.header.visible = True
        self.main_body.visible = True
        self.page.run_task(self.load_data)
        safe_update(self)

    # -- Today's Doses & Adherence (PNG 3) -------------------------------- #
    async def load_todays_doses(self) -> None:
        doses: List[Dict[str, Any]] = []
        try:
            doses = await asyncio.to_thread(self._api.get_todays_doses)
        except ApiError:
            pass

        # Also get medication lookup map
        med_map: Dict[str, Dict[str, Any]] = {}
        try:
            meds = await asyncio.to_thread(self._api.list_medications)
            med_map = {m["id"]: m for m in meds}
        except ApiError:
            pass

        # Also get schedules lookup map
        sched_map: Dict[str, Dict[str, Any]] = {}
        try:
            scheds = await asyncio.to_thread(self._api.list_schedules)
            sched_map = {s["id"]: s for s in scheds}
        except ApiError:
            pass

        self.today_meds_col.controls.clear()

        total = len(doses)
        taken = sum(1 for d in doses if d.get("status") == "taken")
        remaining = sum(1 for d in doses if d.get("status") == "pending")

        # Update Progress Card
        self.progress_subtitle.value = f"{taken} / {total} Doses Taken"
        pct: float = (taken / total * 100) if total > 0 else 0
        self.progress_pct.value = f"{int(pct)}%"
        # progress track has width approx 280
        self.progress_fill.width = int(280 * (pct / 100))
        rem_str: str = f"{remaining} medicine{'s' if remaining != 1 else ''} remaining"
        if total > 0 and remaining == 0:
            rem_str = "All medicines taken! 🎉"
        self.remaining_badge_text.value = rem_str

        # Render Dose Cards (No demo hardcoding)
        pending_doses = [d for d in doses if d.get("status") == "pending"]
        if not pending_doses:
            msg: str = (
                "All medicines taken today! Great job! 🎉"
                if total > 0
                else "No medicines scheduled for today."
            )
            self.today_meds_col.controls.append(
                ft.Container(
                    bgcolor=CARD_BG_BLUE,
                    border=ft.Border.all(1, CARD_BORDER_BLUE),
                    border_radius=20,
                    padding=20,
                    width=360,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=GREEN, size=38),
                            ft.Text(msg, size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        else:
            for dose in pending_doses:
                card = self._build_dose_card(dose, sched_map, med_map)
                self.today_meds_col.controls.append(card)

        safe_update(self)

    def _build_dose_card(
        self,
        dose: Dict[str, Any],
        sched_map: Dict[str, Dict[str, Any]],
        med_map: Dict[str, Dict[str, Any]],
    ) -> ft.Container:
        sched_id: str = dose.get("schedule_id", "")
        sched = sched_map.get(sched_id, {})
        med_id: str = sched.get("medication_id", "")
        med = med_map.get(med_id, {})

        med_name: str = med.get("name", "Prescription Med")
        dosage: str = med.get("dosage", "")
        form: str = med.get("form", "Tablet")
        dose_label: str = f"1 {form}" if form else "1 Tablet"

        raw_time: str = sched.get("due_time", "09:00:00")
        try:
            t = datetime.strptime(raw_time, "%H:%M:%S")
            time_display: str = t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            time_display = "9:00 AM"

        async def take_now(_e: Any) -> None:
            try:
                await asyncio.to_thread(self._api.set_dose_status, dose["id"], "taken")
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, f"Marked {med_name} as taken!")
            await self.load_data()

        return ft.Container(
            bgcolor=CARD_BG_BLUE,
            border=ft.Border.all(1, CARD_BORDER_BLUE),
            border_radius=20,
            padding=ft.Padding(16, 16, 16, 16),
            width=360,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        shape=ft.BoxShape.CIRCLE,
                                        bgcolor=YELLOW,
                                        width=16,
                                        height=16,
                                    ),
                                    ft.Text(
                                        time_display,
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color="#334155",
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Text(
                                med_name,
                                size=17,
                                weight=ft.FontWeight.W_600,
                                color="#334155",
                            ),
                            ft.Text(
                                dose_label,
                                size=15,
                                color="#475569",
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Image(
                                src=get_asset_path("pill_icon.png"),
                                width=52,
                                height=52,
                                fit=ft.BoxFit.CONTAIN,
                            ),
                            ft.Button(
                                content=ft.Text("TAKE NOW", size=13, weight=ft.FontWeight.BOLD),
                                bgcolor=CYAN,
                                color=WHITE,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                                height=36,
                                on_click=take_now,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # -- Dialogs (Schedule, History, Profile) ---------------------------- #
    def show_pairing_dialog(self) -> None:
        code_box = ft.Text(self.code_display.value, size=32, weight=ft.FontWeight.BOLD, color=GREEN)

        async def generate(_e: Any) -> None:
            await self.on_generate_code()
            code_box.value = self.code_display.value
            safe_update(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Caregiver Pairing Code", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Share this 6-digit code with your caregiver:", size=14),
                    ft.Container(content=code_box, alignment=ft.Alignment.CENTER, padding=10),
                    ft.Button(content=ft.Text("Generate New Code"), on_click=generate),
                ],
                tight=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self._page_ref.show_dialog(dlg)

    def show_schedule_dialog(self) -> None:
        dlg = ft.AlertDialog(
            title=ft.Text("Schedule", weight=ft.FontWeight.BOLD),
            content=ft.Text("Your active dosage schedules are synchronized daily at 9:00 AM.", size=14),
        )
        self._page_ref.show_dialog(dlg)

    def show_history_dialog(self) -> None:
        dlg = ft.AlertDialog(
            title=ft.Text("Dose History", weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Progress today: {self.progress_subtitle.value}", size=14),
        )
        self._page_ref.show_dialog(dlg)

    def show_profile_dialog(self) -> None:
        async def logout_click(_e: Any) -> None:
            self._page_ref.pop_dialog()
            await self.on_logout()

        dlg = ft.AlertDialog(
            title=ft.Text("Patient Profile", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text(f"Name: {self._user.get('name')}", size=15),
                    ft.Text(f"Email: {self._user.get('email')}", size=14, color=MUTED),
                    ft.Text(f"Pairing Code: {self.code_display.value}", size=14),
                    ft.Container(height=6),
                    ft.Button(content=ft.Text("Generate Pairing Code"), on_click=lambda _e: self.on_generate_code()),
                    ft.Button(content=ft.Text("Log Out"), bgcolor=RED, color=WHITE, on_click=logout_click),
                ],
                tight=True,
                spacing=8,
            ),
        )
        self._page_ref.show_dialog(dlg)

    # -- Smoke Test Compatibility Methods ------------------------------- #
    async def on_generate_code(self, *_args: Any) -> None:
        try:
            res: Dict[str, Any] = await asyncio.to_thread(self._api.generate_invite_code)
            self.code_display.value = res["invite_code"]
            toast(self._page_ref, "Code generated — share it with your caregiver.")
            safe_update(self)
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)

    async def load_medications(self, *_args: Any) -> None:
        try:
            meds: List[Dict[str, Any]] = await asyncio.to_thread(self._api.list_medications)
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return
        self.med_list.controls.clear()
        for med in meds:
            self.med_list.controls.append(ft.Text(med.get("name", "")))
        safe_update(self)

    async def on_add_medication(self, *_args: Any) -> None:
        name: str = (self.med_name.value or "").strip()
        if not name:
            toast(self._page_ref, "Medication name required.", error=True)
            return
        try:
            stock = int(self.med_stock.value or "10")
            threshold = int(self.med_threshold.value or "7")
        except ValueError:
            toast(self._page_ref, "Stock and threshold must be numbers.", error=True)
            return
        try:
            await asyncio.to_thread(
                self._api.add_medication, name=name, stock_qty=stock, restock_notify_days=threshold
            )
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return
        await self.load_data()

    async def on_logout(self, *_args: Any) -> None:
        self._on_logout()

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        actor_id: str = str(payload.get("actor_id", ""))
        if actor_id and actor_id == self._user.get("id"):
            return
        if event_type in ("MEDICATION_CREATED", "MEDICATION_UPDATED", "MEDICATION_DELETED"):
            toast(self._page_ref, f"Caregiver updated your medications.")
            if self.parent is not None:
                self.page.run_task(self.load_data)
        elif event_type == "CARE_LINK_ACTIVATED":
            toast(self._page_ref, f"A caregiver joined your care team.")
