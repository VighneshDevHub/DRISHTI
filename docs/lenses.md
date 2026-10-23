# Detection lenses

## L1 Role Fit  (`detection/role_fit.py`)  – built in Phase 2
*"Is this action inside the job this agent was hired for?"*

| Condition | Score |
|---|---|
| Resource class in `denied_resource_classes` | 1.0 |
| Not in contract, semantically **unrelated** to role | 0.6 |
| Not in contract, semantically **close** to role | 0.3 |
| Sensitivity above contract ceiling | ≥ 0.7 |
| Destination `external`/`unknown` (not allowlisted) | ≥ 0.8 |
| Inside the contract | 0.0 |

Lens score = max of everything that triggered; every triggered rule is kept as evidence.

**Semantic similarity** = cosine similarity of word counts between the action (tool name + description + resource class) and the role "reference document" (purpose + descriptions of allowed tools + allowed classes). Generic words (`get`, `read`, `list`, `api`…) are ignored so unrelated actions don't look similar. Threshold `similarity_tau` lives in `config.py`.

**Why it matters**
- Works on an agent's **first action** (cold start; no history).
- Hard limits ignore how "normal" traffic looks, which defeats **mimicry**.
- `doc.read` of `hr/…` is *reclassified* by path rules in the registry, so an agent cannot read HR files through a generic tool.

**Known limits (be honest in Q&A):** bag-of-words similarity is crude; a too-broad contract weakens the lens (see blast-radius report); L1 alone cannot say *why* the agent changed (Phase 3).

## L3 Causal Provenance  (`detection/provenance_lens.py`, `gateway/provenance.py`)  – Phase 3
*"Did untrusted content just push this agent into a risky action its role does not authorise?"*

```
s_prov = U_strength x sink_weight x (1 - 0.8 x justified)
U_strength  = exp(-age_steps / 10)   freshest untrusted label (peer_agent labels count x0.5)
sink_weight = egress_external 0.9 | read_sensitive 0.7 | write 0.6 | out_of_contract 0.5 | benign 0
justified   = 1 if the action is inside the role contract (role score == 0)
```
- The tracker counts tool calls per agent; a label's **age** is the calls since it was recorded; labels expire after 10 calls.
- Tool outputs are labelled by the registry's `output_trust` (documents, supplier data, tickets, logs = untrusted; ERP/CRM/HR = system).
- **Never reads document text.** Rewording, encoding or translating the injection changes nothing (tested across 5 disguises).
- **Key idea:** the role contract is the owner's standing authorisation, and untrusted text cannot widen it. So purchasing after reading a quote is fine (justified), while reading HR files right after reading a quote is not.
- **Limits:** it is a *correlation in time*, not proof of causation (an LLM mixes its whole context). That is why it is one lens among several, and why a legitimate declared change (Phase 7) can switch `justified` on.

## L4 Decoys  (`detection/decoys.py`)  – Phase 3  (the D3COY layer)
| Kind | Example | Trigger |
|---|---|---|
| file | `hr/salaries_2026_final.xlsx`, `payroll/bank_accounts_export.csv` | open/read = 1.0, directory listing = 0.4 |
| credential | `ERP_ADMIN_KEY_7f3a91c2` | appears in any tool argument = 1.0 |
| endpoint | `admin-export.internal` | destination host or path = 1.0 |
| canary | `CNRY-HR-5521-ZK` watermarked inside the real HR data | appears in an outbound payload = 1.0 (**proof of exfiltration**, even to an allowlisted host) |

Needs no history and no model, so it covers brand-new agents. An attacker mimicking normal behaviour still cannot know which resources are fake. Floors: decoy touch ≥ 85, canary exfil = 100.

## Fusion  (`risk/engine.py`)
`R = 1 - prod(1 - w_i * s_i)`, `risk = 100 * R * (0.5 + 0.5 * impact)`, then floors. Weights: role 0.8, provenance 0.9, decoy 1.0. Floors: decoy touch 85, tainted+sensitive+external egress 95, canary exfil 100.

## L2 Baseline  (`detection/baseline.py`)  – Phase 4
`P = w·P_own + (1−w)·P_prior`, `w = n_ctx/(n_ctx+20)`; prior = 50% contract typical sequences + 50% uniform over allowed tools, mixed 50/50 with same-role peer counts once peers have 20+ observations. `score = sigmoid(1.2·(max(surprise, sensitivity_z) − 3.5))`. A brand-new agent has `w = 0`. Learns only from events judged LOW. See `docs/phase-4.md`.

## L2b Drift  (`detection/drift.py`)  – Phase 4
Capability = `(tool, resource_class, destination_class)`. Frozen anchor (first 30 trusted events; contract capabilities count until then) + cumulative capability budget (weight 0.5+sensitivity, ×0.75 if permitted; budget 2.5; no decay) + CUSUM burst detector (decays). Scores only events that *use* a new capability. Budget exhausted ⇒ floor 60 (step-up) for new-capability use. Catches slow staircases, including under an over-broad contract.

## Fusion weights now
role 0.8 · provenance 0.9 · decoy 1.0 · baseline 0.5 · drift 0.5. Floors: decoy touch 85 · tainted+sensitive+external egress 95 · canary exfil 100 · drift budget exhausted 60.

## Beyond the lenses: the rest of the risk engine (Phase 5)
- **Session risk** (`risk/session.py`): decaying, noisy-OR accumulation; only raises events already at risk ≥ 20, so ordinary work is never penalised.
- **Floors guarantee a minimum band** (decoy touch HIGH · canary leak CRITICAL · tainted+sensitive egress CRITICAL · drift budget ELEVATED), surviving jitter.
- **Threshold jitter** (`risk/jitter.py`) and **score hiding** against threshold probing.
- **Explanations** (`risk/explain.py`): leave-one-out measured effect, causal timeline, OWASP tags (`risk/owasp_map.py`).

## Coming
L5 Chain + Fingerprint (Phase 7)
