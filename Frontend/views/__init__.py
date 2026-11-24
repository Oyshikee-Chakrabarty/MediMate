"""View modules — one per screen."""

from views.add_medicine_view import AddMedicineView
from views.auth_view import AuthView
from views.caretaker_view import CaretakerView
from views.history_view import HistoryView
from views.insulin_view import InsulinView
from views.medicines_view import MedicinesView
from views.patient_view import PatientView
from views.schedule_view import ScheduleView

__all__ = [
    "AddMedicineView",
    "AuthView",
    "CaretakerView",
    "HistoryView",
    "InsulinView",
    "MedicinesView",
    "PatientView",
    "ScheduleView",
]
