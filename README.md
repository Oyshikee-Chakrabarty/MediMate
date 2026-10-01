# Medimate

MediMate is a cross-platform medication reminder and management application built entirely with Python. It provides a user-friendly interface for patients and caregivers to manage medicines, medication schedules, dose events, and related notifications.

## Project Structure
-frontend/: Flet-based frontend application written in Python.
-backend/: FastAPI-based Python API server.
-README.md: Project documentation.

## Getting Started

### Prerequisites
- Python 3.x
- pip
- Git

### Setup
1. **Frontend (`frontend/app/`):**
   ```bash
   cd frontend/app
   flet run main.py
   ```
   > flet is cross platform, to run in a browser use `--web`, to run on android directly without having to cmpile an APK run with `--android`.
2. **Backend (`backend/`):**
   ```bash
   cd backend
   pip install -r requirements.txt
   source .venv/bin/activate
   uvicorn app.main:app --reload
   ```
   > It can also be run with `uv`
