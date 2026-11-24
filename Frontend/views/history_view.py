"""HistoryView — Medication adherence calendar history screen.

Implements the exact UI design from the reference image:
- Spiral notebook calendar with hanging binder rings and teal month/year header.
- Color-coded adherence days:
    * Solid Blue: All medications are taken for that day.
    * Solid Red: None of the medications are taken.
    * Hollow Circle (red border): One or few medications missed, but some taken.
    * Green Dotted Date: Scheduled medication date needed to be taken in future days.
- Lower card showing detailed dose list for the selected date (time, medication name, dosage, status).
- Orange circular syringe button in header navigating to the Insulin History screen.
"""

from __future__ import annotations

import asyncio
import calendar
from datetime import date, datetime
import logging
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from components.common import (
    SHADOW_CARD,
    SHADOW_SUBTLE,
    build_bottom_nav,
    build_language_toggle,
    safe_update,
    toast,
)
from config import (
    APP_WIDTH,
    BLUE,
    CARD_BG_BLUE,
    CARD_BORDER_BLUE,
    CARD_WIDTH,
    CYAN,
    GREEN,
    MUTED,
    ORANGE,
    RED,
    SCHEDULE_NAVY,
    TEXT,
    TITLE_NAVY,
    WHITE,
)
from services import i18n
from services.api_client import Api, ApiError

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
]

MONTH_NAMES_SHORT = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEPT", "OCT", "NOV", "DEC"
]


class HistoryView(ft.Column):
    """View showing adherence calendar and dose history by date."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        role: str,
        user: Dict[str, Any],
        target_patient_id: Optional[str],
        on_back: Callable[[], None],
        on_medicines: Optional[Callable[[], None]] = None,
        on_schedule: Optional[Callable[[], None]] = None,
        on_insulin: Optional[Callable[[], None]] = None,
        on_profile: Optional[Callable[[], None]] = None,
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
        self._on_schedule: Optional[Callable[[], None]] = on_schedule
        self._on_insulin: Optional[Callable[[], None]] = on_insulin
        self._on_profile: Optional[Callable[[], None]] = on_profile

        today = date.today()
        self._today: date = today
        self._current_year: int = today.year
        self._current_month: int = today.month
        self._selected_date: str = today.strftime("%Y-%m-%d")

        self._history_days: Dict[str, Dict[str, Any]] = {}
        self._selected_doses: List[Dict[str, Any]] = []

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Green Header with Syringe Button (PNG 2) ------------- #
        self.header_title: ft.Text = ft.Text(
            i18n.t("history_title"),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.today_pill_text: ft.Text = ft.Text(
            today.strftime("%A, %B %d"),
            size=12,
            italic=True,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.today_pill: ft.Container = ft.Container(
            bgcolor=SCHEDULE_NAVY,
            border_radius=16,
            padding=ft.Padding(12, 4, 12, 4),
            content=self.today_pill_text,
        )

        # Orange circular button with syringe icon for Insulin screen
        self.insulin_btn: ft.Container = ft.Container(
            shape=ft.BoxShape.CIRCLE,
            bgcolor="#FF7043",  # bright orange from design
            width=48,
            height=48,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.VACCINES, color=WHITE, size=26),
            tooltip="Insulin History & Chart",
            on_click=lambda _e: self._on_insulin() if self._on_insulin else None,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color="#33000000"),
        )

        self.lang_toggle: ft.Container = build_language_toggle(
            on_toggle=self._on_lang_changed,
            api=self._api,
            bg_color="#1E293B",
            text_color=WHITE,
            height=28,
        )

        self.header: ft.Container = ft.Container(
            bgcolor=theme_color,
            padding=ft.Padding(16, 8, 16, 16),
            border_radius=ft.BorderRadius(0, 0, 32, 0),
            width=APP_WIDTH,
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
                                ft.Column(
                                    controls=[
                                        self.header_title,
                                        self.today_pill,
                                    ],
                                    spacing=4,
                                ),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                self.lang_toggle,
                                self.insulin_btn,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                avoid_intrusions_bottom=False,
            ),
        )

        # ---- Sub-header: History Calender ------------------------------ #
        self.calendar_title_text: ft.Text = ft.Text(
            i18n.t("history_calendar_title"),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )
        self.calendar_title_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 4, 4, 0),
            content=self.calendar_title_text,
        )

        # ---- Spiral Binder Rings (5 dark gray loops overhanging top) --- #
        self.binder_rings: ft.Container = ft.Container(
            width=CARD_WIDTH,
            height=28,
            margin=ft.Margin(0, 0, 0, -14),  # overlap onto the calendar top
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=18,
                        height=28,
                        bgcolor="#374151",
                        border_radius=9,
                        border=ft.Border.all(2, "#1F2937"),
                    )
                    for _ in range(5)
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
        )

        # ---- Calendar Top Teal Header (Month & Year selectors) --------- #
        self.month_label: ft.Text = ft.Text(
            MONTH_NAMES[self._current_month - 1],
            size=15,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.year_label: ft.Text = ft.Text(
            str(self._current_year),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )

        self.month_dropdown: ft.PopupMenuButton = ft.PopupMenuButton(
            content=ft.Row(
                controls=[
                    self.month_label,
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=WHITE, size=18),
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            tooltip="Select Month",
            items=self._build_month_menu_items(),
        )

        self.year_dropdown: ft.PopupMenuButton = ft.PopupMenuButton(
            content=ft.Row(
                controls=[
                    self.year_label,
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=WHITE, size=18),
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            tooltip="Select Year",
            items=self._build_year_menu_items(),
        )

        self.cal_header_row: ft.Container = ft.Container(
            bgcolor="#0D9488",  # rich teal color from image
            border_radius=ft.BorderRadius(20, 20, 0, 0),
            padding=ft.Padding(14, 16, 14, 14),
            width=CARD_WIDTH,
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        icon_color=WHITE,
                        icon_size=22,
                        tooltip="Previous Month",
                        on_click=self._prev_month,
                    ),
                    self.month_dropdown,
                    self.year_dropdown,
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        icon_color=WHITE,
                        icon_size=22,
                        tooltip="Next Month",
                        on_click=self._next_month,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Day-of-week header row (S M T W T F S) -------------------- #
        day_names_controls: List[ft.Control] = []
        for i, dn in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
            # Sundays (0) and Saturdays (6) in bold red per design
            c = RED if i in (0, 6) else TITLE_NAVY
            day_names_controls.append(
                ft.Container(
                    width=42,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(dn, size=14, weight=ft.FontWeight.BOLD, color=c),
                )
            )
        self.days_header: ft.Container = ft.Container(
            bgcolor="#E0F2FE",  # light sky blue calendar background
            padding=ft.Padding(8, 10, 8, 4),
            width=CARD_WIDTH,
            content=ft.Row(
                controls=day_names_controls,
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
        )

        # ---- Days Number Grid (populated in _render_calendar) ----------- #
        self.days_grid_col: ft.Column = ft.Column(spacing=6, width=CARD_WIDTH - 20)
        self.calendar_body: ft.Container = ft.Container(
            bgcolor="#E0F2FE",
            border_radius=ft.BorderRadius(0, 0, 20, 20),
            padding=ft.Padding(8, 4, 8, 14),
            width=CARD_WIDTH,
            content=self.days_grid_col,
        )

        # ---- Full Calendar Card Container ------------------------------ #
        self.calendar_container: ft.Container = ft.Container(
            width=CARD_WIDTH,
            shadow=SHADOW_CARD,
            border_radius=20,
            content=ft.Column(
                controls=[
                    self.binder_rings,
                    self.cal_header_row,
                    self.days_header,
                    self.calendar_body,
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Selected Date Details Card (Lower Card in PNG 2) ---------- #
        self.selected_date_title: ft.Text = ft.Text(
            self._format_date_heading(self._selected_date),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=RED,
        )
        self.doses_list_col: ft.Column = ft.Column(spacing=10, width=CARD_WIDTH - 24)

        self.details_card: ft.Container = ft.Container(
            bgcolor="#E0F2FE",
            border=ft.Border.all(1, "#BAE6FD"),
            border_radius=20,
            shadow=SHADOW_CARD,
            padding=ft.Padding(16, 14, 16, 14),
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    self.selected_date_title,
                    ft.Divider(height=1, color="#CBD5E1"),
                    self.doses_list_col,
                ],
                spacing=8,
            ),
        )

        # ---- Bottom Navigation Bar ------------------------------------- #
        self.nav_bar: ft.Container = build_bottom_nav(
            role=self._role,
            on_medicines=self._on_medicines,
            on_schedule=self._on_schedule,
            on_alerts_or_history=lambda: self.page.run_task(self.load_history) if getattr(self, "page", None) else None,
            on_profile=self._on_profile,
        )

        # Fixed Footer Layout: Scrollable body area (expand=True) + Pinned Footer
        self.scroll_content: ft.Column = ft.Column(
            controls=[
                self.calendar_title_row,
                self.calendar_container,
                self.details_card,
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

    def _format_date_heading(self, date_str: str) -> str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            month_short = MONTH_NAMES_SHORT[d.month - 1]
            return f"{d.day} {month_short}, {d.year}"
        except Exception:
            return date_str

    def _prev_month(self, _e: Any) -> None:
        if self._current_month == 1:
            self._current_month = 12
            self._current_year -= 1
        else:
            self._current_month -= 1
        self._update_month_labels()
        self._trigger_load()

    def _build_month_menu_items(self) -> List[ft.PopupMenuItem]:
        items: List[ft.PopupMenuItem] = []
        for i, m_name in enumerate(MONTH_NAMES, start=1):
            is_selected = (i == self._current_month)
            items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                m_name,
                                weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL,
                                color="#0D9488" if is_selected else TITLE_NAVY,
                                size=13,
                            ),
                            ft.Icon(ft.Icons.CHECK, size=16, color="#0D9488") if is_selected else ft.Container(width=16),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    on_click=lambda _e, m=i: self._select_month(m),
                )
            )
        return items

    def _build_year_menu_items(self) -> List[ft.PopupMenuItem]:
        items: List[ft.PopupMenuItem] = []
        current_y = self._today.year
        start_year = min(current_y - 4, self._current_year - 2)
        end_year = max(current_y + 5, self._current_year + 3)
        for y in range(start_year, end_year + 1):
            is_selected = (y == self._current_year)
            items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                str(y),
                                weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL,
                                color="#0D9488" if is_selected else TITLE_NAVY,
                                size=13,
                            ),
                            ft.Icon(ft.Icons.CHECK, size=16, color="#0D9488") if is_selected else ft.Container(width=16),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    on_click=lambda _e, yr=y: self._select_year(yr),
                )
            )
        return items

    def _select_month(self, m: int) -> None:
        if self._current_month != m:
            self._current_month = m
            self._update_month_labels()
            self._trigger_load()

    def _select_year(self, y: int) -> None:
        if self._current_year != y:
            self._current_year = y
            self._update_month_labels()
            self._trigger_load()

    def _prev_month(self, _e: Any) -> None:
        if self._current_month == 1:
            self._current_month = 12
            self._current_year -= 1
        else:
            self._current_month -= 1
        self._update_month_labels()
        self._trigger_load()

    def _next_month(self, _e: Any) -> None:
        if self._current_month == 12:
            self._current_month = 1
            self._current_year += 1
        else:
            self._current_month += 1
        self._update_month_labels()
        self._trigger_load()

    def _update_month_labels(self) -> None:
        self.month_label.value = MONTH_NAMES[self._current_month - 1]
        self.year_label.value = str(self._current_year)
        self.month_dropdown.items = self._build_month_menu_items()
        self.year_dropdown.items = self._build_year_menu_items()
        safe_update(self.cal_header_row)

    def _trigger_load(self) -> None:
        try:
            sel_d = datetime.strptime(self._selected_date, "%Y-%m-%d").date()
            if sel_d.year != self._current_year or sel_d.month != self._current_month:
                if self._today.year == self._current_year and self._today.month == self._current_month:
                    self._selected_date = self._today.strftime("%Y-%m-%d")
                else:
                    self._selected_date = f"{self._current_year:04d}-{self._current_month:02d}-01"
                self.selected_date_title.value = self._format_date_heading(self._selected_date)
        except Exception:
            pass

        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_history)
                p.run_task(self.load_doses_for_selected)
        except Exception:
            pass

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_history)
                p.run_task(self.load_doses_for_selected)
        except Exception:
            pass

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _on_lang_changed(self, _new_lang: str) -> None:
        self.header_title.value = i18n.t("history_title")
        self.calendar_title_text.value = i18n.t("history_calendar_title")
        self._render_calendar()
        self._render_doses()
        safe_update(self)

    async def load_history(self, *_args: Any) -> None:
        """Fetch monthly adherence summary for the calendar."""
        try:
            res = await asyncio.to_thread(
                self._api.get_dose_history,
                self._current_year,
                self._current_month,
                self._target_patient_id,
            )
            days_list = res.get("days", [])
            self._history_days = {d["date"]: d for d in days_list}
        except Exception as exc:
            logger.debug("Failed loading dose history: %s", exc)
            self._history_days = {}

        self._render_calendar()
        safe_update(self)

    async def load_doses_for_selected(self, *_args: Any) -> None:
        """Fetch doses for the selected date."""
        try:
            doses = await asyncio.to_thread(
                self._api.get_doses_for_date,
                self._selected_date,
                self._target_patient_id,
            )
            self._selected_doses = doses
        except Exception as exc:
            logger.debug("Failed loading doses for date: %s", exc)
            self._selected_doses = []

        self.selected_date_title.value = self._format_date_heading(self._selected_date)
        self._render_doses()
        safe_update(self.details_card)

    def _select_date(self, date_str: str) -> None:
        self._selected_date = date_str
        self._render_calendar()
        safe_update(self.calendar_body)
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_doses_for_selected)
        except Exception:
            pass

    def _render_calendar(self) -> None:
        """Render the 7-column calendar matrix with exact user color rules."""
        self.days_grid_col.controls.clear()

        # Month calendar starts on Sunday (calendar.SUNDAY = 6 in setfirstweekday)
        cal = calendar.Calendar(firstweekday=6)
        month_weeks = cal.monthdayscalendar(self._current_year, self._current_month)

        for week in month_weeks:
            week_row_controls: List[ft.Control] = []
            for day_num in week:
                if day_num == 0:
                    # Blank cell before start / after end of month
                    week_row_controls.append(ft.Container(width=42, height=42))
                    continue

                cur_date_str = f"{self._current_year:04d}-{self._current_month:02d}-{day_num:02d}"
                day_info = self._history_days.get(cur_date_str, {})
                status_color = day_info.get("status_color", "normal")
                is_selected = (cur_date_str == self._selected_date)

                cell = self._build_day_cell(day_num, cur_date_str, status_color, is_selected)
                week_row_controls.append(cell)

            self.days_grid_col.controls.append(
                ft.Row(
                    controls=week_row_controls,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                )
            )

    def _build_day_cell(
        self, day_num: int, date_str: str, status_color: str, is_selected: bool
    ) -> ft.Container:
        """Apply exact user rules:
        - blue marked date means all medications are taken
        - red means none of the medication is taken
        - hollow circle means one or few medication is missed but some are taken
        - green dotted date means scheduled medication date in future days
        """
        size = 36
        num_text = str(day_num)

        cell_content: ft.Control
        bg_color: Optional[str] = None
        border: Optional[ft.Border] = None

        if status_color == "blue":
            # Solid blue circle, white text
            bg_color = "#2563EB"
            cell_content = ft.Text(num_text, size=15, weight=ft.FontWeight.BOLD, color=WHITE)
        elif status_color == "red":
            # Solid red circle, white text
            bg_color = "#DC2626"
            cell_content = ft.Text(num_text, size=15, weight=ft.FontWeight.BOLD, color=WHITE)
        elif status_color == "hollow":
            # Hollow circle with red border, dark text
            border = ft.Border.all(2, "#DC2626")
            cell_content = ft.Text(num_text, size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY)
        elif status_color == "green_dot":
            # Number with a solid green dot above
            cell_content = ft.Column(
                controls=[
                    ft.Container(
                        shape=ft.BoxShape.CIRCLE,
                        bgcolor="#10B981",  # emerald green dot
                        width=6,
                        height=6,
                    ),
                    ft.Text(num_text, size=14, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1,
            )
        else:
            # Normal date
            cell_content = ft.Text(num_text, size=14, weight=ft.FontWeight.W_500, color=TITLE_NAVY)

        # Selected ring indicator
        if is_selected:
            if border is None:
                border = ft.Border.all(2, "#00A3E0")
            else:
                # If already hollow circle, make border slightly thicker
                border = ft.Border.all(3, "#DC2626")

        return ft.Container(
            width=size,
            height=size,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=bg_color,
            border=border,
            alignment=ft.Alignment.CENTER,
            content=cell_content,
            on_click=lambda _e, ds=date_str: self._select_date(ds),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        )

    def _render_doses(self) -> None:
        """Render doses list inside lower card for the selected day."""
        self.doses_list_col.controls.clear()

        if not self._selected_doses:
            self.doses_list_col.controls.append(
                ft.Container(
                    padding=12,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        i18n.t("no_doses_on_date"),
                        size=13,
                        color=MUTED,
                        italic=True,
                    ),
                )
            )
            return

        for d in self._selected_doses:
            due_raw = d.get("due_time", "09:00:00")
            try:
                t = datetime.strptime(due_raw, "%H:%M:%S")
                time_disp = t.strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_disp = due_raw[:5]

            med_name = d.get("medication_name", "Medicine")
            dosage = d.get("dosage", "")
            full_med_label = f"{med_name} {dosage}".strip()
            status_val = d.get("status", "pending").lower()

            # Time color and status badge matching photo 2:
            # e.g., 9:00 AM - (red if missed, green if taken)
            if status_val == "taken":
                time_color = "#16A34A"
                badge_bg = "#10B981"
                badge_label = i18n.t("taken")
            elif status_val == "missed":
                time_color = "#DC2626"
                badge_bg = "#EF4444"
                badge_label = i18n.t("missed")
            elif status_val == "skipped":
                time_color = "#EA580C"
                badge_bg = "#F97316"
                badge_label = i18n.t("skip")
            else:
                time_color = "#2563EB"
                badge_bg = "#3B82F6"
                badge_label = i18n.t("pending")

            row = ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"{time_disp} - ", size=15, weight=ft.FontWeight.BOLD, color=time_color),
                            ft.Text(full_med_label, size=15, weight=ft.FontWeight.W_500, color="#334155"),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                    ft.Container(
                        bgcolor=badge_bg,
                        border_radius=8,
                        padding=ft.Padding(10, 4, 10, 4),
                        content=ft.Text(badge_label, size=12, weight=ft.FontWeight.BOLD, color=WHITE),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.doses_list_col.controls.append(row)
