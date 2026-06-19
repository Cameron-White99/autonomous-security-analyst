# Autonomous Security Analyst

**Live demo:** https://autonomous-security-analyst.vercel.app/

An AI-powered Security Operations Centre (SOC) assistant that ingests security logs,
analyses them with **parallel specialist Claude agents**, correlates events across
sources, and produces actionable incident reports with MITRE ATT&CK mappings.

The core technical differentiator is a **self-orchestrated fan-out / fan-in multi-agent
architecture** built on Python `asyncio` and the Anthropic Messages API — no managed
agent infrastructure, full control over the agent loop.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  COORDINATOR                         │
│   Receives raw log batch → splits by log type        │
│   Fans out to specialists via asyncio.gather()       │
│   Waits for all results → passes to correlation      │
│   Synthesises final incident report                  │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
       │  asyncio.gather() — all run in parallel
       │          │          │          │
       ▼          ▼          ▼          ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐
  │  AUTH   │ │NETWORK  │ │MALWARE  │ │  CORRELATION │
  │  AGENT  │ │  AGENT  │ │  AGENT  │ │    AGENT     │
  │ haiku   │ │ haiku   │ │ haiku   │ │   sonnet     │
  └─────────┘ └─────────┘ └─────────┘ └──────────────┘
```

- **Auth / Network / Malware agents** (`claude-haiku-4-5`) analyse their log slice in
  parallel and return structured JSON findings with confidence scores.
- **Correlation agent** (`claude-sonnet-4-6`) reconstructs the attack kill chain across
  sources, maps it to MITRE ATT&CK, and produces recommended response actions.
- Every agent lifecycle event is streamed to the frontend over **Server-Sent Events**
  and written to an **audit log** — you can watch the three specialists start
  simultaneously and finish at different times.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + uvicorn |
| Parallelism | Python `asyncio` (`asyncio.gather`) |
| AI | Anthropic Messages API (`AsyncAnthropic`) |
| Database | Neon PostgreSQL (asyncpg + SQLAlchemy async), in-memory fallback for demos |
| Real-time | Server-Sent Events |
| Frontend | React + Vite + Recharts |
| Deploy | Docker → Google Cloud Run (backend), Vercel (frontend) |

## Quick Start (no API key, no database)

The system ships with a **demo mode**: when `ANTHROPIC_API_KEY` is unset (or
`DEMO_MODE=true`), specialist agents return realistic canned findings derived from the
actual ingested logs, with staggered latency so the parallel execution is visible.
Without `DATABASE_URL`, incidents are stored in memory.

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on mac/linux)
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173

# Or seed scenarios from the CLI
python scripts/seed_logs.py
```

Open the dashboard, hit **“Full Kill Chain”**, and watch the agent activity feed.

### With real Claude agents + PostgreSQL

```bash
cp .env.example .env            # set ANTHROPIC_API_KEY and DATABASE_URL
docker compose up --build       # postgres + api + frontend
```

## API

| Endpoint | Description |
|---|---|
| `POST /ingest` | Accept a log batch, start parallel analysis, return `job_id` |
| `GET /stream/{job_id}` | SSE feed of live agent activity (with replay for late subscribers) |
| `GET /incidents` | List incident reports |
| `GET /incidents/{id}` | Full report: attack chain, MITRE mapping, per-agent findings |
| `GET /healthz` | Health + demo-mode status |

Example SSE stream:

```
data: {"event": "agent_start", "agent": "auth-analyst", ...}
data: {"event": "agent_start", "agent": "network-analyst", ...}
data: {"event": "agent_start", "agent": "malware-analyst", ...}
data: {"event": "agent_complete", "agent": "network-analyst", "findings_count": 2, ...}
data: {"event": "agent_complete", "agent": "auth-analyst", "findings_count": 1, ...}
data: {"event": "agent_complete", "agent": "malware-analyst", "findings_count": 2, ...}
data: {"event": "correlation_start", "agent": "correlation-analyst", ...}
data: {"event": "complete", "incident_id": "...", "severity": "Critical", ...}
```

## Tests

```bash
pytest tests/ -v
```

Includes a test that asserts the three specialist API calls **overlap in time**
(true parallelism via `asyncio.gather`), plus full-pipeline API tests covering
ingest → SSE stream → incident retrieval.

## Deployment

- **Backend → Cloud Run:** `./scripts/deploy.sh <gcp-project-id> [region]`
  (expects `anthropic-api-key` and `database-url` in Secret Manager)
- **Frontend → Vercel:** import `frontend/`, set `VITE_API_URL` to the Cloud Run URL
- **CI:** GitHub Actions runs backend tests, frontend build, and docker build on every push

## Project Structure

```
app/
├── main.py                  # FastAPI entrypoint
├── config.py                # pydantic-settings (API key, DB, demo mode)
├── agents/
│   ├── orchestrator.py      # asyncio fan-out/fan-in (the core)
│   ├── prompts.py           # all four agent system prompts
│   └── demo.py              # canned responses when no API key is set
├── api/                     # /ingest, /incidents, /stream
├── background/              # event bus + analysis worker
├── db/                      # async engine, migrations, repositories
└── models/                  # pydantic schemas
frontend/                    # React dashboard (Vite + Recharts)
tests/                       # orchestrator + API tests, sample log fixtures
scripts/                     # seed_logs.py, deploy.sh
```
