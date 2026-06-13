# app/agents/orchestrator.py

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from app.agents import demo
from app.agents.prompts import (
    AUTH_AGENT_PROMPT,
    CORRELATION_AGENT_PROMPT,
    MALWARE_AGENT_PROMPT,
    NETWORK_AGENT_PROMPT,
)
from app.config import get_settings

SPECIALIST_MODEL = "claude-haiku-4-5"
CORRELATION_MODEL = "claude-sonnet-4-6"

# Optional async callback used to stream agent activity events (SSE feed).
EmitFn = Callable[[dict], Awaitable[None]]

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    """Lazy client init so the app imports cleanly without an API key (demo mode)."""
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _emit(emit: EmitFn | None, event: dict) -> None:
    if emit is not None:
        await emit({**event, "timestamp": _now()})


async def run_specialist_agent(
    agent_name: str,
    system_prompt: str,
    log_data: list[dict],
    model: str = SPECIALIST_MODEL,
    emit: EmitFn | None = None,
) -> dict:
    """Run a single specialist agent against a subset of logs."""
    if not log_data:
        await _emit(emit, {"event": "agent_skipped", "agent": agent_name, "reason": "no logs"})
        return {"agent": agent_name, "findings": {"findings": [], "summary": "No logs of this type in batch."},
                "confidence": 0, "processing_time_ms": 0}

    await _emit(emit, {"event": "agent_start", "agent": agent_name, "log_count": len(log_data)})
    started = time.perf_counter()

    if get_settings().use_demo_agents:
        findings = await demo.specialist_findings(agent_name, log_data)
    else:
        response = await get_client().messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyse these logs and return findings as JSON:\n\n{json.dumps(log_data, indent=2)}"
                }
            ],
        )
        raw = response.content[0].text
        try:
            findings = json.loads(raw)
        except json.JSONDecodeError:
            findings = {"raw": raw, "parse_error": True}

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    findings_count = len(findings.get("findings", [])) if isinstance(findings, dict) else 0
    await _emit(emit, {
        "event": "agent_complete",
        "agent": agent_name,
        "findings_count": findings_count,
        "processing_time_ms": elapsed_ms,
    })

    return {"agent": agent_name, "findings": findings, "processing_time_ms": elapsed_ms}


async def run_correlation_agent(specialist_results: list[dict], emit: EmitFn | None = None) -> dict:
    """Run correlation agent against combined specialist findings."""
    await _emit(emit, {"event": "correlation_start", "agent": "correlation-analyst"})
    started = time.perf_counter()

    if get_settings().use_demo_agents:
        report = await demo.correlation_report(specialist_results)
    else:
        combined = json.dumps(specialist_results, indent=2)
        response = await get_client().messages.create(
            model=CORRELATION_MODEL,
            max_tokens=4096,
            system=CORRELATION_AGENT_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Correlate these specialist findings and produce an incident report:\n\n{combined}"
                }
            ],
        )
        raw = response.content[0].text
        try:
            report = json.loads(raw)
        except json.JSONDecodeError:
            report = {"raw": raw, "parse_error": True}

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await _emit(emit, {
        "event": "correlation_complete",
        "agent": "correlation-analyst",
        "severity": report.get("severity") if isinstance(report, dict) else None,
        "processing_time_ms": elapsed_ms,
    })
    report["processing_time_ms"] = elapsed_ms
    return report


async def analyse_log_batch(log_batch: list[dict], emit: EmitFn | None = None) -> dict:
    """
    Main orchestration function.
    Splits logs by type, runs specialists in parallel, correlates results.
    """
    # Split logs by source type
    auth_logs = [l for l in log_batch if l.get("source") == "auth"]
    network_logs = [l for l in log_batch if l.get("source") == "network"]
    endpoint_logs = [l for l in log_batch if l.get("source") == "endpoint"]

    # Fan out — run all three specialists in parallel
    specialist_results = await asyncio.gather(
        run_specialist_agent("auth-analyst", AUTH_AGENT_PROMPT, auth_logs, emit=emit),
        run_specialist_agent("network-analyst", NETWORK_AGENT_PROMPT, network_logs, emit=emit),
        run_specialist_agent("malware-analyst", MALWARE_AGENT_PROMPT, endpoint_logs, emit=emit),
        return_exceptions=True,  # don't let one failure kill all three
    )

    # Filter out any exceptions, log them
    clean_results = []
    for result in specialist_results:
        if isinstance(result, Exception):
            clean_results.append({"agent": "unknown", "error": str(result)})
        else:
            clean_results.append(result)

    # Fan in — correlation pass on combined findings
    incident_report = await run_correlation_agent(clean_results, emit=emit)

    return {
        "specialist_findings": clean_results,
        "incident_report": incident_report,
    }
