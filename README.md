# BLUE CARBON REGISTRATION AND MONITORING

A local academic prototype with React + TypeScript + Vite, FastAPI, JSON-file persistence, Leaflet polygon drawing, and an explicit ML-analysis-unavailable state until a real imagery/model pipeline is configured.

## Requirements
- Python 3.11+ (Python 3.14 may not yet be supported by every geospatial wheel)
- Node.js 20+ and npm
- Windows 10/11

## Run on Windows PowerShell
1. Open PowerShell in this project folder.
2. Backend: `cd backend; py -3.11 -m venv .venv; .\.venv\Scripts\python.exe -m pip install --upgrade pip; .\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Frontend in a second terminal: `cd frontend; npm install`
4. Create the first admin: `cd backend; .\.venv\Scripts\python.exe ..\scripts\create_admin.py`
5. Start backend: `cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
6. Start frontend in a second terminal: `cd frontend; npm run dev`
7. Open the Vite URL printed in the terminal, usually `http://localhost:5173`. API docs: `http://127.0.0.1:8000/docs`.

For environments where `py -3.11` is unavailable, install Python 3.11 from python.org, then rerun the commands. Geospatial dependencies are optional in this initial prototype; geometry validation has a pure-Python fallback.

## Bootstrap administrator
Run `python scripts/create_admin.py` from the project root using your backend virtual environment. The script prompts for username and password. Admin creation is not exposed as a public registration route.

## Storage and ML
Records are stored in `database/*.json`. Uploaded files belong in `uploads/`. Back up the `database` folder before changes. JSON storage is suitable for a small single-process prototype, not production concurrency or high-volume workloads.

The map uses OpenStreetMap tiles and attribution; follow the tile usage policy. Tree counting is deliberately reported as `analysis_unavailable` until compatible georeferenced imagery and a validated, licensed model are configured. No synthetic measurements or credits are presented as real. Carbon-credit issuance is disabled unless eligibility evidence and an authorized admin action are implemented and verified.

## Tests
Backend tests: `cd backend; python -m pytest -q`
Frontend build: `cd frontend; npm run build`
