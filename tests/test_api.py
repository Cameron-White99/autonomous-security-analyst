"""API tests — ingest → SSE stream → incident retrieval, all against demo agents."""

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents import orchestrator
from app.config import Settings
from app.db.repositories import findings as findings_repo
from app.db.repositories import incidents as incidents_repo
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "sample_logs"


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    """Force demo agents with near-instant latency and a clean in-memory store."""
    monkeypatch.setattr(
        orchestrator, "get_settings",
        lambda: Settings(anthropic_api_key=None, demo_mode=True, database_url=None, _env_file=None),
    )
    monkeypatch.setattr("app.agents.demo.random.uniform", lambda a, b: 0.01)
    incidents_repo.reset_memory_store()
    findings_repo.reset_memory_store()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def fixture_batch(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


async def drain_stream(client: AsyncClient, job_id: str) -> list[dict]:
    events = []
    async with client.stream("GET", f"/stream/{job_id}") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


async def test_health(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["demo_mode"] is True


async def test_ingest_returns_job_id(client):
    response = await client.post("/ingest", json=fixture_batch("brute_force"))
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["job_id"]


async def test_ingest_rejects_empty_batch(client):
    response = await client.post("/ingest", json={"source": "demo", "logs": []})
    assert response.status_code == 422


async def test_stream_unknown_job_404(client):
    response = await client.get("/stream/not-a-real-job")
    assert response.status_code == 404


async def test_full_pipeline_ingest_stream_incident(client):
    # 1. Ingest
    response = await client.post("/ingest", json=fixture_batch("lateral_movement"))
    job_id = response.json()["job_id"]

    # 2. SSE stream shows parallel agents then completion
    stream_events = await drain_stream(client, job_id)
    events = [e["event"] for e in stream_events]
    assert events.count("agent_start") == 3
    assert events.count("agent_complete") == 3
    assert "correlation_start" in events
    assert events[-1] == "complete"

    complete = stream_events[-1]
    assert complete["severity"] in {"Critical", "High", "Medium", "Low", "Informational"}

    # 3. Incident list and detail
    incidents = (await client.get("/incidents")).json()
    assert len(incidents) == 1
    assert incidents[0]["job_id"] == job_id

    detail = (await client.get(f"/incidents/{complete['incident_id']}")).json()
    assert detail["mitre_techniques"]
    assert detail["recommended_actions"]
    assert len(detail["agent_findings"]) == 3
    agent_names = {f["agent_name"] for f in detail["agent_findings"]}
    assert agent_names == {"auth-analyst", "network-analyst", "malware-analyst"}


async def test_late_subscriber_gets_event_replay(client):
    """SSE clients connecting after the job finished still receive full history."""
    response = await client.post("/ingest", json=fixture_batch("brute_force"))
    job_id = response.json()["job_id"]

    # Drain once (waits for completion), then connect again
    await drain_stream(client, job_id)
    replay = await drain_stream(client, job_id)
    assert [e["event"] for e in replay][-1] == "complete"
    assert any(e["event"] == "agent_start" for e in replay)


async def test_incident_not_found(client):
    response = await client.get("/incidents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
