"""InsulinView — Blood sugar level & insulin line graph tracking screen.

Implements the exact UI design from the reference image:
- Top green curved header with back navigation and date subtitle.
- Sub-header with "Insulin Chart", date dropdown selector, and "+ Add Reading" button.
- Card 1: Insulin Line Graph drawn via Flet Canvas:
    * Y-axis: "Sugar level" with ticks 0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0+
    * X-axis: "Time" with labels e.g. 9:00 AM, 1:00 PM, 9:00 PM
    * Smooth blue curve with data point dots (e.g. 9.0 -> 14.0 -> 8.0)
- Card 2: Daily readings list showing:
    * Date header and "Insulin taken" navy badge
    * Rows e.g. "9:00 AM - " [ 9.0 ] (green pill badges)
    * Delete entry capability
- Manual Input Modal:
    * Allows manually entering Sugar Level (y-axis) and Time (x-axis) for any date.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
import logging
from typing import Any, Callable, Dict, List, Optional

import flet as ft
import flet.canvas as cv

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

MONTH_NAMES_SHORT = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEPT", "OCT", "NOV", "DEC"
]


def _format_time_display(raw_time: str) -> str:
    """Convert '09:00:00' to '9:00 AM'."""
    try:
        t = datetime.strptime(raw_time[:8], "%H:%M:%S")
        return t.strftime("%I:%M %p").lstrip("0")
    except Exception:
        try:
            t = datetime.strptime(raw_time[:5], "%H:%M")
            return t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return raw_time[:5]


def _to_24h_time(hour_str: str, min_str: str, period: str) -> str:
    try:
        h = int(str(hour_str).strip())
    except Exception:
        h = 9
    try:
        m = int(str(min_str).strip())
    except Exception:
        m = 0
    p = str(period).strip().upper()
    if p == "PM" and h < 12:
        h += 12
    elif p == "AM" and h == 12:
        h = 0
    return f"{h:02d}:{m:02d}:00"


class InsulinView(ft.Column):
    """View showing blood sugar line graph and daily insulin logs."""

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
        on_history: Optional[Callable[[], None]] = None,
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
        self._on_history: Optional[Callable[[], None]] = on_history
        self._on_profile: Optional[Callable[[], None]] = on_profile

        today = date.today()
        self._selected_date: str = today.strftime("%Y-%m-%d")
        self._readings: List[Dict[str, Any]] = []

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Green Header (PNG 1) ---------------------------------- #
        self.header_title: ft.Text = ft.Text(
            i18n.t("insulin_title"),
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
                        self.lang_toggle,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                avoid_intrusions_bottom=False,
            ),
        )

        # ---- Sub-header: Insulin Chart & Date Selector ----------------- #
        self.chart_section_title: ft.Text = ft.Text(
            i18n.t("insulin_chart_title"),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )

        self.date_btn_text: ft.Text = ft.Text(
            self._format_date_label(self._selected_date),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.date_btn: ft.Container = ft.Container(
            bgcolor="#2563EB",  # bright blue pill from PNG 1
            border_radius=12,
            padding=ft.Padding(12, 7, 12, 7),
            content=ft.Row(
                controls=[
                    self.date_btn_text,
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=WHITE, size=18),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=self.open_date_picker_dialog,
        )

        # Quick Add button in top row
        self.add_reading_quick_btn: ft.Container = ft.Container(
            content=ft.Icon(ft.Icons.ADD, color=WHITE, size=18),
            bgcolor="#10B981",
            width=34,
            height=34,
            shape=ft.BoxShape.CIRCLE,
            alignment=ft.Alignment.CENTER,
            tooltip=i18n.t("add_reading_btn"),
            on_click=lambda _e: self.open_add_reading_dialog(),
        )

        self.sub_header_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 6, 4, 2),
            content=ft.Row(
                controls=[
                    self.chart_section_title,
                    ft.Row(
                        controls=[
                            self.date_btn,
                            self.add_reading_quick_btn,
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Card 1: Insulin Line Graph (via Canvas) -------------------- #
        self.graph_title: ft.Text = ft.Text(
            i18n.t("insulin_line_graph"),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            text_align=ft.TextAlign.CENTER,
        )
        self.canvas_container: ft.Container = ft.Container(
            width=CARD_WIDTH - 24,
            height=210,
            alignment=ft.Alignment.CENTER,
            content=None,  # populated in _render_chart
        )

        self.graph_card: ft.Container = ft.Container(
            bgcolor="#E0F2FE",  # light sky blue card
            border=ft.Border.all(1, "#BAE6FD"),
            border_radius=20,
            shadow=SHADOW_CARD,
            padding=ft.Padding(12, 10, 12, 10),
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=self.graph_title,
                        alignment=ft.Alignment.CENTER,
                        padding=ft.Padding(0, 0, 0, 4),
                    ),
                    self.canvas_container,
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Card 2: Daily Readings List (Lower Card in PNG 1) -------- #
        self.list_date_heading: ft.Text = ft.Text(
            self._format_date_label(self._selected_date),
            size=16,
            weight=ft.FontWeight.BOLD,
            color="#2563EB",
        )
        self.insulin_badge_text: ft.Text = ft.Text(
            i18n.t("insulin_taken_badge"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
        )
        self.insulin_taken_badge: ft.Container = ft.Container(
            bgcolor=SCHEDULE_NAVY,
            border_radius=8,
            padding=ft.Padding(10, 4, 10, 4),
            content=self.insulin_badge_text,
        )

        self.readings_list_col: ft.Column = ft.Column(spacing=8, width=CARD_WIDTH - 28)

        self.add_reading_card_btn: ft.Button = ft.Button(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, color=WHITE, size=16),
                    ft.Text(i18n.t("add_reading_btn"), size=13, weight=ft.FontWeight.BOLD, color=WHITE),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#10B981",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            height=40,
            width=CARD_WIDTH - 28,
            on_click=lambda _e: self.open_add_reading_dialog(),
        )
        # Compatibility reference for tests
        self.add_reading_btn: ft.Button = self.add_reading_card_btn

        self.readings_card: ft.Container = ft.Container(
            bgcolor="#E0F2FE",
            border=ft.Border.all(1, "#BAE6FD"),
            border_radius=20,
            shadow=SHADOW_CARD,
            padding=ft.Padding(14, 12, 14, 12),
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.list_date_heading,
                            self.insulin_taken_badge,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=1, color="#CBD5E1"),
                    self.readings_list_col,
                    ft.Container(height=4),
                    self.add_reading_card_btn,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Bottom Navigation Bar ------------------------------------- #
        self.nav_bar: ft.Container = build_bottom_nav(
            role=self._role,
            on_medicines=self._on_medicines,
            on_schedule=self._on_schedule,
            on_alerts_or_history=self._on_history,
            on_profile=self._on_profile,
        )

        # Fixed Footer Layout: Scrollable body area (expand=True) + Pinned Footer
        self.scroll_content: ft.Column = ft.Column(
            controls=[
                self.sub_header_row,
                self.graph_card,
                self.readings_card,
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

    def _format_date_label(self, date_str: str) -> str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            month_str = MONTH_NAMES_SHORT[d.month - 1]
            return f"{d.day} {month_str}, {d.year}"
        except Exception:
            return date_str

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_readings)
        except Exception:
            pass

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _on_lang_changed(self, _new_lang: str) -> None:
        self.header_title.value = i18n.t("insulin_title")
        self.chart_section_title.value = i18n.t("insulin_chart_title")
        self.graph_title.value = i18n.t("insulin_line_graph")
        self.insulin_badge_text.value = i18n.t("insulin_taken_badge")
        self._render_chart()
        self._render_readings_list()
        safe_update(self)

    async def load_readings(self, *_args: Any) -> None:
        """Fetch blood sugar readings for the selected date."""
        try:
            items = await asyncio.to_thread(
                self._api.list_insulin_readings,
                self._selected_date,
                self._target_patient_id,
            )
            self._readings = items
        except Exception as exc:
            logger.debug("Failed loading insulin readings: %s", exc)
            self._readings = []

        self.date_btn_text.value = self._format_date_label(self._selected_date)
        self.list_date_heading.value = self._format_date_label(self._selected_date)
        self._render_chart()
        self._render_readings_list()
        safe_update(self)

    def _render_chart(self) -> None:
        """Render the Insulin Line Graph on Flet Canvas matching Photo 1."""
        c_width = 326
        c_height = 205

        shapes: List[cv.Shape] = []

        # Graph dimensions and margins
        left_m = 56
        right_m = 16
        top_m = 16
        bottom_m = 36

        plot_w = c_width - left_m - right_m
        plot_h = c_height - top_m - bottom_m

        # Y-axis range: ticks 0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0
        max_y = 14.0
        if self._readings:
            highest_val = max(float(r.get("sugar_level", 0)) for r in self._readings)
            if highest_val > max_y:
                max_y = (int(highest_val // 2) + 1) * 2.0

        ticks_y = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0]
        if max_y > 14.0:
            step = (max_y / 7.0)
            ticks_y = [round(i * step, 1) for i in range(8)]

        # Draw horizontal grid lines & Y-axis labels
        grid_paint = ft.Paint(color="#BFDBFE", stroke_width=1, style=ft.PaintingStyle.STROKE)
        axis_paint = ft.Paint(color="#64748B", stroke_width=1.5, style=ft.PaintingStyle.STROKE)

        for tick in ticks_y:
            y_ratio = tick / max_y
            y_pos = top_m + plot_h - (y_ratio * plot_h)

            # Grid line
            shapes.append(cv.Line(left_m, y_pos, left_m + plot_w, y_pos, paint=grid_paint))

            # Y-axis label text right-aligned to left_m - 8
            lbl = f"{tick:.1f}" if tick > 0 else "0"
            shapes.append(
                cv.Text(
                    left_m - 8,
                    y_pos,
                    value=lbl,
                    alignment=ft.Alignment.CENTER_RIGHT,
                    style=ft.TextStyle(size=10, color="#475569", weight=ft.FontWeight.W_500),
                )
            )

        # Y-axis vertical label: "Sugar level" cleanly oriented outside tick numbers
        shapes.append(
            cv.Text(
                12,
                top_m + (plot_h / 2),
                value=i18n.t("sugar_level"),
                alignment=ft.Alignment.CENTER,
                rotate=-1.5708,  # -90 deg vertical reading upwards
                style=ft.TextStyle(size=10, color="#64748B", weight=ft.FontWeight.BOLD),
            )
        )

        # Baseline axis line
        shapes.append(
            cv.Line(left_m, top_m + plot_h, left_m + plot_w, top_m + plot_h, paint=axis_paint)
        )

        # X-axis label: "Time" centered at bottom
        shapes.append(
            cv.Text(
                left_m + (plot_w / 2),
                c_height - 6,
                value=i18n.t("time"),
                alignment=ft.Alignment.BOTTOM_CENTER,
                style=ft.TextStyle(size=11, color="#475569", weight=ft.FontWeight.BOLD),
            )
        )

        if not self._readings:
            # Empty graph hint
            shapes.append(
                cv.Text(
                    left_m + (plot_w / 2),
                    top_m + (plot_h / 2),
                    value="No readings logged yet for this day.",
                    alignment=ft.Alignment.CENTER,
                    style=ft.TextStyle(size=11, color="#64748B", italic=True),
                )
            )
            self.canvas_container.content = cv.Canvas(shapes, width=c_width, height=c_height)
            return

        # Sort readings by reading_time
        sorted_readings = sorted(self._readings, key=lambda r: r.get("reading_time", ""))
        n_pts = len(sorted_readings)

        pts_coords = []
        for i, r in enumerate(sorted_readings):
            sugar_val = float(r.get("sugar_level", 0))
            y_ratio = min(sugar_val / max_y, 1.0)
            y_pos = top_m + plot_h - (y_ratio * plot_h)

            if n_pts == 1:
                x_pos = left_m + (plot_w / 2)
            else:
                x_pos = left_m + (i / (n_pts - 1)) * plot_w

            pts_coords.append((x_pos, y_pos))

            # X-axis time tick label centered under point
            t_str = _format_time_display(r.get("reading_time", ""))
            shapes.append(
                cv.Text(
                    x_pos,
                    top_m + plot_h + 8,
                    value=t_str,
                    alignment=ft.Alignment.TOP_CENTER,
                    style=ft.TextStyle(size=10, color="#334155", weight=ft.FontWeight.W_500),
                )
            )

        # Draw connected curve / line segments
        line_paint = ft.Paint(
            color="#3B82F6",  # vibrant curve blue from image
            stroke_width=3.0,
            stroke_cap=ft.StrokeCap.ROUND,
            stroke_join=ft.StrokeJoin.ROUND,
            style=ft.PaintingStyle.STROKE,
        )

        if n_pts == 1:
            pass  # single dot drawn below
        elif n_pts == 2:
            shapes.append(
                cv.Line(pts_coords[0][0], pts_coords[0][1], pts_coords[1][0], pts_coords[1][1], paint=line_paint)
            )
        else:
            # Smooth cubic or multi-segment curve connecting points
            path_elements = [cv.Path.MoveTo(pts_coords[0][0], pts_coords[0][1])]
            for i in range(n_pts - 1):
                p0 = pts_coords[i]
                p1 = pts_coords[i + 1]
                mid_x = (p0[0] + p1[0]) / 2.0
                path_elements.append(
                    cv.Path.CubicTo(mid_x, p0[1], mid_x, p1[1], p1[0], p1[1])
                )
            shapes.append(cv.Path(path_elements, paint=line_paint))

        # Draw solid circular dots at data points
        dot_fill = ft.Paint(color="#3B82F6", style=ft.PaintingStyle.FILL)
        dot_ring = ft.Paint(color=WHITE, stroke_width=1.5, style=ft.PaintingStyle.STROKE)

        for x_pos, y_pos in pts_coords:
            shapes.append(cv.Circle(x_pos, y_pos, 5, paint=dot_fill))
            shapes.append(cv.Circle(x_pos, y_pos, 5, paint=dot_ring))

        self.canvas_container.content = cv.Canvas(shapes, width=c_width, height=c_height)

    def _render_readings_list(self) -> None:
        """Render the entries inside the lower card (e.g. 9:00 AM - [ 9.0 ])."""
        self.readings_list_col.controls.clear()

        if not self._readings:
            self.readings_list_col.controls.append(
                ft.Container(
                    padding=10,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        i18n.t("no_readings_for_date"),
                        size=13,
                        color=MUTED,
                        italic=True,
                    ),
                )
            )
            return

        sorted_readings = sorted(self._readings, key=lambda r: r.get("reading_time", ""))

        for r in sorted_readings:
            r_id = r.get("id", "")
            raw_time = r.get("reading_time", "09:00:00")
            time_disp = _format_time_display(raw_time)
            sugar = float(r.get("sugar_level", 0))

            async def delete_item(_e: Any, reading_id: str = r_id) -> None:
                try:
                    await asyncio.to_thread(self._api.delete_insulin_reading, reading_id)
                    toast(self._page_ref, i18n.t("reading_deleted_toast"))
                    await self.load_readings()
                except Exception as exc:
                    toast(self._page_ref, f"Delete failed: {exc}", error=True)

            row = ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"{time_disp} - ", size=16, weight=ft.FontWeight.BOLD, color="#10B981"),
                            ft.Container(
                                bgcolor="#10B981",  # bright green badge from image
                                border_radius=6,
                                padding=ft.Padding(10, 4, 10, 4),
                                content=ft.Text(f"{sugar:.1f}", size=14, weight=ft.FontWeight.BOLD, color=WHITE),
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="#94A3B8",
                        icon_size=18,
                        tooltip="Delete Reading",
                        on_click=lambda _e, rid=r_id: self.page.run_task(delete_item, rid) if getattr(self, "page", None) else None,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.readings_list_col.controls.append(row)

    # ------------------------------------------------------------------ #
    # Manual Sugar Level & Time Input Dialog
    # ------------------------------------------------------------------ #
    def open_add_reading_dialog(self) -> None:
        """Modal dialog to manually enter Sugar Level (y-axis) and Time (x-axis)."""
        now = datetime.now()
        cur_hour = (now.hour % 12) or 12
        cur_min = f"{now.minute:02d}"
        cur_period = "PM" if now.hour >= 12 else "AM"

        hour_drop = ft.Dropdown(
            value=str(cur_hour),
            options=[ft.dropdown.Option(str(h)) for h in range(1, 13)],
            width=86,
            bgcolor="#F1F5F9",
            border=ft.NoInputBorder(),
            border_radius=10,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TITLE_NAVY,
            text_size=13,
        )
        min_drop = ft.Dropdown(
            value=f"{now.minute:02d}",
            options=[ft.dropdown.Option(f"{m:02d}") for m in range(0, 60, 5)],
            width=86,
            bgcolor="#F1F5F9",
            border=ft.NoInputBorder(),
            border_radius=10,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TITLE_NAVY,
            text_size=13,
        )
        period_drop = ft.Dropdown(
            value=cur_period,
            options=[ft.dropdown.Option("AM"), ft.dropdown.Option("PM")],
            width=86,
            bgcolor="#F1F5F9",
            border=ft.NoInputBorder(),
            border_radius=10,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TITLE_NAVY,
            text_size=13,
        )

        sugar_input = ft.TextField(
            value="9.0",
            label=i18n.t("sugar_level_label"),
            prefix_icon=ft.Icons.SPEED,
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
            bgcolor="#F8FAFC",
            border=ft.NoInputBorder(),
            border_radius=12,
            content_padding=ft.Padding(14, 10, 14, 10),
        )

        units_input = ft.TextField(
            value="",
            label=i18n.t("insulin_units_label"),
            prefix_icon=ft.Icons.MEDICATION,
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
            bgcolor="#F8FAFC",
            border=ft.NoInputBorder(),
            border_radius=12,
            content_padding=ft.Padding(14, 10, 14, 10),
        )

        def set_preset_time(h: int, m: int, p: str) -> None:
            hour_drop.value = str(h)
            min_drop.value = f"{m:02d}"
            period_drop.value = p
            safe_update(hour_drop)
            safe_update(min_drop)
            safe_update(period_drop)

        def set_preset_sugar(val: str) -> None:
            sugar_input.value = val
            safe_update(sugar_input)

        def _make_preset_time_btn(label: str, is_now: bool, click_handler: Any) -> ft.Container:
            return ft.Container(
                content=ft.Text(label, size=11, color=WHITE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                bgcolor=CYAN if is_now else SCHEDULE_NAVY,
                height=32,
                border_radius=8,
                alignment=ft.Alignment.CENTER,
                expand=True,
                ink=True,
                on_click=click_handler,
            )

        preset_time_row = ft.Row(
            controls=[
                _make_preset_time_btn("9:00 AM", False, lambda _e: set_preset_time(9, 0, "AM")),
                _make_preset_time_btn("1:00 PM", False, lambda _e: set_preset_time(1, 0, "PM")),
                _make_preset_time_btn("9:00 PM", False, lambda _e: set_preset_time(9, 0, "PM")),
                _make_preset_time_btn(
                    "Now",
                    True,
                    lambda _e: set_preset_time(
                        (datetime.now().hour % 12) or 12,
                        (datetime.now().minute // 5) * 5,
                        "PM" if datetime.now().hour >= 12 else "AM",
                    ),
                ),
            ],
            spacing=6,
            width=300,
        )

        def _make_preset_sugar_btn(val: str, color: str) -> ft.Container:
            return ft.Container(
                content=ft.Text(val, size=11, color=WHITE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                bgcolor=color,
                height=30,
                border_radius=8,
                alignment=ft.Alignment.CENTER,
                expand=True,
                ink=True,
                on_click=lambda _e: set_preset_sugar(val),
            )

        preset_sugar_row = ft.Row(
            controls=[
                _make_preset_sugar_btn("5.5", "#10B981"),
                _make_preset_sugar_btn("8.0", "#10B981"),
                _make_preset_sugar_btn("9.0", "#F59E0B"),
                _make_preset_sugar_btn("14.0", "#EF4444"),
            ],
            spacing=6,
            width=300,
        )

        def save_reading(_e: Any) -> None:
            try:
                sugar_val = float(sugar_input.value or "9.0")
            except ValueError:
                toast(self._page_ref, "Invalid sugar level value", error=True)
                return

            time_24 = _to_24h_time(hour_drop.value or "9", min_drop.value or "00", period_drop.value or "AM")
            units_val = None
            if units_input.value:
                try:
                    units_val = float(units_input.value)
                except ValueError:
                    pass

            if hasattr(self._page_ref, "pop_dialog"):
                self._page_ref.pop_dialog()

            async def _bg_save() -> None:
                try:
                    await asyncio.to_thread(
                        self._api.add_insulin_reading,
                        reading_date=self._selected_date,
                        reading_time=time_24,
                        sugar_level=sugar_val,
                        insulin_units=units_val,
                        patient_id=self._target_patient_id,
                    )
                    toast(self._page_ref, i18n.t("reading_saved_toast", level=sugar_val, time=_format_time_display(time_24)))
                    await self.load_readings()
                except Exception as exc:
                    toast(self._page_ref, f"Failed saving reading: {exc}", error=True)

            if getattr(self, "page", None) and hasattr(self.page, "run_task"):
                self.page.run_task(_bg_save)

        def close_dialog(_e: Any = None) -> None:
            if hasattr(self._page_ref, "pop_dialog"):
                self._page_ref.pop_dialog()

        dlg = ft.AlertDialog(
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                controls=[
                    ft.Text(i18n.t("log_reading_modal_title"), weight=ft.FontWeight.BOLD, size=16, color=TITLE_NAVY),
                    ft.IconButton(ft.Icons.CLOSE, icon_color="#64748B", icon_size=18, on_click=close_dialog),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                controls=[
                    ft.Divider(height=1, color="#E2E8F0"),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ACCESS_TIME, size=15, color=SCHEDULE_NAVY),
                            ft.Text(i18n.t("reading_time_label"), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                        ],
                        spacing=4,
                    ),
                    preset_time_row,
                    ft.Row(
                        controls=[
                            hour_drop,
                            ft.Text(":", size=18, weight=ft.FontWeight.BOLD, color="#64748B"),
                            min_drop,
                            period_drop,
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=4),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WATER_DROP, size=15, color="#2563EB"),
                            ft.Text(i18n.t("sugar_level_label"), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                        ],
                        spacing=4,
                    ),
                    preset_sugar_row,
                    sugar_input,
                    units_input,
                    ft.Container(height=6),
                    ft.Button(
                        content=ft.Text(i18n.t("save_reading_btn"), size=14, weight=ft.FontWeight.BOLD, color=WHITE),
                        bgcolor="#10B981",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                        height=44,
                        width=300,
                        on_click=save_reading,
                    ),
                ],
                tight=True,
                spacing=6,
                width=300,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        if hasattr(self._page_ref, "show_dialog"):
            self._page_ref.show_dialog(dlg)

    def open_date_picker_dialog(self, _e: Any) -> None:
        """Simple date switcher popup to jump between days."""
        today = date.today()
        dates_options = []
        from datetime import timedelta
        for offset in range(-7, 8):
            d = today + timedelta(days=offset)
            dates_options.append(d.strftime("%Y-%m-%d"))

        def pick_date(d_str: str) -> None:
            self._selected_date = d_str
            if hasattr(self._page_ref, "pop_dialog"):
                self._page_ref.pop_dialog()
            try:
                p = self.page
                if p and hasattr(p, "run_task"):
                    p.run_task(self.load_readings)
            except Exception:
                pass

        dlg = ft.AlertDialog(
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                controls=[
                    ft.Text("Select Date", weight=ft.FontWeight.BOLD, size=16, color=TITLE_NAVY),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color="#64748B",
                        icon_size=18,
                        on_click=lambda _e: self._page_ref.pop_dialog() if hasattr(self._page_ref, "pop_dialog") else None,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                controls=[
                    ft.Divider(height=1, color="#E2E8F0"),
                    *[
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text(self._format_date_label(ds), size=13, weight=ft.FontWeight.W_500, color=TITLE_NAVY),
                                    ft.Icon(ft.Icons.CHECK, color="#10B981", size=16, visible=(ds == self._selected_date)),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            padding=8,
                            border_radius=8,
                            bgcolor="#F1F5F9" if ds == self._selected_date else WHITE,
                            on_click=lambda _ev, target_d=ds: pick_date(target_d),
                        )
                        for ds in dates_options
                    ],
                ],
                tight=True,
                spacing=4,
                width=260,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        if hasattr(self._page_ref, "show_dialog"):
            self._page_ref.show_dialog(dlg)
