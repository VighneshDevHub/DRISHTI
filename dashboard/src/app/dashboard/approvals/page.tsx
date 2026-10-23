"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJson, postJson, type ApprovalItem } from "@/lib/api";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadApprovals() {
    const rows = await fetchJson<ApprovalItem[]>("/approvals?status=pending");
    setApprovals(rows);
  }

  useEffect(() => {
    let active = true;
    fetchJson<ApprovalItem[]>("/approvals?status=pending")
      .then((rows) => { if (active) setApprovals(rows); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load pending approvals."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function resolve(id: string, action: "approve_once" | "deny") {
    const verb = action === "approve_once" ? "approve this action once" : "deny this action";
    if (!window.confirm(`Are you sure you want to ${verb}? The backend will resolve the pending request.`)) return;
    setResolving(id);
    setError(null);
    try {
      await postJson(`/approvals/${encodeURIComponent(id)}/resolve`, { action, by: "dashboard" });
      await loadApprovals();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Approval could not be resolved. It may already be expired or resolved.");
      try { await loadApprovals(); } catch (reloadCause) {
        setError(`${cause instanceof Error ? cause.message : "Resolution failed."} Refresh failed: ${reloadCause instanceof Error ? reloadCause.message : "unknown error"}`);
      }
    } finally {
      setResolving(null);
    }
  }

  return (
    <div className="page-content">
      <section className="page-heading">
        <div><div className="eyebrow">HUMAN REVIEW</div><h1>Approvals</h1><p>Resolve backend-created step-up approvals. Approval authorizes only the associated action, not future requests.</p></div>
        <span className="status-badge badge-warning">{approvals.length} pending</span>
      </section>
      {error && <div className="notice notice-danger" role="alert">{error}</div>}
      <section className="panel panel-shadow">
        <div className="card-title"><h2 className="section-title">Pending actions</h2></div>
        {loading ? <div className="empty-state">Loading the approval queue…</div> : approvals.length === 0 ? (
          <div className="empty-state">{error ? "Approval queue unavailable." : "No pending approvals were returned by the backend."}</div>
        ) : (
          <div className="table-card">
            <table>
              <thead><tr><th>Approval</th><th>Agent</th><th>Related event</th><th>Requested tool</th><th>Request context</th><th>Resolution</th></tr></thead>
              <tbody>{approvals.map((approval) => (
                <tr key={approval.id}>
                  <td>{approval.id}</td>
                  <td><Link href={`/dashboard/agents/${encodeURIComponent(approval.agent_id)}`}>{approval.agent_id}</Link></td>
                  <td><Link href={`/dashboard/events/${encodeURIComponent(approval.event_id)}`}>{approval.event_id}</Link></td>
                  <td>{approval.request.tool}</td>
                  <td><code className="context-code">{JSON.stringify(approval.request.args)}</code></td>
                  <td><div className="action-buttons">
                    <button className="secondary-btn" disabled={resolving !== null} onClick={() => void resolve(approval.id, "approve_once")}>{resolving === approval.id ? "Resolving…" : "Approve once"}</button>
                    <button className="danger-btn" disabled={resolving !== null} onClick={() => void resolve(approval.id, "deny")}>Deny</button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
