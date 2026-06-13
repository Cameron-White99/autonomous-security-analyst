"""FastAPI app entrypoint — Autonomous Security Analyst."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import incidents, ingest, stream
from app.config import get_settings
from app.db.connection import close_db, init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Autonomous Security Analyst",
    description=(
        "AI-powered SOC assistant — parallel multi-agent log analysis with "
        "cross-source correlation and MITRE ATT&CK mapping."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(incidents.router)
app.include_router(stream.router)


@app.get("/healthz", tags=["health"])
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "demo_mode": settings.use_demo_agents,
        "environment": settings.environment,
    }
