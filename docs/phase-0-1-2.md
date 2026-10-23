# Phases 0, 1, 2: Build Guide

What exists after these phases, how each piece works, how to test it, and what to say about it.

---

## 1. What you can do now

1. Register agents with a declared role.
2. Route every tool call through a **gateway** that turns it into a normalised, security-meaningful **event**.
3. Judge each event against the agent's **role contract** (lens L1) and produce a **0-100 risk score**, a band, and a plain-English reason.
4. Store events and alerts; watch them live in a dashboard.
5. Generate realistic, repeatable normal traffic and a hijack preview with the simulator.

Not yet: provenance/decoys (Phase 3), baselines/drift (4), full risk fusion (5), blocking (6), chains (7).

---

## 2. Technology

| Layer | Tech | Why |
|---|---|---|
| Core engine | Python 3.11+, dataclasses, `sqlite3`, PyYAML | Zero install risk, trivially unit-testable |
| API | FastAPI + pydantic v2 + uvicorn | Fast, auto docs at `/docs`, WebSocket support |
| Storage | SQLite (file or `:memory:`) | No setup; swap for Postgres later via `store/` |
| Simulator | Python stdlib (`urllib`, `random`) | Runs anywhere, deterministic with seeds |
| Dashboard | React 18 + Vite + TypeScript | Quick to build, easy to extend in Phase 8 |
| Packaging | Docker Compose + Makefile | One-command run |
| Tests | stdlib `unittest` (pytest-compatible) | No test dependency needed |

---

## 3. Directory structure (what each file is for)

```
agent-warden/
├── Makefile                          make test | api | dashboard | sim | sim-attack
├── docker-compose.yml                backend:8000 + dashboard:5173
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── config.py                 ALL thresholds/weights/bands (single source of truth)
│   │   ├── services.py               builds the object graph (repo, registry, contracts, gateway)
│   │   ├── main.py                   FastAPI app factory + /health
│   │   ├── models/
│   │   │   ├── events.py             ToolCallRequest, Event, LensResult, Decision
│   │   │   └── contracts.py          RoleContract + validation + size parsing
│   │   ├── contracts/
│   │   │   ├── loader.py             ContractStore (append-only versions) + blast_radius()
│   │   │   └── templates/            procurement / support / devops YAML contracts
│   │   ├── gateway/
│   │   │   ├── tool_registry.py      tool -> class, sensitivity, sink type, manifest hash
│   │   │   ├── interceptor.py        THE pipeline: handle_tool_call()
│   │   │   └── mock_tools.py         simulated tool backends + `outbox` (what leaked)
│   │   ├── detection/role_fit.py     L1 Role Fit lens
│   │   ├── risk/
│   │   │   ├── impact.py             impact factor
│   │   │   └── engine.py             band_for() + provisional_risk()
│   │   ├── store/
│   │   │   ├── db.py                 schema
│   │   │   └── repo.py               all SQL
│   │   └── api/                      routes_*.py + ws.py (live feed)
│   └── tests/                        38 tests
├── simulator/
│   ├── client.py                     WardenClient (in-process or HTTP)
│   ├── agents/                       base Markov agent, procurement, support
│   └── runner.py                     CLI
├── dashboard/                        Vite React TS app
└── docs/
```

---

## 4. How a single tool call flows (`gateway/interceptor.py`)

```
agent --POST /gateway/tool-call--> handle_tool_call(req)
  1. look up agent + its contract version            (UnknownAgent / MissingContract -> 404/422)
  2. registry.resolve(tool, args)                    -> resource, class, sensitivity, destination
     - path rules: doc.read("hr/..") becomes class hr_data, sensitivity 0.9
  3. classify_destination(host, contract)            -> internal | allowlisted | external | unknown
  4. build Event                                     (normalised facts, no opinions)
  5. L1 RoleFitLens.evaluate(event, contract)        -> score 0..1 + reason + evidence
  6. impact = 0.5*sensitivity + 0.3*egress + 0.2*irreversible
  7. risk = 100 * (0.8 * s_role) * (0.5 + 0.5*impact)      <- provisional (Phase 5 replaces)
  8. band/action from thresholds (30 / 60 / 80 / 95)
  9. store event; if risk >= 30 also store alert
 10. SHADOW MODE: run the mock tool anyway, return Decision(ALLOW, shadow_action=...)
```

### Worked example (from the simulator)

| Action | s_role | impact | risk | band |
|---|---|---|---|---|
| `supplier_api.get_price SKU-100` | 0.0 | 0.10 | **0** | LOW |
| `hr_files.read hr/salaries_2026.xlsx` | 1.0 (denied class) | 0.45 | 100·0.8·(0.5+0.225) = **58** | WATCH |
| `http.post http://203.0.113.9/...` | 0.8 (unknown destination) | 0.5 | 100·0.64·0.75 = **48** | WATCH |

These are intentionally modest. One lens alone must not isolate an agent; Phase 3 adds provenance + decoys, and Phase 5 fuses them so the same attack reaches HIGH/CRITICAL.

---

## 5. Feature-by-feature explanation

### 5.1 Config (`config.py`)
Bands, egress factors, sensitivity levels, lens weights, similarity threshold, mode. If a number appears anywhere else it is a bug. Phase 9 tuning and ablations only touch this file.

### 5.2 Events and decisions (`models/events.py`)
- `ToolCallRequest`: what the agent sends (agent_id, tool, args, optional `context_labels`, `chain`, `fingerprint`).
- `Event`: the normalised record. No scores inside it, only facts. This keeps detectors independent and replayable.
- `LensResult`: every lens returns `{score, reason, evidence, details}`, so explanations come for free.
- `Decision`: `decision` (always ALLOW in shadow mode), `risk`, `band`, `shadow_action`, `message`, `lens`, `result`, `event`.

### 5.3 Tool registry (`gateway/tool_registry.py`)
Maps raw tool names to security facts: resource class, sensitivity, sink type (`benign / write / read_sensitive / egress`), which argument names the resource and destination, irreversibility.
- **Path rules** reclassify by path prefix (`hr/`, `payroll/`, `src/`).
- **Unknown tools** are scored, never trusted (`registered=False`).
- **Manifest hash** (sha256 of name + description + arg names) will detect a poisoned/changed tool in Phase 7 (scenario S3). Tested now.

### 5.4 Role contracts (`models/contracts.py`, `contracts/loader.py`, `templates/*.yaml`)
A contract is the agent's machine-readable job description: allowed tools (globs allowed), allowed/denied resource classes, sensitivity ceiling, egress allowlist, typical sequences, budgets.
- Validation catches missing fields, bad ceilings, contradictory allow/deny.
- `ContractStore` is **append-only**: a change must be a higher version. Phase 7 uses versions to re-freeze the drift anchor when an owner sanctions a change.
- `blast_radius()` answers *"if this agent is hijacked, what can it do?"* and warns on `*` tools/destinations, missing budgets, egress without an allowlist, tools more sensitive than the contract's own ceiling. Exposed at `/contracts/{role}/blast-radius`. A least-privilege recommender seed.

### 5.5 L1 Role Fit (`detection/role_fit.py`)
Scores 0.0 / 0.3 / 0.6 / 1.0 plus sensitivity (≥0.7) and destination (≥0.8) escalations. Needs **no history**, so it works on an agent's first action. Hard limits ignore how normal the traffic looks, which defeats mimicry. Details and limits in `docs/lenses.md`.

### 5.6 Impact and bands (`risk/`)
Impact factor weights how bad an action would be if malicious (sensitivity, egress distance, irreversibility). `band_for()` is final: LOW <30, WATCH 30-59, ELEVATED 60-79, HIGH 80-94, CRITICAL ≥95, each with a recommended action. `provisional_risk()` is the temporary single-lens formula.

### 5.7 Storage (`store/`)
SQLite via `Database` (schema) and `Repo` (all SQL). Tables: `agents`, `events` (indexed per agent), `alerts`. Event ids are `evt_000001…`, alert ids `alr_0001…`. `list_agents()` computes `event_count`, `last_risk`, `max_risk` for the dashboard.

### 5.8 Mock tool backends (`gateway/mock_tools.py`)
Simulated suppliers, ERP, docs, HR, email/http. The `outbox` records everything that "left the building", acting as the attacker's server. This is how we later **prove 0 bytes leaked** (Phase 6) and how we show today's shadow-mode leak as the "before".

### 5.9 API (`api/`, `main.py`)
Thin FastAPI wrappers around the gateway (see `docs/api.md`). The tool-call route also broadcasts `event` and `alert` messages over `/ws/live`.

### 5.10 Simulator (`simulator/`)
- `SimAgent`: seeded Markov chain per role with realistic arguments. Same seed gives identical traffic.
- `ProcurementAgent`, `SupportAgent`: role-specific chains.
- `WardenClient`: **in-process** (no server) or **HTTP**, same interface.
- `runner.py`: `--mode normal` (fleet traffic) and `--mode preview-attack` (normal, then a hijack: poisoned doc read → HR read → external POST).

### 5.11 Dashboard (`dashboard/`)
Fleet cards with live risk bars, an alert list (with "would: ACTION"), and a live event feed over WebSocket (auto-reconnect). Phase 8 adds alert detail, agent detail, chain graph and replay.

---

## 6. Running and testing

### 6.1 Automated tests (no install, no server)
```bash
make test
# or: PYTHONPATH=backend:backend/tests:. python3 -m unittest discover -s backend/tests -v
```
Expected: `Ran 38 tests ... OK` (the 5 API tests are skipped unless `fastapi` + `httpx` are installed; after `make install` they run → 38 run, 0 skipped).

| Test file | What it proves |
|---|---|
| `test_contracts.py` | templates load; validation rejects bad contracts; wildcards; append-only versions; blast-radius warnings |
| `test_tool_registry.py` | resolution; HR reclassified via generic `doc.read`; host parsing; unknown tool not trusted; manifest hash changes when a tool changes |
| `test_role_fit.py` | 0 inside contract; 1.0 denied; 0.6 unrelated; 0.3 close; ≥0.8 unknown destination; allowlisted not escalated; ceiling; **cold start flagged on first action** |
| `test_store_and_gateway.py` | band edges; impact math; ALLOW + tool result; alert/event persisted; **shadow mode lets data leak**; unknown agent/role/tool handling; stats; ids |
| `test_simulator.py` | **1,800 normal actions → 0 alerts** (false-positive guard); same seed → identical traffic; hijack flagged with zero history |
| `test_api.py` | health, register/call, errors, contracts/tools, websocket push |

### 6.2 Manual: attack preview (no server)
```bash
make sim-attack
```
Expected: five LOW actions, then `hr_files.read` → **WATCH 58** (class `hr_data` denied), then `http.post` to `203.0.113.9` → **WATCH 48** (unknown destination), then `Bytes that left the organisation: 24`.

### 6.3 Manual: full stack
```bash
make install
make api            # http://localhost:8000/docs
make dashboard      # http://localhost:5173
make sim            # live traffic
```
Check: header shows **Warden online · shadow mode · live**; fleet cards fill in; events scroll; alerts stay empty during normal traffic. Then in a fourth terminal:
```bash
python3 -m simulator.runner --base-url http://localhost:8000 --mode preview-attack
```
Alerts appear instantly in the dashboard.

Quick curl check:
```bash
curl localhost:8000/health
curl -X POST localhost:8000/agents -H 'content-type: application/json' \
     -d '{"agent_id":"proc-99","role":"procurement_agent"}'
curl -X POST localhost:8000/gateway/tool-call -H 'content-type: application/json' \
     -d '{"agent_id":"proc-99","tool":"hr_files.read","args":{"path":"hr/salaries_2026.xlsx"}}'
curl localhost:8000/contracts/procurement_agent/blast-radius
```

### 6.4 Verification status (honest)
| Part | Status |
|---|---|
| Core engine, registry, contracts, L1, storage, simulator | **Run and passing** (33 tests + attack preview executed) |
| FastAPI routes, WebSocket, `test_api.py` | Written and compile-checked; **not run** in my sandbox (no network to install FastAPI). Run `make install && make test` to execute them. |
| Dashboard | Written; **not built/run** (same reason). `npm install && npm run dev` |
| Docker files | Written, not executed |

If any of the last three fail on your machine, paste the error and I'll fix it first thing in the next step.

---

## 7. Troubleshooting
| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: app` | run via `make …` (sets `PYTHONPATH`), or `export PYTHONPATH=backend:backend/tests:.` |
| Dashboard says "backend offline" | start `make api`; check `VITE_API_URL`; CORS allows `localhost:5173` by default |
| Port 8000/5173 busy | change in Makefile/compose |
| Stale data | `make clean` removes `backend/warden.db` |
| API tests skipped | `pip install -r backend/requirements.txt` |

---

## 8. What to say about this in Q&A
- "Detection works from the very first action: no history needed. Our test creates an agent with zero events and flags the first HR read."
- "In shadow mode we measured what happens without enforcement: 24 bytes left the organisation. That's our baseline; Phase 6 takes it to zero."
- "Normal traffic: 1,800 simulated actions, zero alerts."
- "A hijacked agent can't read HR through a generic doc tool: path rules reclassify it."

---

## 9. Definition of done for Phases 0-2 (checklist)
- [x] Repo layout, Makefile, Docker, config
- [x] Models, storage, tool registry, mock backends
- [x] Simulator with seeded agents + CLI
- [x] Contracts (3 templates), validation, versioning, blast radius
- [x] L1 Role Fit with cold-start behaviour
- [x] Provisional risk, bands, alerts
- [x] API + live WebSocket + dashboard (needs your first run)
- [x] 38 tests; 33 executed here, 5 API tests pending your machine

## 10. Next: Phase 3 (the hero demo)
Context labels become real: `POST /gateway/context` registers untrusted ingestion, **L3 Provenance** scores "untrusted content → risky action", **L4 Decoys** plant fake HR file / API key / endpoint / canary string. The S1 injection scenario (5 payload variants) runs end to end, and the same attack climbs from WATCH to HIGH/CRITICAL.
