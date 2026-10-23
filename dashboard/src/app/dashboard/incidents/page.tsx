"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJson, type AlertItem } from "@/lib/api";

function badge(band: string) {
  return band === "HIGH" || band === "CRITICAL" ? "badge-danger" : band === "ELEVATED" || band === "WATCH" ? "badge-warning" : "badge-normal";
}

export default function IncidentsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchJson<AlertItem[]>("/alerts?limit=100")
      .then((rows) => { if (active) setAlerts(rows); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load alert records."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <div className="page-content">
      <section className="page-heading"><div><div className="eyebrow">ALERT INVESTIGATION</div><h1>Incidents</h1><p>Alerts are generated from backend events at or above the configured risk floor. An alert is evidence for review, not a claim of confirmed compromise.</p></div><span className="status-badge badge-info">{alerts.length} recent alerts</span></section>
      {error && <div className="notice notice-danger" role="alert">Alerts unavailable: {error}</div>}
      <section className="panel panel-shadow">
        <div className="card-title"><h2 className="section-title">Recent alerts</h2></div>
        {loading ? <div className="empty-state">Loading alerts…</div> : alerts.length === 0 ? <div className="empty-state">{error ? "Alert records are unavailable." : "No alerts were returned in the latest 100 records."}</div> : (
          <div className="table-card"><table>
            <thead><tr><th>Alert</th><th>Event</th><th>Agent</th><th>Risk</th><th>Recommended response</th><th>Decision</th><th>Explanation</th></tr></thead>
            <tbody>{alerts.map((alert) => (
              <tr key={alert.id}>
                <td>{alert.id}</td>
                <td><Link href={`/dashboard/events/${encodeURIComponent(alert.event_id)}`}>{alert.event_id}</Link></td>
                <td><Link href={`/dashboard/agents/${encodeURIComponent(alert.agent_id)}`}>{alert.agent_id}</Link></td>
                <td><span className={`status-badge ${badge(alert.band)}`}>{alert.band} · {Math.round(alert.risk)}</span></td>
                <td>{alert.shadow_action}</td><td>{alert.decision ?? "Not returned"}</td>
                <td><Link href={`/dashboard/events/${encodeURIComponent(alert.event_id)}`}>{alert.message ?? "Investigate event"}</Link></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
    </div>
  );
}
