
<p align="center">
  <img width="160" height="160" alt="logo" src="https://github.com/user-attachments/assets/80e038ce-da7e-411d-800d-ed7bed5e0f4a" />
</p>

<h1 align="center">MediMate</h1>

<p align="center">
  <strong>Cross-Platform Medication Adherence & Caregiver Coordination Platform</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://flet.dev/"><img src="https://img.shields.io/badge/Frontend-Flet%20(Flutter)-02569B?logo=flutter&logoColor=white" alt="Flet" /></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/Database-SQLAlchemy%20%7C%20SQLite%20%2F%20PostgreSQL-D71F00" alt="SQLAlchemy" /></a>
  <a href="https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API"><img src="https://img.shields.io/badge/Realtime-WebSockets-orange?logo=websocket" alt="WebSockets" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
</p>

---

## 📘 About 

MediMate is a cross-platform medication reminder and management application built entirely with Python. It provides a user-friendly interface for patients and caregivers to manage medicines, medication schedules, dose events, and related notifications.

---

## 👥 Development Team

<div align="center">
<table>
  <tr>
    <td align="center" width="33.33%">
      <a href="https://github.com/Shadow-ranger01">
        <img src="https://github.com/Shadow-ranger01.png?size=120" width="100" style="border-radius: 50%;" alt="Shadow-ranger01" />
        <br />
        <sub><b>Rafi </b></sub>
      </a>
      <br />
      <a href="https://github.com/Shadow-ranger01">
        <img src="https://img.shields.io/badge/GitHub-Profile-181717?style=flat&logo=github" alt="GitHub" />
      </a>
    </td>
    <td align="center" width="33.33%">
      <a href="https://github.com/Oyshikee-Chakrabarty">
        <img src="https://github.com/Oyshikee-Chakrabarty.png?size=120" width="100" style="border-radius: 50%;" alt="Oyshikee Chakrabarty" />
        <br />
        <sub><b>Oyshikee </b></sub>
      </a>
      <br />
      <a href="https://github.com/Oyshikee-Chakrabarty">
        <img src="https://img.shields.io/badge/GitHub-Profile-181717?style=flat&logo=github" alt="GitHub" />
      </a>
    </td>
    <td align="center" width="33.33%">
      <a href="https://github.com/dipu-basak">
        <img src="https://github.com/dipu-basak.png?size=120" width="100" style="border-radius: 50%;" alt="Dipu Basak" />
        <br />
        <sub><b>Dipu </b></sub>
      </a>
      <br />
      <a href="https://github.com/dipu-basak">
        <img src="https://img.shields.io/badge/GitHub-Profile-181717?style=flat&logo=github" alt="GitHub" />
      </a>
    </td>
  </tr>
</table>
</div>

---

## 📌 Overview

This directory contains the self-contained production implementation of **MediMate**:
- **`backend/`**: High-performance FastAPI server providing REST APIs, WebSocket real-time broadcast channels, SQLite/PostgreSQL ORM models, and automatic 30-day dose event generation.
- **`frontend/`**: Modern, reactive Flet application supporting native Desktop (Windows, macOS, Linux), Web (`--web`), and Mobile (`--android`).

---

## 🌟 Core Highlights

- **👥 Patient ↔ Caregiver Coordination**: Real-time caregiver pairing with 6-digit codes and remote medication management.
- **⏰ Smart Dose Scheduling & Auditory Alerts**: Custom times, intervals, quick time shortcuts (`Now`, `+2 min`, `Morning`, `Night`), and native sound alarms.
- **📦 Stock & Consumption Forecasting**: Automatic calculation of supply depletion date and restock notifications (`healthy`, `reschedule_soon`, `reschedule_now`).
- **🩸 Glucose & Insulin Vitals Log**: Full tracking of blood sugar levels, insulin units, and timestamps.
- **📅 Visual Adherence Calendar**: Monthly color-coded adherence status (Blue = all taken, Red = missed, Hollow = partial, Green-dot = upcoming).
- **🌐 Bilingual Localization**: English & Bengali (বাংলা) with cloud preference persistence.
- **⚡ Zero-Polling Realtime Sync**: Instantaneous updates over WebSockets (`/ws/events/{user_id}`).

---

## 📂 Architecture & Directory Structure

```
medimate_standalone/
├── assets/                       # Branding graphics and icons
├── backend/                      # FastAPI API server
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint & WebSocket startup lifecycle
│   │   ├── database.py           # SQLAlchemy database configuration
│   │   ├── models.py             # ORM models (User, CareLink, Medication, Schedule, DoseEvent, InsulinReading)
│   │   ├── schemas.py            # Pydantic v2 validation models
│   │   ├── security.py           # Password hashing & JWT token issuance
│   │   ├── services/
│   │   │   └── dose_tracking.py  # Supply rate calculations and rescheduling logic
│   │   └── routers/
│   │       ├── auth.py           # Auth & language preference (/auth/me/language)
│   │       ├── care_links.py     # 6-digit invite code generation & pairing
│   │       ├── dose_events.py    # Dose outcomes, history & adherence
│   │       ├── insulin.py        # Blood sugar and insulin tracking
│   │       ├── medicines.py      # Medication CRUD & stock tracking
│   │       ├── notifications.py  # WebSocket manager & push broadcasting
│   │       └── schedules.py      # Dose schedule generation
│   ├── fallback.db               # Embedded local SQLite database
│   ├── schema.sql                # SQL reference schema
│   ├── Dockerfile                # Production container deployment
│   └── requirements.txt          # Backend dependencies
└── frontend/                     # Flet client application
    ├── main.py                   # UI entrypoint, routing & view orchestrator
    ├── config.py                 # Design tokens, colors, breakpoints & URLs
    ├── components/
    │   └── common.py             # Reusable UI widgets & dialogs
    ├── services/
    │   ├── api_client.py         # HTTP REST client (httpx)
    │   └── event_socket.py       # WebSocket push listener
    ├── views/
    │   ├── auth_view.py          # Sign in / Sign up
    │   ├── patient_view.py       # Patient dashboard & adherence summary
    │   ├── caretaker_view.py     # Caregiver dashboard & patient switching
    │   ├── medicines_view.py     # Medicine catalog & stock status
    │   ├── add_medicine_view.py  # Medicine creation & time picker
    │   ├── schedule_view.py      # Active schedules
    │   └── history_view.py       # Adherence calendar & insulin logger
    ├── smoke_test.py             # Headless 17-point automated verification
    └── requirements.txt          # Frontend dependencies
```

---

## 🚀 Quick Launch

### Run with `uv` (Fastest)

```bash
# Terminal 1 — Backend on port 8000
uv run uvicorn app.main:app --app-dir backend --reload --port 8000

# Terminal 2 — Frontend Desktop App
uv run flet run frontend/main.py
```

### Run with Standard Python `venv`

#### 1. Backend
```bash
cd backend
python -m venv .venv
# Activate:
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend
```bash
cd frontend
pip install -r requirements.txt

# Run Desktop:
flet run main.py

# Run in Browser:
flet run --web --port 8550 main.py

# Run on Android:
flet run --android main.py
```

---

## 🧪 Verification & Automated Tests

All tests run headlessly without requiring a physical monitor:

```bash
# Run 17-point end-to-end integration check
python frontend/smoke_test.py

# Test supply forecasting and reschedule service
python frontend/dose_tracking_test.py

# Test adherence calendar and insulin logs
python frontend/test_history_and_insulin.py

# Test real-time WebSocket push latency
python frontend/realtime_test.py
```

---

## 📖 API Documentation

- **Swagger Interactive Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Reference**: `http://127.0.0.1:8000/redoc`

---

## 📄 License

This software is released under the **MIT License**.
