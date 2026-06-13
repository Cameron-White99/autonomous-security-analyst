function formatWhen(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function IncidentFeed({ incidents, selectedId, onSelect }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Incident Feed</h2>
        <span className="meta">{incidents.length} filed</span>
      </div>
      <div className="incident-list">
        {incidents.length === 0 && (
          <div className="detail-empty">no incidents yet — run a scenario</div>
        )}
        {incidents.map((incident) => (
          <div
            key={incident.id}
            className={`incident-row ${incident.id === selectedId ? "selected" : ""}`}
            onClick={() => onSelect(incident.id)}
          >
            <span className={`badge ${incident.severity}`}>{incident.severity}</span>
            <span>
              <div className="title">{incident.title}</div>
              <div className="when">
                {formatWhen(incident.created_at)} · confidence {incident.overall_confidence}%
              </div>
            </span>
            <span className="meta">
              {(incident.mitre_techniques || []).length} TTPs
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
