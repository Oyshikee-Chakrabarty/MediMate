"""Comprehensive verification for exact minute control (e.g. 3:53 PM) and local alarm firing."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import os
import sys
import uuid
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.api_client import Api
from services.alarm_service import AlarmRinger, AlarmService
from views.schedule_view import _to_24h_time, _parse_minute, _format_time
from views.add_medicine_view import _to_24h_time as add_to_24h, _parse_minute as add_parse_min


class MockPage:
    def __init__(self) -> None:
        self.dialogs: List[Any] = []
        self.popped: int = 0
        self.toasts: List[str] = []

    def show_dialog(self, dlg: Any) -> None:
        self.dialogs.append(dlg)

    def pop_dialog(self) -> None:
        self.popped += 1
        if self.dialogs:
            self.dialogs.pop()

    def run_task(self, coro_fn: Any, *args: Any) -> None:
        # In headless testing, coros can be scheduled on event loop
        asyncio.create_task(coro_fn(*args))


def run_checks() -> None:
    print("== 1. Exact Minute Conversion & Validation ==")
    # 3:53 PM test
    assert _parse_minute("53") == "53"
    assert _to_24h_time("3", "53", "PM") == "15:53:00"
    assert add_parse_min("53") == "53"
    assert add_to_24h("3", "53", "PM") == "15:53:00"
    assert _format_time("15:53:00") == "3:53 PM"

    # Edge cases
    assert _to_24h_time("12", "00", "AM") == "00:00:00"
    assert _to_24h_time("12", "00", "PM") == "12:00:00"
    assert _to_24h_time("11", "59", "PM") == "23:59:00"
    assert _to_24h_time("7", "05", "AM") == "07:05:00"
    print("  [OK] Minute controls and 24h conversion passed for 3:53 PM and edge cases")

    print("== 2. AlarmRinger Melodic Audio Engine ==")
    ringer = AlarmRinger()
    assert not ringer.is_ringing
    ringer.start()
    assert ringer.is_ringing
    time.sleep(0.3)
    ringer.stop()
    assert not ringer.is_ringing
    print("  [OK] AlarmRinger started, played chime, and stopped cleanly")

    print("== 3. Backend Integration with Exact Minute Schedule ==")
    api = Api("http://127.0.0.1:8000")
    suffix = uuid.uuid4().hex[:6]
    res = api.register(
        name=f"Patient {suffix}",
        email=f"patient_{suffix}@test.dev",
        password="pass1234",
        role="patient",
    )
    api.save_token(res["access_token"])
    user = res["user"]
    assert api.token

    # Add medication with exact time 15:53:00 (3:53 PM)
    exact_time = "15:53:00"
    med = api.add_medication(
        name="Lisinopril 10mg",
        stock_qty=30,
        dosage="10mg",
        form="Tablet",
        disease="Blood Pressure",
        notes="Take with water",
        schedule_times=[exact_time],
        schedule_days="daily",
    )
    print(f"  [OK] Medication added with exact schedule: {exact_time}")

    scheds = api.list_schedules(medication_id=med["id"])
    assert len(scheds) == 1
    assert scheds[0]["due_time"] == exact_time
    print(f"  [OK] Schedule recorded in backend: due_time={scheds[0]['due_time']}")

    # Check today's dose events
    doses = api.get_todays_doses()
    assert len(doses) >= 1
    dose = next(d for d in doses if d["schedule_id"] == scheds[0]["id"])
    due_ts = dose["due_timestamp"]
    assert "15:53:00" in due_ts
    print(f"  [OK] Today's dose event generated with exact minute timestamp: {due_ts}")

    print("== 4. AlarmService Pending Dose Check & Alarm Firing ==")
    mock_page = MockPage()
    status_updated_called = [False]

    def on_status_updated():
        status_updated_called[0] = True

    alarm_service = AlarmService(
        page=mock_page,
        api=api,
        role="patient",
        user=user,
        on_status_updated=on_status_updated,
    )

    # Test Alarm Trigger
    alarm_service.test_alarm()
    assert len(mock_page.dialogs) == 1
    assert alarm_service._ringer.is_ringing
    assert alarm_service._is_dialog_open
    print("  [OK] Manual test alarm fired dialog and ringer")

    # Dismiss test alarm
    alarm_service.stop()
    assert not alarm_service._ringer.is_ringing
    assert not alarm_service._is_dialog_open
    print("  [OK] Test alarm dismissed")

    # Now create a schedule matching the CURRENT minute right now
    now = datetime.now()
    now_time = now.strftime("%H:%M:00")
    now_sched = api.create_schedule(
        medication_id=med["id"],
        due_time=now_time,
        days_of_week="daily",
    )
    print(f"  [OK] Created schedule for current minute: {now_time}")

    # Run _check_pending_doses
    asyncio.run(alarm_service._check_pending_doses())
    assert alarm_service._ringer.is_ringing, "Alarm should ring when due dose matches current minute"
    assert alarm_service._is_dialog_open, "Alarm dialog should be open"
    assert len(mock_page.dialogs) == 1
    print(f"  [OK] AlarmService detected pending dose and automatically fired alarm + ringer!")

    # Simulate Take Now from Alarm Dialog
    dlg = mock_page.dialogs[-1]
    col = dlg.content
    # Find TAKE NOW button (controls[3])
    take_now_btn = col.controls[3]
    take_now_btn.on_click(None)

    assert not alarm_service._ringer.is_ringing, "Ringer must stop on Take Now"
    assert not alarm_service._is_dialog_open, "Dialog must close on Take Now"

    # Wait briefly for background status update thread
    time.sleep(0.5)
    assert status_updated_called[0], "on_status_updated callback fired"

    # Verify dose status in backend
    doses_after = api.get_todays_doses()
    taken_dose = next(d for d in doses_after if d["schedule_id"] == now_sched["id"])
    assert taken_dose["status"] == "taken"
    print("  [OK] Take Now action successfully marked dose as 'taken' in backend")

    # Verify stock decrement
    meds_after = api.list_medications()
    target_med = next(m for m in meds_after if m["id"] == med["id"])
    assert target_med["stock_qty"] == 29
    print("  [OK] Medication stock automatically decremented from 30 to 29")

    # Clean up created schedule
    api.delete_schedule(now_sched["id"])
    print("  [OK] Cleaned up temporary test schedule")

    print("\nALL EXACT MINUTE AND LOCAL ALARM TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_checks()
