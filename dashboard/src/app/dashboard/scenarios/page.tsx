"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Play, RotateCcw } from "lucide-react";
import { postJson, type EventItem, type ScenarioResult } from "@/lib/api";

const scenarios: Array<{
  id: ScenarioResult["scenario"];
  name: string;
  category: string;
  description: string;
}> = [
  {
    id: "normal",
    name: "Normal procurement",
    category: "Baseline workflow",
    description: "Run routine supplier and purchase actions to verify legitimate work remains available."
  },
  {
    id: "injection",
    name: "Malicious document",
    category: "Prompt injection",
    description: "Read an untrusted supplier document, then attempt sensitive access and simulated data egress."
  },
  {
    id: "drift",
    name: "Gradual behavior drift",
    category: "Behavioral drift",
    description: "Add new capabilities incrementally and observe the backend risk progression against its baseline."
  },
  {
    id: "mimicry",
    name: "Mimicry attack",
    category: "Routine-shaped probing",
    description: "Mix sensitive probes into ordinary work and inspect the resulting posture and allowed work."
  }
];

function summarize(result: ScenarioResult): string[] {
  const summary = result.summary;
  if (result.scenario === "normal") {
    const steps = Array.isArray(summary.steps) ? summary.steps as Array<{ decision?: string }> : [];
    return [`${steps.length} simulated actions`, `${steps.filter((step) => step.decision === "ALLOW").length} allowed`];
  }
  if (result.scenario === "injection") {
    return [
      `${String(summary.leaked_bytes ?? 0)} simulated bytes egressed`,
      `Injection parsed: ${summary.injection_understood ? "yes" : "no"}`,
      `Agent: ${result.agent_id}`
    ];
  }
  if (result.scenario === "drift") {
    return [
      `Maximum risk: ${String(summary.max_attack_risk ?? "n/a")}`,
      `Final band: ${String(summary.final_attack_band ?? "n/a")}`,
      `Final drift signal: ${String(summary.drift_final ?? "n/a")}`
    ];
  }
  return [
    `Final posture: ${String(summary.final_posture ?? "n/a")}`,
    `Simulated bytes egressed: ${String(summary.leaked_bytes ?? 0)}`,
    `Legitimate work afterward: ${String(summary.legit_after_allowed ?? 0)}/${String(summary.legit_after_total ?? 0)}`
  ];
}

export default function ScenariosPage() {
  const [running, setRunning] = useState<ScenarioResult["scenario"] | null>(null);
  const [results, setResults] = useState<Partial<Record<ScenarioResult["scenario"], ScenarioResult>>>({});
  const [error, setError] = useState<string | null>(null);

  async function runScenario(id: ScenarioResult["scenario"]) {
    setRunning(id);
    setError(null);
    try {
      const result = await postJson<ScenarioResult>(`/sim/scenarios/${id}/run`);
      setResults((current) => ({ ...current, [id]: result }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Scenario run failed.");
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="page-content">
      <section className="page-heading">
        <div>
          <div className="eyebrow">SIMULATION WORKSPACE</div>
          <h1>Scenario runner</h1>
          <p>Run fixed simulator scenarios against the active FastAPI backend. Results reflect its current mode and policy.</p>
        </div>
        <span className="status-badge badge-warning">Simulated agents and tools</span>
      </section>

      <div className="notice notice-warning">
        <AlertTriangle size={18} />
        <span>These scenarios use the project’s mock tool backends. They do not call external systems.</span>
      </div>
      {error && <div className="notice notice-danger" role="alert">{error}</div>}

      <section className="scenario-grid">
        {scenarios.map((scenario) => {
          const result = results[scenario.id];
          return (
            <article className="scenario-card panel-shadow" key={scenario.id}>
              <div className="scenario-card-top">
                <span className="scenario-icon"><Play size={17} /></span>
                <span className="status-badge badge-info">{scenario.category}</span>
              </div>
              <h2>{scenario.name}</h2>
              <p>{scenario.description}</p>
              <div className="scenario-actions">
                <button
                  className="primary-btn"
                  disabled={running !== null}
                  onClick={() => void runScenario(scenario.id)}
                >
                  {running === scenario.id ? "Running scenario…" : <><Play size={15} /> Run scenario</>}
                </button>
                {result && (
                  <button
                    className="secondary-btn"
                    onClick={() => setResults((current) => {
                      const next = { ...current };
                      delete next[scenario.id];
                      return next;
                    })}
                    aria-label={`Clear ${scenario.name} result`}
                  >
                    <RotateCcw size={15} /> Clear result
                  </button>
                )}
              </div>
              {result && (
                <div className="scenario-result" aria-live="polite">
                  <div className="scenario-result-title"><CheckCircle2 size={16} /> Completed against {result.mode.toUpperCase()} mode</div>
                  <ul>{summarize(result).map((line) => <li key={line}>{line}</li>)}</ul>
                  <div className="scenario-event-links">
                    {result.events.slice(0, 5).map((event: EventItem) => (
                      <Link href={`/dashboard/events/${event.id}`} key={event.id}>
                        {event.tool} · {event.band} <ArrowUpRight size={13} />
                      </Link>
                    ))}
                    {result.events.length === 0 && <span>No events were returned by the backend.</span>}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}
