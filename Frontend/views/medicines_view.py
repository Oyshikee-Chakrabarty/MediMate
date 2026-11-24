"""MedicinesView — Medicines button page matching PNG 5."""

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
from config import (
    APP_WIDTH,
    BLUE,
    CARD_WIDTH,
    CYAN,
    FIELD_WIDTH,
    FONT,
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

#
def _format_time(raw_time: str) -> str:
    try:
        t = datetime.strptime(raw_time, "%H:%M:%S")
        return t.strftime("%I:%M %p").lstrip("0")
    except Exception:
        try:
            t = datetime.strptime(raw_time, "%H:%M")
            return t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return raw_time


class MedicinesView(ft.Column):
    """Your Medicines screen matching PNG 5."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        role: str,
        user: Dict[str, Any],
        target_patient_id: Optional[str],
        on_back: Callable[[], None],
        on_add_click: Callable[[], None],
        on_schedule: Optional[Callable[[], None]] = None,
        on_alerts_or_history: Optional[Callable[[], None]] = None,
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
        self._on_add_click: Callable[[], None] = on_add_click
        self._on_schedule: Optional[Callable[[], None]] = on_schedule
        self._on_alerts_or_history: Optional[Callable[[], None]] = on_alerts_or_history
        self._on_profile: Optional[Callable[[], None]] = on_profile

        self._filter_mode: str = "all"  # "all" or "low_stock"
        self._all_meds: List[Dict[str, Any]] = []
        self._med_sched_map: Dict[str, List[Dict[str, Any]]] = {}

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Header ------------------------------------------------ #
        self.header_title: ft.Text = ft.Text(
            i18n.t("medicines_title"),
            size=22,
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
                                    width=38,
                                    height=38,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.ARROW_BACK, color=theme_color, size=20),
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

        # ---- Title + ADD+ button row ----------------------------------- #
        self.count_text: ft.Text = ft.Text(
            i18n.t("medicines_count", count=0),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=TEXT,
        )

        self.add_btn_text: ft.Text = ft.Text(
            i18n.t("add_btn"), size=16, weight=ft.FontWeight.BOLD, color=WHITE
        )

        self.add_btn: ft.Button = ft.Button(
            content=ft.Row(
                [
                    self.add_btn_text,
                    ft.Icon(ft.Icons.ADD, color=WHITE, size=18),
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#66BB6A",
            color=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            height=42,
            width=110,
            on_click=lambda _e: self._on_add_click(),
        )

        self.title_text: ft.Text = ft.Text(
            i18n.t("your_medicines"),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
        )

        self.title_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 8, 4, 0),
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
                    self.add_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Filter Row (FILTER : Low Stock, All) ---------------------- #
        self.filter_low_stock_badge: ft.Container = ft.Container(
            content=ft.Text(i18n.t("low_stock_filter"), size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=SCHEDULE_NAVY,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_low_stock,
        )
        self.filter_all_badge: ft.Container = ft.Container(
            content=ft.Text(i18n.t("all_filter"), size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=BLUE,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_all,
        )

        self.filter_label: ft.Text = ft.Text(
            i18n.t("filter_label"), size=14, weight=ft.FontWeight.BOLD, color=TITLE_NAVY
        )

        self.filter_row: ft.Container = ft.Container(
            width=CARD_WIDTH,
            padding=ft.Padding(4, 0, 4, 6),
            content=ft.Row(
                controls=[
                    self.filter_label,
                    self.filter_low_stock_badge,
                    self.filter_all_badge,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Medicines List --------------------------------------------- #
        self.med_list: ft.Column = ft.Column(spacing=12, width=CARD_WIDTH)

        # ---- Bottom Nav ------------------------------------------------- #
        self.nav_bar: ft.Container = build_bottom_nav(
            role=self._role,
            on_medicines=lambda: None,
            on_schedule=self._on_schedule,
            on_alerts_or_history=self._on_alerts_or_history,
            on_profile=self._on_profile,
        )

        # Fixed Footer Layout: Scrollable body area (expand=True) + Pinned Footer
        self.scroll_content: ft.Column = ft.Column(
            controls=[
                self.title_row,
                self.filter_row,
                self.med_list,
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

    def _on_lang_changed(self, _new_lang: str) -> None:
        self.header_title.value = i18n.t("medicines_title")
        self.title_text.value = i18n.t("your_medicines")
        self.add_btn_text.value = i18n.t("add_btn")
        self.filter_label.value = i18n.t("filter_label")
        self.filter_low_stock_badge.content = ft.Text(i18n.t("low_stock_filter"), size=12, weight=ft.FontWeight.BOLD, color=WHITE)
        self.filter_all_badge.content = ft.Text(i18n.t("all_filter"), size=12, weight=ft.FontWeight.BOLD, color=WHITE)
        self._render_meds()
        safe_update(self)

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)
        try:
            p = self.page
            if p and hasattr(p, "run_task"):
                p.run_task(self.load_medications)
        except Exception:
            pass

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def _select_low_stock(self, *_args: Any) -> None:
        self._filter_mode = "low_stock"
        self.filter_low_stock_badge.bgcolor = BLUE
        self.filter_all_badge.bgcolor = SCHEDULE_NAVY
        self._render_meds()
        safe_update(self)

    def _select_all(self, *_args: Any) -> None:
        self._filter_mode = "all"
        self.filter_low_stock_badge.bgcolor = SCHEDULE_NAVY
        self.filter_all_badge.bgcolor = BLUE
        self._render_meds()
        safe_update(self)

    async def load_medications(self, *_args: Any) -> None:
        try:
            self._all_meds = await asyncio.to_thread(
                self._api.list_medications, self._target_patient_id
            )
            scheds = await asyncio.to_thread(
                self._api.list_schedules, None, self._target_patient_id
            )
            self._med_sched_map = {}
            for s in scheds:
                self._med_sched_map.setdefault(s.get("medication_id", ""), []).append(s)
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return

        self._render_meds()
        safe_update(self)

    def _render_meds(self) -> None:
        filtered: List[Dict[str, Any]] = []
        for med in self._all_meds:
            stock: int = int(med.get("stock_qty", 0))
            threshold: int = int(med.get("restock_notify_days", 7))
            if self._filter_mode == "low_stock":
                if stock <= threshold:
                    filtered.append(med)
            else:
                filtered.append(med)

        count = len(filtered)
        count_key = "medicine_count_single" if count == 1 else "medicines_count"
        self.count_text.value = i18n.t(count_key, count=count)
        self.med_list.controls.clear()

        if not filtered:
            msg: str = (
                i18n.t("no_low_stock_found")
                if self._filter_mode == "low_stock"
                else i18n.t("no_meds_add_hint")
            )
            self.med_list.controls.append(
                ft.Container(
                    content=ft.Text(msg, size=14, color=MUTED, text_align=ft.TextAlign.CENTER),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            )
            return

        for med in filtered:
            self.med_list.controls.append(self._build_med_card(med))

    def _build_med_card(self, med: Dict[str, Any]) -> ft.Container:
        stock: int = int(med.get("stock_qty", 0))
        disease: str = med.get("disease") or "General"
        form: str = med.get("form") or "Tablet"
        dosage: str = med.get("dosage") or ""
        dose_label: str = f"1 {form}" if form else "1 Dose"

        async def restock(_e: Any) -> None:
            try:
                await asyncio.to_thread(
                    self._api.update_medication,
                    med["id"],
                    stock_qty=stock + 10,
                    patient_id=self._target_patient_id,
                )
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, i18n.t("restocked_toast", name=med['name']))
            await self.load_medications()

        async def remove(_e: Any) -> None:
            try:
                await asyncio.to_thread(
                    self._api.delete_medication, med["id"], self._target_patient_id
                )
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, i18n.t("deleted_med_toast", name=med['name']))
            await self.load_medications()

        scheds = self._med_sched_map.get(med.get("id", ""), [])
        sched_row: Optional[ft.Row] = None
        if scheds:
            times = [_format_time(s.get("due_time", "")) for s in scheds]
            times_str = ", ".join(times)
            sched_row = ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SCHEDULE, size=14, color=SCHEDULE_NAVY),
                    ft.Text(f"{times_str}", size=12, color=SCHEDULE_NAVY, weight=ft.FontWeight.BOLD),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        card_col_controls: List[ft.Control] = [
            ft.Text(
                med.get("name", ""),
                size=18,
                weight=ft.FontWeight.BOLD,
                color="#2C3E50",
            ),
            ft.Text(
                dose_label,
                size=15,
                color="#475569",
                weight=ft.FontWeight.W_500,
            ),
        ]
        if sched_row:
            card_col_controls.append(sched_row)

        doses_per_week = 0.0
        for s in scheds:
            d_str = (s.get("days_of_week") or "daily").strip().lower()
            if d_str == "daily":
                doses_per_week += 7.0
            else:
                doses_per_week += len([x for x in d_str.split(",") if x.strip()])
        doses_per_day = doses_per_week / 7.0 if doses_per_week > 0 else 0.0

        supply_chip = None
        if stock <= 0:
            supply_chip = ft.Container(
                content=ft.Text(i18n.t("out_of_stock_chip"), size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                bgcolor=RED,
                border_radius=8,
                padding=ft.Padding(6, 4, 6, 4),
            )
        elif doses_per_day > 0:
            days_left = stock / doses_per_day
            is_low = days_left <= med.get("restock_notify_days", 7)
            supply_chip = ft.Container(
                content=ft.Text(i18n.t("days_left_chip", days=f"{days_left:.0f}"), size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                bgcolor=ORANGE if is_low else "#2E7D32",
                border_radius=8,
                padding=ft.Padding(6, 4, 6, 4),
            )

        tracking_data = {
            "medication_id": med["id"],
            "medication_name": med.get("name", "Medication"),
            "stock_qty": stock,
            "days_supply_remaining": (stock / doses_per_day) if doses_per_day > 0 else (0 if stock <= 0 else 999.0),
            "frequency_summary": f"{doses_per_day:.1f} doses/day" if doses_per_day > 0 else "As needed",
            "reschedule_status": "reschedule_now" if stock <= 0 else ("reschedule_soon" if doses_per_day > 0 and (stock / doses_per_day) <= med.get("restock_notify_days", 7) else "healthy"),
        }

        top_row = ft.Row(
            controls=[
                ft.Column(
                    controls=card_col_controls,
                    spacing=2,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Image(
                        src=get_asset_path("pill_icon.png"),
                        width=46,
                        height=46,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    alignment=ft.Alignment.TOP_RIGHT,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        chips_controls: List[ft.Control] = [
            ft.Container(
                content=ft.Text(
                    disease,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=WHITE,
                ),
                bgcolor="#00A3E0",
                border_radius=8,
                padding=ft.Padding(7, 3, 7, 3),
            ),
            ft.Container(
                content=ft.Text(
                    i18n.t("stock_chip", stock=stock),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=WHITE,
                ),
                bgcolor=SCHEDULE_NAVY,
                border_radius=8,
                padding=ft.Padding(7, 3, 7, 3),
            ),
        ]
        if supply_chip:
            chips_controls.append(supply_chip)

        action_buttons: List[ft.Control] = [
            ft.IconButton(
                icon=ft.Icons.UPDATE,
                tooltip=i18n.t("reschedule_refill_tooltip"),
                icon_color=SCHEDULE_NAVY,
                icon_size=18,
                width=30,
                height=30,
                padding=0,
                on_click=lambda _e: show_reschedule_dialog(
                    self._page_ref,
                    self._api,
                    tracking_data,
                    on_rescheduled=lambda: self.page.run_task(self.load_medications),
                    patient_id=self._target_patient_id,
                ),
            ),
            ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                tooltip=i18n.t("schedule_dose_tooltip"),
                icon_color=SCHEDULE_NAVY,
                icon_size=18,
                width=30,
                height=30,
                padding=0,
                on_click=lambda _e: self._on_schedule() if self._on_schedule else None,
            ),
            ft.IconButton(
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                tooltip=i18n.t("restock_tooltip"),
                icon_color="#2E7D32",
                icon_size=18,
                width=30,
                height=30,
                padding=0,
                on_click=restock,
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                tooltip=i18n.t("delete_tooltip"),
                icon_color=RED,
                icon_size=18,
                width=30,
                height=30,
                padding=0,
                on_click=remove,
            ),
        ]

        bottom_row = ft.Row(
            controls=[
                ft.Row(
                    controls=chips_controls,
                    spacing=4,
                    wrap=True,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=action_buttons,
                    spacing=1,
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            bgcolor="#D4EDDA",
            border=ft.Border.all(1, "#B4E1F8"),
            border_radius=18,
            shadow=SHADOW_SUBTLE,
            padding=ft.Padding(14, 12, 14, 12),
            width=CARD_WIDTH,
            content=ft.Column(
                controls=[
                    top_row,
                    ft.Container(height=4),
                    bottom_row,
                ],
                spacing=2,
                tight=True,
            ),
        )
