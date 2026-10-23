# 09 – Risk Scoring Specification

Goal: a score that is **simple enough to explain on a slide**, **deterministic enough to debug**, and **hard to game**.

---

## 1. Inputs per action

```
event = {
  agent_id, role, role_version, ts,
  tool, resource, resource_class, sensitivity (0..1),
  destination, destination_class (internal|allowlisted|external|unknown),
  bytes_out, is_irreversible,
  context_labels: [ {source, trust: owner|system|peer_agent|untrusted, age_steps} ],
  chain: { depth, origin, ceiling, inherited_taint },
  fingerprint: { workload_id, net_origin, inter_call_ms }
}
```

---

## 2. Lens scores (each 0..1)

### L1 Role Fit  `s_role`
| Condition | Score |
|---|---|
| Tool + resource class in contract | 0.0 |
| Not listed, but semantically close (similarity ≥ τ) | 0.3 |
| Not listed, unrelated | 0.6 |
| Listed in `denied_resource_classes` | 1.0 |
| Destination not in egress allowlist | max(current, 0.8) |

### L2 Baseline  `s_base`
- Sequence surprise: `surprise = -log P(tool_t | tool_{t-1}, tool_{t-2})` using the blended transition model.
- Feature z-scores: rate, bytes, hour-of-day.
- `s_base = sigmoid(a · (max(surprise_norm, z_max) − b))`; start with `a=1.2, b=2.5`.
- **Blend:** `P = w · P_own + (1 − w) · P_prior`, `w = n / (n + k)`, `k ≈ 50`. `P_prior` comes from the role contract's typical sequences plus peer-group counts.

### L2b Drift  `s_drift`
- **Capability surface** `C_t` = number of distinct (resource_class, destination_class, tool) triples touched since the frozen anchor, beyond those in the anchor.
- **CUSUM:** `S_t = max(0, S_{t-1} + (x_t − μ_anchor − δ))`, alarm when `S_t > h`. `x_t` = novelty indicator or sensitivity-weighted novelty.
- `s_drift = min(1, S_t / h)`; also compare `C_t` to `budgets.new_resource_classes_per_week`.

### L3 Causal Provenance  `s_prov`
Let `U` = any untrusted label in the recent window (default last 10 steps; decays with age).
Let `sink_weight` = {read_sensitive: 0.7, write/modify: 0.6, new_tool_or_destination: 0.5, egress_external: 0.9, benign: 0.0}.
`owner_justified` = 1 if the action maps to an owner-originated instruction or declared change, else 0.
```
s_prov = U_strength × sink_weight × (1 − 0.8·owner_justified)
U_strength = max over untrusted labels of exp(−age/10)   # fresher = stronger
```

### L4 Decoy  `s_decoy`
- Touch (read/use/auth) of decoy → 1.0
- Listing/stat only → 0.4
- Canary string seen in outbound payload → 1.0 (**exfil proof**)

### L5 Chain & Fingerprint  `s_chain`
- Requested permission exceeds envelope ceiling → 1.0
- Inherited taint from parent and risky sink → 0.7
- Fingerprint mismatch (workload ID / network origin) → 0.6–0.9
- Inter-call timing outside learned rhythm (z>3) → +0.2 (cap 1.0)

---

## 3. Fusion

**Noisy-OR** (any strong signal raises the score; independent signals compound):
```
R_b = 1 − Π_i (1 − w_i · s_i)
weights: w_role=0.8, w_base=0.5, w_drift=0.5, w_prov=0.9, w_decoy=1.0, w_chain=0.8
```

**Impact factor** `I ∈ [0,1]`:
```
I = clamp( 0.5·sensitivity + 0.3·egress_factor + 0.2·irreversibility )
egress_factor: internal 0, allowlisted 0.3, external 0.8, unknown 1.0
```

**Risk (0-100):**
```
Risk = 100 · R_b · (0.5 + 0.5·I)
```

**Floors (hard rules):**
- Decoy touch → `Risk ≥ 85`
- Canary string in outbound payload → `Risk = 100`
- Untrusted taint + sensitive data + external/unknown egress → `Risk ≥ 95`
- Authority ceiling violation → `Risk ≥ 80`

**Session risk** (to catch slow or repeated activity):
```
Session_t = max(Risk_t, 0.7 · Session_{t−1} + 0.3 · Risk_t)    # decays when quiet
Decision uses max(Risk_t, Session_t)
```

**Sanctioned-change discount:** if the Drift Classifier says `SANCTIONED` (valid declaration, owner-originated trigger), reduce `s_role` and `s_base`/`s_drift` to 0 for the declared scope only. It does **not** discount decoys or provenance to external egress.

---

## 4. Bands & actions

| Score | Band | Action | UX |
|---|---|---|---|
| 0-29 | LOW | Allow | None |
| 30-59 | WATCH | Allow + log + sample more | Dashboard badge |
| 60-79 | ELEVATED | **Step-up**: pause risky action; human approve/deny | Approval card |
| 80-94 | HIGH | **Restrict**: scope-down token (no sensitive read, no egress) | Alert + undo button |
| 95-100 | CRITICAL | **Isolate**: revoke, sandbox, checkpoint, notify chain | Incident |

Thresholds are **jittered ±3** (per agent, secret) to blunt threshold probing.

---

## 5. Drift Classifier (legit vs adversarial)

Features: `has_declaration`, `trigger ∈ {owner, schedule, untrusted, unknown}`, `peer_adoption_ratio`, `speed (steps to reach new surface)`, `sensitivity_of_new`.

Rule-based first (explainable), model later:
```
if has_declaration and trigger==owner:                 SANCTIONED
elif peer_adoption_ratio ≥ 0.5 and sensitivity_new<0.3: ORGANIC   # fleet-wide benign
elif trigger==untrusted and sensitivity_new ≥ 0.5:      ADVERSARIAL
else:                                                   SUSPICIOUS
```

---

## 6. Alert explanation template

```
ALERT #123  |  Procurement-Agent-07  |  Risk 82 (HIGH → RESTRICT)
Why (top 3):
 1. Out of role: read `hr/salaries.xlsx` (resource class hr_data is denied for procurement_agent v1)   [L1 = 1.0]
 2. Caused by untrusted input: untrusted PDF `supplier_quote_3.pdf` ingested 2 steps earlier           [L3 = 0.63]
 3. Never seen: this transition has probability 0.0004 for this role/peers                            [L2 = 0.7]
Impact: sensitivity 0.9 (payroll), no egress yet → impact factor 0.45+
Mapped risks: OWASP ASI01 Agent Goal Hijack, ASI03 Identity & Privilege Abuse
Action taken: token scope reduced (no sensitive reads, no external sends); price-check and purchase tools still available
Counterfactual: would not alert if owner had declared "payroll reconciliation" task for this agent
Controls: [Approve once] [Approve & declare change] [Keep restricted] [Isolate] [Restore scope]
```

---

## 7. Calibration plan (24 h)
1. Generate normal traffic; set `a, b, k` so false-block rate < 2%.
2. Run S1-S8; adjust weights only if a scenario is missed; document each change.
3. Run ablations (turn each lens off) and record which scenarios break.
4. Freeze weights; evaluate on fresh random seeds; report those numbers.
