# API reference (Phases 0-6)

Base URL `http://localhost:8000` · interactive docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status, mode, roles loaded, tool count |
| POST | `/agents` | register `{agent_id, role, owner?, role_version?}` (422 if no contract) |
| GET | `/agents` | fleet with `event_count`, `last_risk`, `max_risk` |
| GET | `/agents/{id}` | agent + 50 recent events (404 if unknown) |
| POST | `/gateway/tool-call` | **the** endpoint every agent action goes through |
| GET | `/events?agent_id=&limit=` | recent events with lens scores |
| GET | `/alerts?limit=` | alerts (band WATCH or above), without explanations |
| GET | `/alerts/{id}` | one alert **with its full explanation**: top reasons with measured effect, leave-one-out table, causal timeline, OWASP tags, what would change the verdict |
| GET | `/contracts` · `/contracts/{role}?version=` | contracts |
| GET | `/contracts/{role}/blast-radius` | what a hijacked agent of this role could do + warnings |
| GET | `/tools` | tool registry incl. manifest hashes |
| POST | `/gateway/context` | tell Warden an agent ingested content **outside** the gateway: `{agent_id, source, trust}` |
| GET | `/agents/{id}/context` | the live provenance labels for an agent |
| GET | `/agents/{id}/behavior` | what Warden learned: top transitions, anchor state, novel capabilities, burst level |
| GET | `/approvals?status=` | paused actions awaiting a human (expired ones are auto-denied first) |
| GET | `/approvals/{id}/status` | agent-facing: status, and the result once approved |
| POST | `/approvals/{id}/resolve` | `{action: approve_once\|deny, by}`; 409 if already resolved / agent isolated |
| POST | `/agents/{id}/token` | renew a token from the agent's CURRENT posture; 403 if isolated |
| POST | `/agents/{id}/isolate` · `/restore` · `/resume` | operator controls; `resume` returns `drop_sources` for the framework to forget |
| GET | `/decoys` | planted decoys and hit counts |
| POST | `/sim/docs` · GET `/sim/outbox` · POST `/sim/reset-outbox` | dev-only: seed documents, see what leaked |
| WS | `/ws/live` | pushes `{type:"event"|"alert", data}` |

## `POST /gateway/tool-call`

Request
```json
{"agent_id":"proc-07","tool":"hr_files.read","args":{"path":"hr/salaries_2026.xlsx"},
 "context_labels":[{"source":"quote_3.pdf","trust":"untrusted","age_steps":2}]}
```
Response
```json
{"decision":"ALLOW","mode":"shadow","risk":58.0,"band":"WATCH","shadow_action":"WATCH",
 "message":"WATCH: resource class 'hr_data' is explicitly denied for role 'procurement_agent' ...",
 "event_id":"evt_000012","alert_id":"alr_0001",
 "lens":{"role":{"score":1.0,"reason":"..."},"provenance":{"score":0.633,"reason":"...","details":{"tainted":true,"sink":"read_sensitive"}},
         "decoy":{"score":0.0},"impact":0.45,"fusion":{"combined":0.914,"contributions":[["role",0.8],["provenance",0.57]],"floors":[]}},
 "result":{"ok":true,"data":"..."},"event":{...}}
```
`decision` is always `ALLOW` in shadow mode; `shadow_action` is what Warden *would* do. `context_labels` you send are merged with the labels Warden tracks itself (freshest age wins). Tool outputs from untrusted tools are labelled automatically; use `/gateway/context` for content read outside the gateway.

`trust` is one of `owner | system | peer_agent | untrusted`.


## Enforcement (Phase 6)
`WARDEN_MODE=shadow` (default) scores and records only. `WARDEN_MODE=enforce` requires a token on every call and returns one of:

| `decision` | meaning |
|---|---|
| `ALLOW` | the tool ran; `result` is present |
| `PENDING_APPROVAL` | one action paused for a human; `approval_id` set; poll `/approvals/{id}/status` |
| `BLOCK` | refused; `block_reason` ∈ `policy_critical, policy_high, scope_denied, restricted_posture, agent_isolated, token_missing, token_invalid, token_revoked, token_expired` |

`POST /agents` returns a `token`. On `token_*` blocks a client should call `POST /agents/{id}/token` once and retry.
The agent view reveals `block_reason` only for token errors; policy reasons stay private.

## Score hiding
With `WARDEN_EXPOSE_SCORES=0` the response to an **agent** is only
`{"decision","mode","event_id","message":"ok"|"flagged for review","result"}`: no score, band, lens, reason or alert id.
Operators still receive everything on `/ws/live` and from `/alerts`. Default is `1` (prototype), so the simulator can print scores.

## Environment variables
| Variable | Default | Meaning |
|---|---|---|
| `WARDEN_MODE` | `shadow` | `shadow` (observe only) or `enforce` (pause / restrict / isolate) |
| `WARDEN_DB` | `warden.db` | SQLite path |
| `WARDEN_JITTER` | `0` | ± points of secret per-agent threshold jitter (production: `3`) |
| `WARDEN_JITTER_SECRET` | `dev-secret-change-me` | HMAC key for jitter. **Change it.** |
| `WARDEN_EXPOSE_SCORES` | `1` | `0` hides scores from agents |
