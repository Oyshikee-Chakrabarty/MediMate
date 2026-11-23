"""Milestone 1+2 API client (JWT auth, care-links, medication CRUD).

Same design as the main app's `app/services/api_client.py`, trimmed to
exactly what the first two milestones need:
  Milestone 1 -> POST /auth/register, POST /auth/login
  Milestone 2 -> care-link generate / pair / my-patients + medication CRUD
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class ApiError(Exception):
    """Raised when the backend answers with an error status code."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code: int = status_code
        self.detail: str = detail


class Api:
    """Thin synchronous wrapper around the MediMate REST API."""

    def __init__(self, base_url: str) -> None:
        # strip a trailing "/" so f"{base}/path" never produces a double slash
        self._base: str = base_url.rstrip("/")
        self._token: Optional[str] = None

    # ------------------------------------------------------------------ #
    # low-level helpers
    # ------------------------------------------------------------------ #
    def _headers(self) -> Dict[str, str]:
        """Build request headers; attach the JWT when we have one."""
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Send one HTTP request and decode the JSON response.

        Raises ApiError with the server's `detail` message on any error
        status, so the UI can show a readable message to the user.
        """
        url: str = f"{self._base}{path}"
        try:
            response: httpx.Response = httpx.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=self._headers(),
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise ApiError(0, f"Cannot reach server at {url}: {exc}") from exc

        if response.status_code >= 400:
            try:
                detail: str = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise ApiError(response.status_code, str(detail))

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # ------------------------------------------------------------------ #
    # Milestone 1: authentication
    # ------------------------------------------------------------------ #
    def register(
        self, name: str, email: str, password: str, role: str, preferred_language: str = "en"
    ) -> Dict[str, Any]:
        """Create an account; the server returns a JWT immediately."""
        payload: Dict[str, Any] = {
            "name": name,
            "email": email,
            "password": password,
            "role": role,
            "preferred_language": preferred_language,
        }
        return self._request("POST", "/auth/register", json_body=payload)

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Exchange email+password for a JWT bearer token."""
        return self._request(
            "POST", "/auth/login", json_body={"email": email, "password": password}
        )

    def update_language(self, language: str) -> Dict[str, Any]:
        """Update and persist the current authenticated user's preferred language."""
        return self._request(
            "PUT", "/auth/me/language", json_body={"language": language}
        )

    def save_token(self, token: str) -> None:
        """Store the JWT for all subsequent requests."""
        self._token = token

    @property
    def token(self) -> Optional[str]:
        """The current JWT (None before login) — read by the event socket."""
        return self._token

    # ------------------------------------------------------------------ #
    # Milestone 2: care-link pairing
    # ------------------------------------------------------------------ #
    def generate_invite_code(self) -> Dict[str, Any]:
        """Patient asks the server for a fresh 6-digit pairing code."""
        return self._request("POST", "/care-links/generate-code", json_body={})

    def pair_with_code(self, invite_code: str) -> Dict[str, Any]:
        """Caretaker submits the 6-digit code to activate the link."""
        return self._request(
            "POST", "/care-links/pair", json_body={"invite_code": invite_code}
        )

    def my_patients(self) -> List[Dict[str, Any]]:
        """Caretaker lists actively paired patients."""
        return self._request("GET", "/care-links/my-patients")

    # ------------------------------------------------------------------ #
    # Milestone 2: medication CRUD
    # ------------------------------------------------------------------ #
    def add_medication(
        self,
        name: str,
        stock_qty: int = 0,
        restock_notify_days: int = 7,
        patient_id: Optional[str] = None,
        dosage: Optional[str] = None,
        form: Optional[str] = "Tablet",
        disease: Optional[str] = None,
        body_part: Optional[str] = None,
        notes: Optional[str] = None,
        schedule_times: Optional[List[str]] = None,
        schedule_days: Optional[str] = "daily",
    ) -> Dict[str, Any]:
        """Create a medication (caretakers must pass the patient_id)."""
        payload: Dict[str, Any] = {
            "name": name,
            "stock_qty": stock_qty,
            "restock_notify_days": restock_notify_days,
            "dosage": dosage,
            "form": form or "Tablet",
            "disease": disease,
            "body_part": body_part,
            "notes": notes,
        }
        if patient_id:
            payload["patient_id"] = patient_id
        if schedule_times is not None:
            payload["schedule_times"] = schedule_times
        if schedule_days is not None:
            payload["schedule_days"] = schedule_days
        return self._request("POST", "/medications", json_body=payload)

    def list_medications(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List medications of the signed-in patient (or of a linked patient)."""
        params: Dict[str, Any] = {}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/medications", params=params)

    def update_medication(
        self,
        medication_id: str,
        name: Optional[str] = None,
        stock_qty: Optional[int] = None,
        restock_notify_days: Optional[int] = None,
        dosage: Optional[str] = None,
        form: Optional[str] = None,
        disease: Optional[str] = None,
        body_part: Optional[str] = None,
        notes: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Edit medication fields. Only non-None fields are changed."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if stock_qty is not None:
            payload["stock_qty"] = stock_qty
        if restock_notify_days is not None:
            payload["restock_notify_days"] = restock_notify_days
        if dosage is not None:
            payload["dosage"] = dosage
        if form is not None:
            payload["form"] = form
        if disease is not None:
            payload["disease"] = disease
        if body_part is not None:
            payload["body_part"] = body_part
        if notes is not None:
            payload["notes"] = notes
        if patient_id is not None:
            payload["patient_id"] = patient_id
        return self._request("PUT", f"/medications/{medication_id}", json_body=payload)

    def delete_medication(self, medication_id: str, patient_id: Optional[str] = None) -> None:
        """Remove a medication (HTTP 204, empty body)."""
        params: Dict[str, Any] = {}
        if patient_id:
            params["patient_id"] = patient_id
        self._request("DELETE", f"/medications/{medication_id}", params=params)

    # ------------------------------------------------------------------ #
    # Milestone 3: schedules & dose events
    # ------------------------------------------------------------------ #
    def list_schedules(
        self, medication_id: Optional[str] = None, patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List schedules for a med or patient."""
        params: Dict[str, Any] = {}
        if medication_id:
            params["medication_id"] = medication_id
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/schedules", params=params)

    def create_schedule(
        self, medication_id: str, due_time: str = "09:00:00", days_of_week: str = "daily"
    ) -> Dict[str, Any]:
        """Create a dose schedule with 30-day generated dose events."""
        return self._request(
            "POST",
            "/schedules",
            json_body={
                "medication_id": medication_id,
                "due_time": due_time,
                "days_of_week": days_of_week,
            },
        )

    def delete_schedule(self, schedule_id: str) -> None:
        """Remove a schedule and all of its dose events (HTTP 204)."""
        self._request("DELETE", f"/schedules/{schedule_id}")

    def get_todays_doses(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get today's dose events for patient."""
        params: Dict[str, Any] = {}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/dose-events/today", params=params)

    def set_dose_status(self, dose_event_id: str, status: str) -> Dict[str, Any]:
        """Set dose outcome: taken, skipped, missed."""
        return self._request(
            "POST", f"/dose-events/{dose_event_id}/status", json_body={"status": status}
        )

    # ------------------------------------------------------------------ #
    # Dose Tracking & Rescheduling
    # ------------------------------------------------------------------ #
    def get_medication_tracking(self, medication_id: str) -> Dict[str, Any]:
        """Fetch dose tracking, consumption rate, and reschedule calculations."""
        return self._request("GET", f"/medications/{medication_id}/tracking")

    def get_tracking_summary(
        self, patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch tracking calculations for all medications of a patient."""
        params: Dict[str, Any] = {}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/medications/tracking/summary", params=params)

    def reschedule_medication(
        self,
        medication_id: str,
        added_stock: int = 30,
        new_due_times: Optional[List[str]] = None,
        new_days_of_week: Optional[str] = None,
        extend_days: int = 30,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restock medication and extend/reschedule dose events."""
        payload: Dict[str, Any] = {
            "added_stock": added_stock,
            "extend_days": extend_days,
        }
        if new_due_times is not None:
            payload["new_due_times"] = new_due_times
        if new_days_of_week is not None:
            payload["new_days_of_week"] = new_days_of_week
        if patient_id is not None:
            payload["patient_id"] = patient_id
        return self._request(
            "POST", f"/medications/{medication_id}/reschedule", json_body=payload
        )

    # ------------------------------------------------------------------ #
    # Medication History & Dose Calendar
    # ------------------------------------------------------------------ #
    def get_dose_history(
        self, year: int, month: int, patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch monthly calendar adherence overview."""
        params: Dict[str, Any] = {"year": year, "month": month}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/dose-events/history", params=params)

    def get_doses_for_date(
        self, date_str: str, patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all dose events and medications for a specific day."""
        params: Dict[str, Any] = {"date_str": date_str}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/dose-events/by-date", params=params)

    # ------------------------------------------------------------------ #
    # Insulin & Blood Sugar Level Tracking
    # ------------------------------------------------------------------ #
    def list_insulin_readings(
        self, date_str: str, patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all sugar level readings for a specific date."""
        params: Dict[str, Any] = {"date": date_str}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/insulin", params=params)

    def list_insulin_dates(
        self, year: int, month: int, patient_id: Optional[str] = None
    ) -> List[str]:
        """List unique dates that have readings in a given month."""
        params: Dict[str, Any] = {"year": year, "month": month}
        if patient_id:
            params["patient_id"] = patient_id
        return self._request("GET", "/insulin/dates", params=params)

    def add_insulin_reading(
        self,
        reading_date: str,
        reading_time: str,
        sugar_level: float,
        insulin_units: Optional[float] = None,
        notes: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a new blood sugar / insulin reading."""
        payload: Dict[str, Any] = {
            "reading_date": reading_date,
            "reading_time": reading_time,
            "sugar_level": sugar_level,
        }
        if insulin_units is not None:
            payload["insulin_units"] = insulin_units
        if notes is not None:
            payload["notes"] = notes
        if patient_id is not None:
            payload["patient_id"] = patient_id
        return self._request("POST", "/insulin", json_body=payload)

    def delete_insulin_reading(self, reading_id: str) -> None:
        """Delete an insulin reading by ID."""
        self._request("DELETE", f"/insulin/{reading_id}")
