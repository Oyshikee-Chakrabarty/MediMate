# Medimate

Medimate is a cross-platform application with a Flutter frontend and a Python backend.

## Project Structure
- `app/`: Flutter mobile application.
- `backend/`: Python API server (FastAPI).

## Getting Started

### Prerequisites
- Flutter SDK
- Python 3.x
- pip

### Setup
1. **Frontend (`app/`):**
   ```bash
   cd app
   flutter pub get
   ```
2. **Backend (`backend/`):**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Running the Application
### For running in codespaces
---
**Terminal 1 — backend (port 8000):**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Codespaces detects port 8000 and forwards it publicly at
`https://<codespace-name>-8000.app.github.dev`.

**Terminal 2 — Flutter app (in Codespaces):**

```bash
cd app
flutter pub get
flutter run -d web-server --web-port 8080

```
---
### running local
---
**Terminal 1 — backend (port 8000):**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
**Terminal 2 — Flutter app (linux local):**

```bash
cd app
flutter pub get
flutter run -d chrome -web port=8080

```

