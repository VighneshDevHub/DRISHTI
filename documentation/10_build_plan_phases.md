# 10 – Build Plan: Phase by Phase

**Product:** Agent Warden prototype
**Stack:** Python 3.11 + FastAPI + SQLite + scikit-learn/numpy/networkx, React + Vite + Tailwind + Recharts + React Flow, Docker Compose.
**Rule:** every phase ends with something that **runs and can be demoed**. Never move on with a broken phase.

---

## 0. Phase overview

| Phase | Name | Output you can demo | Est. time (1 dev) |
|---|---|---|---|
| 0 | Scaffold | Repo runs, health check, empty dashboard | 1 h |
| 1 | Events, agents, simulator | Simulated agents emit events; stored; live feed | 2-3 h |
| 2 | Role contracts + Gateway + L1 | Out-of-role actions get flagged | 2-3 h |
| 3 | Provenance (L3) + Decoys (L4) | PS example attack detected end-to-end | 3 h |
| 4 | Baseline, cold start, drift (L2) | Sequence surprise, Day-0, slow-drift alert | 3-4 h |
| 5 | Risk engine + explanations | Score 0-100, reasons, OWASP tags | 2 h |
| 6 | Response orchestrator + token broker | Step-up, restrict, isolate, restore | 3 h |
| 7 | Chains (L5), fingerprint, change declarations | Delegation ceiling, taint travels, legit change = no alert | 3-4 h |
| 8 | Dashboard | Fleet, alert detail, chain graph, replay | 5-6 h |
| 9 | Evaluation + demo polish | Metrics table, ablation, one-click demo | 3 h |

Total about 28-34 hours of focused work. For 4 people in parallel, see the split in section 9. If time is short, **Phases 0-3, 5, 6 and a thin dashboard** already demonstrate the core story.

---

## 1. Directory structure

```
agent-warden/
├── README.md
├── docker-compose.yml
├── Makefile                      # make dev | make test | make demo | make eval
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py               # FastAPI app, routers, startup
│   │   ├── config.py             # thresholds, weights, windows (single source of truth)
│   │   ├── models/
│   │   │   ├── events.py         # Event, ContextLabel, Chain, Fingerprint (pydantic)
│   │   │   ├── contracts.py      # RoleContract schema
│   │   │   ├── alerts.py         # Alert, LensScores, Decision
│   │   │   └── agents.py         # Agent, AgentStatus, TokenScope
│   │   ├── store/
│   │   │   ├── db.py             # SQLite engine/session
│   │   │   └── repo.py           # CRUD: agents, events, alerts, baselines, declarations
│   │   ├── contracts/
│   │   │   ├── loader.py         # load/validate YAML, versioning
│   │   │   ├── generator.py      # role text -> draft contract (template + optional LLM)
│   │   │   └── templates/
│   │   │       ├── procurement_agent.yaml
│   │   │       ├── support_agent.yaml
│   │   │       └── devops_agent.yaml
│   │   ├── gateway/
│   │   │   ├── interceptor.py    # POST /gateway/tool-call: build event, run engine, enforce
│   │   │   ├── provenance.py     # context labeling + taint window
│   │   │   ├── tool_registry.py  # tool -> resource class, sensitivity, sink type, manifest hash
│   │   │   └── token_service.py  # issue/narrow/revoke short-lived scoped tokens
│   │   ├── detection/
│   │   │   ├── role_fit.py       # L1
│   │   │   ├── baseline.py       # L2 Markov + blend + peer pooling
│   │   │   ├── drift.py          # L2b frozen anchor, CUSUM, capability budget
│   │   │   ├── provenance_lens.py# L3 taint -> sink score
│   │   │   ├── decoys.py         # L4 registry, touch detection, canary scan
│   │   │   ├── chain.py          # L5 envelope, ceiling, contagion
│   │   │   ├── fingerprint.py    # L5 token-use fingerprint
│   │   │   └── change_classifier.py # sanctioned / organic / suspicious / adversarial
│   │   ├── risk/
│   │   │   ├── engine.py         # fusion, impact, floors, session risk
│   │   │   ├── impact.py
│   │   │   ├── explain.py        # reasons, counterfactual, OWASP tags
│   │   │   └── owasp_map.py
│   │   ├── response/
│   │   │   ├── orchestrator.py   # band -> action
│   │   │   ├── policies.py       # what each mode allows
│   │   │   ├── approvals.py      # step-up queue
│   │   │   └── checkpoints.py    # clean checkpoint + resume-without-tainted-input
│   │   └── api/
│   │       ├── routes_agents.py
│   │       ├── routes_events.py
│   │       ├── routes_alerts.py
│   │       ├── routes_contracts.py
│   │       ├── routes_declarations.py
│   │       ├── routes_sim.py     # trigger scenarios from dashboard
│   │       └── ws.py             # WebSocket live feed
│   └── tests/
│       ├── test_role_fit.py
│       ├── test_provenance.py
│       ├── test_decoys.py
│       ├── test_baseline_coldstart.py
│       ├── test_drift_slow.py
│       ├── test_risk_engine.py
│       ├── test_response.py
│       ├── test_chain.py
│       └── test_change_classifier.py
│
├── simulator/
│   ├── runner.py                 # runs normal traffic + scenarios against gateway
│   ├── agents/
│   │   ├── base.py               # SimAgent: reads docs, calls tools via gateway client
│   │   ├── procurement.py
│   │   └── support.py
│   ├── scenarios/
│   │   ├── s1_injection.py
│   │   ├── s2_stolen_token.py
│   │   ├── s3_poisoned_tool.py
│   │   ├── s4_slow_drift.py
│   │   ├── s5_mimicry.py
│   │   ├── s6_chain.py
│   │   ├── s7_memory.py
│   │   └── s8_legit_change.py
│   ├── mock_services/
│   │   ├── supplier_api.py       # fake supplier prices
│   │   ├── hr_files.py           # real-looking HR data + decoy
│   │   ├── erp.py
│   │   └── evil_server.py        # records exfil attempts
│   ├── payloads/                 # injection variants (comment, base64, table, alt-text, multilingual)
│   └── client.py                 # thin SDK: warden.call_tool(agent, tool, args, context)
│
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── api.ts                # REST + WS client
│       ├── pages/
│       │   ├── Overview.tsx      # fleet cards + live feed
│       │   ├── AgentDetail.tsx   # timeline, baseline vs now, capability surface
│       │   ├── AlertDetail.tsx   # score, reasons, evidence, action buttons
│       │   ├── ChainGraph.tsx    # React Flow with taint highlighting
│       │   ├── Contracts.tsx     # view/edit role contracts, blast-radius report
│       │   └── Replay.tsx        # one-click scenario runner
│       └── components/
│           ├── RiskGauge.tsx
│           ├── LensBars.tsx
│           ├── EvidenceTimeline.tsx
│           └── ApprovalCard.tsx
│
├── eval/
│   ├── run_eval.py               # runs all scenarios x seeds
│   ├── metrics.py                # detect rate, TTD, leak bytes, false-block, latency
│   ├── ablation.py               # disable each lens, rerun
│   └── results/                  # CSV + markdown tables for slides
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── lenses.md
    ├── demo_script.md
    └── decisions.md              # why each design choice
```

---

## 2. Shared contracts (define first, in Phase 1; everything depends on them)

### 2.1 Event (what the gateway builds for every tool call)
```json
{
  "id": "evt_000123",
  "ts": "2026-10-20T10:15:03Z",
  "agent_id": "proc-07",
  "role": "procurement_agent",
  "role_version": 1,
  "tool": "hr_files.read",
  "resource": "hr/salaries_2026.xlsx",
  "resource_class": "hr_data",
  "sensitivity": 0.9,
  "sink_type": "read_sensitive",
  "destination": null,
  "destination_class": "internal",
  "bytes_out": 0,
  "is_irreversible": false,
  "context_labels": [
    {"source": "supplier_quote_3.pdf", "trust": "untrusted", "age_steps": 2}
  ],
  "chain": {"depth": 0, "origin": "priya", "ceiling": ["supplier_data","purchase_requests"], "inherited_taint": []},
  "fingerprint": {"workload_id": "wl-proc-07", "net_origin": "10.0.4.12", "inter_call_ms": 840}
}
```

### 2.2 Decision (what the gateway returns to the agent)
```json
{
  "decision": "BLOCK",
  "risk": 82,
  "band": "HIGH",
  "action": "RESTRICT",
  "alert_id": "alr_0042",
  "message": "Blocked: out-of-role sensitive read after untrusted input",
  "token": {"scopes": ["supplier_api:read","purchase:create"], "expires_in": 300}
}
```

### 2.3 Core REST API
| Method | Path | Purpose |
|---|---|---|
| POST | `/gateway/tool-call` | Agent calls a tool through Warden; returns decision (and result if allowed) |
| POST | `/gateway/context` | Register context ingestion (doc read, web fetch, peer message) with trust label |
| GET | `/agents` | Fleet list with live risk |
| GET | `/agents/{id}` | Detail: baseline, events, capability surface |
| GET | `/alerts` / `/alerts/{id}` | Alert list/detail |
| POST | `/alerts/{id}/action` | approve_once / approve_and_declare / keep_restricted / isolate / restore |
| GET/PUT | `/contracts/{role}` | View/update contract (creates new version) |
| POST | `/declarations` | Owner declares a change |
| POST | `/sim/run/{scenario}` | Trigger scenario from dashboard |
| WS | `/ws/live` | Streams events, alerts, state changes |

---

## 3. Phase 0 – Scaffold (1 h)

**Goal:** a repo that starts with one command.

**Build:**
- Monorepo layout above (create empty modules with docstrings).
- `backend/app/main.py` with `/health`.
- `dashboard` via Vite React-TS template; Tailwind configured; dark red/black theme to match the hackathon brand.
- `docker-compose.yml`: `backend` (uvicorn, port 8000), `dashboard` (port 5173).
- `Makefile` shortcuts; `.env.example`; README skeleton.

**Done when:** `make dev` → open dashboard → shows "Warden online" pulled from `/health`.

---

## 4. Phase 1 – Events, agents, simulator (2-3 h)

**Goal:** fake agents generate realistic traffic and you can see it live.

**Build:**
1. `models/*.py` – pydantic models from section 2.
2. `store/db.py`, `repo.py` – tables: `agents`, `events`, `alerts`, `baselines`, `declarations`, `decoys`, `delegations`.
3. `gateway/tool_registry.py` – table mapping each tool → `resource_class`, `sensitivity`, `sink_type`, `destination_class`. Example:
   - `supplier_api.get_price` → supplier_data, 0.2, benign
   - `purchase.create_request` → purchase_requests, 0.3, write
   - `hr_files.read` → hr_data, 0.9, read_sensitive
   - `http.post` → external, 0.0, egress
4. `simulator/agents/base.py` – a `SimAgent` with `read_context(doc, trust)` and `call(tool, args)`; normal behavior generated from a role-specific Markov chain with noise and think-time.
5. `simulator/client.py` – `WardenClient.call_tool(...)`.
6. `/gateway/tool-call` stub: builds the event, stores it, returns ALLOW.
7. `ws.py` – broadcast events.

**Feature explanation – tool registry:** the registry is how raw tool names become security-meaningful facts (sensitivity, sink type). It is the single place to extend for new tools.

**Done when:** `python -m simulator.runner --normal` runs 5 agents for a minute and the dashboard feed scrolls events.

---

## 5. Phase 2 – Role contracts + Gateway + L1 Role Fit (2-3 h)

**Goal:** out-of-role actions are scored.

**Build:**
1. `models/contracts.py` + `contracts/loader.py` – YAML schema (see `03_solution_design.md` §3.1), validation, versioning (v1, v2 …), `anchor_frozen_at`.
2. Three templates in `contracts/templates/`.
3. `detection/role_fit.py`:
   - exact checks: tool in allowed list, resource class allowed/denied, destination in allowlist, sensitivity ≤ ceiling;
   - fuzzy check for unlisted actions: similarity between `tool+resource description` and `purpose` (TF-IDF cosine by default; sentence-transformers if installed) → 0.3 vs 0.6.
4. `gateway/interceptor.py` calls L1 and records `lens_scores.role`.
5. `routes_contracts.py` + a "blast radius" helper: lists everything the contract allows and flags over-broad items (e.g., wildcard tools).

**Feature explanation – why L1 beats mimicry:** it doesn't care how "normal" the traffic looks; if the resource class is denied it is a violation.

**Tests:** `test_role_fit.py` – allowed → 0; denied class → 1; unlisted-similar → 0.3; unlisted-unrelated → 0.6; non-allowlisted destination ≥ 0.8.

**Done when:** a script calls `hr_files.read` as procurement agent and the response contains `lens.role = 1.0`.

---

## 6. Phase 3 – Provenance (L3) + Decoys (L4) (3 h)

**Goal:** the PS example attack is detected end to end. This is your **hero demo**.

**Build:**
1. `gateway/provenance.py`:
   - `POST /gateway/context` registers `{agent_id, source, trust}` and appends to the agent's **context window** (list of labels with step counter).
   - `age_steps` increments per tool call; labels expire after N steps (config) or on checkpoint reset.
   - Trust levels: `owner`, `system`, `peer_agent`, `untrusted` (documents, web, email, tool outputs unless the tool is marked trusted).
2. `detection/provenance_lens.py` – implement `s_prov` from `09_risk_scoring_spec.md` §2 (freshness decay × sink weight × owner-justification discount).
3. `detection/decoys.py`:
   - decoy registry (`type`, `location`, `role_scope`); seed: fake `hr/salaries_2026_final.xlsx`, fake key `ERP_ADMIN_KEY_canary`, fake endpoint `/admin/export`, canary string in sample docs;
   - **touch detection** in interceptor (tool args referencing decoy resource);
   - **canary scan** on outbound payloads (`http.post` body / email body).
4. `simulator/scenarios/s1_injection.py` + `payloads/` with 5 injection variants.
5. `simulator/mock_services/evil_server.py` records anything that actually arrives (to prove 0 bytes leaked).

**Feature explanation – taint is about data flow, not words:** the lens never inspects the document's text; so rewording or encoding the injection does not change detection.

**Tests:** `test_provenance.py`, `test_decoys.py`. Add a parametrized test across all 5 payload variants → all flagged identically.

**Done when:** running S1 triggers alerts at the HR read, and the evil server received nothing.

---

## 7. Phase 4 – Baseline, cold start, drift (L2) (3-4 h)

**Goal:** statistical lens + Day-0 detection + slow-drift catch.

**Build:**
1. `detection/baseline.py`:
   - per-agent tool-transition counts (order-2 with back-off to order-1);
   - role-level **prior** built from contract `typical_sequences` plus peer agents' pooled counts;
   - blend `P = w·P_own + (1−w)·P_prior`, `w = n/(n+k)`;
   - features: rate, bytes_out, hour-of-day → running mean/variance (Welford);
   - `s_base` via sigmoid of surprise/z (spec §2);
   - optional `IsolationForest` over feature vectors, trained periodically on peer data (secondary, off by default for explainability).
2. `detection/drift.py`:
   - `freeze_anchor(role_version)` snapshots baseline stats;
   - capability surface set `C_t` of (tool, resource_class, destination_class) not in the anchor;
   - CUSUM over sensitivity-weighted novelty; compare `|C_t|` to `budgets.new_resource_classes_per_week`.
3. `simulator/scenarios/s4_slow_drift.py` (one new capability every N minutes) and cold-start variant (agent with 0 history attacked at step 1).

**Feature explanation – frozen anchor:** a rolling baseline "forgives" a slow attacker because the baseline keeps moving; the anchor does not move until an owner sanctions a new contract version.

**Tests:** `test_baseline_coldstart.py` (with n=0 still flags out-of-role transitions), `test_drift_slow.py` (each step individually below threshold, cumulative trips).

**Done when:** S4 produces a WATCH → ELEVATED escalation by step ~N and the agent detail page can plot capability surface growth.

---

## 8. Phases 5-7 (summary specs)

### Phase 5 – Risk engine + explanations (2 h)
- `risk/engine.py`: noisy-OR fusion, impact factor, floors, session risk, threshold jitter (all constants from `config.py`).
- `risk/explain.py`: pick top-3 lens contributions → templated plain-English reasons; add counterfactual ("would not alert if…"); evidence = event ids.
- `risk/owasp_map.py`: lens/scenario → ASI tags (L3 → ASI01; L1/L5 → ASI03; manifest drift → ASI04; memory → ASI06; chain → ASI07/ASI08; decoy/rogue → ASI10).
- Persist `alerts`; push over WS.
- **Done when:** the alert JSON matches the template in spec §6.

### Phase 6 – Response orchestrator + token broker (3 h)
- `gateway/token_service.py`: in-memory (signed JWT-like) tokens with `scopes`, `exp` (default 5 min), `narrow(agent, remove_scopes)`, `revoke(agent)`; interceptor validates token **and** scopes on every call.
- `response/policies.py`: scope sets per mode (`restrict` removes `*sensitive*`, `egress`, keeps `benign` + role-core tools).
- `response/orchestrator.py`: band → action; STEP_UP creates an approval in `approvals.py` (timeout → auto-deny).
- `response/checkpoints.py`: store a clean snapshot (context labels cleared of the tainted source); `resume(agent, drop_source)`.
- Alert actions API: approve_once, approve_and_declare, keep_restricted, isolate, restore.
- **Tests:** `test_response.py` – after RESTRICT, price-check still passes, HR read and external post fail; restore returns the original scopes.
- **Done when:** S1 shows the agent still completing purchase requests *after* being restricted (the "no disruption" proof).

### Phase 7 – Chains, fingerprint, change declarations (3-4 h)
- `detection/chain.py`: delegation envelope `{origin, ceiling, inherited_taint}`; `effective = role ∩ parent_ceiling ∩ scope`; contagion: child risk adds `0.3×` to parent session risk and vice versa; networkx graph for the dashboard.
- `detection/fingerprint.py`: learn per-agent workload ID/network origin/inter-call timing; mismatch score.
- `detection/change_classifier.py` + `routes_declarations.py`: SANCTIONED / ORGANIC / SUSPICIOUS / ADVERSARIAL as in spec §5; a SANCTIONED result bumps the contract version and re-freezes the anchor.
- Manifest hashing in `tool_registry.py` for S3.
- Scenarios S2, S3, S6, S7, S8.
- **Done when:** S8 yields no alert and baseline v2; the negative variant yields an alert; S6 shows worker B limited by A's ceiling.

---

## 9. Phase 8 – Dashboard (5-6 h)

| Page | Contents | Why judges care |
|---|---|---|
| **Overview** | Agent cards with live risk gauge + status chip (Normal / Watch / Restricted / Isolated); live event feed | Immediate "wow" |
| **AlertDetail** | Risk, band, top-3 reasons, lens bars, evidence timeline with taint chain, OWASP chips, action buttons, counterfactual | Proves explainability |
| **AgentDetail** | Baseline vs now, capability-surface growth chart, token scopes before/after | Proves drift + restriction |
| **ChainGraph** | React Flow nodes per agent, edges per delegation, taint highlighted red | Proves chain handling |
| **Contracts** | Contract viewer + blast-radius report | Proves contract concept |
| **Replay** | Buttons for S1-S8; shows the live reaction | Drives the live demo |

Keep visuals simple, high contrast. Start with Overview + AlertDetail + Replay; the others are bonus.

---

## 10. Phase 9 – Evaluation + polish (3 h)
- `eval/run_eval.py`: all scenarios × 20 seeds × history sizes (0, 10, 100); `metrics.py` computes the metrics in `08_threat_scenarios_and_evasion.md`; `ablation.py` toggles lenses via `config.py`.
- Output markdown tables into `eval/results/` and paste into the README and slides (label "simulated").
- One-command demo: `make demo` seeds data, starts services, opens the Replay page.
- Record a 60-90 s screen capture.

---

## 11. Parallel work split (4 people)

| Person | Phases |
|---|---|
| **Dev A – Core/Gateway** | 0, 1 (gateway, store), 2, 6 |
| **Dev B – Detection** | 3, 4, 7 (lenses, classifier) |
| **Dev C – Frontend** | 8 (starts after API contracts in §2 are frozen; use mocked JSON until backend is ready) |
| **Dev D – Simulator + Eval + Story** | 1 (simulator), scenarios, 9, demo script, slides |

**Contract freeze first (30 min, all four):** event schema, decision schema, REST/WS list. Then work independently.

---

## 12. Build rules (keep scope sane)
1. **Config in one file** (`config.py`): weights, thresholds, windows, so tuning is a one-file change.
2. **No heavy ML in the critical path.** Rules + simple stats first; ML optional.
3. **Every lens returns** `{score, reason, evidence}` so explanation is automatic.
4. **Deterministic simulator** (seeded) so demo and eval are repeatable.
5. **Write the test for each lens before the dashboard.** The dashboard can't hide a broken detector.
6. **Fail closed** for sensitive tools if Warden is unreachable.
7. **Commit at each phase** with a tag (`phase-3-done`) so you can always demo a working version.

---

## 13. What to say is real vs simulated (put in README)
| Real in prototype | Simulated |
|---|---|
| Gateway, contracts, all 5 lenses, risk engine, response, dashboard | Agents (scripted Markov agents; optional LLM agent), tools/data, supplier/HR/ERP services, evil server |
| Token scoping enforced by gateway | Production OAuth/SPIFFE integration (future) |
