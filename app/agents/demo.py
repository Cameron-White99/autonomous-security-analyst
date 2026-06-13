"""Canned agent responses for demo mode (no ANTHROPIC_API_KEY required).

Each function returns output in the same JSON shape the real agents are
prompted to produce, derived from the actual logs in the batch so the demo
stays grounded in the ingested data. Staggered async sleeps simulate the
differing completion times of the parallel specialists.
"""

import asyncio
import random


def _timestamp_range(logs: list[dict]) -> dict:
    timestamps = sorted(l.get("timestamp", "") for l in logs if l.get("timestamp"))
    if not timestamps:
        return {"start": "", "end": ""}
    return {"start": timestamps[0], "end": timestamps[-1]}


async def specialist_findings(agent_name: str, log_data: list[dict]) -> dict:
    # Simulate real model latency — specialists finish at different times,
    # which is what makes the parallel SSE feed visually compelling.
    await asyncio.sleep(random.uniform(1.0, 3.0))

    if agent_name == "auth-analyst":
        return _auth_findings(log_data)
    if agent_name == "network-analyst":
        return _network_findings(log_data)
    if agent_name == "malware-analyst":
        return _malware_findings(log_data)
    return {"findings": [], "summary": "Unknown agent."}


def _auth_findings(logs: list[dict]) -> dict:
    failures = [l for l in logs if l.get("event_type") == "login_failure"]
    if not failures:
        return {"findings": [], "summary": "No suspicious auth activity detected."}

    by_ip: dict[str, list[dict]] = {}
    for log in failures:
        by_ip.setdefault(log.get("source_ip", "unknown"), []).append(log)

    findings = []
    for ip, entries in by_ip.items():
        attempts = max((e.get("attempt_count", 1) for e in entries), default=len(entries))
        users = sorted({e.get("user", "unknown") for e in entries})
        findings.append({
            "type": "brute_force",
            "severity": "High",
            "description": f"{attempts} failed login attempts from IP {ip} targeting {', '.join(users)}",
            "indicators": [ip, *users],
            "confidence": 92,
            "timestamp_range": _timestamp_range(entries),
        })
    return {
        "findings": findings,
        "summary": f"{len(findings)} high-confidence brute force pattern(s) detected.",
    }


def _network_findings(logs: list[dict]) -> dict:
    suspicious_ports = {4444, 8443, 1337, 6667}
    findings = []

    c2 = [l for l in logs if l.get("dst_port") in suspicious_ports]
    for log in c2:
        findings.append({
            "type": "c2_communication",
            "severity": "Critical",
            "description": (
                f"Outbound connection from {log.get('src_ip')} to {log.get('dst_ip')} "
                f"on port {log.get('dst_port')} (common C2 port)"
            ),
            "indicators": [log.get("dst_ip"), log.get("src_ip"), f"port:{log.get('dst_port')}"],
            "confidence": 88,
            "timestamp_range": _timestamp_range([log]),
        })

    exfil = [l for l in logs if l.get("bytes_out", 0) > 1_000_000 and l not in c2]
    for log in exfil:
        findings.append({
            "type": "data_exfiltration",
            "severity": "High",
            "description": (
                f"Large outbound transfer ({log.get('bytes_out'):,} bytes) from "
                f"{log.get('src_ip')} to external IP {log.get('dst_ip')}"
            ),
            "indicators": [log.get("dst_ip"), log.get("src_ip")],
            "confidence": 81,
            "timestamp_range": _timestamp_range([log]),
        })

    if not findings:
        return {"findings": [], "summary": "No suspicious network activity detected."}
    return {
        "findings": findings,
        "summary": f"{len(findings)} suspicious network pattern(s) detected.",
    }


def _malware_findings(logs: list[dict]) -> dict:
    findings = []
    for log in logs:
        cmd = (log.get("command_line") or "").lower()
        if "-enc" in cmd or "certutil" in cmd or "frombase64" in cmd:
            findings.append({
                "type": "obfuscated_execution",
                "severity": "High",
                "description": (
                    f"{log.get('process_name')} executing encoded payload on "
                    f"{log.get('hostname')} (parent: {log.get('parent_process')})"
                ),
                "indicators": [log.get("hostname"), log.get("process_name"), "-enc"],
                "confidence": 95,
                "timestamp_range": _timestamp_range([log]),
            })
        elif log.get("event_type") == "registry_modify" or "schtasks" in cmd:
            findings.append({
                "type": "persistence_mechanism",
                "severity": "Medium",
                "description": f"Persistence mechanism observed on {log.get('hostname')}",
                "indicators": [log.get("hostname"), log.get("process_name")],
                "confidence": 78,
                "timestamp_range": _timestamp_range([log]),
            })

    if not findings:
        return {"findings": [], "summary": "No suspicious endpoint activity detected."}
    return {
        "findings": findings,
        "summary": f"{len(findings)} suspicious endpoint pattern(s) detected.",
    }


async def correlation_report(specialist_results: list[dict]) -> dict:
    await asyncio.sleep(random.uniform(1.5, 2.5))

    all_findings = []
    for result in specialist_results:
        payload = result.get("findings") or {}
        all_findings.extend(payload.get("findings", []) if isinstance(payload, dict) else [])

    if not all_findings:
        return {
            "severity": "Informational",
            "title": "No Suspicious Activity Detected",
            "summary": "All three specialist analysts reviewed the log batch and found no indicators of compromise.",
            "attack_chain": [],
            "mitre_tactics": [],
            "mitre_techniques": [],
            "recommended_actions": ["Continue routine monitoring."],
            "confidence": 90,
        }

    severities = [f.get("severity") for f in all_findings]
    overall = "Critical" if "Critical" in severities else "High" if "High" in severities else "Medium"

    stage_map = {
        "brute_force": ("Initial Access", "T1110"),
        "credential_stuffing": ("Initial Access", "T1110.004"),
        "c2_communication": ("Command & Control", "T1071.001"),
        "data_exfiltration": ("Exfiltration", "T1041"),
        "obfuscated_execution": ("Execution", "T1059.001"),
        "persistence_mechanism": ("Persistence", "T1547"),
    }

    attack_chain = []
    tactics: list[str] = []
    techniques: list[str] = []
    indicators: set[str] = set()
    for finding in sorted(all_findings, key=lambda f: f.get("timestamp_range", {}).get("start", "")):
        stage, technique = stage_map.get(finding.get("type"), ("Unknown", "T1078"))
        attack_chain.append({
            "stage": stage,
            "event": finding.get("description", ""),
            "timestamp": finding.get("timestamp_range", {}).get("start", ""),
        })
        if stage not in tactics:
            tactics.append(stage)
        if technique not in techniques:
            techniques.append(technique)
        indicators.update(i for i in finding.get("indicators", []) if i)

    actions = []
    external_ips = sorted(i for i in indicators if i.count(".") == 3 and not i.startswith("10."))
    users = sorted(i for i in indicators if "@" in i)
    hosts = sorted(i for i in indicators if isinstance(i, str) and i.upper() == i and "-" in i)
    for ip in external_ips:
        actions.append(f"Block IP {ip} at perimeter firewall immediately")
    for user in users:
        actions.append(f"Reset credentials for {user}")
    for host in hosts:
        actions.append(f"Isolate {host} from network pending forensic investigation")
    if not actions:
        actions.append("Escalate to Tier 2 SOC analyst for manual review")

    return {
        "severity": overall,
        "title": " and ".join(dict.fromkeys(s.replace("&", "and") for s in tactics)) + " Activity Detected",
        "summary": (
            f"Correlated analysis of {len(all_findings)} specialist findings reconstructs a "
            f"{overall.lower()}-severity attack chain spanning {', '.join(tactics)}. "
            "Events that appear benign in isolation form a coherent intrusion sequence when correlated across sources."
        ),
        "attack_chain": attack_chain,
        "mitre_tactics": tactics,
        "mitre_techniques": techniques,
        "recommended_actions": actions,
        "confidence": 91,
    }
