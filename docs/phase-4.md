# Phase 4: Baseline, Cold Start and Slow Drift (L2 + L2b)

After this phase Warden has a model of *each agent's habits*, judges brand-new agents from day zero, and notices an agent that is being walked, step by step, beyond what it was trusted to do.

---

## 1. What changed

| Added | Where |
|---|---|
| **L2 Baseline lens**: transition model, role prior, peer pooling, sensitivity z-score | `detection/baseline.py` |
| **L2b Drift lens**: frozen anchor, capability budget, CUSUM burst detector | `detection/drift.py` |
| Learn-gate (learn only from events judged LOW) and ablation switches | `gateway/interceptor.py`, `config.py` (`Settings`) |
| New floor `drift_budget_exceeded` (60) | `risk/engine.py`, `config.py` |
| Five near-purpose tools (the "staircase") + one **deliberately over-broad contract** | `gateway/tool_registry.py`, `contracts/templates/procurement_broad_agent.yaml` |
| S4 slow-drift scenario (tight and over-broad variants) | `simulator/scenarios/s4_slow_drift.py` |
| `GET /agents/{id}/behavior`; dashboard chips `habit` and `drift` | `api/routes_agents.py`, `dashboard/src/` |

---

## 2. Feature explanations

### 2.1 L2 Baseline: "is this normal for THIS agent and agents like it?"
The model learns **tool-to-tool transitions** (after `supplier_api.get_price`, what comes next?). Every action gets a probability, converted to *surprise* in nats (`-ln p`), then to a 0-1 score: `s = sigmoid(1.2 × (x − 3.5))`, where `x` is the larger of the surprise and the sensitivity z-score.

**Cold start (a core challenge in the PS).** The model never starts empty:

```
P = w × P_own + (1 − w) × P_prior              w = n_ctx / (n_ctx + 20)
P_prior = 50% typical sequences from the role contract
        + 50% uniform over the tools the contract allows
        (then mixed 50/50 with POOLED counts from same-role peers, once they have 20+ observations)
```
- A **brand-new agent has w = 0** and is judged entirely by its role and its peers.
- As it builds history, `w` rises and its own behaviour takes over.
- A tool the contract doesn't allow gets only 0.4% prior probability, so it is surprising from action one (score 0.96 on day 0).
- **Sensitivity z-score:** after 10 learned events, reading data far more sensitive than the agent's norm scores high even through a perfectly normal tool (e.g. `doc.read` of a payroll file).

**Learn-gate (anti-poisoning).** The model learns only from events the whole pipeline judged LOW. Without it, an attacker who repeats a bad action teaches the baseline that it is normal. Tested directly: after 30 repeats of an HR read, the gated baseline still scores 0.96; the ungated one has dropped below 0.2.

### 2.2 L2b Drift: "has the capability surface grown beyond what this agent did while trusted?"
A **capability** is a triple `(tool, resource_class, destination_class)`.

1. **Frozen anchor.** The set of capabilities the agent was actually seen using in its first 30 trusted events. Until it freezes, the contract's own capabilities also count as expected (a new agent has no history yet). After the freeze it never moves, except when an owner sanctions the change (`refreeze`, wired to change declarations in Phase 7).
2. **Capability budget.** Every capability outside the anchor is remembered forever with weight `0.5 + sensitivity` (×0.75 if the contract permits it). No decay, so a slow staircase still adds up. When the total reaches **2.5**, the budget is spent and any further use of a new capability is **floored at 60 (step-up)**: the owner must sanction or refuse.
3. **CUSUM burst detector.** Catches many new capabilities in a short time. It forgives 0.25 per event, which is exactly why it can't be the only defence against *slow* drift: the budget is the real protection.

**The score applies only to events that use a new capability.** An agent that has drifted is not slowed down on its ordinary work. This was a bug in my first design (see §5).

### 2.3 Why this matters: the over-broad contract
Real teams write contracts like `supplier_api.*, erp.*`. Then *everything* is permitted, role-fit scores 0, and a baseline that adapts to recent behaviour is blind. `procurement_broad_agent.yaml` is that contract on purpose; `GET /contracts/procurement_broad_agent/blast-radius` warns about it. The drift lens is what catches abuse of the slack.

---

## 3. Results (S4: five plausible capabilities added one at a time, each used 6×, with normal work in between)

Risk of each capability's first and last use, by configuration. **A** = full system. **B** = rolling baseline only (no drift lens, learns from everything). **C** = baseline with learn-gate, no drift.

### S4a: tight contract (new capabilities are also out-of-contract)

| Capability | A first→last | B first→last | C first→last |
|---|---|---|---|
| 1 quote history | 40.6 → 41.0 WATCH | 38.2 → 33.1 WATCH | 38.2 → 38.7 WATCH |
| 2 invoices | 48.1 → 49.5 WATCH | 42.4 → 41.5 WATCH | 42.4 → 44.5 WATCH |
| 3 supplier contacts | **60.0 ELEVATED** | 44.6 → 36.9 WATCH | 44.6 → 43.7 WATCH |
| 4 all purchase requests | **60.0 ELEVATED** | 40.4 → 41.5 WATCH | 40.4 → 41.5 WATCH |
| 5 vendor terms | **60.0 ELEVATED** | 41.8 → 42.3 WATCH | 41.8 → 42.3 WATCH |

Takeaways: every step is already visible at WATCH (the tools are out-of-contract). What drift adds is the **escalation**: a pile of WATCH-level signals becomes one step-up decision at the 3rd capability. Without it nothing ever passes WATCH, and B shows **habituation** (capability 3 falls from 44.6 to 36.9 as the model gets used to it).

### S4b: over-broad contract (every step is permitted)

| Capability | A first→last | B and C (no drift) |
|---|---|---|
| 1 quote history | 17.6 → 16.0 **LOW** | 13.2 → 11.4 LOW |
| 2 invoices | 27.4 → 21.7 **LOW** | 17.2 → 9.7 LOW |
| 3 supplier contacts | 34.6 → 35.5 WATCH | 19.4 → 13.7 LOW |
| 4 all purchase requests | 38.6 → 36.2 WATCH | 20.2 → 15.3 LOW |
| 5 vendor terms | **60.0 ELEVATED** | 15.0 → 12.2 LOW |

Takeaways: without the drift lens the attacker is **completely invisible** (nothing ever above 21). With it, the 3rd and 4th steps reach WATCH and the **5th forces a step-up**.

**Legitimate work is untouched in every configuration:** 0 alerts, max normal risk 7 to 11.

### The honest limits
- **Early steps slip through.** On the broad contract, capabilities 1 and 2 stay LOW. Catching them would also flag normal exploration. This is tested and documented, not hidden (`test_documented_limit_early_steps_slip_through`).
- **Detection point depends on the budget.** Sweep over `DRIFT_H` (budget) × in-contract discount, showing the capability at which step-up is forced (None = never):

| DRIFT_H | S4a tight | S4b broad (×0.75) | S4b broad (×0.5) |
|---|---|---|---|
| 1.5 | 2 | 3 | 4 |
| 2.0 | 3 | 4 | 5 |
| **2.5 (chosen)** | **3** | **5** | None |
| 3.0 | 4 | 5 | None |
| 3.5 | 5 | None | None |
| 4.5 | None | None | None |

False positives stayed at 0 across the whole sweep, **but only because my simulated normal traffic has no rare-but-legitimate tools.** Real agents do, and each one spends budget, so I can't claim a lower budget is free. I picked 2.5 by reasoning (roughly "three or four meaningful new capabilities") *before* running the sweep. The sweep shows the result is **not fragile to small changes** but **does fail if the budget is set too loose.**
- Rate and hour-of-day features aren't implemented: they need a controllable clock (Phase 9). Two features are: transition surprise and sensitivity.
- `new_resource_classes_per_week` is a tolerance, not a real weekly window.
- Baselines live in memory; a restart forgets them (persisting counts is a Phase 9 item).
- Order-1 transitions only (the plan mentioned order-2 with back-off; order-1 was enough for every scenario here).

---

## 4. Numbers that changed for the earlier demo (S1)

| | Phase 3 lenses | Full pipeline (Phase 4) |
|---|---|---|
| HR read, new agent | 66.3 ELEVATED | **70.0** ELEVATED |
| HR read, agent with 40 prior actions | 66.3 | **70.1** (cold start ≈ warm) |
| Exfiltration | 100 CRITICAL | 100 CRITICAL |
| Stolen token, no poisoned doc (HR read) | 58.0 WATCH | **66.7** ELEVATED |

Use **70** for the HR read in your slides. Note the stolen-token case now reaches ELEVATED on its own, because the baseline and drift lenses see that this agent never reads HR data.
Provenance's marginal contribution on top of all other lenses is smaller than in Phase 3 (70.0 vs 66.7). It is the lens that explains *why*, but the other lenses already detect *that*. Be accurate about this in Q&A.

---

## 5. Two design flaws this phase exposed (kept in the record)

1. **Drift punished normal work.** My first version applied the cumulative drift score to *every* event once any surface had grown: 59 normal actions were pushed into WATCH. Fix: score only events that use a new capability. Test: `test_budget_exhaustion_forces_step_up_only_on_new_capabilities` asserts ordinary work right afterwards stays LOW with drift score 0.
2. **My first staircase wasn't actually invisible, and my anchor made drift blind to the hard case.** Even with drift off, L1 and the baseline caught each out-of-contract step, and an anchor that included everything the contract allows could never see abuse of a broad contract. Fix: anchor = what the agent demonstrably did while trusted (contract capabilities only count before the freeze), plus the over-broad-contract scenario S4b.

Also corrected during testing: two assertions I had guessed (a probability threshold and a rounding comparison) were wrong; the code was behaving as designed.

---

## 6. Testing

```bash
make test         # 115 tests: 107 run with no install; 8 API tests need FastAPI
make sim-drift    # S4 tight + over-broad, with the ablation tables printed
make sim-attack   # S1, now with all lenses
```

| Test file | What it proves |
|---|---|
| `test_baseline.py` | day-0 typical start is unsurprising; contract-unlisted tool is surprising from action one; own history takes over; **learns only from LOW events**; **gate stops poisoned learning (0.96 vs <0.2)**; sensitivity z-score; **peer pooling helps a new agent**; ablation switches work |
| `test_drift.py` | normal work never drifts, even pre-freeze; anchor freezes at 30 events; out-of-contract novelty counted once; attacks never absorbed into the anchor; in-contract-but-unused counts at ×0.75; **budget exhaustion floors only novel capabilities and leaves ordinary work LOW**; burst detector rises and decays while the budget doesn't; `refreeze` accepts a sanctioned change |
| `test_s4_scenario.py` | tight contract: step-up by capability 3; rolling baseline never escalates and habituates; broad contract: invisible without drift, caught at capability 5 with drift, **early steps documented as slipping through**; legitimate work never disrupted |
| updated | S1 cold-start parity (70.0 vs 70.1) and disguise invariance still hold with all lenses; the full pipeline never scores below the isolated Phase 3 lenses (noisy-OR monotonicity) |

### Verification status (honest)
| Part | Status |
|---|---|
| Baseline, drift, floors, S4, S1 with all lenses | **Run and passing** (107 tests; both demos executed) |
| `/agents/{id}/behavior` + its API test, dashboard chips | Written; **not run** (no FastAPI/npm in my sandbox) |

---

## 7. Questions this phase lets you answer
- *"What about an agent with no history?"* Day-0 uses the contract and peer agents. A new agent scored 70.0 on the S1 attack against 70.1 for a veteran.
- *"What if the attacker changes behaviour slowly?"* A frozen anchor plus a cumulative capability budget; a rolling baseline measurably habituates (44.6 → 36.9) and never escalates.
- *"What if our contract is too broad?"* That's the hardest case: without drift the attacker was invisible; with it, step-up at the 5th capability. We flag over-broad contracts in the blast-radius report. And we say plainly that the first two steps slip through.
- *"Can an attacker retrain your baseline?"* No: it only learns from events judged LOW (30 repeated attacks: still 0.96).
- *"Does this slow down legitimate work?"* 0 alerts on legitimate work in every S4 configuration; only new-capability use is stepped up.

## 8. Next: Phase 5, explanations and the full risk engine
Session (multi-step) risk, per-agent secret threshold jitter, the complete alert format (top-3 reasons, evidence timeline, counterfactual, OWASP tags), and the S2 stolen-token fingerprint groundwork. After that, **Phase 6 turns shadow mode into real enforcement** (step-up, scope-reduced tokens, isolate, restore) and takes "bytes leaked" to zero.
