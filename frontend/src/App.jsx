import { useCallback, useEffect, useState } from "react";
import { fetchIncident, fetchIncidents, ingestBatch, SCENARIOS } from "./api.js";
import useAgentStream from "./hooks/useAgentStream.js";
import AgentActivityFeed from "./components/AgentActivityFeed.jsx";
import IncidentFeed from "./components/IncidentFeed.jsx";
import IncidentDetail from "./components/IncidentDetail.jsx";
import SeverityDashboard from "./components/SeverityDashboard.jsx";
import MitreHeatmap from "./components/MitreHeatmap.jsx";

export default function App() {
  const [jobId, setJobId] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);

  const { events, status, incidentId } = useAgentStream(jobId);

  const refreshIncidents = useCallback(async () => {
    try {
      setIncidents(await fetchIncidents());
    } catch {
      // backend not up yet — leave the feed empty
    }
  }, []);

  useEffect(() => {
    refreshIncidents();
  }, [refreshIncidents]);

  // When an analysis completes, refresh the feed and open the new incident
  useEffect(() => {
    if (status === "complete" && incidentId) {
      refreshIncidents().then(() => setSelectedId(incidentId));
    }
  }, [status, incidentId, refreshIncidents]);

  useEffect(() => {
    if (!selectedId) return;
    fetchIncident(selectedId).then(setDetail).catch(() => setDetail(null));
  }, [selectedId]);

  async function runScenario(key) {
    const { batch } = SCENARIOS[key];
    const { job_id } = await ingestBatch(batch);
    setJobId(job_id);
  }

  const busy = status === "streaming";

  return (
    <div className="shell">
      <header className="topbar">
        <h1>
          ASA<span>_</span>
        </h1>
        <span className="sub">
          Autonomous Security Analyst — parallel multi-agent SOC
        </span>
        <span className="status-pill">
          <span className="dot" /> {busy ? "analysing" : "monitoring"}
        </span>
      </header>

      <div className="layout">
        <aside className="side-col">
          <div className="panel">
            <div className="panel-head">
              <h2>Ingest Log Batch</h2>
              <span className="meta">demo scenarios</span>
            </div>
            <div className="panel-body scenario-row">
              {Object.entries(SCENARIOS).map(([key, { label }]) => (
                <button
                  key={key}
                  className="btn"
                  disabled={busy}
                  onClick={() => runScenario(key)}
                >
                  {label} <span className="arrow">→</span>
                </button>
              ))}
            </div>
          </div>

          <AgentActivityFeed events={events} status={status} />
        </aside>

        <main className="main-col">
          <SeverityDashboard incidents={incidents} />
          <IncidentFeed
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <IncidentDetail incident={detail} />
          <MitreHeatmap incidents={incidents} />
        </main>
      </div>
    </div>
  );
}
