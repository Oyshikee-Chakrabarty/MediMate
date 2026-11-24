"""AddMedicineView — Add medicine form matching PNG 6."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

import flet as ft

from components.common import build_language_toggle, safe_update, toast
from config import (
    APP_WIDTH,
    BLUE,
    BUTTON_HEIGHT,
    CARD_WIDTH,
    FIELD_WIDTH,
    FONT,
    GREEN,
    INPUT_BG,
    INPUT_TEXT,
    MUTED,
    ORANGE,
    SCHEDULE_NAVY,
    TEXT,
    WHITE,
)
from services import i18n
from services.api_client import Api, ApiError


def _parse_minute(val: Any) -> str:
    try:
        m = int(str(val or "").strip())
        if 0 <= m <= 59:
            return f"{m:02d}"
    except Exception:
        pass
    return "00"


def _to_24h_time(hour_str: str, min_str: str, period: str) -> str:
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


class AddMedicineView(ft.Column):
    """Add medicine form designed exactly after PNG 6."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        role: str,
        user: Dict[str, Any],
        target_patient_id: Optional[str],
        on_back: Callable[[], None],
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__(
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._role: str = role
        self._user: Dict[str, Any] = user
        self._target_patient_id: Optional[str] = target_patient_id
        self._on_back: Callable[[], None] = on_back
        self._on_saved: Callable[[], None] = on_saved

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Header ------------------------------------------------ #
        self.header_title: ft.Text = ft.Text(
            i18n.t("add_medicine"),
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
            padding=ft.Padding(16, 24, 16, 20),
            border_radius=ft.BorderRadius(0, 0, 32, 0),
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
            width=APP_WIDTH,
        )

        # ---- Form Fields (Matching PNG 6) ------------------------------ #
        self.med_name: ft.TextField = ft.TextField(
            hint_text="e.g. Thyrox",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.med_dosage: ft.TextField = ft.TextField(
            hint_text="e.g. 50mcg",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.form_choice: ft.Dropdown = ft.Dropdown(
            value="Tablet",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            color=INPUT_TEXT,
            options=[
                ft.DropdownOption(key="Tablet", text="Tablet"),
                ft.DropdownOption(key="Capsule", text="Capsule"),
                ft.DropdownOption(key="Syrup", text="Syrup"),
                ft.DropdownOption(key="Injection", text="Injection"),
                ft.DropdownOption(key="Drops", text="Drops"),
                ft.DropdownOption(key="Ointment", text="Ointment"),
            ],
        )

        self.med_disease: ft.TextField = ft.TextField(
            hint_text="e.g. Thyroid",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.med_body_part: ft.TextField = ft.TextField(
            hint_text="e.g. Throat",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.stock_input: ft.TextField = ft.TextField(
            value="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            width=FIELD_WIDTH,
            height=56,
            bgcolor=BLUE,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=22, color=WHITE, weight=ft.FontWeight.BOLD),
            cursor_color=WHITE,
        )

        self.restock_notify: ft.Dropdown = ft.Dropdown(
            value="1",
            width=80,
            bgcolor="#4B77A8",
            border=ft.OutlineInputBorder(border_radius=12, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            color=WHITE,
            content_padding=ft.Padding(12, 6, 12, 6),
            options=[
                ft.DropdownOption(key=str(d), text=str(d)) for d in [1, 2, 3, 5, 7, 10, 14, 30]
            ],
        )

        self.med_note: ft.TextField = ft.TextField(
            hint_text="Special instructions or notes...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=FIELD_WIDTH,
            bgcolor="#C4DAFD",
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(16, 12, 16, 12),
            text_style=ft.TextStyle(size=15, color=INPUT_TEXT),
            cursor_color=SCHEDULE_NAVY,
        )

        # ---- Dose Scheduling Fields ------------------------------------ #
        self.sched_freq: ft.Dropdown = ft.Dropdown(
            value="Once daily",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=16, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            color=INPUT_TEXT,
            options=[
                ft.DropdownOption(key="Once daily", text="Once daily (1 dose/day)"),
                ft.DropdownOption(key="Twice daily", text="Twice daily (2 doses/day)"),
                ft.DropdownOption(key="Three times daily", text="Three times daily (3 doses/day)"),
                ft.DropdownOption(key="Custom days", text="Specific days of week"),
            ],
            on_select=self._on_frequency_change,
        )

        def make_time_row(default_h: str, default_m: str, default_p: str):
            h_dd = ft.Dropdown(
                value=default_h,
                options=[ft.DropdownOption(key=f"{h:02d}", text=f"{h:02d}") for h in range(1, 13)],
                width=100,
                height=48,
                text_size=15,
                bgcolor=INPUT_BG,
                color=INPUT_TEXT,
                border=ft.OutlineInputBorder(border_radius=12, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
                content_padding=ft.Padding(14, 4, 4, 4),
            )
            m_field = ft.TextField(
                value=default_m,
                width=80,
                height=48,
                text_align=ft.TextAlign.CENTER,
                keyboard_type=ft.KeyboardType.NUMBER,
                input_filter=ft.NumbersOnlyInputFilter(),
                bgcolor=INPUT_BG,
                border=ft.OutlineInputBorder(border_radius=12, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
                content_padding=ft.Padding(0, 8, 0, 8),
                text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.BOLD),
                cursor_color=SCHEDULE_NAVY,
            )
            p_dd = ft.Dropdown(
                value=default_p,
                options=[ft.DropdownOption(key="AM", text="AM"), ft.DropdownOption(key="PM", text="PM")],
                width=96,
                height=48,
                text_size=15,
                bgcolor=INPUT_BG,
                color=INPUT_TEXT,
                border=ft.OutlineInputBorder(border_radius=12, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
                content_padding=ft.Padding(14, 4, 4, 4),
            )
            row = ft.Row(
                controls=[
                    h_dd,
                    ft.Text(":", size=18, weight=ft.FontWeight.BOLD),
                    m_field,
                    p_dd,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            return h_dd, m_field, p_dd, row

        self.dose1_h, self.dose1_m, self.dose1_p, self.dose1_row = make_time_row("09", "00", "AM")
        self.dose2_h, self.dose2_m, self.dose2_p, self.dose2_row = make_time_row("09", "00", "PM")
        self.dose3_h, self.dose3_m, self.dose3_p, self.dose3_row = make_time_row("02", "00", "PM")

        def set_dose1(h: str, m: str, p: str):
            self.dose1_h.value = h
            self.dose1_m.value = m
            self.dose1_p.value = p
            safe_update(self.dose1_row)

        def set_now_plus(minutes: int = 0):
            target = datetime.now() + timedelta(minutes=minutes)
            h = target.hour % 12 or 12
            p = "PM" if target.hour >= 12 else "AM"
            set_dose1(f"{h:02d}", f"{target.minute:02d}", p)

        btn_style = ft.ButtonStyle(
            padding=ft.Padding(10, 2, 10, 2),
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        self.quick_time_row: ft.Row = ft.Row(
            controls=[
                ft.Button(
                    content=ft.Text("Now", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    style=btn_style,
                    height=30,
                    on_click=lambda _e: set_now_plus(0),
                ),
                ft.Button(
                    content=ft.Text("+2 min", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    style=btn_style,
                    height=30,
                    on_click=lambda _e: set_now_plus(2),
                ),
                ft.Button(
                    content=ft.Text("Morning (8am)", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    style=btn_style,
                    height=30,
                    on_click=lambda _e: set_dose1("08", "00", "AM"),
                ),
                ft.Button(
                    content=ft.Text("Night (9pm)", size=11, color=WHITE),
                    bgcolor=SCHEDULE_NAVY,
                    style=btn_style,
                    height=30,
                    on_click=lambda _e: set_dose1("09", "00", "PM"),
                ),
            ],
            spacing=6,
            run_spacing=6,
            wrap=True,
            width=FIELD_WIDTH,
        )

        self.dose1_label: ft.Container = self._make_label("Dose Time (Hour : Minute : AM/PM)")
        self.dose2_label: ft.Container = self._make_label("2nd Dose Time")
        self.dose3_label: ft.Container = self._make_label("3rd Dose Time")
        self.dose2_label.visible = False
        self.dose2_row.visible = False
        self.dose3_label.visible = False
        self.dose3_row.visible = False

        self.days_dropdown: ft.Dropdown = ft.Dropdown(
            value="Weekdays",
            options=[
                ft.DropdownOption(key="Weekdays", text="Weekdays (Mon - Fri)"),
                ft.DropdownOption(key="Weekends", text="Weekends (Sat - Sun)"),
                ft.DropdownOption(key="MWF", text="Mon, Wed, Fri"),
                ft.DropdownOption(key="TTS", text="Tue, Thu, Sat"),
            ],
            width=FIELD_WIDTH,
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding(18, 14, 18, 14),
            color=INPUT_TEXT,
        )
        self.days_label: ft.Container = self._make_label("Choose Days")
        self.days_label.visible = False
        self.days_dropdown.visible = False

        self.save_btn: ft.Button = ft.Button(
            content=ft.Text("SAVE MEDICINE", size=18, weight=ft.FontWeight.BOLD),
            width=FIELD_WIDTH,
            height=56,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=24)),
            bgcolor=SCHEDULE_NAVY,
            color=WHITE,
            on_click=self.on_save,
        )

        # ---- Assemble Fields ------------------------------------------- #
        self.controls.extend(
            [
                self.header,
                ft.Container(height=4),
                self._make_label("Medicine Name"),
                self.med_name,
                self._make_label("Dosage"),
                self.med_dosage,
                self._make_label("Form"),
                self.form_choice,
                ft.Container(
                    content=ft.Container(
                        content=ft.Text("Category", size=13, weight=ft.FontWeight.BOLD, color=WHITE),
                        bgcolor=SCHEDULE_NAVY,
                        border_radius=8,
                        padding=ft.Padding(14, 6, 14, 6),
                    ),
                    width=FIELD_WIDTH,
                    alignment=ft.Alignment.CENTER_LEFT,
                    padding=ft.Padding(4, 6, 4, 2),
                ),
                self._make_label("Disease"),
                self.med_disease,
                self._make_label("Body Part (Optional )"),
                self.med_body_part,
                self._make_label("Current Stock"),
                self.stock_input,
                # Restock alert notification row
                ft.Container(
                    width=FIELD_WIDTH,
                    padding=ft.Padding(6, 6, 6, 6),
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                "Restock Alert  Notify\nwhen below",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT,
                            ),
                            self.restock_notify,
                            ft.Text("days", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                # Dose Scheduling section
                ft.Container(
                    content=ft.Container(
                        content=ft.Text("Dose Scheduling", size=13, weight=ft.FontWeight.BOLD, color=WHITE),
                        bgcolor=SCHEDULE_NAVY,
                        border_radius=8,
                        padding=ft.Padding(14, 6, 14, 6),
                    ),
                    width=FIELD_WIDTH,
                    alignment=ft.Alignment.CENTER_LEFT,
                    padding=ft.Padding(4, 6, 4, 2),
                ),
                self._make_label("Frequency"),
                self.sched_freq,
                self.dose1_label,
                self.quick_time_row,
                self.dose1_row,
                self.dose2_label,
                self.dose2_row,
                self.dose3_label,
                self.dose3_row,
                self.days_label,
                self.days_dropdown,
                self._make_label("Note: (if needed)"),
                self.med_note,
                ft.Container(height=10),
                self.save_btn,
                ft.Container(height=30),
            ]
        )

    def _on_lang_changed(self, _new_lang: str) -> None:
        self.header_title.value = i18n.t("add_medicine")
        self.save_btn.content = ft.Text(i18n.t("save_medication"), size=17, weight=ft.FontWeight.BOLD, color=WHITE)
        safe_update(self)

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _make_label(self, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                text,
                size=14,
                weight=ft.FontWeight.BOLD,
                color=TEXT,
            ),
            width=FIELD_WIDTH,
            alignment=ft.Alignment.CENTER_LEFT,
            padding=ft.Padding(4, 4, 4, 0),
        )

    def _on_frequency_change(self, _e: Any) -> None:
        val = self.sched_freq.value or "Once daily"
        if val == "Once daily":
            self.dose2_label.visible = False
            self.dose2_row.visible = False
            self.dose3_label.visible = False
            self.dose3_row.visible = False
            self.days_label.visible = False
            self.days_dropdown.visible = False
        elif val == "Twice daily":
            self.dose2_label.visible = True
            self.dose2_row.visible = True
            self.dose3_label.visible = False
            self.dose3_row.visible = False
            self.days_label.visible = False
            self.days_dropdown.visible = False
        elif val == "Three times daily":
            self.dose2_label.visible = True
            self.dose2_row.visible = True
            self.dose3_label.visible = True
            self.dose3_row.visible = True
            self.days_label.visible = False
            self.days_dropdown.visible = False
        elif val == "Custom days":
            self.dose2_label.visible = False
            self.dose2_row.visible = False
            self.dose3_label.visible = False
            self.dose3_row.visible = False
            self.days_label.visible = True
            self.days_dropdown.visible = True
        safe_update(self)

    async def on_save(self, *_args: Any) -> None:
        name: str = (self.med_name.value or "").strip()
        dosage: str = (self.med_dosage.value or "").strip()
        full_name: str = f"{name} {dosage}".strip() if dosage else name
        if not full_name:
            toast(self._page_ref, "Medicine Name is required.", error=True)
            return

        try:
            stock: int = int(self.stock_input.value or "0")
            threshold: int = int(self.restock_notify.value or "1")
        except ValueError:
            toast(self._page_ref, "Stock must be a whole number.", error=True)
            return

        # Calculate dose schedule times and days
        freq = self.sched_freq.value or "Once daily"
        t1 = _to_24h_time(
            self.dose1_h.value or "09", self.dose1_m.value or "00", self.dose1_p.value or "AM"
        )
        times = [t1]
        days = "daily"

        if freq == "Twice daily":
            t2 = _to_24h_time(
                self.dose2_h.value or "09", self.dose2_m.value or "00", self.dose2_p.value or "PM"
            )
            times.append(t2)
        elif freq == "Three times daily":
            t2 = _to_24h_time(
                self.dose2_h.value or "02", self.dose2_m.value or "00", self.dose2_p.value or "PM"
            )
            t3 = _to_24h_time(
                self.dose3_h.value or "09", self.dose3_m.value or "00", self.dose3_p.value or "PM"
            )
            times.extend([t2, t3])
        elif freq == "Custom days":
            dv = self.days_dropdown.value or "Weekdays"
            if dv == "Weekdays":
                days = "MON,TUE,WED,THU,FRI"
            elif dv == "Weekends":
                days = "SAT,SUN"
            elif dv == "MWF":
                days = "MON,WED,FRI"
            elif dv == "TTS":
                days = "TUE,THU,SAT"

        try:
            await asyncio.to_thread(
                self._api.add_medication,
                name=full_name,
                stock_qty=max(0, stock),
                restock_notify_days=max(0, threshold),
                patient_id=self._target_patient_id,
                dosage=dosage,
                form=self.form_choice.value or "Tablet",
                disease=(self.med_disease.value or "").strip(),
                body_part=(self.med_body_part.value or "").strip(),
                notes=(self.med_note.value or "").strip(),
                schedule_times=times,
                schedule_days=days,
            )
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return

        toast(self._page_ref, f"{full_name} saved with dose schedule!")
        self._on_saved()
