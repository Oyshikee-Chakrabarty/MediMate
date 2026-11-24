"""AuthView — Pixel-perfect Login & Sign Up screen matching PNG 1 & PNG 2."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List

import flet as ft

from components.common import build_language_toggle, error_text, get_asset_path, safe_update, toast
from config import (
    APP_WIDTH,
    BLUE,
    BUTTON_HEIGHT,
    FIELD_WIDTH,
    FONT,
    INPUT_BG,
    INPUT_TEXT,
    MUTED,
    TITLE_NAVY,
    WHITE,
)
from services import i18n
from services.api_client import Api, ApiError


class AuthView(ft.Column):
    """Combined register / login card styled identically to PNG 1 and PNG 2."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        on_logged_in: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        super().__init__(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=APP_WIDTH,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._on_logged_in: Callable[[str, Dict[str, Any]], None] = on_logged_in

        # ---- Language Toggle (placed at bottom of screen) --------------- #
        self.lang_toggle: ft.Container = build_language_toggle(
            on_toggle=self._on_lang_changed,
            api=self._api,
            bg_color="#E0F2FE",
            text_color=TITLE_NAVY,
            border_color="#BAE6FD",
        )
        self.bottom_bar: ft.Container = ft.Container(
            content=self.lang_toggle,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(0, 8, 0, 16),
            width=FIELD_WIDTH,
        )
        self.top_bar: ft.Container = self.bottom_bar

        # ---- Top Header Banner with circles & MediMate 'M' logo ---------- #
        self.banner: ft.Container = self._build_banner()

        # ---- Title & Subtitle ------------------------------------------- #
        self.title: ft.Text = ft.Text(
            "Sign up",
            size=36,
            weight=ft.FontWeight.BOLD,
            color=TITLE_NAVY,
            text_align=ft.TextAlign.CENTER,
        )
        self.subtitle: ft.Text = ft.Text(
            "Sign in to continue.",
            size=14,
            color=MUTED,
            text_align=ft.TextAlign.CENTER,
        )

        # ---- Field Labels ----------------------------------------------- #
        self.name_label: ft.Container = self._make_label("NAME")
        self.role_label: ft.Container = self._make_label("ROLE")
        self.email_label: ft.Container = self._make_label("E-MAIL")
        self.password_label: ft.Container = self._make_label("PASSWORD")

        # ---- Inputs ----------------------------------------------------- #
        self.name_field: ft.TextField = ft.TextField(
            hint_text="e.g. Oyshikee Sithee",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=18, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.role_choice: ft.Dropdown = ft.Dropdown(
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=18, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            color=INPUT_TEXT,
            value="caretaker",
            options=[
                ft.DropdownOption(key="patient", text="Patient"),
                ft.DropdownOption(key="caretaker", text="Caretaker"),
            ],
        )

        self.email_field: ft.TextField = ft.TextField(
            hint_text="e.g. sithee123@gmail.com",
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=18, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.password_field: ft.TextField = ft.TextField(
            hint_text="******",
            password=True,
            can_reveal_password=True,
            width=FIELD_WIDTH,
            bgcolor=INPUT_BG,
            border=ft.OutlineInputBorder(border_radius=18, side=ft.BorderSide(width=0, color=ft.Colors.TRANSPARENT)),
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.error: ft.Text = error_text("")
        self.error.visible = False

        # ---- Action Buttons --------------------------------------------- #
        self.register_btn: ft.Button = ft.Button(
            content=ft.Text("Sign up", size=16, weight=ft.FontWeight.BOLD),
            width=FIELD_WIDTH,
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=16)),
            bgcolor="#009FD9",
            color=WHITE,
            on_click=self.on_register,
        )

        self.login_btn: ft.Button = ft.Button(
            content=ft.Text("Log in", size=16, weight=ft.FontWeight.BOLD),
            width=FIELD_WIDTH,
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=16)),
            bgcolor=BLUE,
            color=WHITE,
            on_click=self.on_login,
        )

        self.switch_link: ft.TextButton = ft.TextButton(
            content=ft.Text("Already have an account? Log in", size=14, color=MUTED),
            on_click=self.toggle,
        )

        # ---- assemble initial (register) form --------------------------- #
        self._show_register: bool = False
        self._render(show_register=True)

    def _build_banner(self) -> ft.Container:
        return ft.Container(
            content=ft.Image(
                src=get_asset_path("auth_header_curved.png"),
                width=FIELD_WIDTH,
                height=160,
                fit=ft.BoxFit.FIT_WIDTH,
                error_content=ft.Container(
                    content=ft.Image(
                        src=get_asset_path("logo.png"),
                        width=100,
                        height=100,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    alignment=ft.Alignment.CENTER,
                    height=160,
                ),
            ),
            width=FIELD_WIDTH,
            height=160,
            alignment=ft.Alignment.CENTER,
            margin=ft.Margin(0, 0, 0, 4),
        )

    def _make_label(self, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                text,
                size=12,
                weight=ft.FontWeight.BOLD,
                color=MUTED,
            ),
            width=FIELD_WIDTH,
            alignment=ft.Alignment.CENTER_LEFT,
            padding=ft.Padding(6, 6, 6, 2),
        )

    # -- form swapping -------------------------------------------------- #
    def _render(self, show_register: bool) -> None:
        """(Re)build the controls list for the requested form."""
        self._show_register = show_register
        self.banner = self._build_banner()
        self.controls.clear()

        # Update dynamic labels based on active language
        self.name_label.content.value = i18n.t("name")
        self.role_label.content.value = i18n.t("role")
        self.email_label.content.value = i18n.t("email")
        self.password_label.content.value = i18n.t("password")
        self.name_field.hint_text = i18n.t("name_hint")
        self.email_field.hint_text = i18n.t("email_hint")
        self.role_choice.options = [
            ft.DropdownOption(key="patient", text=i18n.t("patient")),
            ft.DropdownOption(key="caretaker", text=i18n.t("caretaker")),
        ]
        self.register_btn.content = ft.Text(i18n.t("sign_up"), size=16, weight=ft.FontWeight.BOLD)
        self.login_btn.content = ft.Text(i18n.t("log_in"), size=16, weight=ft.FontWeight.BOLD)

        if show_register:
            self.title.value = i18n.t("sign_up")
            self.subtitle.value = i18n.t("sign_in_to_continue")
            self.switch_link.content = ft.Text(i18n.t("already_have_account"), size=14, color=MUTED)
            self.controls.extend(
                [
                    self.banner,
                    self.title,
                    self.subtitle,
                    self.error,
                    self.name_label,
                    self.name_field,
                    self.role_label,
                    self.role_choice,
                    self.email_label,
                    self.email_field,
                    self.password_label,
                    self.password_field,
                    ft.Container(height=8),
                    self.register_btn,
                    self.switch_link,
                    ft.Container(height=12),
                    self.bottom_bar,
                    ft.Container(height=16),
                ]
            )
        else:
            self.title.value = i18n.t("log_in")
            self.subtitle.value = i18n.t("log_in_to_continue")
            self.switch_link.content = ft.Text(i18n.t("signup_link"), size=14, color=MUTED, weight=ft.FontWeight.W_500)
            self.controls.extend(
                [
                    self.banner,
                    self.title,
                    self.subtitle,
                    self.error,
                    self.email_label,
                    self.email_field,
                    self.password_label,
                    self.password_field,
                    ft.Container(height=12),
                    self.login_btn,
                    self.switch_link,
                    ft.Container(height=16),
                    self.bottom_bar,
                    ft.Container(height=24),
                ]
            )
        self._set_error("")

    def _on_lang_changed(self, _new_lang: str) -> None:
        """Triggered upon single-click language toggle."""
        self._render(self._show_register)
        safe_update(self)

    def did_mount(self) -> None:
        i18n.register_language_listener(self._on_lang_changed)

    def will_unmount(self) -> None:
        i18n.unregister_language_listener(self._on_lang_changed)

    def toggle(self, *_args: Any) -> None:
        """Switch between Register and Login forms."""
        self._render(not self._show_register)
        safe_update(self)

    # -- error helper ---------------------------------------------------- #
    def _set_error(self, message: str) -> None:
        self.error.value = message
        self.error.visible = bool(message)
        safe_update(self.error)

    # -- handlers (async: never block the UI loop) ----------------------- #
    async def on_register(self, *_args: Any) -> None:
        self._set_error("")
        name: str = (self.name_field.value or "").strip()
        email: str = (self.email_field.value or "").strip()
        password: str = self.password_field.value or ""
        role: str = self.role_choice.value or "patient"

        if not name or not email or not password:
            self._set_error(i18n.t("all_fields_required"))
            return

        current_lang = i18n.get_current_language()
        try:
            token: Dict[str, Any] = await asyncio.to_thread(
                self._api.register, name, email, password, role, current_lang
            )
        except ApiError as exc:
            self._set_error(exc.detail)
            return

        self._api.save_token(token["access_token"])
        toast(self._page_ref, i18n.t("welcome_user", name=name))
        self._on_logged_in(role, token["user"])

    async def on_login(self, *_args: Any) -> None:
        self._set_error("")
        email: str = (self.email_field.value or "").strip()
        password: str = self.password_field.value or ""
        if not email or not password:
            self._set_error(i18n.t("email_password_required"))
            return
        try:
            token: Dict[str, Any] = await asyncio.to_thread(self._api.login, email, password)
        except ApiError as exc:
            self._set_error(exc.detail)
            return
        self._api.save_token(token["access_token"])
        user: Dict[str, Any] = token["user"]
        pref_lang = user.get("preferred_language")
        if pref_lang in ("en", "bn"):
            i18n.set_language(pref_lang, notify=True)
        toast(self._page_ref, i18n.t("welcome_back_user", name=user.get('name', '')))
        self._on_logged_in(user.get("role", "patient"), user)
