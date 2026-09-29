"""AuthView — Pixel-perfect Login & Sign Up screen matching PNG 1 & PNG 2."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List

import flet as ft

from components.common import error_text, get_asset_path, safe_update, toast
from config import (
    BLUE,
    FIELD_WIDTH,
    FONT,
    INPUT_BG,
    INPUT_TEXT,
    MUTED,
    TITLE_NAVY,
    WHITE,
)
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
            width=380,
        )
        self._page_ref: ft.Page = page
        self._api: Api = api
        self._on_logged_in: Callable[[str, Dict[str, Any]], None] = on_logged_in

        # ---- Top Header Banner with circles & MediMate 'M' logo ---------- #
        self.banner: ft.Container = ft.Container(
            content=ft.Image(
                src=get_asset_path("auth_header_curved.png"),
                width=380,
                fit=ft.BoxFit.FIT_WIDTH,
            ),
            width=380,
            margin=ft.Margin(0, 0, 0, 4),
        )

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
            border_radius=18,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.role_choice: ft.Dropdown = ft.Dropdown(
            width=FIELD_WIDTH,
            border_radius=18,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
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
            border_radius=18,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(18, 14, 18, 14),
            text_style=ft.TextStyle(size=16, color=INPUT_TEXT, weight=ft.FontWeight.W_500),
            cursor_color=BLUE,
        )

        self.password_field: ft.TextField = ft.TextField(
            hint_text="******",
            password=True,
            can_reveal_password=True,
            width=FIELD_WIDTH,
            border_radius=18,
            bgcolor=INPUT_BG,
            border=ft.InputBorder.NONE,
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
        self.controls.clear()
        if show_register:
            self.title.value = "Sign up"
            self.subtitle.value = "Sign in to continue."
            self.switch_link.content = ft.Text("Already have an account? Log in", size=14, color=MUTED)
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
                    ft.Container(height=24),
                ]
            )
        else:
            self.title.value = "Log in"
            self.subtitle.value = "Log in to continue."
            self.switch_link.content = ft.Text("Signup !", size=14, color=MUTED, weight=ft.FontWeight.W_500)
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
                    ft.Container(height=36),
                ]
            )
        self._set_error("")

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
            self._set_error("All fields are required.")
            return

        try:
            token: Dict[str, Any] = await asyncio.to_thread(
                self._api.register, name, email, password, role
            )
        except ApiError as exc:
            self._set_error(exc.detail)
            return

        self._api.save_token(token["access_token"])
        toast(self._page_ref, f"Welcome, {name}!")
        self._on_logged_in(role, token["user"])

    async def on_login(self, *_args: Any) -> None:
        self._set_error("")
        email: str = (self.email_field.value or "").strip()
        password: str = self.password_field.value or ""
        if not email or not password:
            self._set_error("Email and password are required.")
            return
        try:
            token: Dict[str, Any] = await asyncio.to_thread(self._api.login, email, password)
        except ApiError as exc:
            self._set_error(exc.detail)
            return
        self._api.save_token(token["access_token"])
        user: Dict[str, Any] = token["user"]
        toast(self._page_ref, f"Welcome back, {user.get('name', '')}!")
        self._on_logged_in(user.get("role", "patient"), user)
