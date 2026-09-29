"""AddMedicineView — Add medicine form matching PNG 6."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

import flet as ft

from components.common import safe_update, toast
from config import (
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
from services.api_client import Api, ApiError


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
            width=380,
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
                        "Add Medicine",
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

        # ---- Form Fields (Matching PNG 6) ------------------------------ #
        self.med_name: ft.TextField = ft.TextField(
            hint_text="e.g. Thyrox",
            width=FIELD_WIDTH,
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.med_dosage: ft.TextField = ft.TextField(
            hint_text="e.g. 50mcg",
            width=FIELD_WIDTH,
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.form_choice: ft.Dropdown = ft.Dropdown(
            value="Tablet",
            width=FIELD_WIDTH,
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
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
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.med_body_part: ft.TextField = ft.TextField(
            hint_text="e.g. Throat",
            width=FIELD_WIDTH,
            border_radius=16,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
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
            border_radius=16,
            bgcolor=BLUE,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=22, color=WHITE, weight=ft.FontWeight.BOLD),
            cursor_color=WHITE,
        )

        self.restock_notify: ft.Dropdown = ft.Dropdown(
            value="1",
            width=80,
            border_radius=12,
            bgcolor="#4B77A8",
            border=ft.InputBorder.NONE,
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
            border_radius=16,
            bgcolor="#C4DAFD",
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(16, 12, 16, 12),
            text_style=ft.TextStyle(size=15, color=INPUT_TEXT),
            cursor_color=SCHEDULE_NAVY,
        )

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
                self._make_label("Note: (if needed)"),
                self.med_note,
                ft.Container(height=10),
                self.save_btn,
                ft.Container(height=30),
            ]
        )

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
            )
        except ApiError as exc:
            toast(self._page_ref, exc.detail, error=True)
            return

        toast(self._page_ref, f"{full_name} saved successfully!")
        self._on_saved()
