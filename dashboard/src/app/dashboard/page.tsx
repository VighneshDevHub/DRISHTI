"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, LockKeyhole, ShieldCheck, ArrowUpRight } from "lucide-react";
import { fetchJson, type Agent, type AlertItem, type ApprovalItem, type DecoyItem, type EventItem, type OutboxItem } from "@/lib/api";

export default function OverviewPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[] | null>(null);
  const [decoys, setDecoys] = useState<DecoyItem[] | null>(null);
  const [outbox, setOutbox] = useState<OutboxItem | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      const requests = await Promise.allSettled([
        fetchJson<Agent[]>("/agents"),
        fetchJson<EventItem[]>("/events?limit=10"),
        fetchJson<AlertItem[]>("/alerts?limit=8"),
        fetchJson<ApprovalItem[]>("/approvals?status=pending"),
        fetchJson<DecoyItem[]>("/decoys"),
        fetchJson<OutboxItem>("/sim/outbox")
      ]);
      if (!active) return;
      const labels = ["Agents", "Events", "Alerts", "Approvals", "Decoys", "Outbox"];
      const failures: string[] = [];
      requests.forEach((result, index) => {
        if (result.status === "rejected") failures.push(`${labels[index]}: ${result.reason instanceof Error ? result.reason.message : "request failed"}`);
      });
      const value = <T,>(index: number): T | null => requests[index].status === "fulfilled" ? requests[index].value as T : null;
      setAgents(value<Agent[]>(0));
      setEvents(value<EventItem[]>(1));
      setAlerts(value<AlertItem[]>(2));
      setApprovals(value<ApprovalItem[]>(3));
      setDecoys(value<DecoyItem[]>(4));
      setOutbox(value<OutboxItem>(5));
      setErrors(failures);
      setLoading(false);
    }
    let refreshTimer: number | undefined;
    const onLiveEvent = () => {
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(() => void load(), 250);
    };
    window.addEventListener("drishti:live-event", onLiveEvent);
    void load();
    return () => {
      active = false;
      window.removeEventListener("drishti:live-event", onLiveEvent);
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
    };
  }, []);

  const highRiskEvents = useMemo(() => events?.filter((event) => ["ELEVATED", "HIGH", "CRITICAL"].includes(event.band)).length ?? null, [events]);
  const blockedActions = useMemo(() => events?.filter((event) => event.decision === "BLOCK").length ?? null, [events]);
  const metrics = [
    { label: "Active agents", value: agents?.length, detail: "Registered in runtime", icon: Activity, tone: "green" },
    { label: "High-risk events", value: highRiskEvents, detail: "Of the latest 10 events", icon: AlertTriangle, tone: "amber" },
    { label: "Block decisions", value: blockedActions, detail: "Latest 10 · decision, not execution proof", icon: ShieldCheck, tone: "red" },
    { label: "Pending approvals", value: approvals?.length, detail: "Awaiting operator review", icon: LockKeyhole, tone: "blue" }
  ];
  const bands = ["LOW", "WATCH", "ELEVATED", "HIGH", "CRITICAL"] as const;
  const maxBandCount = Math.max(1, ...bands.map((band) => events?.filter((event) => event.band === band).length ?? 0));

  return (
    <div className="page-content">
      <section className="page-heading command-heading">
        <div><div className="eyebrow">SEE YOUR AGENT FLEET AT A GLANCE</div><h1>AI Command Center</h1><p>Monitor agent activity, policy decisions, and runtime risk from one place.</p></div>
        <div className="heading-context"><span className="heading-live"><span className="health-dot" />Operational view</span><span>Recent activity · latest 10 events</span></div>
      </section>
      {errors.length > 0 && <div className="notice notice-danger" role="alert">Some dashboard data is unavailable: {errors.join(" · ")}</div>}
      <section className="metric-strip">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return <div className="metric-card command-metric" key={metric.label}>
            <div className="metric-topline"><span className="stat-label">{metric.label}</span><span className={`metric-icon tone-${metric.tone}`}><Icon size={16} /></span></div>
            <div className="kpi-value">{loading ? "…" : metric.value ?? "—"}</div>
            <div className="metric-detail">{metric.detail}</div>
          </div>;
        })}
      </section>

      <section className="overview-grid">
        <div className="panel command-panel event-panel">
          <div className="card-title"><div><div className="eyebrow">RUNTIME MONITOR</div><h2 className="section-title">Recent security events</h2></div><Link className="text-link" href="/dashboard/events">View event feed <ArrowUpRight size={14} /></Link></div>
          {events?.length ? <div className="table-card"><table><thead><tr><th>Time</th><th>Agent</th><th>Tool</th><th>Risk</th><th>Decision</th></tr></thead><tbody>
            {events.map((event) => <tr key={event.id}><td>{new Date(event.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td><td><Link href={`/dashboard/agents/${encodeURIComponent(event.agent_id)}`}>{event.agent_id}</Link></td><td>{event.tool}</td><td><span className={`status-badge ${event.band === "CRITICAL" || event.band === "HIGH" ? "badge-danger" : event.band === "ELEVATED" || event.band === "WATCH" ? "badge-warning" : "badge-normal"}`}>{event.band} · {Math.round(event.risk)}</span></td><td>{event.decision ?? "Not returned"}</td></tr>)}
          </tbody></table></div> : <div className="empty-state">{loading ? "Loading event feed…" : events ? "No events recorded in the recent feed." : "Event feed unavailable."}</div>}
        </div>
        <div className="panel command-panel risk-panel">
          <div className="card-title"><div><div className="eyebrow">THREAT SIGNALS</div><h2 className="section-title">Risk distribution</h2></div><span className="risk-total">{events?.length ?? "—"} <small>events</small></span></div>
          {events ? <div className="distribution-list">{bands.map((band) => {
            const count = events.filter((event) => event.band === band).length;
            return <div className="distribution-row" key={band}><div><span>{band}</span><strong>{count}</strong></div><div className="distribution-track"><span className={`distribution-fill risk-${band.toLowerCase()}`} style={{ width: `${count / maxBandCount * 100}%` }} /></div></div>;
          })}</div> : <div className="empty-state">{loading ? "Loading distribution…" : "Event distribution unavailable."}</div>}
        </div>
      </section>

      <section className="overview-grid">
        <div className="panel command-panel">
          <div className="card-title"><div><div className="eyebrow">IDENTITIES</div><h2 className="section-title">Agent posture</h2></div><Link className="text-link" href="/dashboard/agents">View fleet <ArrowUpRight size={14} /></Link></div>
          {agents?.length ? <div className="posture-list">{agents.slice(0, 6).map((agent) => <Link className="posture-row" href={`/dashboard/agents/${encodeURIComponent(agent.agent_id)}`} key={agent.agent_id}>
            <span><strong>{agent.agent_id}</strong><small>{agent.role} · risk {Math.round(agent.last_risk)}</small></span>
            <span className={`status-badge ${agent.status === "normal" ? "badge-normal" : agent.status === "restricted" ? "badge-warning" : "badge-danger"}`}>{agent.status || "normal"}</span>
          </Link>)}</div> : <div className="empty-state">{loading ? "Loading agents…" : agents ? "No registered agents." : "Agent registry unavailable."}</div>}
        </div>
        <div className="panel command-panel">
          <div className="card-title"><div><div className="eyebrow">NEEDS ATTENTION</div><h2 className="section-title">Recent alerts</h2></div><Link className="text-link" href="/dashboard/incidents">Investigate <ArrowUpRight size={14} /></Link></div>
          {alerts?.length ? <div className="posture-list">{alerts.slice(0, 5).map((alert) => <Link href={`/dashboard/events/${encodeURIComponent(alert.event_id)}`} className="alert-row" key={alert.id}>
            <span className={`status-badge ${alert.band === "HIGH" || alert.band === "CRITICAL" ? "badge-danger" : "badge-warning"}`}>{alert.band}</span>
            <span><strong>{alert.agent_id}</strong><small>{alert.message ?? alert.shadow_action}</small></span>
          </Link>)}</div> : <div className="empty-state">{loading ? "Loading alerts…" : alerts ? "No alerts in the recent feed." : "Alerts unavailable."}</div>}
        </div>
      </section>

      <section className="overview-grid">
        <div className="panel command-panel">
          <div className="card-title"><div><div className="eyebrow">DECEPTION LAYER</div><h2 className="section-title">Decoy tripwires</h2></div><span className="status-badge badge-info">Backend registry</span></div>
          {decoys?.length ? <div className="posture-list">{decoys.map((decoy) => <div className="posture-row" key={decoy.id}><span><strong>{decoy.kind}</strong><small>{decoy.description}</small></span><span className={`status-badge ${decoy.hits ? "badge-danger" : "badge-normal"}`}>{decoy.hits} hits</span></div>)}</div> : <div className="empty-state">{loading ? "Loading decoy status…" : decoys ? "No decoys are registered." : "Decoy status unavailable."}</div>}
        </div>
        <div className="panel command-panel">
          <div className="card-title"><div><div className="eyebrow">DEMO ENVIRONMENT</div><h2 className="section-title">Simulated outbox</h2></div><span className="status-badge badge-warning">Mock integration</span></div>
          {outbox ? <div className="metric-strip metric-strip-two"><div><div className="stat-label">Messages</div><div className="kpi-value">{outbox.messages}</div></div><div><div className="stat-label">Bytes</div><div className="kpi-value">{outbox.bytes}</div></div></div> : <div className="empty-state">{loading ? "Loading mock outbox…" : "Outbox unavailable."}</div>}
        </div>
      </section>
    </div>
  );
}
