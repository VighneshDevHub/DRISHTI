# Agent Warden

**Valid credentials. Invalid behavior.**
A behavioral identity layer for autonomous AI agents: it checks whether an agent is *still doing the job it was created for*, even though its token is valid.

> Built for D3COY 1.0 – *Identity Drift Detection in Autonomous AI Agents.*

## Status

| Phase | What | State |
|---|---|---|
| 0 | Scaffold, Docker, Makefile, health check | ✅ done |
| 1 | Events, agents, storage, tool registry, simulator, live feed | ✅ done |
| 2 | Role contracts, gateway, **L1 Role Fit lens**, provisional risk | ✅ done |
| 3 | **Provenance (L3) + decoys (L4) + noisy-OR fusion + hero attack S1** | ✅ done |
| 4 | **Baseline + cold-start blend + peer pooling + frozen-anchor drift (L2, L2b), S4 slow drift** | ✅ done |
| 5 | **Explainable alerts (measured reasons, causal chain, OWASP tags), session risk, threshold jitter, score hiding** | ✅ done |
| 6 | **Enforcement: token broker, step-up approvals, restrict, isolate, restore/resume. S1 leaks 0 bytes** | ✅ done |
| 7 | Delegation chains, token fingerprints, poisoned tools, change declarations | next |
| 8-9 | Full dashboard, evaluation | planned |

Runs in **shadow mode** by default (score and record, block nothing: the safe way to roll out). Set `WARDEN_MODE=enforce` to act: pause, restrict, isolate. Try `make sim-enforce`.

## Quick start (no server, 10 seconds)

```bash
make test            # 207 tests (13 API tests need FastAPI installed)
make sim-attack      # S1 end to end, with the full printed explanation of each alert
make sim-disguises   # same attack in 5 disguises -> identical detection
make sim-drift       # S4 slow drift (tight + over-broad contract) with ablation tables
make sim-enforce     # S1 under enforcement: 0 bytes leaked, even if a human approves everything
make sim-mimicry     # S5: attacker restricted, legitimate work continues
```

## Full stack

```bash
make install       # backend packages + pnpm dashboard dependencies
make api           # terminal 1 -> http://localhost:8000/docs
make dashboard     # terminal 2 -> http://localhost:3000
make sim           # terminal 3 -> live traffic into the dashboard
# or: docker compose up --build
```

The Next.js dashboard sends browser requests directly to FastAPI. Set
`NEXT_PUBLIC_DRISHTI_API_URL` to the backend's browser-reachable origin (default
`http://localhost:8000`) and allow the dashboard origin in
`WARDEN_CORS_ORIGINS`. The development defaults permit localhost ports 3000 and
5173. Restart FastAPI after changing its environment.

The Scenario Runner executes fixed development simulations against the active
backend via `/sim/scenarios/{scenario_id}/run`. It is intended for local demos:
agents and tool backends are simulated, and no scenario invokes arbitrary
commands or connects to external systems.

## Layout

```
backend/app/
  config.py            every tunable number (one file)
  models/              events, contracts (plain dataclasses)
  contracts/           loader + versioning + blast-radius, templates/*.yaml
  gateway/             tool_registry, interceptor (the pipeline), provenance, token_service (broker), mock_tools
  response/            policies, approvals, orchestrator, checkpoints
  detection/           role_fit (L1), provenance_lens (L3), decoys (L4), baseline (L2), drift (L2b) ... chain in Phase 7
  risk/                impact, engine (noisy-OR fusion, floors, bands), session, jitter, explain, owasp_map
  store/               sqlite db + repo (all SQL)
  api/                 FastAPI routes + websocket hub
simulator/             seeded agents, client SDK, runner CLI, payloads/ (5 injection disguises), scenarios/ (S1, S4, S5)
dashboard/             Next.js App Router + React + TypeScript
docs/                  guides (docs/phase-0-1-2.md, phase-3.md, phase-4.md, phase-5.md, phase-6.md)
```

Full design: see the planning pack (`00`–`11` markdown files).

## What is real vs simulated
Real: gateway, contracts, L1 lens, risk bands, storage, API, dashboard.
Simulated: agents (scripted Markov chains), tool backends (`gateway/mock_tools.py`), the "attacker server" (`backend.outbox`).
