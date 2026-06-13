const TACTIC_ORDER = [
  "Reconnaissance",
  "Initial Access",
  "Execution",
  "Persistence",
  "Privilege Escalation",
  "Defense Evasion",
  "Credential Access",
  "Discovery",
  "Lateral Movement",
  "Collection",
  "Command & Control",
  "Exfiltration",
  "Impact",
];

export default function MitreHeatmap({ incidents }) {
  const counts = new Map();
  for (const incident of incidents) {
    for (const tactic of incident.mitre_tactics || []) {
      const key = tactic.replace("Command and Control", "Command & Control");
      counts.set(key, (counts.get(key) || 0) + 1);
    }
  }
  const max = Math.max(1, ...counts.values());

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>MITRE ATT&amp;CK Coverage</h2>
        <span className="meta">tactic heat</span>
      </div>
      <div className="panel-body">
        {counts.size === 0 ? (
          <div className="mitre-empty">no tactics observed yet</div>
        ) : (
          <div className="mitre-grid">
            {TACTIC_ORDER.filter((t) => counts.has(t) || counts.size > 0).map((tactic) => {
              const count = counts.get(tactic) || 0;
              return (
                <div key={tactic} className="mitre-cell">
                  <span
                    className="heat"
                    style={{ opacity: count === 0 ? 0 : 0.12 + 0.5 * (count / max) }}
                  />
                  <div className="tactic">{tactic}</div>
                  <div className="count">{count} incident(s)</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
