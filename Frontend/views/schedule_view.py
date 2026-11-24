"""ScheduleView — Full dose scheduling and management screen."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

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
from config import (
    APP_WIDTH,
    BLUE,
    CARD_BG_BLUE,
    CARD_BORDER_BLUE,
    CARD_WIDTH,
    CYAN,
    FONT,
    GREEN,
    INPUT_BG,
    INPUT_TEXT,
    MUTED,
    ORANGE,
    RED,
    SCHEDULE_NAVY,
    TEXT,
    TITLE_NAVY,
    WHITE,
    YELLOW,
)
from services import i18n
from services.api_client import Api, ApiError

#
def _format_time(raw_time: str) -> str:
    """Format HH:MM:SS string to 12-hour AM/PM string."""
    try:
        t = datetime.strptime(raw_time, "%H:%M:%S")
        return t.strftime("%I:%M %p").lstrip("0")
    except Exception:
        try:
            t = datetime.strptime(raw_time, "%H:%M")
            return t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return raw_time


def _parse_minute(val: Any) -> str:
    try:
        m = int(str(val or "").strip())
        if 0 <= m <= 59:
            return f"{m:02d}"
    except Exception:
        pass
    return "00"


def _to_24h_time(hour_str: str, min_str: str, period: str) -> str:
    """Convert 12-hour hour, minute, period to HH:MM:00."""
    try:
        h = int(str(hour_str).strip())
    except Exception:
        h = 9
    m = int(_parse_minute(min_str))
    p = str(period).strip().upper()
    if p == "PM" and h < 12:
        h += 12
    elif p == "AM" and h == 12:
        h = 0
    return f"{h:02d}:{m:02d}:00"


class ScheduleView(ft.Column):
    """View and manage all dose schedules for a patient."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        role: str,
        user: Dict[str, Any],
        target_patient_id: Optional[str],
        on_back: Callable[[], None],
        on_medicines: Optional[Callable[[], None]] = None,
        on_alerts_or_history: Optional[Callable[[], None]] = None,
        on_profile: Optional[Callable[[], None]] = None,
        initial_med_id: Optional[str] = None,
        alarm_service: Optional[Any] = None,
        initial_tab: str = "schedules",
    ) -> None:
        super().__init__(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            expand=True,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._role: str = role
        self._user: Dict[str, Any] = user
        self._target_patient_id: Optional[str] = target_patient_id
        self._on_back: Callable[[], None] = on_back
        self._on_medicines: Optional[Callable[[], None]] = on_medicines
        self._on_alerts_or_history: Optional[Callable[[], None]] = on_alerts_or_history
        self._on_profile: Optional[Callable[[], None]] = on_profile
        self._initial_med_id: Optional[str] = initial_med_id
        self._alarm_service: Optional[Any] = alarm_service
        self._current_tab: str = initial_tab

        self._filter_mode: str = "all"  # "all" or "today"
        self._schedules: List[Dict[str, Any]] = []
        self._medications: List[Dict[str, Any]] = []
        self._med_map: Dict[str, Dict[str, Any]] = {}
        self._tracking_items: List[Dict[str, Any]] = []

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Header ------------------------------------------------ #
        self.header_title: ft.Text = ft.Text(
            i18n.t("schedule_title"),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.lang_toggle: ft.Container = build_language_toggle(
            on_toggle=self._on_lang_changed,
            api=self._api,
            bg_color="#1E293B",
            text_color=WHITE,
        )
        self.header: ft.Container = ft.Container(
            bgcolor=theme_color,
            padding=ft.Padding(16, 8, 16, 16),
            border_radius=ft.BorderRadius(0, 0, 32, 0),
            content=ft.SafeArea(
                content=ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    shape=ft.BoxShape.CIRCLE,
                                    bgcolor=WHITE,
                                    width=40,
                                    height=40,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.ARROW_BACK, color=theme_color, size=22),
                                    on_click=lambda _e: self._on_back(),
                                ),
                                self.header_title,
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        self.lang_toggle,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                avoid_intrusions_bottom=False,
            ),
            width=APP_WIDTH,
        )

        # ---- Segment / Tab Selector (Schedules vs Tracking & Reschedule) ---- #
        is_sched_init = (self._current_tab == "schedules")
        self.tab_schedules_text: ft.Text = ft.Text(
            i18n.t("tab_schedules"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE if is_sched_init else TITLE_NAVY,
        )
        self.tab_tracking_text: ft.Text = ft.Text(
            i18n.t("tab_tracking"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE if not is_sched_init else TITLE_NAVY,
        )

        self.tab_schedules_btn: ft.Container = ft.Container(
            content=self.tab_schedules_text,
            bgcolor=SCHEDULE_NAVY if is_sched_init else WHITE,
            border=ft.Border.all(1, SCHEDULE_NAVY if is_sched_init else CARD_BORDER_BLUE),
            border_radius=14,
            padding=ft.Padding(10, 8, 10, 8),
            alignment=ft.Alignment.CENTER,
            on_click=lambda _e: self._switch_tab("schedules"),
            expand=True,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.tab_tracking_btn: ft.Container = ft.Container(
            content=self.tab_tracking_text,
            bgcolor=SCHEDULE_NAVY if not is_sched_init else WHITE,
            border=ft.Border.all(1, SCHEDULE_NAVY if not is_sched_init else CARD_BORDER_BLUE),
            border_radius=14,
            padding=ft.Padding(10, 8, 10, 8),
            alignment=ft.Alignment.CENTER,
            on_click=lambda _e: self._switch_tab("tracking"),
            expand=True,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.tab_selector: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 4, 4, 2),
            content=ft.Row(
                controls=[
                    self.tab_schedules_btn,
                    self.tab_tracking_btn,
                ],
                spacing=8,
            ),
        )

        # ---- Title + ADD+ button row ----------------------------------- #
        self.count_text: ft.Text = ft.Text(
            i18n.t("schedules_count", count=0),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=TEXT,
        )

        self.test_alarm_btn_text: ft.Text = ft.Text(
            i18n.t("test_alarm_btn"), size=11, weight=ft.FontWeight.BOLD, color=WHITE
        )

        self.test_alarm_btn: ft.Button = ft.Button(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.NOTIFICATION_IMPORTANT, color=WHITE, size=15),
                    self.test_alarm_btn_text,
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=RED,
            color=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            height=40,
            width=105,
            on_click=lambda _e: self._trigger_test_alarm(),
        )

        self.add_btn_text: ft.Text = ft.Text(
            i18n.t("add_btn"), size=14, weight=ft.FontWeight.BOLD, color=WHITE
        )

        self.add_btn: ft.Button = ft.Button(
            content=ft.Row(
                [
                    self.add_btn_text,
                    ft.Icon(ft.Icons.ADD, color=WHITE, size=17),
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#66BB6A",
            color=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            height=40,
            width=85,
            on_click=lambda _e: self.open_add_schedule_dialog(),
        )

        self.title_text: ft.Text = ft.Text(
            i18n.t("dose_schedules_title"),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )

        self.title_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 4, 4, 0),
            visible=is_sched_init,
            content=ft.Row(
                controls=[
                    ft.Column(
                        [
                            self.title_text,
                            self.count_text,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            self.test_alarm_btn,
                            self.add_btn,
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Filter Row (FILTER : All, Today) -------------------------- #
        self.filter_all_badge: ft.Container = ft.Container(
            content=ft.Text(i18n.t("all"), size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=BLUE,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_all,
        )
        self.filter_today_badge: ft.Container = ft.Container(
            content=ft.Text(i18n.t("today"), size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=SCHEDULE_NAVY,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_today,
        )

        self.filter_label: ft.Text = ft.Text(
            i18n.t("filter_label"), size=14, weight=ft.FontWeight.BOLD, color=TITLE_NAVY
        )

        self.filter_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 0, 4, 6),
            visible=is_sched_init,
            content=ft.Row(
                controls=[
                    self.filter_label,
                    self.filter_all_badge,
                    self.filter_today_badge,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Schedule List --------------------------------------------- #
        self.schedule_list: ft.Column = ft.Column(spacing=12, width=CARD_WIDTH, visible=is_sched_init)

        # ---- DOSE TRACKING & RESCHEDULE Section ------------------------- #
        self.tracking_title_text: ft.Text = ft.Text(
            i18n.t("dose_tracking_reschedule"),
            size=18,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )
        self.tracking_subtitle_text: ft.Text = ft.Text(
            i18n.t("tracking_subtitle"),
            size=12,
            color=MUTED,
        )
        self.tracking_refresh_btn: ft.IconButton = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=CYAN,
            tooltip="Refresh Tracking",
            on_click=lambda _e: self.page.run_task(self.load_tracking) if getattr(self, "page", None) else None,
        )
        self.tracking_header_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 4, 4, 2),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            self.tracking_title_text,
                            self.tracking_subtitle_text,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    self.tracking_refresh_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self.tracking_list: ft.Column = ft.Column(spacing=10, width=CARD_WIDTH)
        self.tracking_section: ft.Column = ft.Column(
            controls=[
                self.tracking_header_row,
                self.tracking_list,
            ],
            spacing=8,
            width=CARD_WIDTH,
            visible=(not is_sched_init),
        )

        # ---- Bottom Nav ------------------------------------------------ #
        self.nav_bar: ft.Container = build_bottom_nav(
            role=self._role,
            on_medicines=self._on_medicines,
            on_schedule=lambda: self._switch_tab("schedules"),
            on_alerts_or_history=self._on_alerts_or_history,
            on_profile=self._on_profile,
        )

        # Fixed Footer Layout: Scrollable body area (expand=True) + Pinned Footer
        self.scroll_content: ft.Column = ft.Column(
            controls=[
                self.tab_selector,
                self.title_row,
                self.filter_row,
                self.schedule_list,
                self.tracking_section,
                ft.Container(height=16),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            expand=True,
        )
        self.body_container: ft.Container = ft.Container(
            content=self.scroll_content,
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
        )
        self.footer_container: ft.Container = ft.Container(
            content=self.nav_bar,
            alignment=ft.Alignment.BOTTOM_CENTER,
            padding=ft.Padding(0, 2, 0, 6),
        )

        self.controls.extend(
            [
                self.header,
                self.body_container,
                self.footer_container,
            ]
        )

    def _switch_tab(self, tab: str) -> None:
        self._current_tab = tab
        is_sched = (tab == "schedules")
        self.tab_schedules_btn.bgcolor = SCHEDULE_NAVY if is_sched else WHITE
        self.tab_schedules_btn.border = ft.Border.all(1, SCHEDULE_NAVY if is_sched else CARD_BORDER_BLUE)
        self.tab_schedules_text.color = WHITE if is_sched else TITLE_NAVY

        self.tab_tracking_btn.bgcolor = SCHEDULE_NAVY if not is_sched else WHITE
        self.tab_tracking_btn.border = ft.Border.all(1, SCHEDULE_NAVY if not is_sched else CARD_BORDER_BLUE)
        self.tab_tracking_text.color = WHITE if not is_sched else TITLE_NAVY

        self.title_row.visible = is_sched
        self.filter_row.visible = is_sched
        self.schedule_list.visible = is_sched
        self.tracking_section.visible = not is_sched

        if not is_sched:
            try:
                p = self.page
                if p and hasattr(p, "run_task"):
                    p.run_task(self.load_tracking)
            except Exception:
                pass
        safe_update(self)

    def _on_lang_changed(self, _new_lang: str) -> None:
        self.header_title.value = i18n.t("schedule_title")
        self.tab_schedules_text.value = i18n.t("tab_schedules")
        self.tab_tracking_text.value = i18n.t("tab_tracking")
        self.title_text.value = i18n.t("dose_schedules_title")
        self.test_alarm_btn_text.value = i18n.t("test_alarm_btn")
        self.add_btn_text.value = i18n.t("add_btn")
        self.filter_label.value = i18n.t("filter_label")
        self.filter_all_badge.content = ft.Text(i18n.t("all"), size=12, weight=ft.FontWeight.BOLD, color=WHITE)
        self.filter_today_badge.content = ft.Text(i18n.t("today"), size=12, weight=ft.FontWeight.BOLD, color=WHITE)
        self.tracking_title_text.value = i18n.t("dose_tracking_reschedule")
        self.tracking_subtitle_text.value = i18n.t("tracking_subtitle")
        self._render_schedules()
        self._render_tracking()
        safe_update(self)

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_schedules)
                p.run_task(self.load_tracking)
        except Exception:
            pass

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _select_all(self, *_args: Any) -> None:
        self._filter_mode = "all"
        self.filter_all_badge.bgcolor = BLUE
        self.filter_today_badge.bgcolor = SCHEDULE_NAVY
        self._render_schedules()
        safe_update(self)

    def _select_today(self, *_args: Any) -> None:
        self._filter_mode = "today"
        self.filter_all_badge.bgcolor = SCHEDULE_NAVY
        self.filter_today_badge.bgcolor = BLUE
        self._render_schedules()
        safe_update(self)

    async def load_schedules(self, *_args: Any) -> None:
        try:
            self._medications = await asyncio.to_thread(
                self._api.list_medications, self._target_patient_id
            )
            self._med_map = {m["id"]: m for m in self._medications}
            self._schedules = await asyncio.to_thread(
                self._api.list_schedules, None, self._target_patient_id
            )
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return

        self._render_schedules()
        safe_update(self)

    async def load_tracking(self, *_args: Any) -> None:
        try:
            items = await asyncio.to_thread(
                self._api.get_tracking_summary, self._target_patient_id
            )
            self._tracking_items = items
        except Exception:
            self._tracking_items = []

        self._render_tracking()
        safe_update(self)

    async def _reload_all(self, *_args: Any) -> None:
        await self.load_schedules()
        await self.load_tracking()

    def _render_tracking(self) -> None:
        self.tracking_list.controls.clear()
        if not self._tracking_items:
            self.tracking_list.controls.append(
                ft.Container(
                    bgcolor=CARD_BG_BLUE,
                    border=ft.Border.all(1, CARD_BORDER_BLUE),
                    border_radius=20,
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.AUTO_GRAPH, color=CYAN, size=40),
                            ft.Text(
                                i18n.t("no_tracking_items"),
                                size=15,
                                color=MUTED,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            return

        for item in self._tracking_items:
            self.tracking_list.controls.append(self._build_tracking_card(item))

    def _build_tracking_card(self, item: Dict[str, Any]) -> ft.Container:
        med_id = item.get("medication_id", "")
        med_name = item.get("medication_name", "Medication")
        stock = item.get("stock_qty", 0)
        days_left = item.get("days_supply_remaining", 0)
        status = item.get("reschedule_status", "healthy")
        freq = item.get("frequency_summary", "")
        resched_date_str = item.get("reschedule_due_date", "")

        due_display = i18n.t("immediate")
        if resched_date_str:
            try:
                dt = datetime.fromisoformat(resched_date_str.replace("Z", "+00:00"))
                due_display = dt.strftime("%b %d, %Y")
            except Exception:
                due_display = resched_date_str[:10]

        if status == "reschedule_now":
            badge_bg = RED
            badge_text = f"🚨 {i18n.t('reschedule_now')} (0 {i18n.t('stock')})"
        elif status == "reschedule_soon":
            badge_bg = ORANGE
            badge_text = f"⚠️ {i18n.t('reschedule_soon')} ({days_left:.0f}d)"
        else:
            badge_bg = "#2E7D32"
            badge_text = f"✅ {i18n.t('healthy_stock')} ({days_left:.0f}d)"

        def on_reschedule_click(_e: Any) -> None:
            show_reschedule_dialog(
                page=self._page_ref,
                api=self._api,
                tracking=item,
                patient_id=self._target_patient_id,
                on_rescheduled=lambda: self.page.run_task(self._reload_all) if getattr(self, "page", None) else None,
            )

        return ft.Container(
            bgcolor=WHITE,
            border=ft.Border.all(
                1.5,
                RED if status == "reschedule_now" else (ORANGE if status == "reschedule_soon" else CARD_BORDER_BLUE),
            ),
            border_radius=18,
            shadow=SHADOW_CARD,
            padding=ft.Padding(16, 14, 16, 14),
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(med_name, size=16, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                                    ft.Text(f"{i18n.t('frequency')}: {freq}", size=12, color=MUTED),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                bgcolor=badge_bg,
                                border_radius=10,
                                padding=ft.Padding(8, 4, 8, 4),
                                content=ft.Text(badge_text, size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"{i18n.t('stock')}: {stock} {i18n.t('units')} • {days_left:.0f} {i18n.t('days_supply_left')}",
                                size=12,
                                color="#475569",
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),
                    ft.Divider(height=1, color="#E2E8F0"),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(i18n.t("reschedule_due"), size=11, color=MUTED),
                                    ft.Text(due_display, size=13, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                                ],
                                spacing=1,
                            ),
                            ft.Button(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.AUTORENEW, color=WHITE, size=14),
                                        ft.Text(i18n.t("reschedule_btn"), size=12, weight=ft.FontWeight.BOLD, color=WHITE),
                                    ],
                                    spacing=4,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                bgcolor=SCHEDULE_NAVY,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                height=34,
                                on_click=on_reschedule_click,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
            ),
        )

    def _render_schedules(self) -> None:
        weekday_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        today_code = weekday_names[datetime.now().weekday()]

        filtered: List[Dict[str, Any]] = []
        for s in self._schedules:
            days = s.get("days_of_week", "daily").strip()
            if self._filter_mode == "today":
                if days.lower() == "daily":
                    filtered.append(s)
                else:
                    wanted = {d.strip().upper() for d in days.split(",")}
                    if today_code in wanted:
                        filtered.append(s)
            else:
                filtered.append(s)

        # Sort by due_time
        filtered.sort(key=lambda s: s.get("due_time", ""))

        count = len(filtered)
        count_key = "schedule_count_single" if count == 1 else "schedules_count"
        self.count_text.value = i18n.t(count_key, count=count)
        self.schedule_list.controls.clear()

        if not filtered:
            msg = (
                i18n.t("no_schedules_today")
                if self._filter_mode == "today"
                else i18n.t("no_schedules_hint")
            )
            self.schedule_list.controls.append(
                ft.Container(
                    bgcolor=CARD_BG_BLUE,
                    border=ft.Border.all(1, CARD_BORDER_BLUE),
                    border_radius=20,
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.CALENDAR_MONTH, color=CYAN, size=40),
                            ft.Text(msg, size=15, color=MUTED, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            return

        for sched in filtered:
            self.schedule_list.controls.append(self._build_schedule_card(sched))

    def _build_schedule_card(self, sched: Dict[str, Any]) -> ft.Container:
        sched_id: str = sched.get("id", "")
        med_id: str = sched.get("medication_id", "")
        med = self._med_map.get(med_id, {})
        med_name: str = med.get("name", "Prescription Med")
        dosage: str = med.get("dosage", "")
        form: str = med.get("form", "Tablet")
        disease: str = med.get("disease", "")

        dose_label: str = f"1 {form}" if form else "1 Dose"
        if dosage:
            dose_label = f"{dose_label} • {dosage}"

        raw_time: str = sched.get("due_time", "09:00:00")
        time_display: str = _format_time(raw_time)

        days_raw: str = sched.get("days_of_week", "daily")
        days_label: str = i18n.t("daily_tag") if days_raw.lower() == "daily" else days_raw

        async def remove(_e: Any) -> None:
            try:
                await asyncio.to_thread(self._api.delete_schedule, sched_id)
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, i18n.t("remove_schedule_toast", time=time_display, name=med_name))
            await self.load_schedules()

        tags_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        days_label,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=WHITE,
                    ),
                    bgcolor=SCHEDULE_NAVY,
                    border_radius=8,
                    padding=ft.Padding(8, 4, 8, 4),
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if disease:
            tags_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        disease,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=WHITE,
                    ),
                    bgcolor="#00A3E0",
                    border_radius=8,
                    padding=ft.Padding(8, 4, 8, 4),
                )
            )

        return ft.Container(
            bgcolor=CARD_BG_BLUE,
            border=ft.Border.all(1, "#D0EDFB"),
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
                                        width=14,
                                        height=14,
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
                                size=14,
                                color="#475569",
                                weight=ft.FontWeight.W_500,
                            ),
                            tags_row,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Image(
                                src=get_asset_path("pill_icon.png"),
                                width=48,
                                height=48,
                                fit=ft.BoxFit.CONTAIN,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=RED,
                                icon_size=22,
                                tooltip=i18n.t("delete_schedule_tooltip"),
                                on_click=remove,
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _trigger_test_alarm(self) -> None:
        if self._alarm_service:
            self._alarm_service.test_alarm()
        else:
            toast(self._page_ref, "Alarm service initializing...")

    # ---- Add Schedule Modal Dialog ------------------------------------ #
    def open_add_schedule_dialog(self, default_med_id: Optional[str] = None) -> None:
        if not self._medications:
            dlg = ft.AlertDialog(
                title=ft.Text(i18n.t("no_meds_found_title"), weight=ft.FontWeight.BOLD),
                content=ft.Text(
                    i18n.t("no_meds_found_desc"), size=14
                ),
            )
            self._page_ref.show_dialog(dlg)
            return

        med_options = [
            ft.DropdownOption(key=m["id"], text=f"{m['name']} ({m.get('form', 'Tablet')})")
            for m in self._medications
        ]
        sel_med_id = default_med_id or self._initial_med_id or self._medications[0]["id"]
        if not any(m["id"] == sel_med_id for m in self._medications):
            sel_med_id = self._medications[0]["id"]

        med_dropdown = ft.Dropdown(
            value=sel_med_id,
            options=med_options,
            width=300,
            bgcolor=INPUT_BG,
            color=INPUT_TEXT,
            border_radius=12,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding(14, 10, 14, 10),
        )

        hour_dropdown = ft.Dropdown(
            value="09",
            options=[ft.DropdownOption(key=f"{h:02d}", text=f"{h:02d}") for h in range(1, 13)],
            width=80,
            bgcolor=INPUT_BG,
            color=INPUT_TEXT,
            border_radius=12,
            border=ft.NoInputBorder(),
        )

        min_input = ft.TextField(
            value="00",
            width=75,
            height=48,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            bgcolor=INPUT_BG,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding(8, 8, 8, 8),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.BOLD),
            cursor_color=SCHEDULE_NAVY,
        )

        period_dropdown = ft.Dropdown(
            value="AM",
            options=[ft.DropdownOption(key="AM", text="AM"), ft.DropdownOption(key="PM", text="PM")],
            width=80,
            bgcolor=INPUT_BG,
            color=INPUT_TEXT,
            border_radius=12,
            border=ft.NoInputBorder(),
        )

        # Quick preset buttons
        def set_preset(h: str, m: str, p: str) -> None:
            hour_dropdown.value = h
            min_input.value = m
            period_dropdown.value = p
            safe_update(dlg)

        def set_now_preset(offset_mins: int = 0) -> None:
            target = datetime.now() + timedelta(minutes=offset_mins)
            h = target.hour % 12 or 12
            p = "PM" if target.hour >= 12 else "AM"
            set_preset(f"{h:02d}", f"{target.minute:02d}", p)

        preset_row = ft.Row(
            controls=[
                ft.Button(
                    content=ft.Text(i18n.t("preset_now"), size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_now_preset(0),
                ),
                ft.Button(
                    content=ft.Text("+1 min", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_now_preset(1),
                ),
                ft.Button(
                    content=ft.Text("+2 min", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_now_preset(2),
                ),
                ft.Button(
                    content=ft.Text(i18n.t("preset_morning"), size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_preset("08", "00", "AM"),
                ),
                ft.Button(
                    content=ft.Text(i18n.t("preset_noon"), size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_preset("01", "00", "PM"),
                ),
                ft.Button(
                    content=ft.Text(i18n.t("preset_night"), size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    height=28,
                    on_click=lambda _e: set_preset("09", "00", "PM"),
                ),
            ],
            spacing=4,
            wrap=True,
        )

        freq_dropdown = ft.Dropdown(
            value="Daily",
            options=[
                ft.DropdownOption(key="Daily", text=i18n.t("freq_daily")),
                ft.DropdownOption(key="Weekdays", text=i18n.t("freq_weekdays")),
                ft.DropdownOption(key="Weekends", text=i18n.t("freq_weekends")),
                ft.DropdownOption(key="Custom", text=i18n.t("freq_custom")),
            ],
            width=300,
            bgcolor=INPUT_BG,
            color=INPUT_TEXT,
            border_radius=12,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding(14, 10, 14, 10),
        )

        # Custom day selection chips
        selected_days: Set[str] = {"MON", "WED", "FRI"}
        day_buttons: List[ft.Container] = []

        def toggle_day(d: str, btn: ft.Container) -> None:
            if d in selected_days:
                if len(selected_days) > 1:
                    selected_days.remove(d)
                    btn.bgcolor = "#E2E8F0"
                    btn.content.color = TEXT
            else:
                selected_days.add(d)
                btn.bgcolor = SCHEDULE_NAVY
                btn.content.color = WHITE
            safe_update(btn)

        all_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        for d in all_days:
            is_active = d in selected_days
            btn_container = ft.Container(
                content=ft.Text(d, size=11, weight=ft.FontWeight.BOLD, color=WHITE if is_active else TEXT),
                bgcolor=SCHEDULE_NAVY if is_active else "#E2E8F0",
                border_radius=8,
                padding=ft.Padding(8, 6, 8, 6),
            )
            # bind click
            btn_container.on_click = (lambda day=d, bc=btn_container: lambda _e: toggle_day(day, bc))()
            day_buttons.append(btn_container)

        days_row_container = ft.Container(
            content=ft.Row(controls=day_buttons, spacing=4, wrap=True),
            visible=False,
            width=300,
        )

        def on_freq_changed(_e: Any) -> None:
            days_row_container.visible = (freq_dropdown.value == "Custom")
            safe_update(dlg)

        freq_dropdown.on_select = on_freq_changed

        async def save_schedule(_e: Any) -> None:
            med_id = med_dropdown.value
            if not med_id:
                toast(self._page_ref, "Please select a medication.", error=True)
                return

            due_time = _to_24h_time(
                hour_dropdown.value or "09",
                min_input.value or "00",
                period_dropdown.value or "AM",
            )

            freq_val = freq_dropdown.value or "Daily"
            if freq_val == "Daily":
                days_of_week = "daily"
            elif freq_val == "Weekdays":
                days_of_week = "MON,TUE,WED,THU,FRI"
            elif freq_val == "Weekends":
                days_of_week = "SAT,SUN"
            else:  # Custom
                days_of_week = ",".join(sorted(list(selected_days), key=lambda x: all_days.index(x)))

            try:
                await asyncio.to_thread(
                    self._api.create_schedule,
                    medication_id=med_id,
                    due_time=due_time,
                    days_of_week=days_of_week,
                )
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return

            self._page_ref.pop_dialog()
            toast(self._page_ref, i18n.t("schedule_added"))
            await self.load_schedules()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.t("schedule_dose_modal_title"), weight=ft.FontWeight.BOLD),
            content=ft.Column(
                controls=[
                    ft.Text(i18n.t("medication_label"), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                    med_dropdown,
                    ft.Container(height=4),
                    ft.Text(i18n.t("dose_time_label"), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                    preset_row,
                    ft.Row(
                        controls=[
                            hour_dropdown,
                            ft.Text(":", size=18, weight=ft.FontWeight.BOLD),
                            min_input,
                            period_dropdown,
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=4),
                    ft.Text(i18n.t("frequency_days_label"), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                    freq_dropdown,
                    days_row_container,
                    ft.Container(height=6),
                    ft.Button(
                        content=ft.Text(i18n.t("save_schedule_btn"), size=15, weight=ft.FontWeight.BOLD),
                        bgcolor=SCHEDULE_NAVY,
                        color=WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
                        height=46,
                        width=300,
                        on_click=save_schedule,
                    ),
                ],
                tight=True,
                spacing=6,
                width=320,
            ),
        )
        self._page_ref.show_dialog(dlg)
