"""Background task — runs the orchestrator, streams SSE events, persists results."""

import logging
from datetime import datetime, timezone

from app.agents.orchestrator import analyse_log_batch
from app.background.events import bus
from app.db.repositories import findings as findings_repo
from app.db.repositories import incidents as incidents_repo

logger = logging.getLogger(__name__)


async def run_analysis(job_id: str, log_batch: list[dict]) -> None:
    """Execute the full fan-out/fan-in pipeline for one ingested batch."""

    async def emit(event: dict) -> None:
        await bus.publish(job_id, event)
        # Full audit trail for all agent decisions
        await findings_repo.write_audit_event(
            job_id=job_id,
            agent_name=event.get("agent", "coordinator"),
            event_type=event.get("event", "unknown"),
            event_data=event,
        )

    try:
        await emit({
            "event": "analysis_start",
            "agent": "coordinator",
            "log_count": len(log_batch),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await analyse_log_batch(log_batch, emit=emit)
        report = result["incident_report"]

        incident = await incidents_repo.save_incident(job_id, report)
        await findings_repo.save_agent_findings(incident["id"], result["specialist_findings"])

        await emit({
            "event": "complete",
            "agent": "coordinator",
            "incident_id": incident["id"],
            "severity": incident["severity"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:  # surface failures to the stream, never crash the server
        logger.exception("Analysis job %s failed", job_id)
        await emit({
            "event": "error",
            "agent": "coordinator",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
