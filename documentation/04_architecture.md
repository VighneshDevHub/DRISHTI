# 04 – Architecture

> Diagrams are in Mermaid (render at mermaid.live, GitHub, or VS Code preview). For slides, redraw the **High-level** and **Decision flow** diagrams in Figma/Canva/draw.io with your theme colors.

---

## 1. High-level architecture

```mermaid
flowchart LR
    subgraph Agents["AI Agents (valid tokens)"]
        A1[Procurement Agent]
        A2[Support Agent]
        A3[Sub-agent]
    end

    subgraph Untrusted["Untrusted inputs"]
        U1[PDFs / Emails]
        U2[Web pages]
        U3[Other agents' messages]
    end

    subgraph GW["Policy Gateway (token broker + interceptor)"]
        T[Tool-call interceptor]
        P[Provenance tagger]
        TB[Token broker - scoped, short-lived]
    end

    subgraph Brain["Warden Engine"]
        RC[(Role Contracts + versions)]
        L1[L1 Role Fit]
        L2[L2 Baseline + Drift]
        L3[L3 Causal Provenance]
        L4[L4 Decoys]
        L5[L5 Chain + Fingerprint]
        DC[Drift Classifier]
        RE[Risk Engine + Explainer]
    end

    subgraph Resp["Response Orchestrator"]
        O[Observe / Step-up / Restrict / Isolate]
    end

    subgraph Tools["Tools & Data"]
        S1[Supplier API]
        S2[ERP]
        S3[HR files - DECOY + real]
        S4[External network]
    end

    DASH[Dashboard + Owner approvals]

    Untrusted --> A1
    A1 & A2 & A3 -->|tool call| T
    U1 & U2 & U3 -.->|labelled by| P
    P --> T
    T -->|event| L1 & L2 & L3 & L4 & L5
    RC --> L1
    RC --> L2
    L1 & L2 & L3 & L4 & L5 --> DC --> RE
    RE --> O
    O -->|decision| T
    O -->|narrow scopes| TB
    T -->|allowed calls| Tools
    RE --> DASH
    DASH -->|approve / restore| O
```

---

## 2. Per-action decision flow

```mermaid
flowchart TD
    A[Agent issues tool call] --> B[Gateway builds event + provenance context]
    B --> C{Hits a DECOY?}
    C -- yes --> X[Risk floor 85 - Restrict/Isolate]
    C -- no --> D[L1 Role fit]
    D --> E[L2 Baseline / drift]
    E --> F[L3 Taint -> sink check]
    F --> G[L5 Chain + fingerprint]
    G --> H[Drift Classifier: sanctioned? cause?]
    H --> I[Risk Engine: fuse lenses x impact]
    I --> J{Risk band}
    J -- under 30 --> K[ALLOW]
    J -- 30-59 --> L[ALLOW + WATCH]
    J -- 60-79 --> M[STEP-UP: human approval]
    J -- 80-94 --> N[RESTRICT: scope-down token]
    J -- 95+ --> O[ISOLATE: revoke + checkpoint]
    X --> N
    K & L & M & N & O --> P[Explainable alert + audit log]
```

---

## 3. Delegation chain with authority attenuation

```mermaid
flowchart LR
    H[Human owner\nauthority: A,B,C] --> M[Manager agent\nceiling: A,B,C]
    M -->|envelope: origin=H, ceiling=A,B| W1[Worker agent 1\neffective: A,B]
    M -->|envelope: origin=H, ceiling=B| W2[Worker agent 2\neffective: B]
    X[Untrusted PDF] -.taint.-> W1
    W1 -->|envelope: origin=H, taint=PDF, ceiling=A| W3[Worker 3\neffective: A, tainted]
    W3 -.tries C.-> BLOCK[[BLOCKED: outside ceiling + tainted]]
```
Rules: **effective permission = intersection of role contract, parent ceiling, and current scope**; **taint is inherited and never silently cleaned**; risk of a child contributes to the parent (contagion) and vice versa.

---

## 4. Decoy placement

```mermaid
flowchart LR
    subgraph Real
      R1[supplier_prices.csv]
      R2[purchase_requests DB]
    end
    subgraph Decoys["Decoys (never touched by real work)"]
      D1[hr/salaries_2026_final.xlsx]
      D2[api key: canary_ERP_ADMIN]
      D3[internal endpoint /admin/export]
      D4[Canary string in docs]
    end
    PA[Procurement agent] --> R1 & R2
    PA -. hijacked .-> D1 & D2 & D3
    D1 & D2 & D3 -->|touch = alarm| WARD[Warden]
    D4 -->|string seen in outbound payload = exfil proof| WARD
```

---

## 5. Cold-start: Bayesian blend

```mermaid
flowchart LR
    P[Role-contract prior\n+ peer-group stats] --> BL[Blend]
    H[Agent's own history] --> BL
    BL --> B[Effective baseline]
    N[n = own observations] -->|weight w = n / n + k| BL
```
`w` starts at 0 (all prior, Day-0) and increases as the agent builds history; a new agent is judged mostly by **its role + its peers**.

---

## 6. Data model (core tables)

| Table | Key fields |
|---|---|
| `agents` | agent_id, owner, role, role_version, parent_id, status, token_scope, created_at |
| `role_contracts` | role, version, yaml, signed_by, created_at |
| `events` | id, ts, agent_id, tool, resource, resource_class, sensitivity, destination, bytes, taint_labels[], parent_chain[], decision |
| `baselines` | agent_id/role, version, transition_matrix, feature_stats, anchor_frozen_at |
| `alerts` | id, ts, agent_id, risk, band, lens_scores{}, reasons[], evidence_event_ids[], owasp_tags[], action_taken, status |
| `change_declarations` | id, agent_id/role, type(task/tool/contract), approved_by, valid_from, valid_to |
| `decoys` | id, type, location, owner_role_scope, created_at, hits |
| `delegations` | id, from_agent, to_agent, ceiling, taint_labels[], ts |

---

## 7. Technology choices (24-hour friendly)

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Fast to build; async; WebSocket for live feed |
| Storage | SQLite (prototype) → Postgres; in-memory Redis optional | Zero setup |
| ML | scikit-learn (Isolation Forest), numpy, own Markov/CUSUM code | Small, explainable |
| Semantic role-fit | sentence-transformers *or* TF-IDF fallback | Works offline |
| Graph | networkx | Chain & contagion |
| Frontend | React + Vite + Tailwind + Recharts + react-flow (graph) | Quick, good-looking |
| Agents for demo | Scripted simulators + optional real LLM agent (any API) | Reliable demo + proof of realism |
| Packaging | Docker Compose | One command to run |

---

## 8. Integration story (for feasibility slide)
- **Today (prototype):** SDK wrapper / HTTP proxy in front of tools.
- **Production:** MCP gateway plugin + OAuth token-exchange broker + OpenTelemetry GenAI spans ingestion + SPIFFE IDs. No change to the agent's model; only the tool-call path is routed through the gateway.
