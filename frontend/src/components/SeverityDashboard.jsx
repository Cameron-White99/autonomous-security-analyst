import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"];
const COLORS = {
  Critical: "#ff3b5c",
  High: "#ff9636",
  Medium: "#ffd23f",
  Low: "#38bdf8",
  Informational: "#8b9bb4",
};

const tooltipStyle = {
  background: "#10151d",
  border: "1px solid #2c3848",
  fontFamily: "IBM Plex Mono, monospace",
  fontSize: 11,
};

function severityCounts(incidents) {
  return SEVERITIES.map((severity) => ({
    severity,
    count: incidents.filter((i) => i.severity === severity).length,
  }));
}

function trendData(incidents) {
  const byMinute = new Map();
  for (const incident of incidents) {
    const key = incident.created_at.slice(0, 16); // minute resolution
    byMinute.set(key, (byMinute.get(key) || 0) + 1);
  }
  return [...byMinute.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([minute, count]) => ({ time: minute.slice(11), count }));
}

export default function SeverityDashboard({ incidents }) {
  const counts = severityCounts(incidents);
  const trend = trendData(incidents);

  return (
    <>
      <div className="panel">
        <div className="stat-strip">
          {counts.map(({ severity, count }) => (
            <div key={severity} className="stat-cell">
              <div className="num" style={{ color: COLORS[severity] }}>
                {count}
              </div>
              <div className="lbl">{severity}</div>
            </div>
          ))}
        </div>
        <div className="charts-row" style={{ padding: 16 }}>
          <div>
            <div className="section-label" style={{ marginTop: 0 }}>Severity Distribution</div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={counts}>
                <CartesianGrid stroke="#1d2530" vertical={false} xAxisId={0} yAxisId={0} />
                <XAxis
                  dataKey="severity"
                  tick={{ fill: "#6b7a8c", fontSize: 10, fontFamily: "IBM Plex Mono" }}
                  axisLine={{ stroke: "#1d2530" }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#43505f", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={24}
                />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(94,242,168,0.05)" }} />
                <Bar dataKey="count" isAnimationActive={false}>
                  {counts.map(({ severity }) => (
                    <Cell key={severity} fill={COLORS[severity]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <div className="section-label" style={{ marginTop: 0 }}>Incident Trend</div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="phosphorFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5ef2a8" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#5ef2a8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1d2530" vertical={false} xAxisId={0} yAxisId={0} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: "#6b7a8c", fontSize: 10, fontFamily: "IBM Plex Mono" }}
                  axisLine={{ stroke: "#1d2530" }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#43505f", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={24}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Area
                  type="step"
                  dataKey="count"
                  stroke="#5ef2a8"
                  strokeWidth={1.5}
                  fill="url(#phosphorFill)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}
