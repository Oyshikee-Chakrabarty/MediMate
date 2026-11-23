"""Small shared UI helpers used by more than one view.

Kept in `components/` (mirroring the main app's structure) so views stay
focused on their own screens.
"""

from __future__ import annotations

from typing import List

import flet as ft

from config import FONT, RED


import os
from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from config import APP_WIDTH, CARD_WIDTH, CYAN, FONT, GREEN, MUTED, RED, SCHEDULE_NAVY, WHITE
from services import i18n


# Shared subtle elevation shadows for premium tactile card rendering
SHADOW_SUBTLE = ft.BoxShadow(
    spread_radius=0,
    blur_radius=10,
    color=ft.Colors.with_opacity(0.04, "#0F172A"),
    offset=ft.Offset(0, 2),
)

SHADOW_CARD = ft.BoxShadow(
    spread_radius=0,
    blur_radius=14,
    color=ft.Colors.with_opacity(0.06, "#0F172A"),
    offset=ft.Offset(0, 4),
)

SHADOW_ELEVATED = ft.BoxShadow(
    spread_radius=1,
    blur_radius=16,
    color=ft.Colors.with_opacity(0.12, "#0096D6"),
    offset=ft.Offset(0, 4),
)


_ASSET_CACHE: Dict[str, str] = {}


def get_asset_path(filename: str) -> str:
    """Return an asset src that displays reliably on Android, Web, and Desktop."""
    clean_name = filename.lstrip("/\\")
    base_dir: Path = Path(__file__).resolve().parent.parent
    file_path = base_dir / clean_name
    if file_path.exists():
        return f"/{clean_name}"
    return filename


def centered(children: List[ft.Control], scroll: bool = False) -> ft.Container:
    """A full-page container that centers its content horizontally with safe area protection."""
    col = ft.Column(
        children,
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO if scroll else None,
        expand=True,
    )
    return ft.Container(
        content=ft.SafeArea(
            content=col,
            avoid_intrusions_top=True,
            avoid_intrusions_bottom=True,
        ),
        alignment=ft.Alignment.TOP_CENTER,
        padding=ft.Padding(0, 0, 0, 0),
        expand=True,
    )


def safe_update(control: ft.Control) -> None:
    """Re-render a control only when it is actually mounted on a page."""
    if control.parent is not None:
        try:
            control.update()
        except Exception:
            pass


def toast(page: ft.Page, message: str, error: bool = False) -> None:
    """Show a short popup message at screen bottom."""
    page.show_dialog(
        ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE, size=FONT),
            bgcolor=RED if error else GREEN,
            duration=3500,
        )
    )


def error_text(message: str) -> ft.Text:
    """A red, centered error line used under form titles."""
    return ft.Text(message, color=RED, size=FONT - 1, text_align=ft.TextAlign.CENTER)


def build_language_toggle(
    on_toggle: Optional[Callable[[str], None]] = None,
    api: Optional[Any] = None,
    bg_color: Optional[str] = None,
    text_color: Optional[str] = None,
    border_color: Optional[str] = None,
    height: int = 32,
    border_radius: int = 16,
) -> ft.Container:
    """A 1-click pill button that interchanges between English and Bangla.

    Displays:
      '🌐 বাংলা' when current language is 'en' (click switches to Bangla)
      '🌐 English' when current language is 'bn' (click switches to English)
    """
    btn_text = ft.Text(
        i18n.get_toggle_button_label(),
        size=12,
        weight=ft.FontWeight.BOLD,
        color=text_color or WHITE,
    )

    def on_click(_e: Any) -> None:
        new_lang = i18n.toggle_language()
        btn_text.value = i18n.get_toggle_button_label()
        safe_update(btn_text)
        if api and getattr(api, "token", None):
            def _bg_update() -> None:
                try:
                    api.update_language(new_lang)
                except Exception:
                    pass
            threading.Thread(target=_bg_update, daemon=True).start()
        if on_toggle:
            on_toggle(new_lang)

    def _on_lang_changed(lang: str) -> None:
        btn_text.value = i18n.get_toggle_button_label()
        safe_update(btn_text)

    i18n.register_language_listener(_on_lang_changed)

    pill = ft.Container(
        content=btn_text,
        bgcolor=bg_color or SCHEDULE_NAVY,
        border=ft.Border.all(1, border_color) if border_color else None,
        border_radius=border_radius,
        padding=ft.Padding(10, 4, 10, 4),
        height=height,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        tooltip="Toggle Language (English / বাংলা)",
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )
    return pill


def build_bottom_nav(
    role: str,
    on_medicines: Optional[Callable[[], None]] = None,
    on_schedule: Optional[Callable[[], None]] = None,
    on_alerts_or_history: Optional[Callable[[], None]] = None,
    on_profile: Optional[Callable[[], None]] = None,
) -> ft.Container:
    """Build a fluid, responsive bottom navigation bar with live multi-language."""
    meds_text = ft.Text(
        i18n.t("nav_medicines"),
        size=11,
        weight=ft.FontWeight.BOLD,
        color=SCHEDULE_NAVY,
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    sched_text = ft.Text(
        i18n.t("nav_schedule"),
        size=11,
        weight=ft.FontWeight.BOLD,
        color=SCHEDULE_NAVY,
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    hist_text = ft.Text(
        i18n.t("nav_history") if role == "patient" else i18n.t("nav_alerts"),
        size=11,
        weight=ft.FontWeight.BOLD,
        color=SCHEDULE_NAVY,
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    def _on_lang_changed(_lang: str) -> None:
        meds_text.value = i18n.t("nav_medicines")
        sched_text.value = i18n.t("nav_schedule")
        hist_text.value = i18n.t("nav_history") if role == "patient" else i18n.t("nav_alerts")
        safe_update(meds_text)
        safe_update(sched_text)
        safe_update(hist_text)

    i18n.register_language_listener(_on_lang_changed)

    pill_style = dict(
        bgcolor=WHITE,
        border_radius=14,
        height=42,
        padding=ft.Padding(4, 0, 4, 0),
        alignment=ft.Alignment.CENTER,
        expand=True,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
    )

    nav_box = ft.Container(
        bgcolor=CYAN,
        border_radius=28,
        height=58,
        padding=ft.Padding(6, 6, 6, 6),
        margin=ft.Margin(0, 2, 0, 12),
        width=CARD_WIDTH,
        shadow=SHADOW_ELEVATED,
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.MEDICATION, color=SCHEDULE_NAVY, size=16),
                            meds_text,
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    on_click=lambda _e: on_medicines() if on_medicines else None,
                    **pill_style,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CALENDAR_MONTH, color=SCHEDULE_NAVY, size=16),
                            sched_text,
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    on_click=lambda _e: on_schedule() if on_schedule else None,
                    **pill_style,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.HISTORY if role == "patient" else ft.Icons.WARNING_ROUNDED,
                                color=SCHEDULE_NAVY,
                                size=16,
                            ),
                            hist_text,
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    on_click=lambda _e: on_alerts_or_history() if on_alerts_or_history else None,
                    **pill_style,
                ),
                ft.Container(
                    shape=ft.BoxShape.CIRCLE,
                    bgcolor=WHITE,
                    width=42,
                    height=42,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.PERSON, color=CYAN, size=22),
                    on_click=lambda _e: on_profile() if on_profile else None,
                    animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
                ),
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    return ft.Container(
        content=ft.SafeArea(
            content=nav_box,
            avoid_intrusions_top=False,
            maintain_bottom_view_padding=True,
        ),
        alignment=ft.Alignment.BOTTOM_CENTER,
    )


def show_reschedule_dialog(
    page: ft.Page,
    api: Any,
    tracking: Dict[str, Any],
    on_rescheduled: Optional[Callable[[], None]] = None,
    patient_id: Optional[str] = None,
) -> None:
    """Reusable modal dialog to restock and reschedule dose events."""
    import asyncio
    import threading
    from datetime import datetime
    from config import CARD_BG_BLUE, CARD_BORDER_BLUE, MUTED, ORANGE, TEXT, TITLE_NAVY

    med_id = tracking.get("medication_id", "")
    med_name = tracking.get("medication_name", "Medication")
    stock = tracking.get("stock_qty", 0)
    days_left = tracking.get("days_supply_remaining", 0)
    freq = tracking.get("frequency_summary", "")
    resched_date_str = tracking.get("reschedule_due_date", "")
    due_display = i18n.t("immediate")
    if resched_date_str:
        try:
            dt = datetime.fromisoformat(resched_date_str.replace("Z", "+00:00"))
            due_display = dt.strftime("%b %d, %Y")
        except Exception:
            due_display = resched_date_str[:10]

    stock_label = ft.Text(
        i18n.t("added_stock_label"),
        size=12,
        weight=ft.FontWeight.BOLD,
        color=TITLE_NAVY,
    )
    added_stock_input = ft.TextField(
        value="30",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=300,
        bgcolor="#F8FAFC",
        border_color=CARD_BORDER_BLUE,
        focused_border_color=ORANGE,
        border_radius=12,
        color=TITLE_NAVY,
        text_size=16,
        text_align=ft.TextAlign.CENTER,
        content_padding=ft.Padding(12, 10, 12, 10),
    )

    def set_add_stock(val: int) -> None:
        added_stock_input.value = str(val)
        safe_update(added_stock_input)

    def _chip(val: int) -> ft.Container:
        return ft.Container(
            content=ft.Text(f"+{val}", size=12, weight=ft.FontWeight.BOLD, color=SCHEDULE_NAVY),
            bgcolor="#E0F2FE",
            border=ft.Border.all(1, "#BAE6FD"),
            border_radius=10,
            padding=ft.Padding(10, 6, 10, 6),
            alignment=ft.Alignment.CENTER,
            expand=True,
            on_click=lambda _e, v=val: set_add_stock(v),
        )

    chips_row = ft.Row(
        controls=[_chip(15), _chip(30), _chip(60), _chip(90)],
        spacing=6,
        width=300,
    )

    def do_reschedule(_e: Any) -> None:
        try:
            qty = int(added_stock_input.value or "30")
            if qty <= 0:
                qty = 30
        except ValueError:
            qty = 30

        if hasattr(page, "pop_dialog"):
            try:
                page.pop_dialog()
            except Exception:
                pass

        def _bg() -> None:
            try:
                api.reschedule_medication(
                    medication_id=med_id,
                    added_stock=qty,
                    extend_days=30,
                    patient_id=patient_id,
                )
                toast(page, i18n.t("rescheduled_toast", name=med_name, qty=qty))
                if on_rescheduled:
                    on_rescheduled()
            except Exception as exc:
                toast(page, i18n.t("reschedule_failed", err=str(exc)), error=True)

        threading.Thread(target=_bg, daemon=True).start()

    info_card = ft.Container(
        bgcolor=CARD_BG_BLUE,
        border=ft.Border.all(1, CARD_BORDER_BLUE),
        border_radius=14,
        padding=12,
        width=300,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(i18n.t("current_stock_label", stock=stock), size=13, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                        ft.Container(
                            content=ft.Text(f"{days_left:.0f}d left", size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                            bgcolor=RED if days_left <= 0 else (ORANGE if days_left <= 7 else "#2E7D32"),
                            border_radius=6,
                            padding=ft.Padding(6, 2, 6, 2),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(i18n.t("frequency_label", freq=freq), size=12, color="#475569"),
                ft.Text(i18n.t("projected_reschedule_label", date=due_display), size=12, weight=ft.FontWeight.BOLD, color=ORANGE if days_left <= 7 else "#2E7D32"),
            ],
            spacing=4,
        ),
    )

    confirm_btn = ft.Button(
        content=ft.Text(i18n.t("confirm_reschedule"), size=14, weight=ft.FontWeight.BOLD, color=WHITE),
        bgcolor=GREEN,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        height=44,
        width=300,
        on_click=do_reschedule,
    )

    dlg = ft.AlertDialog(
        bgcolor=WHITE,
        shape=ft.RoundedRectangleBorder(radius=20),
        title=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.EVENT_REPEAT_ROUNDED, color=ORANGE, size=22),
                        ft.Text(
                            i18n.t("reschedule_refill_title", name=med_name),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_NAVY,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=18,
                    icon_color=MUTED,
                    on_click=lambda _e: page.pop_dialog() if hasattr(page, "pop_dialog") else None,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Column(
            controls=[
                info_card,
                ft.Container(height=2),
                stock_label,
                added_stock_input,
                chips_row,
                ft.Container(height=4),
                confirm_btn,
            ],
            tight=True,
            spacing=6,
            width=300,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    if hasattr(page, "show_dialog"):
        page.show_dialog(dlg)
