"""MedicinesView — Medicines button page matching PNG 5."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from components.common import build_bottom_nav, get_asset_path, safe_update, toast
from config import (
    BLUE,
    CYAN,
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
from services.api_client import Api, ApiError


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
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=380,
            scroll=ft.ScrollMode.AUTO,
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

        theme_color: str = ORANGE if role == "caretaker" else GREEN

        # ---- Top Header ------------------------------------------------ #
        self.header: ft.Container = ft.Container(
            bgcolor=theme_color,
            padding=ft.Padding(16, 24, 16, 20),
            border_radius=ft.BorderRadius(0, 0, 36, 0),
            content=ft.Row(
                controls=[
                    ft.Container(
                        shape=ft.BoxShape.CIRCLE,
                        bgcolor=WHITE,
                        width=42,
                        height=42,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.ARROW_BACK, color=theme_color, size=24),
                        on_click=lambda _e: self._on_back(),
                    ),
                    ft.Text(
                        "Medicines",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                        color=WHITE,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=380,
        )

        # ---- Title + ADD+ button row ----------------------------------- #
        self.count_text: ft.Text = ft.Text(
            "0 medicines",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=TEXT,
        )

        self.add_btn: ft.Button = ft.Button(
            content=ft.Row(
                [
                    ft.Text("ADD", size=16, weight=ft.FontWeight.BOLD, color=WHITE),
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

        self.title_row: ft.Container = ft.Container(
            width=360,
            padding=ft.Padding(4, 8, 4, 0),
            content=ft.Row(
                controls=[
                    ft.Column(
                        [
                            ft.Text(
                                "Your Medicines",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=TITLE_NAVY,
                            ),
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
            content=ft.Text("Low Stock", size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=SCHEDULE_NAVY,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_low_stock,
        )
        self.filter_all_badge: ft.Container = ft.Container(
            content=ft.Text("All", size=12, weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=BLUE,
            border_radius=8,
            padding=ft.Padding(12, 6, 12, 6),
            on_click=self._select_all,
        )

        self.filter_row: ft.Container = ft.Container(
            width=360,
            padding=ft.Padding(4, 0, 4, 6),
            content=ft.Row(
                controls=[
                    ft.Text("FILTER : ", size=14, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    self.filter_low_stock_badge,
                    self.filter_all_badge,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Medicines List --------------------------------------------- #
        self.med_list: ft.Column = ft.Column(spacing=12, width=360)

        # ---- Bottom Nav ------------------------------------------------- #
        self.nav_bar: ft.Container = build_bottom_nav(
            role=self._role,
            on_medicines=lambda: None,
            on_schedule=self._on_schedule,
            on_alerts_or_history=self._on_alerts_or_history,
            on_profile=self._on_profile,
        )

        self.controls.extend(
            [
                self.header,
                self.title_row,
                self.filter_row,
                self.med_list,
                self.nav_bar,
            ]
        )

    def did_mount(self) -> None:
        self.page.run_task(self.load_medications)

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

        self.count_text.value = f"{len(filtered)} medicines"
        self.med_list.controls.clear()

        if not filtered:
            msg: str = (
                "No low stock medicines found."
                if self._filter_mode == "low_stock"
                else "No medicines added yet. Tap ADD + above to add one!"
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
            toast(self._page_ref, f"Restocked 10 units for {med['name']}!")
            await self.load_medications()

        async def remove(_e: Any) -> None:
            try:
                await asyncio.to_thread(
                    self._api.delete_medication, med["id"], self._target_patient_id
                )
            except ApiError as exc:
                toast(self._page_ref, exc.detail, error=True)
                return
            toast(self._page_ref, f"Deleted {med['name']}.")
            await self.load_medications()

        return ft.Container(
            bgcolor="#D4EDDA",
            border=ft.Border.all(1, "#B4E1F8"),
            border_radius=20,
            padding=ft.Padding(16, 16, 16, 16),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
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
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(
                                            disease,
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=WHITE,
                                        ),
                                        bgcolor="#00A3E0",
                                        border_radius=8,
                                        padding=ft.Padding(10, 4, 10, 4),
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            f"Stock: {stock}",
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=WHITE,
                                        ),
                                        bgcolor=SCHEDULE_NAVY,
                                        border_radius=8,
                                        padding=ft.Padding(10, 4, 10, 4),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                        tooltip="Restock +10",
                                        icon_color="#2E7D32",
                                        icon_size=20,
                                        on_click=restock,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Delete",
                                        icon_color=RED,
                                        icon_size=20,
                                        on_click=remove,
                                    ),
                                ],
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Image(
                        src=get_asset_path("pill_icon.png"),
                        width=56,
                        height=56,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
