# Phase 5: The Full Risk Engine and Explainable Alerts

The PS says: *"The system should explain every alert with a clear risk score."* After this phase every alert carries its reasons, the **measured** effect of each reason, the causal chain, standards tags, and what would change the verdict.

---

## 1. What changed

| Added | Where |
|---|---|
| **Explanation builder** (reasons, leave-one-out, causal timeline, counterfactuals, text report) | `risk/explain.py` |
| **OWASP Agentic Top 10 (2026) mapping**, each tag with a "because" | `risk/owasp_map.py` |
| **Session risk**: repeated mid-level suspicion escalates | `risk/session.py` |
| **Threshold jitter**: secret per-agent shift of the band lines | `risk/jitter.py` |
| **Floors guarantee a minimum band**, so they survive jitter | `risk/engine.py`, `config.py` |
| **Score hiding**: `Decision.agent_view()` gives an agent a bare verdict | `models/events.py`, `api/routes_gateway.py` |
| Explanations stored with each alert (+ migration for old DBs), `GET /alerts/{id}` | `store/`, `api/routes_events.py` |
| Dashboard alert panel (click an alert) | `dashboard/src/AlertPanel.tsx` |

---

## 2. A real alert (S1, the HR read) as the system prints it

```
proc-plain-0-p (procurement_agent) used hr_files.read on hr/salaries_2026.xlsx: ELEVATED risk 70, recommended action STEP_UP

Why (strongest first):
  1. resource class 'hr_data' is explicitly denied for role 'procurement_agent' (tool hr_files.read)   [without this: 61, so it adds 9]
  2. untrusted input 'doc.read:supplier/quote_3_plain.pdf' was ingested 1 step(s) earlier, then the agent attempted read sensitive ('hr_files.read') that its role contract does not authorise   [without this: 67, so it adds 3]
  3. transition 'doc.read' -> 'hr_files.read' has probability 0.002 for this agent/role (6.2 nats of surprise, 0% own history / 100% role prior)   [without this: 68, so it adds 2]
  (+1 more)

Evidence timeline:
     evt_000001 LOW         2  doc.read supplier/quote_3_plain.pdf   <- ingested the untrusted source blamed for this alert
  >> evt_000002 ELEVATED   70  hr_files.read hr/salaries_2026.xlsx   <- action that triggered this alert

OWASP Agentic Top 10 (2026):
  ASI01 Agent Goal Hijack: untrusted content was ingested shortly before an action the role does not authorise
  ASI03 Identity and Privilege Abuse: the agent reached for data its role is explicitly not entitled to
  ASI10 Rogue Agents: behaviour departs sharply from this agent's and its peers' normal pattern

What would change the verdict:
  - Role-fit would drop to 0 only if the owner deliberately changed the contract to permit 'hr_data' for role 'procurement_agent'.
  - Provenance would be near 0 if the action were inside the role contract; ...
```
Reproduce with `make sim-attack`.

---

## 3. Feature explanations

### 3.1 "Without this" is measured, not prose (leave-one-out)
For every lens that contributed, we **re-run the fusion without it** and report the difference. So "adds 9" is a computed fact. It also yields a defence-in-depth number:

> For the S1 HR read, **removing any single detector still leaves the score at 61 or more (ELEVATED).** Detection does not hinge on any one lens.

(Test: `test_detection_survives_losing_any_single_lens`.) The marginal numbers are small *because* the lenses overlap. That's the point of defence in depth, and we say so rather than inflating each lens's credit. On the exfiltration alert, provenance "adds 0" because conclusive floors already set the score to 100; the report states that honestly.

### 3.2 The evidence timeline is a causal chain, not a log dump
It shows the agent's last actions with exactly two annotations: the action that **ingested the untrusted source blamed for the alert**, and the action that **triggered** it. (My first version annotated every ordinary lookup as "untrusted in context" and buried the cause; fixed after reading real output.)

### 3.3 OWASP mapping
Categories verified against the published list (Dec 2025): ASI01 Agent Goal Hijack · ASI02 Tool Misuse and Exploitation · ASI03 Identity and Privilege Abuse · ASI04 Agentic Supply Chain · ASI05 Unexpected Code Execution · ASI06 Memory and Context Poisoning · ASI07 Insecure Inter-Agent Communication · ASI08 Cascading Failures · ASI09 Human-Agent Trust Exploitation · ASI10 Rogue Agents.

| What fired | Tag |
|---|---|
| provenance | ASI01 |
| role: denied class / above ceiling | ASI03 |
| role: tool outside the grant | ASI02 |
| decoy touch, canary leak, sharp behavioural departure, drift | ASI10 (drift also ASI03) |

**The mapping from our lenses to categories is our judgement, not OWASP's.** Each tag carries a plain-language "because" so a reviewer can disagree. ASI04/06/07/08 are reserved for Phase 7 (poisoned tools, memory, chains).

### 3.4 Session risk: patterns, without punishing normal work
```
every call:           S = S × 0.85
if event_risk ≥ 20:   S = 1 − (1 − S)(1 − 0.5 × event_risk/100);  effective = max(event_risk, S)
```
A lone `hr_files.list` scores 55 (WATCH). Repeated: **55, 55, 55, 61 (ELEVATED), 65, 68, 69**. Without session risk it stays WATCH forever.
**Hard rule, learned from the drift lens:** the session only raises events that are *already* mildly suspicious. Ordinary work scores exactly what it would for an agent with no incident (tested), and the session fades after a quiet period (tested against an identical control agent).

### 3.5 Threshold jitter and score hiding (anti-probing)
A hijacked agent that can see its own score can learn the line at which it gets stopped and stay one point below. Two defences:
1. **Jitter**: each agent's thresholds are shifted by a secret, deterministic amount (HMAC of the agent id, ±`WARDEN_JITTER` points). The same score of 58 is WATCH for one agent and ELEVATED for another (tested over 60 agents).
2. **Score hiding** (`WARDEN_EXPOSE_SCORES=0`): the agent gets only `decision / mode / event_id / "ok" or "flagged for review" / result`. No score, no reasons, nothing to probe with. Operators still see everything on the websocket and in `/alerts`.

**Conclusive evidence must survive jitter.** Floors now guarantee a **minimum band** (decoy touch ≥ HIGH, canary leak and tainted-sensitive-egress = CRITICAL, drift budget ≥ ELEVATED), not just a number. Tested across 40 agents with jitter on: a decoy touch is never below HIGH.

**Default is jitter off** (amplitude 0) so research and evaluation are exactly reproducible. Production sets `WARDEN_JITTER=3`.

---

## 4. Testing

```bash
make test         # 151 tests: 141 run with no install; 10 API tests need FastAPI
make sim-attack   # S1 with the full printed explanation for both alerts
```

| Test file | What it proves |
|---|---|
| `test_explain.py` | readable headline; ≤3 reasons, strongest first, each with measured effect; **any single lens removed still ≥ ELEVATED**; conclusive evidence leads; **timeline is a 2-annotation causal chain**; OWASP tags use the real names and each has a "because"; honest "no counterfactual" for decoys; text report has every section; persisted and retrievable; **old databases are migrated** |
| `test_session.py` | accumulation math; quiet events neither feed nor inherit; decay; agent isolation; **repeats escalate on the 4th**; off-switch ablation; **ordinary work identical to a control agent**; fades after quiet period |
| `test_jitter.py` | off = 0; deterministic per agent+secret; bounded and well spread; shifts every threshold except LOW; same score → different bands for different agents; **floors guarantee minimum band at ±3**; decoy touch never downgraded across 40 agents; normal traffic still quiet with jitter on; **agent view leaks no score, band, lens, reason or alert id** |
| earlier suites | all 115 prior tests still pass unchanged with the new machinery active |

### Verification status (honest)
| Part | Status |
|---|---|
| Explanations, OWASP map, session, jitter, floors, score hiding, store migration | **Run and passing** (141 tests; demos executed) |
| `/alerts/{id}`, the `expose_scores` route behaviour (the new API tests), `AlertPanel.tsx` | Written; **not run** here (no FastAPI/npm in my sandbox). The same behaviour is unit-tested at service level (`agent_view`, `get_alert`). |

---

## 5. Findings worth knowing (including the unflattering ones)

1. **Session risk didn't change a single S4 number.** S4 spaces its attack steps with normal work in between, so the session decays. It matters for *bursts* of repeated mid-level activity, not for patient attackers; the drift budget (Phase 4) is what handles those. Don't oversell session risk.
2. **Lenses overlap heavily.** Each one's marginal contribution is small (+9, +3, +2) once the others are present. That's robustness, not weakness; but "provenance is the star" would be an overstatement.
3. **Two guessed test values were wrong, not the code** (a hand-computed 44.5 vs the true 44.4; and a "quiet period" expectation that forgot the agent had ingested untrusted data meanwhile, so provenance legitimately added 3.5). Fixed by comparing to an identical control agent instead of a magic number.
4. **A silent wiring bug caught by reading code, not tests:** my first patch added `agent_view` to the wrong class (`Event`, not `Decision`). Compiled fine; would have failed at first use. Now has a test.

## 6. Limits
- Counterfactuals are **template-based hints**, not causal proofs (the leave-one-out table is the measured part).
- Jitter protects thresholds only if scores are also hidden; with scores visible an agent can still estimate its own offset over many probes.
- OWASP tags are our mapping; ASI04/06/07/08 not yet exercised.
- Session risk uses call counts, not wall-clock time (needs a controllable clock; Phase 9).

## 7. Questions this phase lets you answer
- *"How do I know why it flagged this?"* Three reasons in plain English, each with the score it would have without it, plus the causal chain from the poisoned document to the action.
- *"Is detection brittle?"* Removing any single lens still leaves the S1 HR read at ELEVATED or above (≥ 61).
- *"Can the attacker learn your thresholds?"* Per-agent secret jitter plus hidden scores; conclusive evidence is guaranteed a minimum band regardless.
- *"How does this map to standards?"* OWASP Agentic Top 10 (2026) tags on every alert, each with a reason.
- *"Slow, repeated low-level activity?"* Session risk escalates repeats; the drift budget (Phase 4) handles patient staircases.

## 8. Next: Phase 6, enforcement
Turn shadow mode into action: the **token broker** (short-lived scoped tokens), **step-up approvals** (pause the action, human approves or denies), **restrict** (scope-reduced token: sensitive reads and egress removed, price checks keep working), **isolate**, **restore**, and checkpoint/resume without the tainted input. Success metric: **S1 leaks 0 bytes**, and legitimate work in the same session keeps flowing.
