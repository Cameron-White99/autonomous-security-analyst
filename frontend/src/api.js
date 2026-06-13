// API client + demo scenario payloads.
// VITE_API_URL is used in production (Cloud Run URL); the Vite dev server
// proxies these paths to localhost:8000 during development.
export const API_BASE = import.meta.env.VITE_API_URL || "";

export async function ingestBatch(batch) {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(batch),
  });
  if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
  return res.json();
}

export async function fetchIncidents() {
  const res = await fetch(`${API_BASE}/incidents`);
  if (!res.ok) throw new Error(`Fetch incidents failed: ${res.status}`);
  return res.json();
}

export async function fetchIncident(id) {
  const res = await fetch(`${API_BASE}/incidents/${id}`);
  if (!res.ok) throw new Error(`Fetch incident failed: ${res.status}`);
  return res.json();
}

export function streamUrl(jobId) {
  return `${API_BASE}/stream/${jobId}`;
}

// ── Demo log batches (mirror tests/fixtures/sample_logs) ─────────────
export const SCENARIOS = {
  brute_force: {
    label: "Brute Force Attack",
    batch: {
      source: "demo",
      logs: [
        { timestamp: "2026-06-12T03:14:22Z", source: "auth", event_type: "login_failure", user: "admin@company.com", source_ip: "185.220.101.47", geo: { country: "RU", city: "Moscow" }, attempt_count: 47 },
        { timestamp: "2026-06-12T03:14:55Z", source: "auth", event_type: "login_failure", user: "admin@company.com", source_ip: "185.220.101.47", geo: { country: "RU", city: "Moscow" }, attempt_count: 52 },
        { timestamp: "2026-06-12T03:15:10Z", source: "auth", event_type: "login_success", user: "admin@company.com", source_ip: "185.220.101.47", geo: { country: "RU", city: "Moscow" } },
      ],
    },
  },
  c2_communication: {
    label: "C2 Communication",
    batch: {
      source: "demo",
      logs: [
        { timestamp: "2026-06-12T03:15:01Z", source: "network", src_ip: "10.0.1.45", dst_ip: "185.220.101.47", dst_port: 4444, protocol: "TCP", bytes_out: 2048576, action: "allow" },
        { timestamp: "2026-06-12T03:16:30Z", source: "network", src_ip: "10.0.1.45", dst_ip: "185.220.101.47", dst_port: 4444, protocol: "TCP", bytes_out: 512, action: "allow" },
        { timestamp: "2026-06-12T03:15:45Z", source: "endpoint", hostname: "WORKSTATION-042", event_type: "process_create", parent_process: "explorer.exe", process_name: "powershell.exe", command_line: "powershell -enc JABjAGwAaQBlAG4AdA...", user: "jsmith" },
      ],
    },
  },
  lateral_movement: {
    label: "Full Kill Chain",
    batch: {
      source: "demo",
      logs: [
        { timestamp: "2026-06-12T03:14:22Z", source: "auth", event_type: "login_failure", user: "admin@company.com", source_ip: "185.220.101.47", geo: { country: "RU", city: "Moscow" }, attempt_count: 47 },
        { timestamp: "2026-06-12T03:15:01Z", source: "network", src_ip: "10.0.1.45", dst_ip: "185.220.101.47", dst_port: 4444, protocol: "TCP", bytes_out: 2048576, action: "allow" },
        { timestamp: "2026-06-12T03:15:45Z", source: "endpoint", hostname: "WORKSTATION-042", event_type: "process_create", parent_process: "explorer.exe", process_name: "powershell.exe", command_line: "powershell -enc JABjAGwAaQBlAG4AdA...", user: "jsmith" },
        { timestamp: "2026-06-12T03:17:02Z", source: "network", src_ip: "10.0.1.45", dst_ip: "10.0.1.60", dst_port: 445, protocol: "TCP", bytes_out: 1843200, action: "allow" },
        { timestamp: "2026-06-12T03:18:11Z", source: "endpoint", hostname: "FILESERVER-01", event_type: "process_create", parent_process: "services.exe", process_name: "schtasks.exe", command_line: "schtasks /create /tn UpdateCheck /tr c:\\temp\\svc.exe /sc onstart", user: "admin" },
      ],
    },
  },
};
