"""Incident persistence — PostgreSQL when configured, in-memory otherwise."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import connection

# In-memory fallback store (DATABASE_URL unset)
_memory_incidents: list[dict] = []


def reset_memory_store() -> None:
    _memory_incidents.clear()


async def save_incident(job_id: str, report: dict) -> dict:
    record = {
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "severity": report.get("severity", "Informational"),
        "title": report.get("title", "Untitled Incident"),
        "summary": report.get("summary", ""),
        "attack_chain": report.get("attack_chain", []),
        "mitre_tactics": report.get("mitre_tactics", []),
        "mitre_techniques": report.get("mitre_techniques", []),
        "recommended_actions": report.get("recommended_actions", []),
        "overall_confidence": report.get("confidence", 0),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    engine = connection.get_engine()
    if engine is None:
        _memory_incidents.insert(0, record)
        return record

    async with engine.begin() as conn:
        await conn.execute(
            text("""
                INSERT INTO incidents (id, job_id, severity, title, summary, attack_chain,
                                       mitre_tactics, mitre_techniques, recommended_actions, overall_confidence)
                VALUES (:id, :job_id, :severity, :title, :summary, CAST(:attack_chain AS JSONB),
                        :mitre_tactics, :mitre_techniques, :recommended_actions, :overall_confidence)
            """),
            {
                **record,
                "attack_chain": json.dumps(record["attack_chain"]),
            },
        )
    return record


def _row_to_record(row) -> dict:
    return {
        "id": str(row.id),
        "job_id": str(row.job_id),
        "severity": row.severity,
        "title": row.title,
        "summary": row.summary,
        "attack_chain": row.attack_chain or [],
        "mitre_tactics": list(row.mitre_tactics or []),
        "mitre_techniques": list(row.mitre_techniques or []),
        "recommended_actions": list(row.recommended_actions or []),
        "overall_confidence": row.overall_confidence or 0,
        "created_at": row.created_at.isoformat(),
    }


async def list_incidents(limit: int = 50) -> list[dict]:
    engine = connection.get_engine()
    if engine is None:
        return _memory_incidents[:limit]

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM incidents ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        )
        return [_row_to_record(row) for row in result]


async def get_incident(incident_id: str) -> dict | None:
    engine = connection.get_engine()
    if engine is None:
        return next((i for i in _memory_incidents if i["id"] == incident_id), None)

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM incidents WHERE id = :id"), {"id": incident_id}
        )
        row = result.first()
        return _row_to_record(row) if row else None
