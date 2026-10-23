# 03 – Solution Design: AGENT WARDEN

**One line:** A behavioral identity layer that checks *"is this agent still doing the job it was hired for, and what made it change?"* – and responds by shrinking the agent's authority instead of killing it.

---

## 1. Core concept in 4 ideas

1. **Role Contract** – every agent's declared role becomes a machine-readable "job description" (allowed tools, data classes, destinations, normal sequences, budgets).
2. **Five Lenses** – every action is judged by five independent detectors, so an attacker must fool all of them.
3. **Cause-aware drift** – we ask *what triggered the change*: owner/ticket (sanctioned) vs untrusted content (adversarial).
4. **Surgical response** – a Policy Gateway mints **short-lived, scope-reduced tokens**. Restricting an agent = giving it a smaller token. The rest of its work continues.

---

## 2. The six innovations (this is the USP list)

| # | Innovation | Solves challenge | One-line explanation |
|---|---|---|---|
| I1 | **Role Contract + Bayesian blend** | Little/no history | Day-0 baseline comes from the declared role + peer agents; own history gradually takes over. |
| I2 | **Causal Provenance (taint → sink)** | Indirect prompt injection | We don't read the evil text; we watch for *untrusted content in context → privileged action not explained by the task*. |
| I3 | **Decoy Tripwires (D3COY layer)** | Evasion, valid credentials | Fake HR file, fake API key, fake endpoint, canary string. No legit agent touches them; any touch = near-certain alarm. Works with zero history and can't be mimicked because attacker can't know which items are fake. |
| I4 | **Frozen Anchor + Capability Budget** | Slow drift / evasion | Compare against a *frozen* reference per role version, and count cumulative new capability classes touched. Boiling-frog attacks accumulate and trip the budget. |
| I5 | **Change Declaration Channel (sanction check)** | Legit change vs drift | Owners can pre-declare new tasks/tools (ticket, contract v2). Matching drift is auto-adapted; unmatched drift with untrusted cause is flagged. |
| I6 | **Authority-Attenuating Delegation Envelope** | Chains of agents | Every agent-to-agent call carries origin, taint labels and an authority ceiling; effective permission = intersection; risk propagates (contagion) along the chain. |

Plus: **Graduated Surgical Response** (Observe → Step-up → Restrict → Isolate + checkpoint rewind) and **Explainable alerts** (score, top reasons, evidence timeline, OWASP mapping).

---

## 3. Components

### 3.1 Agent Registry & Role Contracts
- Each agent registered with: `agent_id`, `owner`, `role`, `role_version`, `parent` (if sub-agent).
- Role contract (YAML) example:

```yaml
role: procurement_agent
version: 1
purpose: "Check supplier prices and create purchase requests"
allowed_tools:
  - supplier_api.get_price
  - supplier_api.list_catalog
  - purchase.create_request
  - doc.read            # supplier docs only
allowed_resource_classes: [supplier_data, purchase_requests, supplier_docs]
denied_resource_classes: [hr_data, payroll, source_code, customer_pii]
data_sensitivity_ceiling: internal
egress_allowlist: [api.supplier-a.com, api.supplier-b.com, erp.internal]
typical_sequences:
  - [doc.read, supplier_api.get_price, purchase.create_request]
budgets:
  actions_per_hour: 120
  new_resource_classes_per_week: 0
  bytes_out_per_hour: 5MB
```
- **Contract generation:** a template library per common role (procurement, support, HR-assistant, DevOps, research) + an LLM-assisted "role → draft contract" helper. Owner reviews and signs. (LLM optional in prototype; templates work offline.)

### 3.2 Policy Gateway (the enforcement point)
- Sits between agents and tools (MCP/HTTP proxy / SDK wrapper). Every tool call passes through it.
- Emits a **normalized event**: `agent_id, role_version, tool, resource, resource_class, data_sensitivity, destination, bytes, context_sources (list of provenance labels in context), parent_chain, timestamp`.
- Applies the decision from the Risk Engine: `ALLOW / ALLOW+LOG / STEP_UP / BLOCK / ISOLATE`.
- Acts as a **token broker**: issues short-lived tokens whose scopes can be narrowed instantly (OAuth token-exchange style).

### 3.3 Five detection lenses

| Lens | Question | Method | Why it can't be dodged alone |
|---|---|---|---|
| **L1 Role Fit** | Is this action inside the declared job? | Contract rules + semantic similarity of action to role purpose for unlisted actions | Hard limits apply even if behavior looks statistically normal (beats mimicry) |
| **L2 Behavioral Baseline** | Is it unusual for this agent / its peers? | Markov transition surprise on tool sequences, rate/volume z-scores, peer-group comparison, Isolation Forest on feature vectors | Learns what the contract didn't foresee |
| **L3 Causal Provenance** | Did untrusted content cause a risky action? | Taint labels on context; sink classification (read-sensitive, write, egress); *no owner-originated justification* | Style-independent: rewording the injection doesn't change the data flow |
| **L4 Decoys** | Did it touch something no one should touch? | Honey-resources per role neighborhood, canary tokens, canary strings in egress | Attacker can't mimic what it can't identify |
| **L5 Chain & Fingerprint** | Does authority/identity chain make sense? Is it the same "hand" that created the token? | Delegation envelope check, authority ceiling, inherited taint; runtime fingerprint (workload ID, tool timing rhythm, network origin) | Catches stolen tokens and confused-deputy abuse |

Plus the **drift tracker** (I4) producing a long-horizon score: CUSUM/EWMA against the frozen anchor and the capability-surface budget.

### 3.4 Drift Classifier (legit vs adversarial)
Inputs for each detected shift:
- Is there a matching **change declaration** (ticket/contract v2/owner approval)?
- **Trigger source:** owner/human instruction, scheduled, or untrusted content?
- **Peer adoption:** are other agents of the same role making the same change? (fleet-wide rollout = likely legit)
- **Speed & shape:** abrupt vs gradual staircase.
- **Sensitivity** of the newly touched resources.

Output: `SANCTIONED | ORGANIC | SUSPICIOUS | ADVERSARIAL` with confidence and reasons.
- SANCTIONED → baseline auto-updated (contract version bump logged).
- ORGANIC (harmless broadening, low sensitivity) → watch + ask owner to confirm.
- SUSPICIOUS/ADVERSARIAL → scored and responded to.

### 3.5 Risk Engine (see `09_risk_scoring_spec.md`)
Combines lens scores with an **impact factor** (data sensitivity × egress × irreversibility). Output 0–100 + reasons + recommended action. Decoy hits and tainted-sensitive-egress have hard floors.

### 3.6 Response Orchestrator (graduated, surgical)

| Risk | Mode | What happens | Disruption |
|---|---|---|---|
| 0–29 | **Observe** | Log only | None |
| 30–59 | **Watch** | Extra logging, raise baseline sampling, notify owner dashboard | None |
| 60–79 | **Step-up** | Risky action paused → human approve/deny (or auto-deny after timeout); tainted context flagged | Only the risky action waits |
| 80–94 | **Restrict** | Token re-issued with reduced scope: no sensitive reads, no egress, read-only; agent continues non-risky tasks | Partial |
| ≥95 or decoy+egress | **Isolate** | Token revoked, agent sandboxed, session checkpointed; downstream agents notified | Agent paused; **work can be re-assigned/resumed from last clean checkpoint** |

**Rewind trick:** the gateway keeps a clean checkpoint (before the tainted document was ingested). After owner approval, the agent can be resumed *without that document* – legitimate work is not lost.

### 3.7 Explainability & Alert format
Every alert contains:
- **Risk score** with band and recommended action
- **Top 3 reasons in plain English** (e.g., "Read `hr/salaries.xlsx` – outside role contract – 2 steps after ingesting untrusted PDF")
- **Evidence timeline** (the actions, with taint chain)
- **Which lens fired** and its sub-score
- **Standards mapping** (OWASP ASI01/ASI03…)
- **What we did** + **how to undo** (restore scope)
- **Counterfactual:** "This would not have alerted if the owner had declared task X."

### 3.8 Dashboard (what judges will see in the prototype)
1. **Fleet overview:** agents as cards with live risk gauges.
2. **Agent detail:** timeline, baseline vs now, capability-surface chart.
3. **Alert detail:** score, reasons, evidence, buttons *Approve / Restore / Keep restricted*.
4. **Chain graph:** agent-to-agent graph with taint propagation highlighted.
5. **Attack replay:** one-click scenario runner (injection, stolen token, slow drift, legit change).

---

## 4. How each of the 6 PS challenges is answered

| Challenge | Mechanism | Evidence in demo |
|---|---|---|
| Valid credentials hide the attack | Behavior-vs-role check at gateway (L1) + decoys (L4) | Token valid; alert still fires |
| Indirect prompt injection | Causal provenance (L3): untrusted-content → risky sink | Different injection wordings → same detection |
| Legit change vs drift | Change Declaration + cause-aware Drift Classifier | "New task approved" scenario → no alert; baseline updates |
| Little/no history | Role contract prior + peer pooling + Bayesian blend | Brand-new agent attacked on step 1 → caught |
| Chains of agents | Delegation envelope, authority intersection, contagion score | A→B: B can't exceed A's authority; taint travels |
| Evasion | Frozen anchor + capability budget + decoys + multi-lens fusion + hard contract limits | Slow-drift and mimicry scenarios |

---

## 5. Honest limitations (say them; judges respect it)
- If the contract is too broad, L1 is weak → we flag "over-broad contract" and recommend tightening (blast-radius report).
- A purely textual attack with no tool consequence is out of scope (no data-flow effect) – same boundary as CaMeL.
- Decoys must be maintained and kept believable.
- Behavioral baselines need tuning; we mitigate with role priors and measure false-block rate.
- Gateway adds latency (target: low tens of ms for rule-based path; heavy models only for escalations).

---

## 6. Future scope (for slide 6)
1. Native **OAuth 2.0 Token Exchange + SPIFFE/SPIRE** integration for production tokens.
2. **MCP gateway plugin** and **OpenTelemetry GenAI** ingestion → plug into any agent framework.
3. **LLM-as-judge "intent check"** for ambiguous high-impact actions (escalation path only).
4. **Federated baselines** across organizations (share role-level statistics, not data).
5. **Contract auto-tightening** from observed usage ("least privilege recommender").
6. **Compliance exports** mapped to NIST 800-53 CA-7, OWASP ASI, ISO 42001.
7. **Memory-poisoning guard**: re-validate long-term memory entries with provenance labels.
8. **Red-team autopilot**: continuous adversarial testing of our own detectors.
