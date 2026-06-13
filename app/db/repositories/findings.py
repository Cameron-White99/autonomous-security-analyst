"""Agent findings and audit log persistence."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import connection

_memory_findings: list[dict] = []
_memory_audit: list[dict] = []


def reset_memory_store() -> None:
    _memory_findings.clear()
    _memory_audit.clear()


async def save_agent_findings(incident_id: str, specialist_results: list[dict]) -> None:
    engine = connection.get_engine()
    for result in specialist_results:
        findings = result.get("findings") or {}
        confidences = [
            f.get("confidence", 0)
            for f in (findings.get("findings", []) if isinstance(findings, dict) else [])
        ]
        record = {
            "id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "agent_name": result.get("agent", "unknown"),
            "findings": findings if isinstance(findings, dict) else {"raw": findings},
            "confidence_score": max(confidences) if confidences else None,
            "processing_time_ms": result.get("processing_time_ms"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if engine is None:
            _memory_findings.append(record)
            continue

        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO agent_findings (id, incident_id, agent_name, findings,
                                                confidence_score, processing_time_ms)
                    VALUES (:id, :incident_id, :agent_name, CAST(:findings AS JSONB),
                            :confidence_score, :processing_time_ms)
                """),
                {**record, "findings": json.dumps(record["findings"])},
            )


async def get_findings_for_incident(incident_id: str) -> list[dict]:
    engine = connection.get_engine()
    if engine is None:
        return [f for f in _memory_findings if f["incident_id"] == incident_id]

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM agent_findings WHERE incident_id = :id ORDER BY created_at"),
            {"id": incident_id},
        )
        return [
            {
                "id": str(row.id),
                "incident_id": str(row.incident_id),
                "agent_name": row.agent_name,
                "findings": row.findings,
                "confidence_score": row.confidence_score,
                "processing_time_ms": row.processing_time_ms,
                "created_at": row.created_at.isoformat(),
            }
            for row in result
        ]


async def write_audit_event(job_id: str, agent_name: str, event_type: str, event_data: dict) -> None:
    """Full audit trail — every agent lifecycle event is recorded."""
    engine = connection.get_engine()
    record = {
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "agent_name": agent_name,
        "event_type": event_type,
        "event_data": event_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if engine is None:
        _memory_audit.append(record)
        return

    async with engine.begin() as conn:
        await conn.execute(
            text("""
                INSERT INTO audit_log (id, job_id, agent_name, event_type, event_data)
                VALUES (:id, :job_id, :agent_name, :event_type, CAST(:event_data AS JSONB))
            """),
            {**record, "event_data": json.dumps(record["event_data"])},
        )
