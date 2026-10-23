"use client";

import { useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { AlertTriangle, Search } from "lucide-react";
import { fetchJson, type Agent, type ContractItem, type ToolItem } from "@/lib/api";

type ContractDetail = ContractItem & {
  version?: number;
  purpose?: string;
  allowed_tools?: string[];
  allowed_resource_classes?: string[];
  denied_resource_classes?: string[];
  data_sensitivity_ceiling?: string;
};

function patternMatches(pattern: string, value: string) {
  const escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp(`^${escaped}$`).test(value);
}

export default function AgentGraphPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [contracts, setContracts] = useState<ContractDetail[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [selected, setSelected] = useState<{ id: string; label: string; details: string[] } | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const [agentData, contractIndex, toolData] = await Promise.all([
          fetchJson<Agent[]>("/agents"),
          fetchJson<ContractItem[]>("/contracts"),
          fetchJson<ToolItem[]>("/tools")
        ]);
        const details = await Promise.all(
          contractIndex.map((contract) =>
            fetchJson<ContractDetail>(`/contracts/${encodeURIComponent(contract.role)}`)
          )
        );
        if (!active) return;
        setAgents(agentData);
        setContracts(details);
        setTools(toolData);
        setError(null);
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load graph data.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  const graph = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const contractByRole = new Map(contracts.map((contract) => [contract.role, contract]));
    const visibleAgents = agents.filter((agent) =>
      `${agent.agent_id} ${agent.role}`.toLowerCase().includes(search.toLowerCase())
    );
    const visibleRoles = Array.from(new Set(visibleAgents.map((agent) => agent.role)));

    visibleAgents.forEach((agent, index) => {
      const nodeId = `agent:${agent.agent_id}`;
      nodes.push({
        id: nodeId,
        position: { x: 40, y: 65 + index * 135 },
        data: { label: `${agent.agent_id}\n${agent.role} · ${agent.status}` },
        style: { width: 220, whiteSpace: "pre-line", borderColor: agent.status === "normal" ? "#34d399" : "#fbbf24" }
      });
      const contract = contractByRole.get(agent.role);
      if (!contract) return;
      const contractId = `contract:${agent.role}`;
      if (!nodes.some((node) => node.id === contractId)) {
        nodes.push({
          id: contractId,
          position: { x: 340, y: 65 + visibleRoles.indexOf(agent.role) * 180 },
          data: { label: `${contract.role} · v${contract.version ?? contract.latest_version}\n${contract.purpose ?? "Role contract"}` },
          style: { width: 245, whiteSpace: "pre-line", borderColor: "#60a5fa" }
        });
      }
      edges.push({ id: `${nodeId}->${contractId}`, source: nodeId, target: contractId, label: "role contract" });
    });

    const activeContracts = visibleRoles.map((role) => contractByRole.get(role)).filter(Boolean) as ContractDetail[];
    const allowedToolNames = new Set<string>();
    activeContracts.forEach((contract) => {
      tools.filter((tool) => contract.allowed_tools?.some((pattern) => patternMatches(pattern, tool.name)))
        .forEach((tool) => allowedToolNames.add(tool.name));
    });

    Array.from(allowedToolNames).forEach((name, index) => {
      const tool = tools.find((item) => item.name === name);
      if (!tool) return;
      const toolId = `tool:${name}`;
      nodes.push({
        id: toolId,
        position: { x: 700, y: 65 + index * 88 },
        data: { label: `${tool.name}\n${tool.resource_class} · ${tool.sensitivity}` },
        style: { width: 240, whiteSpace: "pre-line", borderColor: "#a78bfa" }
      });
      activeContracts.filter((contract) => contract.allowed_tools?.some((pattern) => patternMatches(pattern, name)))
        .forEach((contract) => edges.push({
          id: `contract:${contract.role}->${toolId}`,
          source: `contract:${contract.role}`,
          target: toolId,
          label: "contract permits"
        }));
    });
    return { nodes, edges };
  }, [agents, contracts, tools, search]);

  function selectNode(_event: unknown, node: Node) {
    const id = String(node.id);
    if (id.startsWith("agent:")) {
      const agent = agents.find((item) => `agent:${item.agent_id}` === id);
      if (agent) setSelected({ id, label: agent.agent_id, details: [`Role: ${agent.role}`, `Posture: ${agent.status}`, `Last risk: ${agent.last_risk}`, `Peak risk: ${agent.max_risk}`] });
    } else if (id.startsWith("contract:")) {
      const contract = contracts.find((item) => `contract:${item.role}` === id);
      if (contract) setSelected({ id, label: contract.role, details: [`Purpose: ${contract.purpose ?? "Not provided"}`, `Allowed tools: ${contract.allowed_tools?.join(", ") ?? "Not listed"}`, `Restricted resources: ${contract.denied_resource_classes?.join(", ") ?? "Not listed"}`, `Sensitivity ceiling: ${contract.data_sensitivity_ceiling ?? "Not specified"}`] });
    } else {
      const tool = tools.find((item) => `tool:${item.name}` === id);
      if (tool) setSelected({ id, label: tool.name, details: [`Resource class: ${tool.resource_class}`, `Sensitivity: ${tool.sensitivity}`, `Sink: ${tool.sink_type ?? "Not specified"}`] });
    }
  }

  return (
    <div className="page-content">
      <section className="page-heading">
        <div>
          <div className="eyebrow">RELATIONSHIP MAP</div>
          <h1>Agent graph</h1>
          <p>Connections are derived from registered agents, declared role contracts, and tool registry metadata.</p>
        </div>
        <label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter agents" /></label>
      </section>
      <div className="notice notice-warning"><AlertTriangle size={18} /><span>Only tools matched by a role contract are connected. The registry does not provide resource endpoint relationships, so resource nodes are omitted.</span></div>
      {error && <div className="notice notice-danger" role="alert">Graph data unavailable: {error}</div>}
      {loading ? <div className="panel panel-shadow empty-state">Loading agent and contract relationships…</div> : agents.length === 0 ? (
        <div className="panel panel-shadow empty-state">{error ? "Agent graph data could not be loaded." : "No registered agents are available to map yet."}</div>
      ) : (
        <div className="graph-layout">
          <div className="panel panel-shadow graph-panel">
            <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView onNodeClick={selectNode}>
              <MiniMap />
              <Controls />
              <Background color="#243247" gap={20} />
            </ReactFlow>
          </div>
          <aside className="panel panel-shadow graph-details">
            {selected ? <>
              <div className="eyebrow">SELECTED NODE</div>
              <h2>{selected.label}</h2>
              <dl>{selected.details.map((detail) => <div key={detail}><dt>{detail.split(":")[0]}</dt><dd>{detail.substring(detail.indexOf(":") + 1).trim()}</dd></div>)}</dl>
            </> : <div className="empty-state">Select an agent, role contract, or tool to inspect its metadata.</div>}
          </aside>
        </div>
      )}
    </div>
  );
}
