"""PatientView — Patient Dashboard matching PNG 3."""

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
    RED,
    SCHEDULE_NAVY,
    TEXT,
    TITLE_NAVY,
    WHITE,
    YELLOW,
)
from services import i18n
from services.api_client import Api, ApiError
from services.alarm_service import AlarmService
from views.add_medicine_view import AddMedicineView
from views.history_view import HistoryView
from views.insulin_view import InsulinView
from views.medicines_view import MedicinesView
from views.schedule_view import ScheduleView

#
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
            width=APP_WIDTH,
            expand=True,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._user: Dict[str, Any] = user
        self._on_logout: Callable[[], None] = on_logout
        self._target_patient_id: Optional[str] = None

        def _on_alarm_status_updated() -> None:
            if getattr(self, "page", None) and hasattr(self.page, "run_task"):
                try:
                    self.page.run_task(self.load_data)
                except Exception:
                    pass

        self.alarm_service: AlarmService = AlarmService(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=None,
            on_status_updated=_on_alarm_status_updated,
        )

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

        self.lang_toggle: ft.Container = build_language_toggle(
            on_toggle=self._on_lang_changed,
            api=self._api,
            bg_color="#1E293B",
            text_color=WHITE,
        )

        self.greeting_container: ft.Container = ft.Container(
            content=self.greeting_col,
            expand=True,
            on_click=lambda _e: self.show_profile_dialog(),
            tooltip="View Profile",
        )

        # ---- Top Dropdown Hamburger Menu -------------------------------- #
        self.menu_button: ft.PopupMenuButton = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            icon_color=WHITE,
            tooltip="Menu",
            items=self._build_menu_items(),
        )

        self.header: ft.Container = ft.Container(
            bgcolor=GREEN,
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

        # ---- TODAY'S MEDICINES Section --------------------------------- #
        self.today_title: ft.Text = ft.Text(
            i18n.t("todays_medicines"),
            size=18,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )

        self.today_meds_col: ft.Column = ft.Column(spacing=12, width=CARD_WIDTH)

        # ---- TODAY'S PROGRESS Card ------------------------------------- #
        self.progress_title: ft.Text = ft.Text(
            i18n.t("todays_progress"),
            size=18,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
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
            width=CARD_WIDTH,
            shadow=SHADOW_ELEVATED,
            content=ft.Column(
                controls=[
                    self.progress_title,
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

        # ---- DOSE TRACKING & RESCHEDULE Section ------------------------- #
        self.tracking_title: ft.Text = ft.Text(
            i18n.t("dose_tracking_reschedule"),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )
        self.tracking_col: ft.Column = ft.Column(spacing=8, width=CARD_WIDTH)
        self.tracking_card: ft.Container = ft.Container(
            bgcolor=WHITE,
            border=ft.Border.all(1, CARD_BORDER_BLUE),
            border_radius=20,
            padding=ft.Padding(16, 14, 16, 14),
            width=CARD_WIDTH,
            shadow=SHADOW_CARD,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.tracking_title,
                            ft.Icon(ft.Icons.AUTO_GRAPH, color=CYAN, size=20),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.tracking_col,
                ],
                spacing=8,
            ),
        )

        # ---- Quick Link to Tracking & Reschedule in Schedule View ----- #
        self.tracking_quick_link_text: ft.Text = ft.Text(
            i18n.t("view_tracking_reschedule"),
            size=12,
            weight=ft.FontWeight.W_600,
            color=TITLE_NAVY,
        )
        self.tracking_quick_link: ft.Container = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.AUTO_GRAPH, color=CYAN, size=16),
                            self.tracking_quick_link_text,
                        ],
                        spacing=6,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS, color=MUTED, size=12),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=WHITE,
            border=ft.Border.all(1, CARD_BORDER_BLUE),
            border_radius=14,
            padding=ft.Padding(14, 10, 14, 10),
            width=CARD_WIDTH,
            shadow=SHADOW_SUBTLE,
            on_click=lambda _e: self.nav_to_schedule("tracking"),
        )

        # ---- Bottom Nav ------------------------------------------------ #
        self.nav_bar: ft.Container = build_bottom_nav(
            role="patient",
            on_medicines=self.nav_to_medicines,
            on_schedule=self.nav_to_schedule,
            on_alerts_or_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
        )

        # ---- Subview Container (swapped when navigating to Medicines, Schedule, History, etc.) --- #
        self.subview_slot: ft.Container = ft.Container(content=None, visible=False, expand=True)

        # ---- Scrollable Dashboard Cards Area --------------------------- #
        self.dashboard_scroll: ft.Column = ft.Column(
            controls=[
                ft.Container(height=12),
                ft.Container(
                    content=self.today_title,
                    width=CARD_WIDTH,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(0, 6, 0, 4),
                ),
                self.today_meds_col,
                ft.Container(height=8),
                self.progress_card,
                ft.Container(height=6),
                self.tracking_quick_link,
                ft.Container(height=16),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            expand=True,
        )
        self.dashboard_body: ft.Container = ft.Container(
            content=self.dashboard_scroll,
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
        )
        self.dashboard_footer: ft.Container = ft.Container(
            content=self.nav_bar,
            alignment=ft.Alignment.BOTTOM_CENTER,
            padding=ft.Padding(0, 2, 0, 6),
        )

        # Full Dashboard layout: Header (fixed top) + Body (scrollable) + Footer (docked bottom)
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

        # Compatibility reference for smoke_test and existing test assertions
        self.main_body: ft.Column = self.dashboard_scroll

        self.controls.extend([self.dashboard_container, self.subview_slot])

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

    def _get_salutation(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            key = "good_morning"
        elif hour < 17:
            key = "good_afternoon"
        else:
            key = "good_evening"
        raw = i18n.t(key, name="").replace(" ,", "").replace("{name}", "").strip().rstrip(",")
        return f"{raw},"

    def _get_username(self) -> str:
        return self._user.get("name") or self._user.get("email") or "User"

    def _get_greeting(self) -> str:
        return f"{self._get_salutation()} {self._get_username()}"

    def _on_lang_changed(self, _new_lang: str) -> None:
        """Called immediately upon single-click language toggle."""
        self.greeting_salutation.value = self._get_salutation()
        self.greeting_username.value = self._get_username()
        self.today_title.value = i18n.t("todays_medicines")
        self.progress_title.value = i18n.t("todays_progress")
        self.tracking_title.value = i18n.t("dose_tracking_reschedule")
        self.tracking_quick_link_text.value = i18n.t("view_tracking_reschedule")
        self.menu_button.items = self._build_menu_items()
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_data)
        except Exception:
            pass
        safe_update(self)

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        self.alarm_service.start()
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_data)
        except Exception:
            pass

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _run_task(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        p = getattr(self, "_page_ref", None)
        if p and hasattr(p, "run_task"):
            try:
                p.run_task(fn, *args, **kwargs)
                return
            except Exception:
                pass
        try:
            if getattr(self, "page", None) and hasattr(self.page, "run_task"):
                self.page.run_task(fn, *args, **kwargs)
        except Exception:
            pass

    async def load_data(self, *_args: Any) -> None:
        await self.load_medications()
        await self.load_todays_doses()
        await self.load_tracking()

    async def load_tracking(self) -> None:
        try:
            items = await asyncio.to_thread(self._api.get_tracking_summary)
        except Exception:
            items = []

        self.tracking_col.controls.clear()
        if not items:
            self.tracking_col.controls.append(
                ft.Text("No medications added yet.", size=13, color=MUTED)
            )
            safe_update(self.tracking_card)
            return

        for item in items:
            self.tracking_col.controls.append(self._build_tracking_card(item))
        safe_update(self.tracking_card)

    def _build_tracking_card(self, item: Dict[str, Any]) -> ft.Container:
        med_name = item.get("medication_name", "Medication")
        stock = item.get("stock_qty", 0)
        days_left = item.get("days_supply_remaining", 0)
        status = item.get("reschedule_status", "healthy")
        freq = item.get("frequency_summary", "Daily")
        resched_date_str = item.get("reschedule_due_date", "")

        due_display = i18n.t("immediate")
        if resched_date_str:
            try:
                dt = datetime.fromisoformat(resched_date_str.replace("Z", "+00:00"))
                due_display = dt.strftime("%b %d, %Y")
            except Exception:
                due_display = resched_date_str[:10]

        if status == "reschedule_now":
            badge_color = RED
            badge_text = f"🚨 {i18n.t('reschedule_now')} (0 {i18n.t('stock')})"
        elif status == "reschedule_soon":
            badge_color = ORANGE
            badge_text = f"⚠️ {i18n.t('reschedule_soon')} ({days_left:.0f}d)"
        else:
            badge_color = "#2E7D32"
            badge_text = f"✅ {i18n.t('supply_healthy')} ({days_left:.0f}d)"

        return ft.Container(
            bgcolor="#F8FAFC",
            border_radius=14,
            padding=12,
            border=ft.Border.all(
                1.5,
                RED if status == "reschedule_now" else (ORANGE if status == "reschedule_soon" else "#E2E8F0"),
            ),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(med_name, size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                                    ft.Text(f"{i18n.t('frequency_label', freq=freq)} • {i18n.t('stock')}: {stock}", size=12, color=TEXT),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(badge_text, size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                                bgcolor=badge_color,
                                border_radius=8,
                                padding=ft.Padding(8, 4, 8, 4),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(f"{i18n.t('reschedule_due')}: {due_display}", size=12, color=MUTED, weight=ft.FontWeight.W_500),
                            ft.Button(
                                content=ft.Text(i18n.t("reschedule_btn"), size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                                bgcolor=SCHEDULE_NAVY,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                height=30,
                                on_click=lambda _e, it=item: show_reschedule_dialog(
                                    self._page_ref,
                                    self._api,
                                    it,
                                    on_rescheduled=lambda: self.page.run_task(self.load_data) if getattr(self, "page", None) else None,
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
            on_schedule=self.nav_to_schedule,
            on_alerts_or_history=self.nav_to_history,
            on_profile=self.show_profile_dialog,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = meds_view
        self.subview_slot.visible = True
        if getattr(self, "page", None) and hasattr(self.page, "run_task"):
            try:
                self.page.run_task(meds_view.load_medications)
            except Exception:
                pass
        safe_update(self)

    def nav_to_schedule(self, initial_tab: str = "schedules") -> None:
        sched_view = ScheduleView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=None,
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
        if getattr(self, "page", None) and hasattr(self.page, "run_task"):
            try:
                self.page.run_task(sched_view.load_schedules)
                self.page.run_task(sched_view.load_tracking)
            except Exception:
                pass
        safe_update(self)

    def nav_to_history(self) -> None:
        hist_view = HistoryView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=self._target_patient_id,
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
        ins_view = InsulinView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=self._target_patient_id,
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
        add_view = AddMedicineView(
            page=self._page_ref,
            api=self._api,
            role="patient",
            user=self._user,
            target_patient_id=None,
            on_back=self.nav_to_medicines,
            on_saved=self._on_med_saved,
        )
        self.dashboard_container.visible = False
        self.subview_slot.content = add_view
        self.subview_slot.visible = True
        safe_update(self)

    def _on_med_saved(self) -> None:
        self.nav_to_medicines()
        self._run_task(self.load_data)

    def nav_to_dashboard(self) -> None:
        self.subview_slot.visible = False
        self.subview_slot.content = None
        self.dashboard_container.visible = True
        self._run_task(self.load_data)
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
        self.progress_subtitle.value = i18n.t("doses_taken", taken=taken, total=total)
        pct: float = (taken / total * 100) if total > 0 else 0
        self.progress_pct.value = f"{int(pct)}%"
        # progress track has width approx 230
        self.progress_fill.width = int(230 * (pct / 100))
        rem_str: str = (
            i18n.t("all_doses_complete")
            if total > 0 and remaining == 0
            else (
                i18n.t("meds_remaining", count=remaining)
                if remaining == 1
                else i18n.t("meds_remaining_plural", count=remaining)
            )
        )
        self.remaining_badge_text.value = rem_str

        # Render Dose Cards (No demo hardcoding)
        pending_doses = [d for d in doses if d.get("status") == "pending"]
        if not pending_doses:
            msg: str = (
                i18n.t("all_doses_complete")
                if total > 0
                else i18n.t("no_meds_scheduled")
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
            if hasattr(self, "alarm_service") and self.alarm_service:
                self.alarm_service.mark_schedule_handled(sched_id, "taken")
                self.alarm_service.dismiss_alarm()
            try:
                await asyncio.to_thread(self._api.set_dose_status, dose["id"], "taken")
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, f"Marked {med_name} as taken!")
            await self.load_data()

        return ft.Container(
            bgcolor=CARD_BG_BLUE,
            border=ft.Border.all(1, "#CCE9FA"),
            border_radius=18,
            shadow=SHADOW_SUBTLE,
            padding=ft.Padding(16, 14, 16, 14),
            width=CARD_WIDTH,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        shape=ft.BoxShape.CIRCLE,
                                        bgcolor=YELLOW,
                                        width=12,
                                        height=12,
                                    ),
                                    ft.Text(
                                        time_display,
                                        size=17,
                                        weight=ft.FontWeight.BOLD,
                                        color=TITLE_NAVY,
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Text(
                                med_name,
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color="#1E293B",
                            ),
                            ft.Text(
                                dose_label,
                                size=14,
                                color="#64748B",
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Container(height=0),
                            ft.Button(
                                content=ft.Text(i18n.t("take_now").upper(), size=12, weight=ft.FontWeight.BOLD),
                                bgcolor=CYAN,
                                color=WHITE,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=14),
                                    padding=ft.Padding(14, 8, 14, 8),
                                ),
                                height=38,
                                on_click=take_now,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
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
            title=ft.Text(i18n.t("share_code_title"), weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text(i18n.t("share_code_desc"), size=14),
                    ft.Container(content=code_box, alignment=ft.Alignment.CENTER, padding=10),
                    ft.Button(content=ft.Text(i18n.t("pairing_code")), on_click=generate),
                ],
                tight=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self._page_ref.show_dialog(dlg)

    def show_schedule_dialog(self) -> None:
        self.nav_to_schedule()

    def show_history_dialog(self) -> None:
        dlg = ft.AlertDialog(
            title=ft.Text("Dose History", weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Progress today: {self.progress_subtitle.value}", size=14),
        )
        self._page_ref.show_dialog(dlg)

    def show_profile_dialog(self) -> None:
        show_oriented_profile_dialog(
            page=self._page_ref,
            user=self._user,
            role="patient",
            code_display_value=self.code_display.value,
            code_display_control=self.code_display,
            on_generate_code=self.on_generate_code,
            on_logout=self.on_logout,
        )

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
            if event_type == "DOSE_STATUS_CHANGED":
                sched_id = payload.get("schedule_id")
                if sched_id and hasattr(self, "alarm_service") and self.alarm_service:
                    self.alarm_service.mark_schedule_handled(sched_id, str(payload.get("status", "taken")))
                    self.alarm_service.dismiss_alarm()
            self.alarm_service.invalidate_cache()
            toast(self._page_ref, f"Medication & schedule updates synced.")
            if self.parent is not None:
                self._run_task(self.load_data)
        elif event_type == "CARE_LINK_ACTIVATED":
            toast(self._page_ref, f"A caregiver joined your care team.")
        elif event_type == "RESCHEDULE_ALERT":
            med_name = payload.get("medication_name", "Medication")
            days = payload.get("days_supply_remaining", 0)
            status = payload.get("reschedule_status", "")
            if status == "reschedule_now":
                toast(self._page_ref, f"🚨 RESCHEDULE REQUIRED: {med_name} is out of stock!", error=True)
            else:
                toast(self._page_ref, f"⚠️ Reschedule Alert: {med_name} has {days:.0f} day(s) of supply left.")
            if self.parent is not None:
                self._run_task(self.load_data)
        elif event_type == "RESCHEDULE_COMPLETED":
            med_name = payload.get("medication_name", "Medication")
            toast(self._page_ref, f"✅ {med_name} rescheduled successfully! Stock updated.")
            if self.parent is not None:
                self._run_task(self.load_data)
