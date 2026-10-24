"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  ExternalLink,
  Filter,
  Flame,
  Gauge,
  LockKeyhole,
  Radio,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Zap
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell
} from "recharts";
import {
  fetchJson,
  type Agent,
  type AlertItem,
  type ApprovalItem,
  type DecoyItem,
  type EventItem,
  type OutboxItem
} from "@/lib/api";

const BAND_COLORS: Record<string, string> = {
  LOW: "#10b981",
  WATCH: "#0ea5e9",
  ELEVATED: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444"
};

const DECISION_COLORS: Record<string, string> = {
  ALLOW: "#10b981",
  BLOCK: "#ef4444",
  REVIEW: "#f59e0b",
  OBSERVE: "#3b82f6"
};

export default function OverviewPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[] | null>(null);
  const [decoys, setDecoys] = useState<DecoyItem[] | null>(null);
  const [outbox, setOutbox] = useState<OutboxItem | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  // Table filter state
  const [eventFilter, setEventFilter] = useState<"ALL" | "HIGH_RISK" | "BLOCK" | "REVIEW">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [chartMode, setChartMode] = useState<"COMBINED" | "RISK">("COMBINED");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      const requests = await Promise.allSettled([
        fetchJson<Agent[]>("/agents"),
        fetchJson<EventItem[]>("/events?limit=100"),
        fetchJson<AlertItem[]>("/alerts?limit=10"),
        fetchJson<ApprovalItem[]>("/approvals?status=pending"),
        fetchJson<DecoyItem[]>("/decoys"),
        fetchJson<OutboxItem>("/sim/outbox")
      ]);
      if (!active) return;
      const labels = ["Agents", "Events", "Alerts", "Approvals", "Decoys", "Outbox"];
      const failures: string[] = [];
      requests.forEach((result, index) => {
        if (result.status === "rejected") {
          failures.push(
            `${labels[index]}: ${result.reason instanceof Error ? result.reason.message : "request failed"}`
          );
        }
      });
      const value = <T,>(index: number): T | null =>
        requests[index].status === "fulfilled" ? (requests[index].value as T) : null;

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

  // Aggregated analytical statistics
  const totalEvents = events?.length ?? 0;
  const highRiskEvents = useMemo(
    () => events?.filter((ev) => ["ELEVATED", "HIGH", "CRITICAL"].includes(ev.band)).length ?? 0,
    [events]
  );
  const blockedEvents = useMemo(
    () => events?.filter((ev) => ev.decision === "BLOCK").length ?? 0,
    [events]
  );
  const reviewEvents = useMemo(
    () => events?.filter((ev) => ev.decision === "REVIEW").length ?? 0,
    [events]
  );
  const allowedEvents = useMemo(
    () => events?.filter((ev) => ev.decision === "ALLOW").length ?? 0,
    [events]
  );

  const blockRate = totalEvents > 0 ? ((blockedEvents / totalEvents) * 100).toFixed(1) : "0.0";
  const complianceRate =
    totalEvents > 0 ? (((allowedEvents) / totalEvents) * 100).toFixed(1) : "100.0";

  const totalDecoyHits = useMemo(
    () => decoys?.reduce((sum, d) => sum + (d.hits || 0), 0) ?? 0,
    [decoys]
  );

  const avgRisk = useMemo(() => {
    if (!events?.length) return 0;
    const sum = events.reduce((acc, ev) => acc + (ev.risk || 0), 0);
    return Math.round((sum / events.length) * 10) / 10;
  }, [events]);

  const maxRecordedRisk = useMemo(() => {
    if (!events?.length) return 0;
    return Math.round(Math.max(...events.map((ev) => ev.risk || 0)) * 10) / 10;
  }, [events]);

  // Timeline / Velocity Chart data: bucket events chronologically into groups
  const trajectoryData = useMemo(() => {
    if (!events || events.length === 0) return [];
    // Chronological order (oldest to newest)
    const sorted = [...events].reverse();
    const bucketCount = Math.min(18, Math.max(6, Math.floor(sorted.length / 5)));
    const bucketSize = Math.max(1, Math.floor(sorted.length / bucketCount));

    const points: Array<{
      time: string;
      events: number;
      avgRisk: number;
      maxRisk: number;
      tool: string;
      band: string;
    }> = [];

    for (let i = 0; i < sorted.length; i += bucketSize) {
      const chunk = sorted.slice(i, i + bucketSize);
      if (chunk.length === 0) continue;
      const last = chunk[chunk.length - 1];
      const timeStr = new Date(last.ts).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
      const avg = Math.round((chunk.reduce((acc, e) => acc + e.risk, 0) / chunk.length) * 10) / 10;
      const max = Math.round(Math.max(...chunk.map((e) => e.risk)) * 10) / 10;
      const worstBand = chunk.some((e) => e.band === "CRITICAL")
        ? "CRITICAL"
        : chunk.some((e) => e.band === "HIGH")
        ? "HIGH"
        : chunk.some((e) => e.band === "ELEVATED")
        ? "ELEVATED"
        : chunk.some((e) => e.band === "WATCH")
        ? "WATCH"
        : "LOW";

      points.push({
        time: timeStr,
        events: chunk.length,
        avgRisk: avg,
        maxRisk: max,
        tool: chunk[0]?.tool || "runtime",
        band: worstBand
      });
    }
    return points;
  }, [events]);

  // Decision Breakdown Donut Data
  const decisionDonutData = useMemo(() => {
    if (!events || events.length === 0) {
      return [{ name: "No telemetry", value: 1, color: "#cbd5e1" }];
    }
    const counts: Record<string, number> = { ALLOW: 0, BLOCK: 0, REVIEW: 0, OBSERVE: 0 };
    events.forEach((e) => {
      const dec = e.decision || "ALLOW";
      if (dec in counts) counts[dec] += 1;
      else counts.OBSERVE += 1;
    });

    const data = [
      { name: "ALLOW", value: counts.ALLOW, color: DECISION_COLORS.ALLOW },
      { name: "BLOCK", value: counts.BLOCK, color: DECISION_COLORS.BLOCK },
      { name: "REVIEW", value: counts.REVIEW, color: DECISION_COLORS.REVIEW },
      { name: "OBSERVE", value: counts.OBSERVE, color: DECISION_COLORS.OBSERVE }
    ].filter((item) => item.value > 0);

    return data.length > 0 ? data : [{ name: "ALLOW", value: 1, color: DECISION_COLORS.ALLOW }];
  }, [events]);

  // Risk Band Distribution Counts
  const bands = ["LOW", "WATCH", "ELEVATED", "HIGH", "CRITICAL"] as const;
  const bandCounts = useMemo(() => {
    const counts: Record<string, number> = { LOW: 0, WATCH: 0, ELEVATED: 0, HIGH: 0, CRITICAL: 0 };
    events?.forEach((e) => {
      if (e.band in counts) counts[e.band] += 1;
    });
    return counts;
  }, [events]);

  // Top Tools Ranking
  const topTools = useMemo(() => {
    if (!events || events.length === 0) return [];
    const map = new Map<string, { count: number; maxRisk: number; band: string }>();
    events.forEach((ev) => {
      const existing = map.get(ev.tool) || { count: 0, maxRisk: 0, band: "LOW" };
      existing.count += 1;
      if (ev.risk > existing.maxRisk) {
        existing.maxRisk = ev.risk;
        existing.band = ev.band;
      }
      map.set(ev.tool, existing);
    });

    return Array.from(map.entries())
      .map(([tool, stats]) => ({ tool, ...stats }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [events]);

  // Filtered live events for telemetry stream
  const filteredEvents = useMemo(() => {
    if (!events) return [];
    return events.filter((ev) => {
      // Type filter
      if (eventFilter === "HIGH_RISK" && !["ELEVATED", "HIGH", "CRITICAL"].includes(ev.band)) {
        return false;
      }
      if (eventFilter === "BLOCK" && ev.decision !== "BLOCK") {
        return false;
      }
      if (eventFilter === "REVIEW" && ev.decision !== "REVIEW") {
        return false;
      }
      // Text search
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesAgent = ev.agent_id.toLowerCase().includes(query);
        const matchesTool = ev.tool.toLowerCase().includes(query);
        const matchesResource = (ev.resource || ev.destination || "").toLowerCase().includes(query);
        const matchesBand = ev.band.toLowerCase().includes(query);
        if (!matchesAgent && !matchesTool && !matchesResource && !matchesBand) {
          return false;
        }
      }
      return true;
    });
  }, [events, eventFilter, searchQuery]);

  return (
    <div className="page-content">
      {/* Executive Command Header */}
      <section className="page-heading command-heading">
        <div>
          <div className="eyebrow flex items-center gap-2">
            <Radio size={12} className="text-emerald-500 animate-pulse" />
            LIVE RUNTIME COMMAND CENTER
          </div>
          <h1>Security & Threat Analytics</h1>
          <p>
            Real-time behavioral telemetry, policy enforcement decisions, and deception signals across
            your autonomous fleet.
          </p>
        </div>
        <div className="heading-context">
          <div className="flex items-center gap-2">
            <span className="heading-live">
              <span className="health-dot" />
              Live Telemetry Stream
            </span>
            <span className="text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 font-medium border border-slate-200">
              {totalEvents} records synced
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>Avg Risk: <strong className="text-slate-800">{avgRisk}</strong> / 100</span>
            <span>·</span>
            <span>Peak Risk: <strong className="text-slate-800">{maxRecordedRisk}</strong> / 100</span>
          </div>
        </div>
      </section>

      {errors.length > 0 && (
        <div className="notice notice-danger" role="alert">
          Some telemetry sources are unavailable: {errors.join(" · ")}
        </div>
      )}

      {/* KPI Metric Strip */}
      <section className="metric-strip">
        <div className="metric-card command-metric">
          <div className="metric-topline">
            <span className="stat-label">Active Fleet</span>
            <span className="metric-icon tone-green">
              <Shield size={16} />
            </span>
          </div>
          <div className="kpi-value">{loading ? "…" : agents?.length ?? 0}</div>
          <div className="metric-detail flex items-center justify-between">
            <span>Monitored in runtime</span>
            <span className="text-emerald-600 font-semibold">100% Online</span>
          </div>
        </div>

        <div className="metric-card command-metric">
          <div className="metric-topline">
            <span className="stat-label">Processed Invocations</span>
            <span className="metric-icon tone-blue">
              <Activity size={16} />
            </span>
          </div>
          <div className="kpi-value">{loading ? "…" : totalEvents}</div>
          <div className="metric-detail flex items-center justify-between">
            <span>In latest 100 window</span>
            <span className="text-blue-600 font-semibold">{complianceRate}% Compliant</span>
          </div>
        </div>

        <div className="metric-card command-metric">
          <div className="metric-topline">
            <span className="stat-label">Enforcement Rate</span>
            <span className="metric-icon tone-purple">
              <ShieldCheck size={16} />
            </span>
          </div>
          <div className="kpi-value">
            {loading ? "…" : blockedEvents > 0 ? `${blockRate}%` : "0.0%"}
          </div>
          <div className="metric-detail flex items-center justify-between">
            <span>{blockedEvents} blocked · {reviewEvents} review</span>
            <span className={blockedEvents > 0 ? "text-rose-600 font-semibold" : "text-slate-500"}>
              {blockedEvents > 0 ? "Action Taken" : "Clean Run"}
            </span>
          </div>
        </div>

        <div className="metric-card command-metric">
          <div className="metric-topline">
            <span className="stat-label">High-Risk Threats</span>
            <span className="metric-icon tone-amber">
              <AlertTriangle size={16} />
            </span>
          </div>
          <div className="kpi-value">{loading ? "…" : highRiskEvents}</div>
          <div className="metric-detail flex items-center justify-between">
            <span>Score ≥ 40 threshold</span>
            <span className={highRiskEvents > 0 ? "text-amber-600 font-semibold" : "text-emerald-600 font-semibold"}>
              {highRiskEvents > 0 ? "Under Watch" : "Safe Posture"}
            </span>
          </div>
        </div>

        <div className="metric-card command-metric">
          <div className="metric-topline">
            <span className="stat-label">Tripwire Decoys</span>
            <span className="metric-icon tone-red">
              <LockKeyhole size={16} />
            </span>
          </div>
          <div className="kpi-value">{loading ? "…" : decoys?.length ?? 0}</div>
          <div className="metric-detail flex items-center justify-between">
            <span>Active canary traps</span>
            <span className={totalDecoyHits > 0 ? "text-rose-600 font-semibold" : "text-emerald-600 font-semibold"}>
              {totalDecoyHits} hits
            </span>
          </div>
        </div>
      </section>

      {/* Analytics Row 1: Threat Trajectory & Policy Enforcement Donut */}
      <section className="overview-grid">
        {/* Threat Trajectory / Velocity Chart */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <Activity size={12} className="text-blue-500" />
                TEMPORAL TELEMETRY
              </div>
              <h2 className="section-title">Threat Velocity & Risk Trajectory</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Event frequency alongside peak risk score across runtime execution timeline
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
                <button
                  type="button"
                  onClick={() => setChartMode("COMBINED")}
                  className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                    chartMode === "COMBINED"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Combined
                </button>
                <button
                  type="button"
                  onClick={() => setChartMode("RISK")}
                  className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                    chartMode === "RISK"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Risk Only
                </button>
              </div>
              <Link className="text-link ml-1" href="/dashboard/events">
                Feed <ArrowUpRight size={13} />
              </Link>
            </div>
          </div>

          <div style={{ width: "100%", height: 260 }} className="mt-2">
            {!mounted || loading ? (
              <div className="empty-state">Loading timeline trajectory…</div>
            ) : trajectoryData.length === 0 ? (
              <div className="empty-state">No temporal telemetry recorded yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={trajectoryData}
                  margin={{ top: 10, right: 12, left: -18, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="invocationsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <YAxis
                    yAxisId="riskAxis"
                    domain={[0, 100]}
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  {chartMode === "COMBINED" && (
                    <YAxis
                      yAxisId="eventsAxis"
                      orientation="right"
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                    />
                  )}
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="custom-recharts-tooltip">
                          <div className="custom-recharts-tooltip-title">
                            Time: {data.time}
                          </div>
                          <div className="custom-recharts-tooltip-row">
                            <span className="text-slate-300">Tool invoked:</span>
                            <code className="text-blue-400 font-mono text-xs">{data.tool}</code>
                          </div>
                          <div className="custom-recharts-tooltip-row">
                            <span className="text-slate-300">Peak Risk:</span>
                            <span
                              className="font-bold text-xs"
                              style={{ color: BAND_COLORS[data.band] || "#10b981" }}
                            >
                              {data.maxRisk} ({data.band})
                            </span>
                          </div>
                          <div className="custom-recharts-tooltip-row">
                            <span className="text-slate-300">Invocations in window:</span>
                            <span className="font-semibold text-slate-100">{data.events}</span>
                          </div>
                        </div>
                      );
                    }}
                  />
                  {chartMode === "COMBINED" && (
                    <Area
                      yAxisId="eventsAxis"
                      type="monotone"
                      dataKey="events"
                      name="Invocations"
                      stroke="#3b82f6"
                      strokeWidth={1.8}
                      fillOpacity={1}
                      fill="url(#invocationsFill)"
                    />
                  )}
                  <Area
                    yAxisId="riskAxis"
                    type="monotone"
                    dataKey="maxRisk"
                    name="Peak Risk"
                    stroke="#ef4444"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#riskFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100 mt-2">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                Peak Risk Score (0-100)
              </span>
              {chartMode === "COMBINED" && (
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
                  Invocation Volume
                </span>
              )}
            </div>
            <span>Adaptive sampling · 100 event window</span>
          </div>
        </div>

        {/* Policy Enforcement Donut */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <ShieldCheck size={12} className="text-emerald-500" />
                GOVERNANCE ENGINE
              </div>
              <h2 className="section-title">Runtime Policy Enforcement</h2>
              <p className="text-xs text-slate-500 mt-0.5">Decision distribution across incoming actions</p>
            </div>
            <Link className="text-link" href="/dashboard/enforcement">
              Policies <ArrowUpRight size={13} />
            </Link>
          </div>

          <div className="relative flex items-center justify-center" style={{ height: 200 }}>
            {!mounted || loading ? (
              <div className="empty-state">Loading policy stats…</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={decisionDonutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={58}
                    outerRadius={82}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {decisionDonutData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="#ffffff" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const item = payload[0];
                      const pct = totalEvents > 0 ? (((Number(item.value) || 0) / totalEvents) * 100).toFixed(1) : 0;
                      return (
                        <div className="custom-recharts-tooltip">
                          <div className="font-semibold text-xs flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full" style={{ background: item.payload.color }} />
                            {item.name}: {item.value} actions ({pct}%)
                          </div>
                        </div>
                      );
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}

            {/* Donut Center KPI */}
            {mounted && !loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-bold tracking-tight text-slate-900">
                  {complianceRate}%
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Compliant
                </span>
              </div>
            )}
          </div>

          {/* Donut Decision Legend */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-50/60 border border-emerald-100">
              <span className="flex items-center gap-1.5 text-emerald-800 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                ALLOW
              </span>
              <strong className="text-emerald-900">{allowedEvents}</strong>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-rose-50/60 border border-rose-100">
              <span className="flex items-center gap-1.5 text-rose-800 font-medium">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                BLOCK
              </span>
              <strong className="text-rose-900">{blockedEvents}</strong>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50/60 border border-amber-100">
              <span className="flex items-center gap-1.5 text-amber-800 font-medium">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                REVIEW
              </span>
              <strong className="text-amber-900">{reviewEvents}</strong>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200">
              <span className="flex items-center gap-1.5 text-slate-700 font-medium">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                OBSERVE
              </span>
              <strong className="text-slate-800">
                {Math.max(0, totalEvents - (allowedEvents + blockedEvents + reviewEvents))}
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* Analytics Row 2: Severity Distribution & Top Attack Surface Tools */}
      <section className="overview-grid">
        {/* Risk Band Severity Distribution */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <Flame size={12} className="text-amber-500" />
                RISK CLASSIFICATION
              </div>
              <h2 className="section-title">Fleet Risk Band Distribution</h2>
              <p className="text-xs text-slate-500 mt-0.5">Classification breakdown across 5 severity thresholds</p>
            </div>
            <span className="risk-total">
              {totalEvents} <small>events</small>
            </span>
          </div>

          <div className="distribution-list mt-2">
            {bands.map((band) => {
              const count = bandCounts[band];
              const pct = totalEvents > 0 ? ((count / totalEvents) * 100).toFixed(1) : "0.0";
              const rangeDesc =
                band === "LOW"
                  ? "0 - 20 · Safe"
                  : band === "WATCH"
                  ? "21 - 40 · Minor variance"
                  : band === "ELEVATED"
                  ? "41 - 60 · Tool mismatch"
                  : band === "HIGH"
                  ? "61 - 80 · Exfiltration risk"
                  : "81 - 100 · Critical alert";

              return (
                <div className="distribution-row" key={band}>
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ background: BAND_COLORS[band] }}
                      />
                      <strong className="text-slate-800">{band}</strong>
                      <span className="text-slate-400 font-normal">({rangeDesc})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 font-mono text-[11px]">{pct}%</span>
                      <strong className="text-slate-900 font-mono">{count}</strong>
                    </div>
                  </div>
                  <div className="distribution-track">
                    <span
                      className="distribution-fill"
                      style={{
                        width: `${Math.max(count > 0 ? 3 : 0, (count / (totalEvents || 1)) * 100)}%`,
                        background: BAND_COLORS[band]
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100 mt-4">
            <span>Deterministic multi-lens risk fusion (0-100)</span>
            <span className="font-semibold text-slate-700">Highest observed: {maxRecordedRisk}</span>
          </div>
        </div>

        {/* Top Tools Attack Surface Exposure */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <Zap size={12} className="text-blue-500" />
                SURFACE EXPOSURE
              </div>
              <h2 className="section-title">Top Invoked Tools & Threat Level</h2>
              <p className="text-xs text-slate-500 mt-0.5">Most frequent capabilities & highest risk recorded</p>
            </div>
            <Link className="text-link" href="/dashboard/events">
              All tools <ArrowUpRight size={13} />
            </Link>
          </div>

          <div className="flex flex-col gap-3 mt-2">
            {topTools.length === 0 ? (
              <div className="empty-state">No tool activity recorded yet.</div>
            ) : (
              topTools.map((toolItem) => {
                const maxToolCalls = topTools[0]?.count || 1;
                const toolPct = Math.round((toolItem.count / maxToolCalls) * 100);
                const isElevated = toolItem.maxRisk >= 40;

                return (
                  <div
                    key={toolItem.tool}
                    className="p-2.5 rounded-lg border border-slate-100 hover:border-slate-200 transition-colors bg-slate-50/50"
                  >
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <code className="text-xs font-semibold text-slate-900 truncate font-mono">
                          {toolItem.tool}
                        </code>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                          className={`status-badge text-[10px] ${
                            isElevated ? "badge-danger" : "badge-normal"
                          }`}
                        >
                          Risk {toolItem.maxRisk} · {toolItem.band}
                        </span>
                        <span className="font-semibold text-slate-700 font-mono">
                          {toolItem.count} calls
                        </span>
                      </div>
                    </div>
                    <div className="distribution-track" style={{ height: 5 }}>
                      <span
                        className="distribution-fill"
                        style={{
                          width: `${toolPct}%`,
                          background: isElevated ? "#ef4444" : "#3b82f6"
                        }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100 mt-4">
            <span>Anchor policy checking active</span>
            <span className="text-emerald-600 font-semibold flex items-center gap-1">
              <CheckCircle2 size={12} /> Guardrails Armed
            </span>
          </div>
        </div>
      </section>

      {/* Interactive Live Telemetry Feed (Filterable Table) */}
      <section className="panel command-panel">
        <div className="card-title flex-wrap gap-4">
          <div>
            <div className="eyebrow flex items-center gap-1.5">
              <Activity size={12} className="text-emerald-500" />
              HIGH-PRECISION TELEMETRY
            </div>
            <h2 className="section-title">Live Telemetry & Policy Enforcement Stream</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Chronological feed with automated risk banding and runtime gatekeeper decisions
            </p>
          </div>

          {/* Quick Filters and Search */}
          <div className="flex items-center flex-wrap gap-2">
            <div className="relative">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search agent, tool, resource…"
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 w-52"
              />
            </div>

            <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
              <button
                type="button"
                onClick={() => setEventFilter("ALL")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  eventFilter === "ALL"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                All ({totalEvents})
              </button>
              <button
                type="button"
                onClick={() => setEventFilter("HIGH_RISK")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  eventFilter === "HIGH_RISK"
                    ? "bg-white text-amber-700 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                High Risk ({highRiskEvents})
              </button>
              <button
                type="button"
                onClick={() => setEventFilter("BLOCK")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  eventFilter === "BLOCK"
                    ? "bg-white text-rose-700 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Blocked ({blockedEvents})
              </button>
              <button
                type="button"
                onClick={() => setEventFilter("REVIEW")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  eventFilter === "REVIEW"
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Review ({reviewEvents})
              </button>
            </div>

            <Link className="text-link ml-2" href="/dashboard/events">
              All 100 <ArrowUpRight size={13} />
            </Link>
          </div>
        </div>

        {/* Table Content */}
        {filteredEvents.length > 0 ? (
          <div className="table-card">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Agent & Role</th>
                  <th>Invoked Tool</th>
                  <th>Resource Target</th>
                  <th>Risk Score</th>
                  <th>Decision</th>
                  <th>Inspection</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.slice(0, 10).map((event) => {
                  const isHigh = ["CRITICAL", "HIGH"].includes(event.band);
                  const isMedium = ["ELEVATED", "WATCH"].includes(event.band);
                  const badgeClass = isHigh
                    ? "badge-danger"
                    : isMedium
                    ? "badge-warning"
                    : "badge-normal";

                  return (
                    <tr key={event.id}>
                      <td className="whitespace-nowrap font-mono text-xs text-slate-600">
                        {new Date(event.ts).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit"
                        })}
                      </td>
                      <td>
                        <Link
                          href={`/dashboard/agents/${encodeURIComponent(event.agent_id)}`}
                          className="font-medium hover:underline text-slate-900"
                        >
                          {event.agent_id}
                        </Link>
                        {event.role && (
                          <div className="text-[11px] text-slate-400 font-normal">
                            {event.role}
                          </div>
                        )}
                      </td>
                      <td>
                        <code className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-xs border border-slate-200">
                          {event.tool}
                        </code>
                      </td>
                      <td className="text-slate-600 font-mono text-xs max-w-xs truncate">
                        {event.resource || event.destination || "—"}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className={`status-badge ${badgeClass}`}>
                            {event.band} · {Math.round(event.risk)}
                          </span>
                          <div
                            className="w-12 h-1.5 rounded-full bg-slate-100 overflow-hidden hidden sm:block"
                            title={`Risk: ${event.risk}/100`}
                          >
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.min(100, Math.max(5, event.risk))}%`,
                                background: BAND_COLORS[event.band] || "#10b981"
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`status-badge ${
                            event.decision === "BLOCK"
                              ? "badge-danger"
                              : event.decision === "REVIEW"
                              ? "badge-warning"
                              : "badge-normal"
                          }`}
                        >
                          {event.decision ?? "ALLOW"}
                        </span>
                      </td>
                      <td>
                        <Link
                          href={`/dashboard/events/${encodeURIComponent(event.id)}`}
                          className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                        >
                          Inspect <ArrowUpRight size={11} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            {loading ? (
              "Loading event telemetry…"
            ) : (
              <div className="flex flex-col items-center gap-2">
                <span>No events match the active filter criteria.</span>
                <button
                  type="button"
                  onClick={() => {
                    setEventFilter("ALL");
                    setSearchQuery("");
                  }}
                  className="text-xs text-blue-600 font-medium underline"
                >
                  Reset all filters
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Fleet Posture & Threat Signals Bottom Grid */}
      <section className="overview-grid">
        {/* Agent Fleet Roster */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <Shield size={12} className="text-emerald-500" />
                SECURITY POSTURE
              </div>
              <h2 className="section-title">Fleet Agent Posture</h2>
              <p className="text-xs text-slate-500 mt-0.5">Runtime health, drift indices, and access bounds</p>
            </div>
            <Link className="text-link" href="/dashboard/agents">
              View roster <ArrowUpRight size={13} />
            </Link>
          </div>

          {agents?.length ? (
            <div className="posture-list">
              {agents.slice(0, 6).map((agent) => {
                const statusClass =
                  agent.status === "normal"
                    ? "badge-normal"
                    : agent.status === "restricted"
                    ? "badge-warning"
                    : "badge-danger";

                return (
                  <Link
                    className="posture-row"
                    href={`/dashboard/agents/${encodeURIComponent(agent.agent_id)}`}
                    key={agent.agent_id}
                  >
                    <span>
                      <strong className="text-slate-900">{agent.agent_id}</strong>
                      <small className="text-slate-500">
                        {agent.role} · {agent.event_count || 0} events · max risk{" "}
                        {Math.round(agent.max_risk || agent.last_risk || 0)}
                      </small>
                    </span>
                    <span className={`status-badge ${statusClass}`}>
                      {agent.status || "normal"}
                    </span>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              {loading ? "Loading agents…" : "No agents currently registered in runtime."}
            </div>
          )}
        </div>

        {/* Deception Honeytokens & Tripwires */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <LockKeyhole size={12} className="text-rose-500" />
                ACTIVE DECEPTION
              </div>
              <h2 className="section-title">Decoy Honeytokens & Tripwires</h2>
              <p className="text-xs text-slate-500 mt-0.5">Synthetic traps planted to catch prompt injections</p>
            </div>
            <span className="status-badge badge-normal flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Armed
            </span>
          </div>

          {decoys?.length ? (
            <div className="posture-list">
              {decoys.slice(0, 5).map((decoy) => (
                <div className="posture-row" key={decoy.id}>
                  <span>
                    <strong className="text-slate-900 flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-600 font-mono uppercase">
                        {decoy.kind}
                      </span>
                      {decoy.match}
                    </strong>
                    <small className="text-slate-500">{decoy.description}</small>
                  </span>
                  <span
                    className={`status-badge ${
                      decoy.hits && decoy.hits > 0 ? "badge-danger animate-pulse" : "badge-normal"
                    }`}
                  >
                    {decoy.hits || 0} hits
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              {loading ? "Loading tripwire traps…" : "No decoy honeytokens registered."}
            </div>
          )}
        </div>
      </section>

      {/* Incidents & Simulated Outbox */}
      <section className="overview-grid">
        {/* Incident Alerts */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <AlertTriangle size={12} className="text-amber-500" />
                NEEDS OPERATOR ATTENTION
              </div>
              <h2 className="section-title">Security Incidents & Alerts</h2>
              <p className="text-xs text-slate-500 mt-0.5">Anomalous transitions, drift alerts, and policy blocks</p>
            </div>
            <Link className="text-link" href="/dashboard/incidents">
              Investigate <ArrowUpRight size={13} />
            </Link>
          </div>

          {alerts?.length ? (
            <div className="posture-list">
              {alerts.slice(0, 5).map((alert) => (
                <Link
                  href={`/dashboard/events/${encodeURIComponent(alert.event_id)}`}
                  className="alert-row"
                  key={alert.id}
                >
                  <span
                    className={`status-badge ${
                      alert.band === "HIGH" || alert.band === "CRITICAL"
                        ? "badge-danger"
                        : "badge-warning"
                    }`}
                  >
                    {alert.band}
                  </span>
                  <span>
                    <strong className="text-slate-900">{alert.agent_id}</strong>
                    <small className="text-slate-500">
                      {alert.message ?? alert.shadow_action ?? "Security policy violation"}
                    </small>
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              {loading ? (
                "Loading alert stream…"
              ) : (
                <div className="flex flex-col items-center gap-1 text-slate-500">
                  <CheckCircle2 size={24} className="text-emerald-500 mb-1" />
                  <span className="font-medium text-slate-700">Zero active incidents</span>
                  <span className="text-xs text-slate-400">
                    No policy breaches or critical alarms detected in the recent telemetry window.
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Simulated Outbox Egress */}
        <div className="panel command-panel">
          <div className="card-title">
            <div>
              <div className="eyebrow flex items-center gap-1.5">
                <Gauge size={12} className="text-blue-500" />
                EGRESS ISOLATION
              </div>
              <h2 className="section-title">Egress & Simulation Outbox</h2>
              <p className="text-xs text-slate-500 mt-0.5">Isolated communication sink preventing external data leak</p>
            </div>
            <span className="status-badge badge-info">Sandbox Sink</span>
          </div>

          {outbox ? (
            <div className="grid grid-cols-2 gap-3 mt-2">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="stat-label text-xs text-slate-500 font-medium">Intercepted Messages</div>
                <div className="kpi-value text-2xl font-bold text-slate-900 mt-1">
                  {outbox.messages}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Held in sandbox</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="stat-label text-xs text-slate-500 font-medium">Payload Volume</div>
                <div className="kpi-value text-2xl font-bold text-slate-900 mt-1">
                  {outbox.bytes >= 1024
                    ? `${(outbox.bytes / 1024).toFixed(1)} KB`
                    : `${outbox.bytes} B`}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Blocked external egress</div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              {loading ? "Loading simulated outbox…" : "Outbox metrics currently unavailable."}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100 mt-4">
            <span>Air-gapped simulator destination</span>
            <Link className="text-link" href="/dashboard/scenarios">
              Run Scenarios <ArrowUpRight size={12} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
