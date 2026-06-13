const AGENTS = ["auth-analyst", "network-analyst", "malware-analyst"];

function laneState(events, agent) {
  let state = "waiting";
  for (const e of events) {
    if (e.agent !== agent) continue;
    if (e.event === "agent_start") state = "running";
    if (e.event === "agent_complete" || e.event === "agent_skipped") state = "done";
  }
  return state;
}

function describe(event) {
  switch (event.event) {
    case "analysis_start":
      return `batch received — ${event.log_count} logs, fanning out`;
    case "agent_start":
      return `started · ${event.log_count} logs`;
    case "agent_skipped":
      return "skipped · no logs of this type";
    case "agent_complete":
      return `complete · ${event.findings_count} finding(s) in ${event.processing_time_ms}ms`;
    case "correlation_start":
      return "correlating cross-source findings…";
    case "correlation_complete":
      return `correlation done · severity ${event.severity}`;
    case "complete":
      return `INCIDENT FILED · severity ${event.severity}`;
    case "error":
      return `FAILED · ${event.message}`;
    default:
      return event.event;
  }
}

export default function AgentActivityFeed({ events, status }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Agent Activity</h2>
        <span className="meta">{status === "streaming" ? "live" : status}</span>
      </div>
      <div className="panel-body">
        <div className="lanes">
          {AGENTS.map((agent) => {
            const state = status === "idle" ? "waiting" : laneState(events, agent);
            return (
              <div key={agent} className={`lane ${state}`}>
                <span className="lane-name">{agent.split("-")[0]}</span>
                {state}
              </div>
            );
          })}
        </div>

        <div className="feed">
          {events.length === 0 && (
            <div className="feed-empty">no active analysis — ingest a log batch to begin</div>
          )}
          {events.map((event, i) => (
            <div key={i} className={`feed-line ev-${event.event}`}>
              <span className="ts">
                {event.timestamp ? event.timestamp.slice(11, 19) : "--:--:--"}
              </span>
              <span>
                <span className="agent-tag">[{event.agent || "system"}]</span>{" "}
                <span className="detail">{describe(event)}</span>
              </span>
            </div>
          ))}
          {status === "streaming" && <div className="cursor-line" />}
        </div>
      </div>
    </div>
  );
}
