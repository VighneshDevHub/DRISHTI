# Phase 3: Provenance + Decoys (the hero demo)

After this phase, the problem statement's own attack is detected end to end, with a causal explanation, in five different disguises.

---

## 1. What changed

| Added | Where |
|---|---|
| Provenance tracker (per-agent taint memory) | `gateway/provenance.py` |
| **L3 Causal Provenance lens** | `detection/provenance_lens.py` |
| **L4 Decoy lens** + decoy registry + canary watermarking | `detection/decoys.py` |
| Noisy-OR fusion + hard floors (replaces the Phase 2 single-lens formula) | `risk/engine.py` |
| `output_trust` per tool; new weights/floors/windows | `gateway/tool_registry.py`, `config.py` |
| Gateway pipeline now runs 3 lenses and records outputs afterwards | `gateway/interceptor.py` |
| `POST /gateway/context`, `GET /decoys`, dev helpers `/sim/*` | `api/` |
| 5 injection disguises + the S1 scenario | `simulator/payloads/`, `simulator/scenarios/s1_injection.py` |
| Dashboard: lens chips, decoy-hit and leaked-bytes tiles, multi-reason alerts | `dashboard/src/` |

---

## 2. The new pipeline

```
request
 1. provenance.begin(agent)                -> step number
 2. labels = live context labels           (tracked + any the caller sent), each with an age
 3. resolve tool, classify destination, build Event
 4. L1 Role Fit        -> s_role
 5. L3 Provenance      -> s_prov     (needs: labels, "is this action justified by the contract?", sensitive reads in context)
 6. L4 Decoys          -> s_decoy    (needs: the tool arguments, to find credentials and canaries)
 7. impact factor
 8. fuse: R = 1 - prod(1 - w*s);  risk = 100*R*(0.5+0.5*impact);  apply floors
 9. store event + alert (reasons: floors first, then lenses by contribution)
10. run the tool (shadow mode)
11. record outputs: untrusted tool output -> new taint label; sensitive read -> remembered
```
Step 11 is how taint gets created: reading a document is what taints the agent, not a flag someone sets.

---

## 3. Feature explanations

### 3.1 Provenance tracker
Counts tool calls per agent. A label (`source`, `trust`) is stamped with the call it arrived on; its **age** is how many calls ago that was. Labels older than 10 calls expire. It also remembers *sensitive reads* (sensitivity ≥ 0.5) so a later outbound send can be recognised as "sensitive data was in play".
Two entry paths: automatic (tools whose output is untrusted), and explicit `POST /gateway/context` for content read outside the gateway (inbound email, web page, a peer agent's message).

### 3.2 L3 Provenance lens
`s_prov = U_strength × sink_weight × (1 − 0.8 × justified)`
- **U_strength** = `exp(-age/10)` for the freshest untrusted label (peer-agent labels count half). Fresh taint matters more; old taint fades.
- **sink_weight**: how dangerous the action is as a destination for tainted influence: external egress 0.9, sensitive read 0.7, write 0.6, out-of-contract 0.5, benign 0.
- **justified**: 1 when the action is inside the role contract.

The important design choice: **the contract is the owner's standing authorisation, and untrusted text cannot widen it.** After reading a supplier quote, creating a purchase request is normal (justified: score ≈ 0.1, risk ≈ 5). Reading HR salaries right after reading a quote is not (unjustified: score 0.63).
It never inspects document text, which is why disguises don't matter.

### 3.3 L4 Decoys
Four kinds (file, credential, endpoint, canary), all seeded by `DecoyRegistry.seed_backend()`.
- **File decoys** sit where an attacker would look (`hr/salaries_2026_final.xlsx`). Opening one scores 1.0 and triggers a floor of 85. Merely listing a directory that contains one scores 0.4 with no floor, so a harmless `ls` doesn't stall an agent.
- **Credential/endpoint decoys** trigger on any argument containing a fake key, or a call to a fake host.
- **Canaries** are unique strings *watermarked into real data*. If one appears in an outbound payload, that data is leaving, even to an allowlisted host. Floor: 100.
No history, no model, no baseline. So it protects a brand-new agent and cannot be mimicked.

### 3.4 Fusion and floors
- **Noisy-OR** lets any strong signal raise the score and lets independent signals compound; an average would let quiet lenses dilute a loud one.
- **Impact** scales the result: the same signal on a payroll file matters more than on a price lookup.
- **Floors** are for conclusive evidence: decoy touch ≥ 85, tainted + sensitive-in-context + external egress ≥ 95, canary exfil = 100. These are proof, not probabilities.
- Phase 5 adds the remaining lenses, session (multi-step) risk, threshold jitter, and the full explanation format.

### 3.5 Injection disguises
`simulator/payloads/injections.py` holds the **same instruction** in five wrappers: plain text, HTML comment, base64, markdown table, Spanish. `extract_instruction()` stands in for the compromised LLM and recovers it from any of them. The point is the test that follows: detection is identical for all five.

### 3.6 S1 scenario
`s1_injection.run(client, variant, history, poisoned)`: register a procurement agent, optionally give it `history` normal actions, seed the poisoned PDF, then: read PDF → read HR file → POST to an attacker address. `poisoned=False` is the **control**: the attacker has the token but no document was read first (token theft).

---

## 4. Real numbers from the prototype

S1, brand-new agent, any of the five disguises:

| Step | Action | L1 role | L3 prov | L4 decoy | Risk | Band | Would do |
|---|---|---|---|---|---|---|---|
| 1 | read supplier quote | 0 | 0 | 0 | **0** | LOW | allow |
| 2 | read `hr/salaries_2026.xlsx` | 1.0 | 0.63 | 0 | **66.3** | ELEVATED | step-up (human approval) |
| 3 | POST to `203.0.113.9` | 0.8 | 0.74 | 1.0 (canary) | **100** | CRITICAL | isolate |

Control (stolen token, no document read first): HR read = **58.0 WATCH**. So provenance lifts the same action from WATCH to ELEVATED (+8.3), purely because untrusted content preceded it.

In shadow mode 55 bytes still leave the organisation. That is the "before" number; Phase 6 takes it to 0.

> **Update your pitch numbers.** The story in `06_story_and_pitch_script.md` used an illustrative "risk 82". The real prototype values are **66 → step-up** for the HR read and **100 → isolate** for the exfiltration. Use the real ones in the demo and slides. Phase 5 adds the remaining lenses and will lift step 2 further.

---

## 5. Testing

```bash
make test             # 84 tests: 77 run without any install; 7 API tests need FastAPI (they run after `make install`)
make sim-attack       # S1 end to end with the alert reasons printed
make sim-disguises    # 5 disguises, identical numbers
```

| Test file | What it proves |
|---|---|
| `test_provenance.py` | age counts tool calls; expiry; per-agent isolation; label merging; `clear`; **normal work after reading a doc is not flagged**; out-of-contract after untrusted input is amplified; no taint → 0; taint fades with age; explicit context endpoint; owner/system never taint; peer taint = ½ |
| `test_decoys.py` | opening a decoy → floor 85; decoy through a generic doc tool; listing = weak, no floor; credential, endpoint; **canary in payload → 100 even to an allowlisted host**; reading watermarked data is not exfil; legit files never hit; hit counting; exempt roles; works on a brand-new agent |
| `test_fusion.py` | zero when quiet; matches Phase 2 for one lens; noisy-OR compounds; monotonic; impact scaling; unknown lens ignored; each floor and its conditions |
| `test_s1_scenario.py` | all 5 disguises hide the same instruction; **identical detection across disguises**; cold start == warm; provenance adds signal over role-fit alone; canary watermark present on exfil; alerts explain the causal chain; shadow mode still leaks |
| `test_simulator.py` (existing) | **1,800 normal actions → still zero alerts** with all new lenses active |
| `test_api.py` (extended) | context endpoint (+422/404), decoys, outbox |

Manual checks with the full stack running:
```bash
make api && make dashboard                       # two terminals
make sim                                         # normal traffic: no alerts
python3 -m simulator.runner --base-url http://localhost:8000 --mode s1 --variant html_comment
```
Dashboard should show: an ELEVATED then CRITICAL alert, **role / taint / decoy chips** on the events, the **bytes-left tile** turning red, and a decoy hit only if you open a decoy file.

Try the decoys directly:
```bash
curl -X POST localhost:8000/agents -H 'content-type: application/json' -d '{"agent_id":"t1","role":"support_agent"}'
curl -X POST localhost:8000/gateway/tool-call -H 'content-type: application/json' \
     -d '{"agent_id":"t1","tool":"doc.read","args":{"path":"payroll/bank_accounts_export.csv"}}'
curl localhost:8000/decoys
```

### Verification status (honest)
| Part | Status |
|---|---|
| All lenses, fusion, tracker, scenario, payloads, runner | **Run and passing** (77 tests executed, S1 demo executed) |
| New API routes + extended `test_api.py` | Written and compile-checked; **not run** here (no FastAPI in my sandbox) |
| Dashboard changes | Written; brace/paren balance checked; **not built** |

---

## 6. Known limits (say these before a judge does)
1. **Taint is correlation in time, not proof of causation.** An LLM mixes everything it has read. Mitigation: L3 is one lens; hard contract limits and decoys don't depend on it.
2. **Everything an agent reads is "untrusted" by default** (documents, supplier data, tickets). The `justified` discount is what prevents false alarms; a contract that is too broad weakens it. The blast-radius report flags this.
3. **Decoys need upkeep** and a believable layout. They are auto-seeded here; production needs rotation.
4. **Canaries only catch data that was watermarked.** Unwatermarked data can still leave; L1/L3 are the net for that.
5. **Shadow mode.** Nothing is blocked yet.

## 7. Questions this phase lets you answer
- *"Doesn't an attacker just reword the injection?"* We ran five disguises including base64 and Spanish; scores were identical because we watch data flow, not words.
- *"What about a new agent with no history?"* Decoys and the contract need none; S1 scores the same at 0 and 40 prior actions.
- *"What if the attacker copies normal behaviour?"* They still can't know which files are decoys, and the contract's hard limits ignore how normal traffic looks.
- *"Won't this flag normal work after reading a PDF?"* 1,800 normal actions raised zero alerts, because the contract justifies in-role actions.

## 8. Next: Phase 4, baseline, cold-start blend and slow drift (L2)
Per-agent tool-transition model blended with a role prior and peer pooling (`w = n/(n+k)`), rate/volume statistics, a **frozen anchor** per contract version, a capability-surface budget with CUSUM, and the S4 slow-drift scenario. It's what catches an attacker who stays inside the contract but changes behaviour gradually.
