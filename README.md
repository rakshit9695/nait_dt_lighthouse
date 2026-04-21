# NAIT CGI Microgrid Digital Twin

A 2D, physics-grounded digital twin of the NAIT Centre for Grid Innovation (CGI) Data Center microgrid testbed (drawing CGI-DC-01 Rev 2). Three coupled systems share one source of truth:

1. **Backend** — Python time-stepping simulator with one model per SLD component, FastAPI northbound API, and persistence.
2. **Evaluation Engine** — confidence scorer that compares twin outputs to industrial reference curves and emits per-component and system-level scores.
3. **Frontend** — React SPA rendering the SLD with 3 drill-through layers and a scenario builder.

## Quick start

### Backend
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```
API: http://localhost:8000  •  Docs: http://localhost:8000/docs  •  Live WS: ws://localhost:8000/ws/live

Auth: bearer token via `NAIT_DT_TOKEN` env var (default `dev-token`).

### Frontend
```powershell
cd frontend
npm install
npm run dev
```
Dev server on http://localhost:5173 with `VITE_API_BASE_URL` defaulting to `http://localhost:8000`.

### Tests
```powershell
pytest --cov=backend --cov-report=term-missing
```

### Docker
```powershell
docker compose up
```

## Layout
```
backend/        # physics, solver, control, eval, api, config
frontend/       # React/TS/Vite/Tailwind SPA
scenarios/      # canned + user scenarios (YAML)
eval/           # generated reports (JSON + HTML)
assumptions.md  # surfaces every assumed=true default
```

See `assumptions.md` for the assumption ledger and section refs in `Questions_for_NAIT.pdf`.
