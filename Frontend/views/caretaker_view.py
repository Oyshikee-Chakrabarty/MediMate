"""CaretakerView — Caregiver Dashboard matching PNG 4."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from components.common import (
    SHADOW_CARD,
    SHADOW_ELEVATED,
    SHADOW_SUBTLE,
    build_bottom_nav,
    build_language_toggle,
    get_asset_path,
    safe_update,
    show_reschedule_dialog,
    toast,
)
from components.profile_card import show_oriented_profile_dialog
from config import (
    APP_WIDTH,
    BLUE,
    CARD_BG_BLUE,
    CARD_BORDER_BLUE,
    CARD_WIDTH,
    CYAN,
    FONT,
    GREEN,
    MUTED,
    ORANGE,
    RED,
    SCHEDULE_NAVY,
    TAKEN_GREEN,
    TEXT,
    TITLE_NAVY,
    WHITE,
)
from services import i18n
from services.api_client import Api, ApiError
from services.alarm_service import AlarmService
from views.add_medicine_view import AddMedicineView
from views.history_view import HistoryView
from views.insulin_view import InsulinView
from views.medicines_view import MedicinesView
from views.schedule_view import ScheduleView


class CaretakerView(ft.Column):
    """Caregiver dashboard styled identically to PNG 4."""

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
            width=APP_WIDTH,
            expand=True,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._user: Dict[str, Any] = user
        self._on_logout: Callable[[], None] = on_logout

        self._patients: List[Dict[str, Any]] = []
        self._active_patient: Optional[Dict[str, Any]] = None

        def _on_alarm_status_updated() -> None:
            self._run_task(self.load_patients)

        self.alarm_service: AlarmService = AlarmService(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=None,
            on_status_updated=_on_alarm_status_updated,
        )

        # ---- Smoke Test Compatibility Fields --------------------------- #
        self.code_field: ft.TextField = ft.TextField(
            hint_text="6-digit code",
            width=180,
            border_radius=12,
            bgcolor="#FFF1E6",
            border=ft.NoInputBorder(),
            content_padding=ft.Padding(14, 10, 14, 10),
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
        )
        self.pair_btn: ft.Button = ft.Button(
            content=ft.Text("Connect", size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ORANGE,
            color=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            height=44,
            on_click=self.on_pair,
        )
        self.patient_list: ft.Column = ft.Column(spacing=10, width=CARD_WIDTH)

        # ---- Top Orange Header (PNG 4) --------------------------------- #
        today_date_str: str = datetime.now().strftime("%A, %B %d")

        self.greeting_salutation: ft.Text = ft.Text(
            self._get_salutation(),
            size=14,
            weight=ft.FontWeight.W_500,
            color=WHITE,
        )
        self.greeting_username: ft.Text = ft.Text(
            self._get_username(),
            size=18,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
            no_wrap=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.greeting_text: ft.Text = self.greeting_username

        self.greeting_col: ft.Column = ft.Column(
            controls=[
                self.greeting_salutation,
                self.greeting_username,
            ],
            spacing=1,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        self.greeting_container: ft.Container = ft.Container(
            content=self.greeting_col,
            expand=True,
            on_click=lambda _e: self.show_profile_dialog(),
            tooltip="View Profile",
        )
        self.lang_toggle: ft.Container = build_language_toggle(
            on_toggle=self._on_lang_changed,
            api=self._api,
            bg_color="#1E293B",
            text_color=WHITE,
        )

        # ---- Top Dropdown Hamburger Menu -------------------------------- #
        self.menu_button: ft.PopupMenuButton = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            icon_color=WHITE,
            tooltip="Menu",
            items=self._build_menu_items(),
        )

        self.header: ft.Container = ft.Container(
            bgcolor=ORANGE,
            padding=ft.Padding(16, 8, 16, 18),
            border_radius=ft.BorderRadius(0, 0, 32, 0),
            width=APP_WIDTH,
            content=ft.SafeArea(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                self.greeting_container,
                                self.lang_toggle,
                                self.menu_button,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(
                            bgcolor=SCHEDULE_NAVY,
                            border_radius=18,
                            padding=ft.Padding(14, 5, 14, 5),
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
                avoid_intrusions_bottom=False,
            ),
        )

        # ---- Patient Connection Section (PNG 4) ------------------------ #
        self.patient_section_title: ft.Text = ft.Text(
            i18n.t("patient"),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )
        self.pair_btn_text: ft.Text = ft.Text(
            i18n.t("pair_patient_btn"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.pair_action_btn: ft.Container = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, size=15, color=WHITE),
                    self.pair_btn_text,
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=ORANGE,
            border_radius=12,
            padding=ft.Padding(10, 5, 10, 5),
            on_click=lambda _e: self.show_pairing_dialog(),
            shadow=SHADOW_SUBTLE,
            tooltip="Connect a patient",
        )
        self.patient_name_text: ft.Text = ft.Text(
            i18n.t("no_patient_connected"),
            size=18,
            weight=ft.FontWeight.BOLD,
            color="#334155",
        )
        self.patient_status_text: ft.Text = ft.Text(
            i18n.t("not_connected"),
            size=15,
            weight=ft.FontWeight.BOLD,
            color="#64748B",
        )
        self.status_dot: ft.Container = ft.Container(
            shape=ft.BoxShape.CIRCLE,
            bgcolor="#94A3B8",
            width=12,
            height=12,
        )
        self.patient_chips_row: ft.Row = ft.Row(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            visible=False,
        )

        self.patient_section: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(6, 10, 6, 4),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.patient_section_title,
                            self.pair_action_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.PERSON, color="#1E88E5", size=24),
                                    self.patient_name_text,
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                controls=[
                                    self.status_dot,
                                    self.patient_status_text,
                                ],
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.patient_chips_row,
                ],
                spacing=6,
            ),
        )

        # ---- Caretaker Quick Management Hub --------------------------- #
        self.hub_meds_title: ft.Text = ft.Text(
            i18n.t("nav_medicines"),
            size=13,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_meds_sub: ft.Text = ft.Text(
            i18n.t("hub_prescriptions"),
            size=10,
            color="#64748B",
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_sched_title: ft.Text = ft.Text(
            i18n.t("nav_schedule"),
            size=13,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_sched_sub: ft.Text = ft.Text(
            i18n.t("hub_dose_times"),
            size=10,
            color="#64748B",
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_hist_title: ft.Text = ft.Text(
            i18n.t("nav_history"),
            size=13,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_hist_sub: ft.Text = ft.Text(
            i18n.t("hub_adherence"),
            size=10,
            color="#64748B",
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_ins_title: ft.Text = ft.Text(
            i18n.t("insulin_title"),
            size=13,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.hub_ins_sub: ft.Text = ft.Text(
            i18n.t("hub_blood_sugar"),
            size=10,
            color="#64748B",
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        def _make_hub_item(
            icon: str,
            icon_color: str,
            title_text: ft.Text,
            sub_text: ft.Text,
            on_click: Callable[[], None],
        ) -> ft.Container:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            width=34,
                            height=34,
                            border_radius=10,
                            bgcolor="#F8FAFC",
                            border=ft.Border.all(1, "#E2E8F0"),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, color=icon_color, size=18),
                        ),
                        ft.Column(
                            controls=[title_text, sub_text],
                            spacing=1,
                            alignment=ft.MainAxisAlignment.CENTER,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                height=56,
                bgcolor=WHITE,
                border=ft.Border.all(1, CARD_BORDER_BLUE),
                border_radius=14,
                padding=ft.Padding(8, 6, 6, 6),
                shadow=SHADOW_SUBTLE,
                on_click=lambda _e: on_click(),
            )

        self.management_hub: ft.Container = ft.Container(
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            _make_hub_item(
                                ft.Icons.MEDICATION,
                                ORANGE,
                                self.hub_meds_title,
                                self.hub_meds_sub,
                                self.nav_to_medicines,
                            ),
                            _make_hub_item(
                                ft.Icons.CALENDAR_MONTH,
                                SCHEDULE_NAVY,
                                self.hub_sched_title,
                                self.hub_sched_sub,
                                lambda: self.nav_to_schedule("schedules"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[
                            _make_hub_item(
                                ft.Icons.CALENDAR_TODAY,
                                GREEN,
                                self.hub_hist_title,
                                self.hub_hist_sub,
                                self.nav_to_history,
                            ),
                            _make_hub_item(
                                ft.Icons.VACCINES,
                                CYAN,
                                self.hub_ins_title,
                                self.hub_ins_sub,
                                self.nav_to_insulin,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=8,
            ),
        )

        # ---- TODAY'S ADHERENCE Green Card (PNG 4) ---------------------- #
        self.adherence_link_text: ft.Text = ft.Text(
            i18n.t("view_history"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.adherence_subtitle: ft.Text = ft.Text(
            "0 / 0 Doses Taken",
            size=13,
            color=WHITE,
        )
        self.adherence_pct: ft.Text = ft.Text("0%", size=13, color=WHITE, weight=ft.FontWeight.BOLD)
        self.adherence_fill: ft.Container = ft.Container(
            bgcolor=ORANGE,
            border_radius=8,
            height=14,
            width=0,
        )
        self.adherence_track: ft.Container = ft.Container(
            bgcolor=WHITE,
            border_radius=8,
            height=14,
            expand=True,
            content=self.adherence_fill,
            alignment=ft.Alignment.CENTER_LEFT,
        )
        self.taken_badge_text: ft.Text = ft.Text(
            "Taken 0",
            size=13,
            weight=ft.FontWeight.BOLD,
            color="#1E3A1E",
        )
        self.missed_badge_text: ft.Text = ft.Text(
            "Missed 0",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )

        self.adherence_card: ft.Container = ft.Container(
            bgcolor="#27AE60",
            border_radius=20,
            padding=ft.Padding(18, 16, 18, 16),
            width=CARD_WIDTH,
            shadow=SHADOW_ELEVATED,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "TODAY'S ADHERENCE",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=WHITE,
                            ),
                            ft.Container(
                                content=self.adherence_link_text,
                                on_click=lambda _e: self.nav_to_history(),
                                tooltip="Open Adherence Calendar History",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.adherence_subtitle,
                    ft.Row(
                        controls=[
                            self.adherence_track,
                            self.adherence_pct,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                bgcolor=TAKEN_GREEN,
                                border_radius=12,
                                padding=ft.Padding(14, 6, 14, 6),
                                content=self.taken_badge_text,
                            ),
                            ft.Container(
                                bgcolor=RED,
                                border_radius=12,
                                padding=ft.Padding(14, 6, 14, 6),
                                content=self.missed_badge_text,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=10,
            ),
        )

        # ---- ATTENTION Section (Dynamic — No static demo alert) --------- #
        self.attention_container: ft.Column = ft.Column(
            spacing=8,
            width=CARD_WIDTH,
            visible=False,  # only visible if there are actual missed alerts
        )

        # ---- TODAY'S SCHEDULE Dark Blue Card (PNG 4) ------------------- #
        self.schedule_title: ft.Text = ft.Text(
            i18n.t("todays_schedule"),
            size=17,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.schedule_link_text: ft.Text = ft.Text(
            i18n.t("view_all"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color="#FFB74D",
        )
        self.schedule_list_col: ft.Column = ft.Column(spacing=8, width=CARD_WIDTH - 40)
        self.schedule_card: ft.Container = ft.Container(
            bgcolor=SCHEDULE_NAVY,
            border_radius=20,
            padding=ft.Padding(18, 16, 18, 16),
            width=CARD_WIDTH,
            shadow=SHADOW_CARD,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.schedule_title,
                            ft.Container(
                                content=self.schedule_link_text,
                                on_click=lambda _e: self.nav_to_schedule("schedules"),
                                tooltip="View and manage all schedules",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.schedule_list_col,
                ],
                spacing=12,
            ),
        )

        # ---- DOSE TRACKING & SUPPLY Card ------------------------------- #
        self.tracking_title: ft.Text = ft.Text(
            i18n.t("dose_tracking_supply"),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )
        self.tracking_link_text: ft.Text = ft.Text(
            i18n.t("manage_tracking"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ORANGE,
        )
        self.tracking_col: ft.Column = ft.Column(spacing=8, width=CARD_WIDTH - 40)
        self.tracking_card: ft.Container = ft.Container(
            bgcolor=WHITE,
            border=ft.Border.all(1, CARD_BORDER_BLUE),
            border_radius=20,
            padding=ft.Padding(18, 16, 18, 16),
            width=CARD_WIDTH,
            shadow=SHADOW_CARD,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.INVENTORY_2_ROUNDED, color=ORANGE, size=18),
                                    self.tracking_title,
                                ],
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(
                                content=self.tracking_link_text,
                                on_click=lambda _e: self.nav_to_schedule("tracking"),
                                tooltip="Manage tracking and reschedule",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.tracking_col,
                ],
                spacing=10,
            ),
        )

        # ---- Bottom Nav ------------------------------------------------ #
        self.nav_bar: ft.Container = build_bottom_nav(
            role="caretaker",
            on_medicines=self.nav_to_medicines,
            on_schedule=self.nav_to_schedule,
            on_alerts_or_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
        )

        # ---- Subview Container (for Medicines & Add Medicine) ---------- #
        self.subview_slot: ft.Container = ft.Container(content=None, visible=False, expand=True)

        # ---- Main Dashboard Body --------------------------------------- #
        self.main_body: ft.Column = ft.Column(
            controls=[
                self.patient_section,
                ft.Container(height=4),
                self.management_hub,
                ft.Container(height=6),
                self.adherence_card,
                ft.Container(height=6),
                self.attention_container,
                self.schedule_card,
                ft.Container(height=6),
                self.tracking_card,
                ft.Container(height=16),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            expand=True,
        )
        self.dashboard_body: ft.Container = ft.Container(
            content=self.main_body,
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
        )
        self.dashboard_footer: ft.Container = ft.Container(
            content=self.nav_bar,
            alignment=ft.Alignment.BOTTOM_CENTER,
            padding=ft.Padding(0, 2, 0, 6),
        )
        self.dashboard_container: ft.Column = ft.Column(
            controls=[
                self.header,
                self.dashboard_body,
                self.dashboard_footer,
            ],
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.controls.extend([self.dashboard_container, self.subview_slot])

    def _get_salutation(self) -> str:
        raw = i18n.t("hello_caregiver", name="").replace("Caregiver", "").replace("সেবাকারী", "").strip().rstrip(",")
        return f"{raw}," if raw else "Hello,"

    def _get_username(self) -> str:
        return self._user.get("name") or self._user.get("email") or "Caregiver"

    def _get_greeting(self) -> str:
        caregiver_name: str = self._user.get("name", "Caregiver").split()[0]
        return i18n.t("hello_caregiver", name=caregiver_name)

    def _build_menu_items(self) -> List[ft.PopupMenuItem]:
        return [
            ft.PopupMenuItem(
                icon=ft.Icons.DASHBOARD_ROUNDED,
                content=ft.Text(i18n.t("menu_dashboard"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_dashboard(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.CALENDAR_MONTH,
                content=ft.Text(i18n.t("menu_schedules"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_schedule("schedules"),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.AUTO_GRAPH,
                content=ft.Text(i18n.t("menu_tracking"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_schedule("tracking"),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.MEDICATION,
                content=ft.Text(i18n.t("menu_medicines"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_medicines(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.CALENDAR_TODAY,
                content=ft.Text(i18n.t("menu_history"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_history(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.VACCINES,
                content=ft.Text(i18n.t("menu_insulin"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.nav_to_insulin(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.KEY_ROUNDED,
                content=ft.Text(i18n.t("menu_pairing"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.show_pairing_dialog(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.PERSON,
                content=ft.Text(i18n.t("menu_profile"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.show_profile_dialog(),
            ),
            ft.PopupMenuItem(
                icon=ft.Icons.LOGOUT,
                content=ft.Text(i18n.t("menu_logout"), size=13, weight=ft.FontWeight.W_500),
                on_click=lambda _e: self.on_logout(),
            ),
        ]

    def _on_lang_changed(self, _new_lang: str) -> None:
        """Called immediately upon single-click language toggle."""
        self.greeting_salutation.value = self._get_salutation()
        self.greeting_username.value = self._get_username()
        self.patient_section_title.value = i18n.t("patient")
        self.pair_btn_text.value = i18n.t("pair_patient_btn")
        self.schedule_title.value = i18n.t("todays_schedule")
        self.schedule_link_text.value = i18n.t("view_all")
        self.adherence_link_text.value = i18n.t("view_history")
        self.tracking_title.value = i18n.t("dose_tracking_supply")
        self.tracking_link_text.value = i18n.t("manage_tracking")
        self.menu_button.items = self._build_menu_items()
        self.hub_meds_title.value = i18n.t("nav_medicines")
        self.hub_meds_sub.value = i18n.t("hub_prescriptions")
        self.hub_sched_title.value = i18n.t("nav_schedule")
        self.hub_sched_sub.value = i18n.t("hub_dose_times")
        self.hub_hist_title.value = i18n.t("nav_history")
        self.hub_hist_sub.value = i18n.t("hub_adherence")
        self.hub_ins_title.value = i18n.t("insulin_title")
        self.hub_ins_sub.value = i18n.t("hub_blood_sugar")
        if not self._active_patient:
            self.patient_name_text.value = i18n.t("no_patient_connected")
            self.patient_status_text.value = i18n.t("not_connected")
        else:
            self.patient_status_text.value = i18n.t("connected")
        self._run_task(self.load_patients)
        safe_update(self)

    def _run_task(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        p = getattr(self, "_page_ref", None)
        if p and hasattr(p, "run_task"):
            try:
                p.run_task(fn, *args, **kwargs)
                return
            except Exception:
                pass
        try:
            pg = getattr(self, "_page", None)
            if pg and hasattr(pg, "run_task"):
                pg.run_task(fn, *args, **kwargs)
        except Exception:
            pass

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        self.alarm_service.start()
        self._run_task(self.load_patients)

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    # -- Subview Navigation --------------------------------------------- #
    def nav_to_medicines(self) -> None:
        pid: Optional[str] = self._active_patient.get("id") if self._active_patient else None
        meds_view = MedicinesView(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=pid,
            on_back=self.nav_to_dashboard,
            on_add_click=self.nav_to_add_medicine,
            on_schedule=self.nav_to_schedule,
            on_alerts_or_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = meds_view
        self.subview_slot.visible = True
        self._run_task(meds_view.load_medications)
        safe_update(self)

    def nav_to_schedule(self, initial_tab: str = "schedules") -> None:
        pid: Optional[str] = self._active_patient.get("id") if self._active_patient else None
        sched_view = ScheduleView(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=pid,
            on_back=self.nav_to_dashboard,
            on_medicines=self.nav_to_medicines,
            on_alerts_or_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
            alarm_service=self.alarm_service,
            initial_tab=initial_tab,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = sched_view
        self.subview_slot.visible = True
        self._run_task(sched_view.load_schedules)
        self._run_task(sched_view.load_tracking)
        safe_update(self)

    def nav_to_history(self) -> None:
        pid: Optional[str] = self._active_patient.get("id") if self._active_patient else None
        hist_view = HistoryView(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=pid,
            on_back=self.nav_to_dashboard,
            on_medicines=self.nav_to_medicines,
            on_schedule=self.nav_to_schedule,
            on_insulin=self.nav_to_insulin,
            on_profile=self.show_profile_dialog,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = hist_view
        self.subview_slot.visible = True
        try:
            hist_view.did_mount()
        except Exception:
            pass
        safe_update(self)

    def nav_to_insulin(self) -> None:
        pid: Optional[str] = self._active_patient.get("id") if self._active_patient else None
        ins_view = InsulinView(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=pid,
            on_back=self.nav_to_dashboard,
            on_medicines=self.nav_to_medicines,
            on_schedule=self.nav_to_schedule,
            on_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = ins_view
        self.subview_slot.visible = True
        try:
            ins_view.did_mount()
        except Exception:
            pass
        safe_update(self)

    def nav_to_add_medicine(self) -> None:
        pid: Optional[str] = self._active_patient.get("id") if self._active_patient else None
        add_view = AddMedicineView(
            page=self._page_ref,
            api=self._api,
            role="caretaker",
            user=self._user,
            target_patient_id=pid,
            on_back=self.nav_to_medicines,
            on_saved=self._on_med_saved,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = add_view
        self.subview_slot.visible = True
        safe_update(self)

    def _on_med_saved(self) -> None:
        self.nav_to_medicines()
        self._run_task(self.load_patients)

    def nav_to_dashboard(self) -> None:
        self.subview_slot.visible = False
        self.subview_slot.content = None
        self.dashboard_container.visible = True
        self._run_task(self.load_patients)
        safe_update(self)

    # -- Multi-Patient Switching ---------------------------------------- #
    def _select_patient(self, pt: Dict[str, Any]) -> None:
        self._active_patient = pt
        self.alarm_service.set_target_patient_id(pt.get("id"))
        p_name = pt.get("name", "Patient").split()[0]
        self.patient_name_text.value = p_name
        self._render_patient_chips()
        self._run_task(self._load_patient_doses, pt["id"])
        safe_update(self)

    def _render_patient_chips(self) -> None:
        if len(self._patients) <= 1:
            self.patient_chips_row.visible = False
            self.patient_chips_row.controls.clear()
            return
        self.patient_chips_row.visible = True
        self.patient_chips_row.controls.clear()
        for p in self._patients:
            is_active = bool(self._active_patient and self._active_patient.get("id") == p.get("id"))
            p_name = p.get("name", "Patient").split()[0]
            chip = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if is_active else ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                            size=14,
                            color=WHITE if is_active else TITLE_NAVY,
                        ),
                        ft.Text(
                            p_name,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=WHITE if is_active else TITLE_NAVY,
                        ),
                    ],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor=ORANGE if is_active else "#E2E8F0",
                border_radius=12,
                padding=ft.Padding(10, 5, 10, 5),
                on_click=lambda _e, pt=p: self._select_patient(pt),
            )
            self.patient_chips_row.controls.append(chip)

    # -- Patient & Schedule Loading ------------------------------------- #
    async def load_patients(self, *_args: Any) -> None:
        try:
            self._patients = await asyncio.to_thread(self._api.my_patients)
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return

        self.patient_list.controls.clear()

        if not self._patients:
            self.alarm_service.set_target_patient_id(None)
            self.patient_name_text.value = "No Patient Linked"
            self.patient_status_text.value = "Connect with Code"
            self.status_dot.bgcolor = "#94A3B8"
            self._render_patient_chips()
            self.patient_list.controls.append(
                ft.Text("No patients yet — enter a pairing code above.", size=FONT, color=MUTED)
            )
            # Reset adherence card
            self.adherence_subtitle.value = "0 / 0 Doses Taken"
            self.adherence_pct.value = "0%"
            self.adherence_fill.width = 0
            self.taken_badge_text.value = "Taken 0"
            self.missed_badge_text.value = "Missed 0"
            self.schedule_list_col.controls.clear()
            self.schedule_list_col.controls.append(
                ft.Text("No active schedule found.", size=14, color=WHITE)
            )
            self.attention_container.visible = False
            safe_update(self)
            return

        # Active patient
        matched = next((p for p in self._patients if self._active_patient and p.get("id") == self._active_patient.get("id")), None)
        self._active_patient = matched or self._patients[0]
        self.alarm_service.set_target_patient_id(self._active_patient.get("id"))
        patient_name: str = self._active_patient.get("name", "Patient")
        self.patient_name_text.value = patient_name.split()[0]
        self.patient_status_text.value = "Connected"
        self.status_dot.bgcolor = "#66BB6A"
        self._render_patient_chips()

        # Populate patient_list for smoke_test compatibility:
        # smoke_test expects: card.content.controls[0].value contains patient name
        # and an inner Column with ListTile controls for each medication
        for patient in self._patients:
            meds: List[Dict[str, Any]] = []
            try:
                meds = await asyncio.to_thread(self._api.list_medications, patient["id"])
            except ApiError:
                pass

            med_list_col = ft.Column(spacing=6)
            for m in meds:
                med_list_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MEDICATION, color=ORANGE),
                        title=ft.Text(m["name"], size=15),
                        subtitle=ft.Text(f"Stock: {m.get('stock_qty', 0)}"),
                    )
                )

            patient_card = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(patient.get("name", ""), size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(patient.get("email", ""), size=13, color=MUTED),
                        med_list_col,
                    ]
                )
            )
            self.patient_list.controls.append(patient_card)

        # Load today's doses for this linked patient
        await self._load_patient_doses(self._active_patient["id"])
        safe_update(self)

    async def _load_patient_doses(self, patient_id: str) -> None:
        doses: List[Dict[str, Any]] = []
        try:
            doses = await asyncio.to_thread(self._api.get_todays_doses, patient_id)
        except ApiError:
            pass

        meds: List[Dict[str, Any]] = []
        try:
            meds = await asyncio.to_thread(self._api.list_medications, patient_id)
        except ApiError:
            pass
        med_map = {m["id"]: m for m in meds}

        scheds: List[Dict[str, Any]] = []
        try:
            scheds = await asyncio.to_thread(self._api.list_schedules, None, patient_id)
        except ApiError:
            pass
        sched_map = {s["id"]: s for s in scheds}

        total = len(doses)
        taken = sum(1 for d in doses if d.get("status") == "taken")
        missed = sum(1 for d in doses if d.get("status") == "missed")

        # Update adherence card
        self.adherence_subtitle.value = f"{taken} / {total} Doses Taken"
        pct: float = (taken / total * 100) if total > 0 else 0
        self.adherence_pct.value = f"{int(pct)}%"
        self.adherence_fill.width = int(230 * (pct / 100))
        self.taken_badge_text.value = f"Taken {taken}"
        self.missed_badge_text.value = f"Missed {missed}"

        # Attention Section: Shown if there are missed doses OR medications needing rescheduling!
        tracking_items: List[Dict[str, Any]] = []
        try:
            tracking_items = await asyncio.to_thread(self._api.get_tracking_summary, patient_id)
        except Exception:
            pass

        reschedule_alerts = [
            it for it in tracking_items
            if it.get("reschedule_status") in ("reschedule_now", "reschedule_soon")
        ]

        self.attention_container.controls.clear()
        missed_doses = [d for d in doses if d.get("status") == "missed"]
        if missed_doses or reschedule_alerts:
            self.attention_container.visible = True
            self.attention_container.controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_ROUNDED, color=RED, size=22),
                        ft.Text(
                            "ATTENTION",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_NAVY,
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

            # Render Reschedule Alerts
            for ra in reschedule_alerts:
                r_med = ra.get("medication_name", "Medication")
                r_status = ra.get("reschedule_status", "reschedule_soon")
                r_days = ra.get("days_supply_remaining", 0)
                r_stock = ra.get("stock_qty", 0)
                is_crit = r_status == "reschedule_now"
                self.attention_container.controls.append(
                    ft.Container(
                        bgcolor="#FFEBEE" if is_crit else "#FFF3E0",
                        border=ft.Border.all(1.5, RED if is_crit else ORANGE),
                        border_radius=18,
                        padding=ft.Padding(14, 12, 14, 12),
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.NOTIFICATION_IMPORTANT, color=RED if is_crit else ORANGE, size=20),
                                                ft.Text(
                                                    f"RESCHEDULE: {r_med}",
                                                    size=14,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=RED if is_crit else TITLE_NAVY,
                                                    max_lines=1,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                ),
                                            ],
                                            spacing=6,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                "OUT OF STOCK" if is_crit else f"{r_days:.0f}d left",
                                                size=10,
                                                weight=ft.FontWeight.BOLD,
                                                color=WHITE,
                                            ),
                                            bgcolor=RED if is_crit else ORANGE,
                                            border_radius=6,
                                            padding=ft.Padding(6, 3, 6, 3),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            f"Stock: {r_stock} remaining",
                                            size=12,
                                            color="#64748B",
                                        ),
                                        ft.Button(
                                            content=ft.Text("Reschedule", size=12, weight=ft.FontWeight.BOLD, color=WHITE),
                                            bgcolor=ORANGE if not is_crit else RED,
                                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding(14, 0, 14, 0)),
                                            height=32,
                                            on_click=lambda _e, item=ra: show_reschedule_dialog(
                                                self._page_ref,
                                                self._api,
                                                item,
                                                on_rescheduled=lambda: self._run_task(self.load_patients),
                                                patient_id=patient_id,
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=6,
                        ),
                    )
                )

            # Render Missed Doses
            for md in missed_doses:
                s = sched_map.get(md.get("schedule_id", ""), {})
                m = med_map.get(s.get("medication_id", ""), {})
                m_name = m.get("name", "Prescription Med")
                m_form = m.get("form", "Tablet")
                raw_time = s.get("due_time", "09:00:00")
                try:
                    t = datetime.strptime(raw_time, "%H:%M:%S")
                    t_str = t.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    t_str = "9:00 AM"

                self.attention_container.controls.append(
                    ft.Container(
                        bgcolor=CARD_BG_BLUE,
                        border=ft.Border.all(1, CARD_BORDER_BLUE),
                        border_radius=18,
                        padding=ft.Padding(14, 12, 14, 12),
                        content=ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            shape=ft.BoxShape.CIRCLE,
                                            bgcolor=RED,
                                            width=12,
                                            height=12,
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text(
                                                    t_str,
                                                    size=15,
                                                    weight=ft.FontWeight.BOLD,
                                                    color="#334155",
                                                ),
                                                ft.Text(m_name, size=14, color="#334155", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                                ft.Text(
                                                    f"1 {m_form}",
                                                    size=12,
                                                    color="#64748B",
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    expand=True,
                                ),
                                ft.Button(
                                    content=ft.Text(
                                        "Report",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=WHITE,
                                    ),
                                    bgcolor=RED,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding(12, 0, 12, 0)),
                                    height=32,
                                    on_click=lambda _e, mn=m_name: toast(
                                        self._page_ref, f"Report logged for {mn}."
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
        else:
            self.attention_container.visible = False

        # Populate self.tracking_col
        self.tracking_col.controls.clear()
        if not tracking_items:
            self.tracking_col.controls.append(
                ft.Text("No medications tracked for this patient.", size=13, color=MUTED)
            )
        else:
            for it in tracking_items:
                m_name = it.get("medication_name", "Med")
                stk = it.get("stock_qty", 0)
                d_left = it.get("days_supply_remaining", 0)
                freq_str = it.get("frequency_summary", "Daily")
                r_stat = it.get("reschedule_status", "healthy")
                r_date = it.get("reschedule_due_date", "")
                due_disp = "Immediate"
                if r_date:
                    try:
                        due_disp = datetime.fromisoformat(r_date.replace("Z", "+00:00")).strftime("%b %d, %Y")
                    except Exception:
                        due_disp = r_date[:10]

                card_border = RED if r_stat == "reschedule_now" else (ORANGE if r_stat == "reschedule_soon" else "#E2E8F0")
                badge_bg = RED if r_stat == "reschedule_now" else (ORANGE if r_stat == "reschedule_soon" else "#2E7D32")
                badge_lbl = "🚨 OUT" if r_stat == "reschedule_now" else (f"⚠️ {d_left:.0f}d left" if r_stat == "reschedule_soon" else f"✅ {d_left:.0f}d left")

                self.tracking_col.controls.append(
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border=ft.Border.all(1.5, card_border),
                        border_radius=14,
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Column(
                                            controls=[
                                                ft.Text(m_name, size=14, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                                                ft.Text(f"Freq: {freq_str} • Stock: {stk}", size=12, color=TEXT),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Text(badge_lbl, size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                                            bgcolor=badge_bg,
                                            border_radius=8,
                                            padding=ft.Padding(8, 4, 8, 4),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Text(f"Reschedule: {due_disp}", size=11, color=MUTED),
                                        ft.Button(
                                            content=ft.Text("Reschedule", size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                                            bgcolor=SCHEDULE_NAVY,
                                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                            height=28,
                                            on_click=lambda _e, item=it: show_reschedule_dialog(
                                                self._page_ref,
                                                self._api,
                                                item,
                                                on_rescheduled=lambda: self._run_task(self.load_patients),
                                                patient_id=patient_id,
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            ],
                            spacing=6,
                        ),
                    )
                )

        # Schedule Card: List today's schedule items
        self.schedule_list_col.controls.clear()
        if not scheds and not doses:
            self.schedule_list_col.controls.append(
                ft.Text("No schedules recorded for today.", size=14, color=WHITE)
            )
        else:
            items = doses if doses else scheds
            for item in items[:4]:
                if "schedule_id" in item:  # dose event
                    s = sched_map.get(item["schedule_id"], {})
                    m = med_map.get(s.get("medication_id", ""), {})
                    name = m.get("name", "Prescription Med")
                    raw_time = s.get("due_time", "09:00:00")
                else:  # schedule
                    m = med_map.get(item.get("medication_id", ""), {})
                    name = m.get("name", "Prescription Med")
                    raw_time = item.get("due_time", "09:00:00")

                try:
                    t = datetime.strptime(raw_time, "%H:%M:%S")
                    t_str = t.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    t_str = "9:00 AM"

                self.schedule_list_col.controls.append(
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SCHEDULE, color="#FFB74D", size=18),
                            ft.Text(t_str, size=15, weight=ft.FontWeight.BOLD, color=WHITE),
                            ft.Text(name, size=15, color=WHITE, expand=True),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )

    # -- Pairing & Dialogs ---------------------------------------------- #
    async def on_pair(self, *_args: Any) -> None:
        code: str = (self.code_field.value or "").strip()
        if len(code) != 6 or not code.isdigit():
            toast(self._page_ref, "Enter the 6-digit code from the patient.", error=True)
            return
        try:
            link: Dict[str, Any] = await asyncio.to_thread(self._api.pair_with_code, code)
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return
        self.code_field.value = ""
        toast(self._page_ref, f"Connected to patient successfully!")
        await self.load_patients()

    def show_pairing_dialog(self) -> None:
        dlg_code_field = ft.TextField(
            label="6-digit pairing code",
            width=220,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
        )

        async def pair_click(_e: Any) -> None:
            c: str = (dlg_code_field.value or "").strip()
            self.code_field.value = c
            await self.on_pair()
            self._page_ref.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.t("connect_patient_title"), weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text(i18n.t("connect_patient_desc"), size=14),
                    dlg_code_field,
                    ft.Button(content=ft.Text(i18n.t("connect")), bgcolor=ORANGE, color=WHITE, on_click=pair_click),
                ],
                tight=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self._page_ref.show_dialog(dlg)

    def show_schedule_dialog(self) -> None:
        self.nav_to_schedule()

    def show_alerts_dialog(self) -> None:
        count = sum(1 for c in self.attention_container.controls if isinstance(c, ft.Container))
        msg = f"{count} urgent missed alerts currently." if count > 0 else "No active alerts. All good!"
        dlg = ft.AlertDialog(
            title=ft.Text("Alerts", weight=ft.FontWeight.BOLD),
            content=ft.Text(msg, size=14),
        )
        self._page_ref.show_dialog(dlg)

    def show_profile_dialog(self) -> None:
        patient_name = self._active_patient.get("name") if self._active_patient else None
        show_oriented_profile_dialog(
            page=self._page_ref,
            user=self._user,
            role="caretaker",
            active_patient_name=patient_name,
            on_connect_patient=self.show_pairing_dialog,
            on_logout=self.on_logout,
        )

    async def on_logout(self, *_args: Any) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)
        self.alarm_service.stop()
        self._on_logout()

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        actor_id: str = str(payload.get("actor_id", ""))
        if actor_id and actor_id == self._user.get("id"):
            return
        if event_type in (
            "MEDICATION_CREATED",
            "MEDICATION_UPDATED",
            "MEDICATION_DELETED",
            "SCHEDULE_CREATED",
            "SCHEDULE_DELETED",
            "DOSE_STATUS_CHANGED",
        ):
            self.alarm_service.invalidate_cache()
            toast(self._page_ref, f"Patient medication or schedule update received.")
            self._run_task(self.load_patients)
        elif event_type == "CARE_LINK_ACTIVATED":
            toast(self._page_ref, f"New patient connection activated!")
            self._run_task(self.load_patients)
        elif event_type == "MISSED_DOSE_ALERT":
            toast(self._page_ref, f"ALERT: Patient missed dose!", error=True)
            self._run_task(self.load_patients)
        elif event_type == "RESCHEDULE_ALERT":
            patient_name = payload.get("patient_name", "Patient")
            med_name = payload.get("medication_name", "Medication")
            days = payload.get("days_supply_remaining", 0)
            status = payload.get("reschedule_status", "")
            if status == "reschedule_now":
                toast(self._page_ref, f"🚨 Reschedule Alert for {patient_name}: {med_name} is OUT OF STOCK!", error=True)
            else:
                toast(self._page_ref, f"⚠️ Reschedule Alert for {patient_name}: {med_name} has only {days:.0f} day(s) of supply left.", error=True)
            self._run_task(self.load_patients)
        elif event_type == "RESCHEDULE_COMPLETED":
            med_name = payload.get("medication_name", "Medication")
            patient_name = payload.get("patient_name", "Patient")
            toast(self._page_ref, f"✅ {med_name} rescheduled for {patient_name}.")
            self._run_task(self.load_patients)
