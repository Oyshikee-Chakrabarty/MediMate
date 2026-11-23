"""Profile card and dialog component.

Displays a well-oriented, beautifully styled medical and personal profile card
including blood group, age, gender, weight, height, emergency contact,
allergies, and conditions, with interactive in-place editing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

import flet as ft

from config import (
    CARD_BORDER_BLUE,
    CYAN,
    GREEN,
    MUTED,
    ORANGE,
    RED,
    SCHEDULE_NAVY,
    TITLE_NAVY,
    WHITE,
)
from services import i18n
from services.profile_service import get_user_profile, update_user_profile

logger = logging.getLogger(__name__)

BLOOD_GROUPS = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
GENDERS = ["Male", "Female", "Other"]


def _get_initials(name: str, email: str) -> str:
    cleaned = (name or "").strip()
    if cleaned:
        parts = cleaned.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return cleaned[:2].upper()
    email_clean = (email or "").strip()
    if email_clean:
        return email_clean[:2].upper()
    return "U"


def build_profile_card(
    page: ft.Page,
    user: Dict[str, Any],
    role: str = "patient",
    code_display_value: Optional[str] = None,
    code_display_control: Optional[Any] = None,
    on_generate_code: Optional[Callable[[], Any]] = None,
    on_connect_patient: Optional[Callable[[], Any]] = None,
    active_patient_name: Optional[str] = None,
    on_logout: Optional[Callable[[], Any]] = None,
    on_close: Optional[Callable[[], Any]] = None,
    width: int = 345,
) -> ft.Container:
    """Build a responsive, oriented profile card control."""
    user_key = str(user.get("id") or user.get("email") or "")
    profile_data = get_user_profile(user_key)

    name_str = user.get("name") or "User"
    email_str = user.get("email") or "No email provided"
    initials_str = _get_initials(name_str, email_str)

    theme_color = ORANGE if role == "caretaker" else GREEN
    role_label = "Caregiver" if role == "caretaker" else "Patient"

    # Dynamic controls with wrapping / ellipsis to stay strictly inside boxes
    blood_val_text = ft.Text(
        profile_data.get("blood_group", "O+"),
        size=15,
        weight=ft.FontWeight.BOLD,
        color="#DC2626",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    age_gender_text = ft.Text(
        f"{profile_data.get('age', '28')} {i18n.t('profile_years_old')} • {profile_data.get('gender', 'Male')}",
        size=10,
        weight=ft.FontWeight.BOLD,
        color="#1D4ED8",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    weight_height_text = ft.Text(
        f"{profile_data.get('weight', '68 kg')} • {profile_data.get('height', '172 cm')}",
        size=10,
        weight=ft.FontWeight.BOLD,
        color="#6D28D9",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    emergency_val_text = ft.Text(
        profile_data.get("emergency_contact", "+880 1712-345678"),
        size=9.5,
        weight=ft.FontWeight.BOLD,
        color="#047857",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    allergies_val_text = ft.Text(
        f"Allergies: {profile_data.get('allergies', 'None')} | Conditions: {profile_data.get('conditions', 'None')}",
        size=10,
        weight=ft.FontWeight.W_600,
        color="#92400E",
        max_lines=3,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    card_container = ft.Container()

    def refresh_vitals() -> None:
        p = get_user_profile(user_key)
        blood_val_text.value = p.get("blood_group", "O+")
        age_gender_text.value = f"{p.get('age', '28')} {i18n.t('profile_years_old')} • {p.get('gender', 'Male')}"
        weight_height_text.value = f"{p.get('weight', '68 kg')} • {p.get('height', '172 cm')}"
        emergency_val_text.value = p.get("emergency_contact", "+880 1712-345678")
        allergies_val_text.value = f"Allergies: {p.get('allergies', 'None')} | Conditions: {p.get('conditions', 'None')}"
        try:
            if card_container.page:
                card_container.update()
        except Exception:
            pass

    # Quick manual input modal when clicking a specific option tile
    def open_single_field_dialog(field_key: str) -> None:
        p = get_user_profile(user_key)

        if field_key == "blood_group":
            bg_radio = ft.RadioGroup(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Radio(value=bg, label=bg)
                                for bg in BLOOD_GROUPS[:4]
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        ),
                        ft.Row(
                            controls=[
                                ft.Radio(value=bg, label=bg)
                                for bg in BLOOD_GROUPS[4:]
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        ),
                    ],
                    spacing=8,
                ),
                value=p.get("blood_group", "O+"),
            )

            def save_bg(_ev: Any) -> None:
                update_user_profile(user_key, {"blood_group": bg_radio.value or "O+"})
                refresh_vitals()
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color="#EF4444", size=22),
                        ft.Text(i18n.t("profile_blood_group"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    ],
                    spacing=8,
                ),
                content=ft.Container(width=300, content=bg_radio, padding=ft.Padding(4, 8, 4, 8)),
                actions=[
                    ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text(i18n.t("save"), color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor="#EF4444",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=save_bg,
                    ),
                ],
            )
            page.show_dialog(dlg)

        elif field_key == "age_gender":
            age_tf = ft.TextField(
                label=i18n.t("profile_age"),
                value=p.get("age", "28"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )
            gender_dd = ft.Dropdown(
                label=i18n.t("profile_gender"),
                value=p.get("gender", "Male"),
                options=[ft.dropdown.Option(g) for g in GENDERS],
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )

            def save_ag(_ev: Any) -> None:
                update_user_profile(user_key, {
                    "age": (age_tf.value or "28").strip(),
                    "gender": gender_dd.value or "Male",
                })
                refresh_vitals()
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PERSON_ROUNDED, color="#2563EB", size=22),
                        ft.Text(i18n.t("profile_age_gender"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    ],
                    spacing=8,
                ),
                content=ft.Container(
                    width=300,
                    content=ft.Column([age_tf, gender_dd], tight=True, spacing=10),
                ),
                actions=[
                    ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text(i18n.t("save"), color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor="#2563EB",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=save_ag,
                    ),
                ],
            )
            page.show_dialog(dlg)

        elif field_key == "weight_height":
            w_tf = ft.TextField(
                label=i18n.t("profile_weight"),
                value=p.get("weight", "68 kg"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )
            h_tf = ft.TextField(
                label=i18n.t("profile_height"),
                value=p.get("height", "172 cm"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )

            def save_wh(_ev: Any) -> None:
                update_user_profile(user_key, {
                    "weight": (w_tf.value or "68 kg").strip(),
                    "height": (h_tf.value or "172 cm").strip(),
                })
                refresh_vitals()
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.MONITOR_WEIGHT_ROUNDED, color="#7C3AED", size=22),
                        ft.Text(i18n.t("profile_weight_height"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    ],
                    spacing=8,
                ),
                content=ft.Container(
                    width=300,
                    content=ft.Column([w_tf, h_tf], tight=True, spacing=10),
                ),
                actions=[
                    ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text(i18n.t("save"), color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor="#7C3AED",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=save_wh,
                    ),
                ],
            )
            page.show_dialog(dlg)

        elif field_key == "emergency":
            e_tf = ft.TextField(
                label=i18n.t("profile_emergency_phone"),
                value=p.get("emergency_contact", "+880 1712-345678"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )

            def save_em(_ev: Any) -> None:
                update_user_profile(user_key, {"emergency_contact": (e_tf.value or "").strip()})
                refresh_vitals()
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PHONE_IN_TALK_ROUNDED, color="#059669", size=22),
                        ft.Text(i18n.t("profile_emergency_phone"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    ],
                    spacing=8,
                ),
                content=ft.Container(width=300, content=e_tf),
                actions=[
                    ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text(i18n.t("save"), color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor="#059669",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=save_em,
                    ),
                ],
            )
            page.show_dialog(dlg)

        elif field_key == "allergies":
            al_tf = ft.TextField(
                label="Allergies",
                value=p.get("allergies", "None"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )
            cd_tf = ft.TextField(
                label="Conditions",
                value=p.get("conditions", "None"),
                border=ft.OutlineInputBorder(border_radius=10),
                dense=True,
                height=48,
            )

            def save_alc(_ev: Any) -> None:
                update_user_profile(user_key, {
                    "allergies": (al_tf.value or "None").strip(),
                    "conditions": (cd_tf.value or "None").strip(),
                })
                refresh_vitals()
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HEALTH_AND_SAFETY_ROUNDED, color="#D97706", size=22),
                        ft.Text(i18n.t("profile_allergies_conditions"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                    ],
                    spacing=8,
                ),
                content=ft.Container(
                    width=300,
                    content=ft.Column([al_tf, cd_tf], tight=True, spacing=10),
                ),
                actions=[
                    ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text(i18n.t("save"), color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor="#D97706",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=save_alc,
                    ),
                ],
            )
            page.show_dialog(dlg)

    def open_full_edit_dialog(_e: Any) -> None:
        p = get_user_profile(user_key)
        blood_dropdown = ft.Dropdown(
            label=i18n.t("profile_blood_group"),
            value=p.get("blood_group", "O+"),
            options=[ft.dropdown.Option(bg) for bg in BLOOD_GROUPS],
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        age_field = ft.TextField(
            label=i18n.t("profile_age"),
            value=p.get("age", "28"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        gender_dropdown = ft.Dropdown(
            label=i18n.t("profile_gender"),
            value=p.get("gender", "Male"),
            options=[ft.dropdown.Option(g) for g in GENDERS],
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        weight_field = ft.TextField(
            label=i18n.t("profile_weight"),
            value=p.get("weight", "68 kg"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        height_field = ft.TextField(
            label=i18n.t("profile_height"),
            value=p.get("height", "172 cm"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        emergency_field = ft.TextField(
            label=i18n.t("profile_emergency_phone"),
            value=p.get("emergency_contact", "+880 1712-345678"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        allergies_field = ft.TextField(
            label="Allergies",
            value=p.get("allergies", "None"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )
        conditions_field = ft.TextField(
            label="Conditions",
            value=p.get("conditions", "None"),
            border=ft.OutlineInputBorder(border_radius=10),
            height=48,
            dense=True,
        )

        def save_changes(_ev: Any) -> None:
            updated = {
                "blood_group": blood_dropdown.value or "O+",
                "age": (age_field.value or "28").strip(),
                "gender": gender_dropdown.value or "Male",
                "weight": (weight_field.value or "68 kg").strip(),
                "height": (height_field.value or "172 cm").strip(),
                "emergency_contact": (emergency_field.value or "+880 1712-345678").strip(),
                "allergies": (allergies_field.value or "None").strip(),
                "conditions": (conditions_field.value or "None").strip(),
            }
            update_user_profile(user_key, updated)
            refresh_vitals()
            try:
                page.pop_dialog()
            except Exception:
                pass

        edit_dlg = ft.AlertDialog(
            shape=ft.RoundedRectangleBorder(radius=18),
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=TITLE_NAVY, size=22),
                    ft.Text(i18n.t("profile_edit_title"), size=15, weight=ft.FontWeight.BOLD, color=TITLE_NAVY),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=310,
                content=ft.Column(
                    controls=[
                        ft.Row([ft.Container(blood_dropdown, expand=1), ft.Container(age_field, expand=1)], spacing=6),
                        ft.Row([ft.Container(gender_dropdown, expand=1), ft.Container(weight_field, expand=1)], spacing=6),
                        ft.Row([ft.Container(height_field, expand=1), ft.Container(emergency_field, expand=1)], spacing=6),
                        allergies_field,
                        conditions_field,
                    ],
                    tight=True,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton(content=ft.Text(i18n.t("cancel")), on_click=lambda _e: page.pop_dialog()),
                ft.Button(
                    content=ft.Text(i18n.t("profile_save_btn"), color=WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=GREEN if role == "patient" else ORANGE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=save_changes,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(edit_dlg)

    # 1. Top Bar with close button
    top_bar = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.BADGE_ROUNDED,
                        color=theme_color,
                        size=18,
                    ),
                    ft.Text(
                        i18n.t("profile_caregiver_title") if role == "caretaker" else i18n.t("profile_patient_title"),
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_NAVY,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.IconButton(
                icon=ft.Icons.CLOSE_ROUNDED,
                icon_color=MUTED,
                icon_size=18,
                tooltip=i18n.t("close"),
                on_click=lambda _e: on_close() if on_close else page.pop_dialog(),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # 2. Hero Identity Card (Avatar + Name + Email + Role)
    hero_card = ft.Container(
        bgcolor="#F0FDF4" if role == "patient" else "#FFF7ED",
        border=ft.Border.all(1, "#DCFCE7" if role == "patient" else "#FFEDD5"),
        border_radius=14,
        padding=ft.Padding(10, 8, 10, 8),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=21,
                    bgcolor=theme_color,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        initials_str,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=WHITE,
                    ),
                ),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    name_str,
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_NAVY,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                                ft.Container(
                                    bgcolor=theme_color,
                                    border_radius=8,
                                    padding=ft.Padding(6, 2, 6, 2),
                                    content=ft.Text(
                                        role_label,
                                        size=9,
                                        weight=ft.FontWeight.BOLD,
                                        color=WHITE,
                                    ),
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.EMAIL_OUTLINED, size=12, color=MUTED),
                                ft.Text(
                                    email_str,
                                    size=11,
                                    color=MUTED,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # 3. Health & Medical Vitals (Tap any option to edit directly)
    vitals_header = ft.Row(
        controls=[
            ft.Row(
                [
                    ft.Icon(ft.Icons.FAVORITE_ROUNDED, color="#EF4444", size=15),
                    ft.Text(
                        i18n.t("profile_health_vitals"),
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_NAVY,
                    ),
                ],
                spacing=5,
            ),
            ft.Text("(Tap to edit)", size=9, color=MUTED, italic=True),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Tile 1: Blood Group (Click to edit directly)
    tile_blood = ft.Container(
        expand=True,
        bgcolor="#FEF2F2",
        border=ft.Border.all(1, "#FECACA"),
        border_radius=12,
        padding=ft.Padding(6, 4, 6, 4),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color="#EF4444", size=16),
                    alignment=ft.Alignment.CENTER,
                    width=18,
                ),
                ft.Column(
                    controls=[
                        ft.Text(i18n.t("profile_blood_group"), size=9, color=MUTED, weight=ft.FontWeight.W_500, no_wrap=True),
                        blood_val_text,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _e: open_single_field_dialog("blood_group"),
        tooltip="Click to change Blood Group",
    )

    # Tile 2: Age & Gender (Click to edit directly)
    tile_age_gender = ft.Container(
        expand=True,
        bgcolor="#EFF6FF",
        border=ft.Border.all(1, "#BFDBFE"),
        border_radius=12,
        padding=ft.Padding(6, 4, 6, 4),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.PERSON_ROUNDED, color="#2563EB", size=16),
                    alignment=ft.Alignment.CENTER,
                    width=18,
                ),
                ft.Column(
                    controls=[
                        ft.Text(i18n.t("profile_age_gender"), size=9, color=MUTED, weight=ft.FontWeight.W_500, no_wrap=True),
                        age_gender_text,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _e: open_single_field_dialog("age_gender"),
        tooltip="Click to edit Age & Gender",
    )

    # Tile 3: Weight & Height (Click to edit directly)
    tile_weight_height = ft.Container(
        expand=True,
        bgcolor="#F5F3FF",
        border=ft.Border.all(1, "#DDD6FE"),
        border_radius=12,
        padding=ft.Padding(6, 4, 6, 4),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.MONITOR_WEIGHT_ROUNDED, color="#7C3AED", size=16),
                    alignment=ft.Alignment.CENTER,
                    width=18,
                ),
                ft.Column(
                    controls=[
                        ft.Text(i18n.t("profile_weight_height"), size=9, color=MUTED, weight=ft.FontWeight.W_500, no_wrap=True),
                        weight_height_text,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _e: open_single_field_dialog("weight_height"),
        tooltip="Click to edit Weight & Height",
    )

    # Tile 4: Emergency Contact (Click to edit directly)
    tile_emergency = ft.Container(
        expand=True,
        bgcolor="#ECFDF5",
        border=ft.Border.all(1, "#A7F3D0"),
        border_radius=12,
        padding=ft.Padding(6, 4, 6, 4),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.PHONE_IN_TALK_ROUNDED, color="#059669", size=16),
                    alignment=ft.Alignment.CENTER,
                    width=18,
                ),
                ft.Column(
                    controls=[
                        ft.Text(i18n.t("profile_emergency_phone"), size=9, color=MUTED, weight=ft.FontWeight.W_500, no_wrap=True),
                        emergency_val_text,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _e: open_single_field_dialog("emergency"),
        tooltip="Click to edit Emergency Contact",
    )

    # Tile 5: Allergies & Conditions (Click to edit directly)
    tile_allergies = ft.Container(
        bgcolor="#FFFBEB",
        border=ft.Border.all(1, "#FDE68A"),
        border_radius=12,
        padding=ft.Padding(10, 6, 10, 6),
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.HEALTH_AND_SAFETY_ROUNDED, color="#D97706", size=18),
                ft.Column(
                    controls=[
                        ft.Text(i18n.t("profile_allergies_conditions"), size=9, color=MUTED, weight=ft.FontWeight.W_500),
                        allergies_val_text,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _e: open_single_field_dialog("allergies"),
        tooltip="Click to edit Allergies & Conditions",
    )

    # 4. Connection / Pairing Section
    pairing_card = None
    if role == "patient":
        cur_code = code_display_value or "------"
        code_label = ft.Text(
            cur_code,
            size=15,
            weight=ft.FontWeight.BOLD,
            color=SCHEDULE_NAVY,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        def handle_gen_code(_e: Any) -> None:
            if on_generate_code:
                res = on_generate_code()
                if asyncio.iscoroutine(res):
                    async def _run_and_refresh() -> None:
                        await res
                        if code_display_control and hasattr(code_display_control, "value"):
                            code_label.value = code_display_control.value
                        try:
                            card_container.update()
                        except Exception:
                            pass
                    try:
                        p = page
                        if p and hasattr(p, "run_task"):
                            p.run_task(_run_and_refresh)
                    except Exception:
                        pass
                else:
                    if code_display_control and hasattr(code_display_control, "value"):
                        code_label.value = code_display_control.value
                    try:
                        card_container.update()
                    except Exception:
                        pass

        pairing_card = ft.Container(
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=12,
            padding=ft.Padding(10, 6, 10, 6),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(i18n.t("profile_pairing_code"), size=9, color=MUTED, weight=ft.FontWeight.W_500),
                            code_label,
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Button(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.KEY_ROUNDED, size=13, color=WHITE),
                                ft.Text(i18n.t("profile_generate_code"), size=10, color=WHITE, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=3,
                        ),
                        bgcolor=SCHEDULE_NAVY,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        height=30,
                        on_click=handle_gen_code,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
    else:
        # Caregiver linked patient
        patient_str = active_patient_name or i18n.t("no_patient_connected")
        pairing_card = ft.Container(
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=12,
            padding=ft.Padding(10, 6, 10, 6),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(i18n.t("profile_linked_patient"), size=9, color=MUTED, weight=ft.FontWeight.W_500),
                            ft.Text(patient_str, size=13, weight=ft.FontWeight.BOLD, color=TITLE_NAVY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Button(
                        content=ft.Text(i18n.t("profile_connect_patient"), size=10, color=WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ORANGE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        height=30,
                        on_click=lambda _e: on_connect_patient() if on_connect_patient else None,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # 5. Bottom Action Buttons (Edit Health Info + Log Out)
    async def handle_logout(_e: Any) -> None:
        try:
            page.pop_dialog()
        except Exception:
            pass
        if on_logout:
            res = on_logout()
            if asyncio.iscoroutine(res):
                await res

    btn_edit = ft.Button(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.EDIT_ROUNDED, size=14, color=WHITE),
                ft.Text(i18n.t("profile_edit_btn"), size=11, weight=ft.FontWeight.BOLD, color=WHITE),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=CYAN,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        height=36,
        expand=True,
        on_click=open_full_edit_dialog,
    )

    btn_logout = ft.Button(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.LOGOUT_ROUNDED, size=14, color=WHITE),
                ft.Text(i18n.t("profile_logout_btn"), size=11, weight=ft.FontWeight.BOLD, color=WHITE),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=RED,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        height=36,
        expand=True,
        on_click=handle_logout,
    )

    action_row = ft.Row(
        controls=[btn_edit, btn_logout],
        spacing=8,
    )

    # Assemble the responsive card
    card_container.content = ft.Column(
        controls=[
            top_bar,
            hero_card,
            vitals_header,
            ft.Row([tile_blood, tile_age_gender], spacing=6),
            ft.Row([tile_weight_height, tile_emergency], spacing=6),
            tile_allergies,
            pairing_card,
            ft.Container(height=2),
            action_row,
        ],
        tight=True,
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )
    card_container.width = width
    card_container.height = 490
    card_container.bgcolor = WHITE
    card_container.border_radius = 20
    card_container.padding = ft.Padding(12, 10, 12, 12)
    return card_container


def show_oriented_profile_dialog(
    page: ft.Page,
    user: Dict[str, Any],
    role: str = "patient",
    code_display_value: Optional[str] = None,
    code_display_control: Optional[Any] = None,
    on_generate_code: Optional[Callable[[], Any]] = None,
    on_connect_patient: Optional[Callable[[], Any]] = None,
    active_patient_name: Optional[str] = None,
    on_logout: Optional[Callable[[], Any]] = None,
) -> None:
    """Display the oriented profile dialog."""
    card = build_profile_card(
        page=page,
        user=user,
        role=role,
        code_display_value=code_display_value,
        code_display_control=code_display_control,
        on_generate_code=on_generate_code,
        on_connect_patient=on_connect_patient,
        active_patient_name=active_patient_name,
        on_logout=on_logout,
        on_close=lambda: page.pop_dialog(),
        width=340,
    )
    dlg = ft.AlertDialog(
        content=card,
        content_padding=ft.Padding(0, 0, 0, 0),
        shape=ft.RoundedRectangleBorder(radius=18),
        bgcolor=WHITE,
    )
    page.show_dialog(dlg)
