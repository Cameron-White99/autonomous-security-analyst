"""Tests for the parallel agent orchestrator using mocked Anthropic responses."""

import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agents import orchestrator
from app.config import Settings

FIXTURES = Path(__file__).parent / "fixtures" / "sample_logs"


def load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())["logs"]


class FakeAnthropicClient:
    """Mimics AsyncAnthropic.messages.create with a configurable delay and payload."""

    def __init__(self, payload: dict | str, delay: float = 0.05):
        self.payload = payload
        self.delay = delay
        self.calls: list[dict] = []
        self.call_windows: list[tuple[float, float]] = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        started = time.perf_counter()
        self.calls.append(kwargs)
        await asyncio.sleep(self.delay)
        self.call_windows.append((started, time.perf_counter()))
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


@pytest.fixture
def live_mode(monkeypatch):
    """Force non-demo mode and install a fake client; returns the fake for assertions."""
    fake = FakeAnthropicClient({"findings": [], "summary": "clean"})
    monkeypatch.setattr(
        orchestrator, "get_settings",
        lambda: Settings(anthropic_api_key="test-key", demo_mode=False, _env_file=None),
    )
    monkeypatch.setattr(orchestrator, "get_client", lambda: fake)
    return fake


@pytest.fixture
def demo_settings(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "get_settings",
        lambda: Settings(anthropic_api_key=None, demo_mode=True, _env_file=None),
    )


async def test_specialists_run_in_parallel(live_mode):
    """All three specialist calls must overlap in time (fan-out via asyncio.gather)."""
    logs = load_fixture("lateral_movement.json")
    await orchestrator.analyse_log_batch(logs)

    # 3 specialists + 1 correlation call
    assert len(live_mode.call_windows) == 4
    specialist_windows = live_mode.call_windows[:3]
    latest_start = max(w[0] for w in specialist_windows)
    earliest_end = min(w[1] for w in specialist_windows)
    assert latest_start < earliest_end, "specialist calls did not overlap — not parallel"


async def test_correlation_runs_after_specialists(live_mode):
    logs = load_fixture("lateral_movement.json")
    await orchestrator.analyse_log_batch(logs)

    correlation_start = live_mode.call_windows[3][0]
    specialist_ends = [w[1] for w in live_mode.call_windows[:3]]
    assert correlation_start >= max(specialist_ends)


async def test_specialist_parses_json_findings(live_mode):
    live_mode.payload = {"findings": [{"type": "brute_force", "severity": "High"}], "summary": "one"}
    result = await orchestrator.run_specialist_agent(
        "auth-analyst", "prompt", load_fixture("brute_force.json"),
    )
    assert result["agent"] == "auth-analyst"
    assert result["findings"]["findings"][0]["type"] == "brute_force"
    assert result["processing_time_ms"] >= 0


async def test_specialist_handles_malformed_json(live_mode):
    live_mode.payload = "I am not JSON, sorry."
    result = await orchestrator.run_specialist_agent("auth-analyst", "prompt", [{"source": "auth"}])
    assert result["findings"]["parse_error"] is True
    assert result["findings"]["raw"] == "I am not JSON, sorry."


async def test_empty_log_subset_skips_api_call(live_mode):
    result = await orchestrator.run_specialist_agent("network-analyst", "prompt", [])
    assert live_mode.calls == []
    assert result["findings"]["findings"] == []


async def test_one_specialist_failure_does_not_kill_batch(live_mode, monkeypatch):
    original = orchestrator.run_specialist_agent

    async def flaky(agent_name, system_prompt, log_data, model=orchestrator.SPECIALIST_MODEL, emit=None):
        if agent_name == "network-analyst":
            raise RuntimeError("API exploded")
        return await original(agent_name, system_prompt, log_data, model=model, emit=emit)

    monkeypatch.setattr(orchestrator, "run_specialist_agent", flaky)
    result = await orchestrator.analyse_log_batch(load_fixture("lateral_movement.json"))

    agents = [r.get("agent") for r in result["specialist_findings"]]
    assert "auth-analyst" in agents and "malware-analyst" in agents
    errors = [r for r in result["specialist_findings"] if "error" in r]
    assert len(errors) == 1
    assert "API exploded" in errors[0]["error"]
    assert "incident_report" in result


async def test_emit_callback_receives_lifecycle_events(live_mode):
    events = []

    async def emit(event):
        events.append(event)

    await orchestrator.analyse_log_batch(load_fixture("lateral_movement.json"), emit=emit)

    names = [e["event"] for e in events]
    assert names.count("agent_start") == 3
    assert names.count("agent_complete") == 3
    assert "correlation_start" in names
    assert "correlation_complete" in names
    # all three specialists start before any completes (parallelism visible in the stream)
    assert max(i for i, n in enumerate(names) if n == "agent_start") < min(
        i for i, n in enumerate(names) if n == "agent_complete"
    )


async def test_demo_mode_end_to_end(demo_settings):
    """Demo mode produces a full incident report with no API client at all."""
    result = await orchestrator.analyse_log_batch(load_fixture("lateral_movement.json"))

    report = result["incident_report"]
    assert report["severity"] in {"Critical", "High", "Medium", "Low", "Informational"}
    assert report["attack_chain"]
    assert report["mitre_techniques"]
    assert any("185.220.101.47" in a for a in report["recommended_actions"])
