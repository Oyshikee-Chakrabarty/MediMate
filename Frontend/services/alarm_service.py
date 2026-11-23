"""AlarmService — Local dose reminder alarm engine with audio chime and visual dialog."""

from __future__ import annotations

import asyncio
import atexit
from datetime import datetime, timedelta
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

import flet as ft

from components.common import get_asset_path, safe_update, toast
from config import BLUE, CARD_BG_BLUE, CARD_BORDER_BLUE, CYAN, GREEN, MUTED, ORANGE, RED, SCHEDULE_NAVY, TEXT, TITLE_NAVY, WHITE

logger = logging.getLogger(__name__)


class AlarmRinger:
    """Thread-safe, singleton medical chime audio engine with auto-timeout and instant stop."""

    _instance: Optional[AlarmRinger] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> AlarmRinger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._stop_event = threading.Event()
                cls._instance._thread = None
                cls._instance._is_ringing = False
            return cls._instance

    @property
    def is_ringing(self) -> bool:
        return self._is_ringing

    @classmethod
    def stop_all(cls) -> None:
        """Globally stop all active alarm sound across the entire process immediately."""
        if cls._instance is not None:
            cls._instance.stop()

    def start(self, max_duration_sec: float = 25.0) -> None:
        """Start playing the melodic alert chime with thread-safety and auto-timeout."""
        with self._lock:
            self.stop()
            self._stop_event.clear()
            self._is_ringing = True

            def _loop() -> None:
                start_time = time.time()
                while not self._stop_event.is_set():
                    # Auto-silence after max_duration_sec to prevent infinite chime loops
                    if time.time() - start_time >= max_duration_sec:
                        break
                    try:
                        import winsound
                        if self._stop_event.is_set():
                            break
                        winsound.Beep(988, 150)
                        if self._stop_event.is_set():
                            break
                        winsound.Beep(1318, 180)
                        if self._stop_event.is_set():
                            break
                        winsound.Beep(1568, 250)
                    except Exception:
                        print("\a", flush=True)

                    # Interruptible pause between chime iterations (exits instantly on stop)
                    if self._stop_event.wait(timeout=1.2):
                        break

                self._is_ringing = False

            self._thread = threading.Thread(target=_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Immediately and permanently signal the ringer thread to halt."""
        self._stop_event.set()
        self._is_ringing = False


atexit.register(AlarmRinger.stop_all)


class AlarmService:
    """Monitors scheduled dose times and fires local auditory + visual alarms."""

    def __init__(
        self,
        page: ft.Page,
        api: Api,
        role: str = "patient",
        user: Optional[Dict[str, Any]] = None,
        target_patient_id: Optional[str] = None,
        on_status_updated: Optional[Callable[[], None]] = None,
    ) -> None:
        self._page: ft.Page = page
        self._api: Api = api
        self._role: str = role
        self._user: Dict[str, Any] = user or {}
        self._target_patient_id: Optional[str] = target_patient_id
        self._on_status_updated: Optional[Callable[[], None]] = on_status_updated

        self._ringer: AlarmRinger = AlarmRinger()
        self._running: bool = False
        self._is_dialog_open: bool = False
        self._current_dialog: Optional[ft.AlertDialog] = None
        self._fired_keys: Set[str] = set()
        self._handled_today_sched_ids: Set[str] = set()
        self._snoozed_until: Dict[str, datetime] = {}
        self._task: Optional[asyncio.Task] = None

        # In-memory cached schedule & medication data to prevent constant HTTP polling
        self._cached_scheds: List[Dict[str, Any]] = []
        self._cached_med_map: Dict[str, Dict[str, Any]] = {}
        self._cached_doses: List[Dict[str, Any]] = []
        self._last_fetch_time: Optional[datetime] = None

    def invalidate_cache(self) -> None:
        """Invalidate in-memory cache to force refresh on next check."""
        self._last_fetch_time = None

    def set_target_patient_id(self, patient_id: Optional[str]) -> None:
        if self._target_patient_id != patient_id:
            self._target_patient_id = patient_id
            self.invalidate_cache()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if hasattr(self._page, "run_task"):
            try:
                self._page.run_task(self._check_loop)
            except Exception as exc:
                logger.debug("Could not start alarm loop via run_task: %s", exc)

    def dismiss_alarm(self) -> None:
        """Immediately stop all audio chime and close alarm dialog."""
        AlarmRinger.stop_all()
        self._ringer.stop()
        self._is_dialog_open = False
        if hasattr(self._page, "pop_dialog"):
            try:
                self._page.pop_dialog()
            except Exception:
                pass
        if getattr(self, "_current_dialog", None) is not None:
            try:
                self._current_dialog.open = False
                safe_update(self._current_dialog)
            except Exception:
                pass
            self._current_dialog = None

    def mark_schedule_handled(self, sched_id: str, status: str = "taken") -> None:
        """Record in local memory that this schedule has been handled for today."""
        if not sched_id:
            return
        self._handled_today_sched_ids.add(sched_id)
        self._snoozed_until.pop(sched_id, None)
        today_str = datetime.now().strftime("%Y-%m-%d")
        for k in list(self._fired_keys):
            if k.startswith(sched_id):
                self._fired_keys.add(k)
        for d in self._cached_doses:
            if d.get("schedule_id") == sched_id:
                d["status"] = status
        AlarmRinger.stop_all()
        self._ringer.stop()

    def stop(self) -> None:
        self._running = False
        self.dismiss_alarm()

    async def _check_loop(self) -> None:
        while self._running:
            try:
                await self._check_pending_doses()
            except Exception as exc:
                logger.debug("Alarm check error: %s", exc)
            await asyncio.sleep(2.0)

    async def _check_pending_doses(self) -> None:
        # Caregivers receive notifications, not audible local clock alarms
        if self._role == "caretaker":
            return
        if self._is_dialog_open or not self._api.token:
            return

        now = datetime.now()
        current_hm = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        weekday_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        today_code = weekday_names[now.weekday()]

        cache_expired = (
            self._last_fetch_time is None
            or (now - self._last_fetch_time).total_seconds() > 60
        )
        if cache_expired:
            try:
                self._cached_scheds = await asyncio.to_thread(
                    self._api.list_schedules, None, self._target_patient_id
                )
                meds = await asyncio.to_thread(
                    self._api.list_medications, self._target_patient_id
                )
                self._cached_med_map = {m["id"]: m for m in meds}
                try:
                    self._cached_doses = await asyncio.to_thread(
                        self._api.get_todays_doses, self._target_patient_id
                    )
                except Exception:
                    self._cached_doses = []
                self._last_fetch_time = now
            except Exception as exc:
                logger.debug("Alarm cache refresh failed: %s", exc)
                return

        scheds = self._cached_scheds
        med_map = self._cached_med_map
        doses = self._cached_doses
        if not scheds:
            return

        for sched in scheds:
            sched_id: str = sched.get("id", "")
            if not sched_id or sched_id in self._handled_today_sched_ids:
                continue

            days = sched.get("days_of_week", "daily").strip()
            runs_today = (
                days.lower() == "daily"
                or today_code in [d.strip().upper() for d in days.split(",")]
            )
            if not runs_today:
                continue
            due_time_raw: str = sched.get("due_time", "09:00:00")
            due_hm = due_time_raw[:5]

            # Check if there is an existing dose event for this schedule today
            dose = next((d for d in doses if d.get("schedule_id") == sched_id), None)
            if dose is not None and dose.get("status") in ("taken", "skipped"):
                continue

            # Check snooze
            snooze_time = self._snoozed_until.get(sched_id)
            if snooze_time is not None:
                if now < snooze_time:
                    continue
                # Snooze expired! Trigger alarm
                self._snoozed_until.pop(sched_id, None)
                self.fire_alarm(sched, med_map.get(sched.get("medication_id", "")), dose)
                return

            # Check if already fired today
            alarm_key = f"{sched_id}_{today_str}_{due_hm}"
            if alarm_key in self._fired_keys:
                continue

            # Check if due now:
            try:
                due_h, due_m = int(due_hm.split(":")[0]), int(due_hm.split(":")[1])
                due_dt = now.replace(hour=due_h, minute=due_m, second=0, microsecond=0)
                diff = (now - due_dt).total_seconds()
                # Fire if due right now or within the past 15 minutes if unacknowledged
                if 0 <= diff <= 900:
                    self._fired_keys.add(alarm_key)
                    self.fire_alarm(sched, med_map.get(sched.get("medication_id", "")), dose)
                    return
            except Exception:
                if due_hm == current_hm:
                    self._fired_keys.add(alarm_key)
                    self.fire_alarm(sched, med_map.get(sched.get("medication_id", "")), dose)
                    return

    def test_alarm(self) -> None:
        """Manually trigger alarm for testing chime and UI."""
        fake_sched = {
            "id": "test_schedule",
            "medication_id": "test_med",
            "due_time": datetime.now().strftime("%H:%M:%S"),
            "days_of_week": "daily",
        }
        fake_med = {
            "id": "test_med",
            "name": "Demo Medication",
            "dosage": "500mg",
            "form": "Tablet",
            "disease": "Test Alarm",
            "notes": "Testing alarm sound and visual popup notification.",
        }
        self.fire_alarm(fake_sched, fake_med, None, is_test=True)

    def fire_alarm(
        self,
        sched: Dict[str, Any],
        med: Optional[Dict[str, Any]],
        dose: Optional[Dict[str, Any]] = None,
        is_test: bool = False,
    ) -> None:
        if self._is_dialog_open:
            return
        self._is_dialog_open = True
        self._ringer.start()

        sched_id = sched.get("id", "")
        med = med or {}
        med_name = med.get("name", "Prescription Medicine")
        dosage = med.get("dosage", "")
        form = med.get("form", "Tablet")
        disease = med.get("disease", "")
        notes = med.get("notes", "")

        dose_label = f"1 {form}" if form else "1 Dose"
        if dosage:
            dose_label = f"{dose_label} • {dosage}"

        raw_time = sched.get("due_time", "09:00:00")
        try:
            t = datetime.strptime(raw_time, "%H:%M:%S")
            time_display = t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            try:
                t = datetime.strptime(raw_time, "%H:%M")
                time_display = t.strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_display = raw_time[:5]

        dose_id = dose.get("id") if dose else None

        def take_now(_e: Any) -> None:
            self.mark_schedule_handled(sched_id, "taken")
            self.dismiss_alarm()
            def _bg_take() -> None:
                target_dose_id = dose_id
                if not target_dose_id and not is_test:
                    try:
                        latest_doses = self._api.get_todays_doses(self._target_patient_id)
                        d = next((x for x in latest_doses if x.get("schedule_id") == sched_id), None)
                        if d:
                            target_dose_id = d.get("id")
                    except Exception:
                        pass
                if target_dose_id and not is_test:
                    try:
                        self._api.set_dose_status(target_dose_id, "taken")
                    except Exception as exc:
                        logger.debug("Failed setting dose status: %s", exc)
                toast(self._page, f"Marked {med_name} as taken! Stock updated.")
                if self._on_status_updated:
                    try:
                        self._on_status_updated()
                    except Exception:
                        pass
            threading.Thread(target=_bg_take, daemon=True).start()

        def snooze(_e: Any) -> None:
            self.dismiss_alarm()
            self._snoozed_until[sched_id] = datetime.now() + timedelta(minutes=5)
            toast(self._page, "Alarm snoozed for 5 minutes.")

        def skip(_e: Any) -> None:
            self.mark_schedule_handled(sched_id, "skipped")
            self.dismiss_alarm()
            def _bg_skip() -> None:
                target_dose_id = dose_id
                if not target_dose_id and not is_test:
                    try:
                        latest_doses = self._api.get_todays_doses(self._target_patient_id)
                        d = next((x for x in latest_doses if x.get("schedule_id") == sched_id), None)
                        if d:
                            target_dose_id = d.get("id")
                    except Exception:
                        pass
                if target_dose_id and not is_test:
                    try:
                        self._api.set_dose_status(target_dose_id, "skipped")
                    except Exception as exc:
                        logger.debug("Failed setting dose status: %s", exc)
                toast(self._page, f"Marked {med_name} as skipped.")
                if self._on_status_updated:
                    try:
                        self._on_status_updated()
                    except Exception:
                        pass
            threading.Thread(target=_bg_skip, daemon=True).start()

        def dismiss(_e: Any) -> None:
            self.mark_schedule_handled(sched_id, "dismissed")
            self.dismiss_alarm()

        # Build visually commanding Alarm Modal
        med_card_content = [
            ft.Text(med_name, size=22, weight=ft.FontWeight.BOLD, color=SCHEDULE_NAVY),
            ft.Text(dose_label, size=16, color="#475569", weight=ft.FontWeight.W_500),
        ]
        if disease:
            med_card_content.append(
                ft.Container(
                    content=ft.Text(disease, size=12, weight=ft.FontWeight.BOLD, color=WHITE),
                    bgcolor=CYAN,
                    border_radius=8,
                    padding=ft.Padding(10, 4, 10, 4),
                )
            )
        if notes:
            med_card_content.append(
                ft.Text(f"Note: {notes}", size=13, italic=True, color="#64748B")
            )

        alarm_dialog = ft.AlertDialog(
            modal=True,
            on_dismiss=lambda _e: self.dismiss_alarm(),
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ALARM_ON, color=RED, size=32),
                    ft.Text(
                        "DOSE REMINDER ALARM",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_NAVY,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ACCESS_TIME_FILLED, color=WHITE, size=20),
                                ft.Text(
                                    f"Scheduled for {time_display}",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=WHITE,
                                ),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        bgcolor=SCHEDULE_NAVY,
                        border_radius=12,
                        padding=ft.Padding(14, 8, 14, 8),
                        width=320,
                    ),
                    ft.Container(
                        bgcolor=CARD_BG_BLUE,
                        border=ft.Border.all(1.5, CARD_BORDER_BLUE),
                        border_radius=18,
                        padding=16,
                        width=320,
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=med_card_content,
                                    spacing=6,
                                    expand=True,
                                ),
                                ft.Image(
                                    src=get_asset_path("pill_icon.png"),
                                    width=52,
                                    height=52,
                                    fit=ft.BoxFit.CONTAIN,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Container(height=4),
                    # TAKE NOW Button
                    ft.Button(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color=WHITE, size=22),
                                ft.Text("TAKE NOW", size=16, weight=ft.FontWeight.BOLD, color=WHITE),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        bgcolor="#27AE60",
                        color=WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=16)),
                        height=50,
                        width=320,
                        on_click=take_now,
                    ),
                    # SNOOZE (5 MIN) Button
                    ft.Button(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SNOOZE, color=WHITE, size=18),
                                ft.Text("SNOOZE (5 MIN)", size=14, weight=ft.FontWeight.BOLD, color=WHITE),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        bgcolor=ORANGE,
                        color=WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
                        height=42,
                        width=320,
                        on_click=snooze,
                    ),
                    # SKIP DOSE Button
                    ft.Row(
                        controls=[
                            ft.Button(
                                content=ft.Text("Skip this dose", size=13, color=RED, weight=ft.FontWeight.BOLD),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT),
                                on_click=skip,
                            ),
                            ft.Button(
                                content=ft.Text("Dismiss", size=13, color=MUTED),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT),
                                on_click=dismiss,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        width=320,
                    ),
                ],
                tight=True,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=320,
            ),
        )
        self._current_dialog = alarm_dialog
        if hasattr(self._page, "show_dialog"):
            try:
                self._page.show_dialog(alarm_dialog)
            except Exception as exc:
                logger.debug("Could not show alarm dialog: %s", exc)
