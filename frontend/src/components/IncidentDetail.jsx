export default function IncidentDetail({ incident }) {
  if (!incident) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h2>Incident Detail</h2>
        </div>
        <div className="panel-body">
          <div className="detail-empty">select an incident to inspect the attack chain</div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>{incident.title}</h2>
        <span className={`badge ${incident.severity}`} style={{ padding: "4px 14px" }}>
          {incident.severity}
        </span>
      </div>
      <div className="panel-body">
        <p className="detail-summary">{incident.summary}</p>

        {incident.attack_chain?.length > 0 && (
          <>
            <div className="section-label">Attack Chain Reconstruction</div>
            <div className="chain">
              {incident.attack_chain.map((step, i) => (
                <div key={i} className="chain-step">
                  <span className="node" />
                  <span className="stage">{step.stage}</span>
                  <span className="event">{step.event}</span>
                  <span className="time">{(step.timestamp || "").slice(11, 19)}</span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="section-label">MITRE ATT&amp;CK Mapping</div>
        <div className="chips">
          {(incident.mitre_tactics || []).map((t) => (
            <span key={t} className="chip">{t}</span>
          ))}
          {(incident.mitre_techniques || []).map((t) => (
            <span key={t} className="chip technique">{t}</span>
          ))}
        </div>

        <div className="section-label">Recommended Response Actions</div>
        <div className="actions">
          {(incident.recommended_actions || []).map((action, i) => (
            <div key={i} className="action-item">
              <span className="idx">{String(i + 1).padStart(2, "0")}</span>
              <span>{action}</span>
            </div>
          ))}
        </div>

        {incident.agent_findings?.length > 0 && (
          <>
            <div className="section-label">Specialist Agent Findings</div>
            <div className="agent-findings-grid">
              {incident.agent_findings.map((af) => (
                <div key={af.agent_name} className="agent-finding-card">
                  <div className="name">{af.agent_name}</div>
                  <div className="stat">
                    {(af.findings?.findings || []).length} finding(s)
                    {af.processing_time_ms != null && <> · {af.processing_time_ms}ms</>}
                    {af.confidence_score != null && <> · conf {af.confidence_score}%</>}
                  </div>
                  <div className="stat">{af.findings?.summary}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
