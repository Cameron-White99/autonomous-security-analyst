import { useEffect, useRef, useState } from "react";
import { streamUrl } from "../api.js";

/**
 * Subscribes to the SSE agent-activity feed for a job.
 * Returns { events, status, incidentId } where status is
 * "idle" | "streaming" | "complete" | "error".
 */
export default function useAgentStream(jobId) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");
  const [incidentId, setIncidentId] = useState(null);
  const sourceRef = useRef(null);

  useEffect(() => {
    if (!jobId) return undefined;

    setEvents([]);
    setIncidentId(null);
    setStatus("streaming");

    const source = new EventSource(streamUrl(jobId));
    sourceRef.current = source;

    source.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      setEvents((prev) => [...prev, event]);
      if (event.event === "complete") {
        setIncidentId(event.incident_id);
        setStatus("complete");
        source.close();
      } else if (event.event === "error") {
        setStatus("error");
        source.close();
      }
    };

    source.onerror = () => {
      // The server closes the stream after the terminal event; only treat
      // as an error if we never reached one.
      setStatus((prev) => (prev === "streaming" ? "error" : prev));
      source.close();
    };

    return () => source.close();
  }, [jobId]);

  return { events, status, incidentId };
}
