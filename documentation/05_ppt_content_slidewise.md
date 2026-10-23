# 05 – PPT Content, Slide by Slide

> Template has **6 slides** with fixed titles. Keep them. Each section below gives: **On-slide text** (short, paste it), **Visual to draw**, and **Speaker notes**. Keep on-slide text to ~6 lines per block. Dark red/black theme: use white text, red accent for "danger", green for "safe", amber for "watch".

---

## SLIDE 1 – Title / Team

**TEAM NAME:** [your team name]
**COLLEGE NAME:** [your college]
**PROBLEM STATEMENT:** Identity Drift Detection in Autonomous AI Agents. *Detect when an agent's behavior no longer matches its declared role, even though its credentials are still valid.*
**TEAM MEMBERS:** 4 names + contact numbers.

**Optional tagline under the title:** *Agent Warden: Valid credentials. Invalid behavior.*

---

## SLIDE 2 – PROPOSED SOLUTION

### On-slide text

**The gap:** Security checks *"is this agent allowed?"*. A hijacked agent is still allowed.

**Our solution: Agent Warden.** A behavioral identity layer that asks *"is this agent still doing the job it was hired for, and what made it change?"*

**How it works (4 steps):**
1. **Declare:** each agent's role becomes a machine-readable *Role Contract*.
2. **Watch:** a gateway sees every tool call and tags where each piece of context came from.
3. **Judge:** 5 independent lenses (role fit, baseline, causal provenance, decoys, chain) produce a **0-100 risk score** with plain-English reasons.
4. **Contain:** graduated response, from *step-up approval* to *scope-reduced token* to *isolate*, so legitimate work keeps running.

**Example:** Procurement agent reads a poisoned PDF, then reaches for HR salaries. Warden blocks the HR read, explains why, and lets price-checking continue.

### Visual to draw
Left-to-right strip: **[Poisoned PDF] → [Agent] → [Gateway/Warden] → ✅ price check allowed / ❌ HR read blocked / ❌ external send blocked**. Under it, a small risk gauge showing "Risk 82: RESTRICTED".

### Speaker notes
- Open with the badge analogy: door security checks the badge, not what the accountant does afterward.
- Stress the last line of the PS: *restrict without disrupting*. This is why we shrink tokens instead of killing agents.

---

## SLIDE 3 – TECHNICAL APPROACH

### On-slide text (left side of the slide, since the book image sits on the right)

**Pipeline:** Agent → **Policy Gateway** (intercept + provenance tags + token broker) → **Warden Engine** (5 lenses → Drift Classifier → Risk Engine) → **Response Orchestrator** → Dashboard.

**5 lenses:**
- **L1 Role Fit:** action vs contract (hard limits beat mimicry)
- **L2 Baseline & Drift:** Markov sequence surprise, peer comparison, CUSUM vs *frozen anchor*
- **L3 Causal Provenance:** untrusted content → risky action with no owner-originated reason
- **L4 Decoys:** fake HR file / API key / endpoint / canary string
- **L5 Chain & Fingerprint:** delegation ceiling, inherited taint, token-use fingerprint

**Risk = lens fusion × impact** (data sensitivity × egress × irreversibility); decoy hit forces a floor.

**Challenge → mechanism:**

| PS challenge | Our answer |
|---|---|
| Valid credentials | Behavior-vs-role check at gateway |
| Prompt injection | Detect the *effect* (data flow), not the text |
| Legit vs adversarial | Cause-aware classifier + change declarations |
| No history | Role-contract prior + peer pooling → Day-0 detection |
| Agent chains | Authority only shrinks; taint travels |
| Evasion | Frozen anchor, capability budget, decoys, multi-lens fusion |

**Stack:** FastAPI, scikit-learn, networkx, SQLite/Postgres, React dashboard, Docker.

### Visual to draw
The **High-level architecture** diagram from `04_architecture.md` (simplified to ~8 boxes). Put the challenge→mechanism table beneath or beside it at small font.

### Speaker notes
- Walk one action through the pipeline in 20 seconds.
- The table proves you read all six challenges. Point at each row quickly.

---

## SLIDE 4 – FEASIBILITY AND VIABILITY

### On-slide text

**Buildable in 24 h (MVP scope):**
- Gateway as SDK wrapper / HTTP proxy in front of simulated tools
- Rule + statistical detectors (no heavy training; works from step 1)
- Dashboard with live risk, alert explanation, attack replay
- 6 scripted attack scenarios + 1 legit-change scenario for evaluation

**Production path (no agent rewrite needed):**
- MCP gateway plugin, OAuth 2.0 token exchange (RFC 8693), SPIFFE workload IDs
- OpenTelemetry GenAI spans for telemetry
- Aligned to **OWASP Top 10 for Agentic Apps 2026** (ASI01, ASI03) and **NIST NCCoE agent identity work**

**Viability:**
- Low latency: rule path is lightweight; heavy checks only on escalations
- Low cost: no GPU needed; LLM judge optional
- Low friction: owners sign a role contract; templates ship per common role
- Measured, not claimed: time-to-detect, data leaked before containment, false-block rate

**Risks & mitigations:** over-broad contracts → blast-radius report; baseline noise → role priors + step-up instead of hard block; decoy upkeep → auto-generated, rotated.

### Visual to draw
Two-column "Prototype now / Production next" with a thin arrow between. Small tech-logo strip (Python, FastAPI, React, Docker).

### Speaker notes
- Say what is *real* and what is *simulated* in the prototype. Honesty here earns trust.

---

## SLIDE 5 – IMPACTS AND BENEFITS

*(The template has three columns/regions here. Suggested headings: **Security**, **Business**, **Society/Industry**.)*

### On-slide text

**Security impact**
- Catches hijacked, poisoned and stolen-token agents that pass every permission check
- Stops exfiltration *before* data leaves (decoys + taint-to-egress)
- Limits blast radius: compromise becomes survivable

**Business impact**
- Fewer outages: only the risky action is paused, not the whole agent
- Fewer false alarms: sanctioned changes are recognized, not flagged
- Audit-ready alerts: score, reasons, evidence, standards tag

**Industry impact**
- Fills the open gap named by NIST and OWASP: *continuous behavior monitoring for agent identity*
- Safe adoption of autonomous agents in banks, hospitals, government and enterprises
- Reusable role-contract format for the ecosystem

**Target numbers (prototype goals):** 0 sensitive bytes leaked before containment · detection within ≤2 actions · false-block rate under 2% · Day-0 coverage for new agents

### Visual to draw
Three icon columns. Put a mini bar chart "Without Warden vs With Warden" for *data leaked* and *time to containment* if you have simulator numbers; otherwise omit rather than fake.

### Speaker notes
- Business angle: judges often include industry people. Say "least disruption" explicitly.

---

## SLIDE 6 – USP AND FUTURE SCOPE

### On-slide text (left side)

**USP: we ask WHY, not just WHETHER**
1. **Cause-aware drift:** tell owner-approved change from content-triggered hijack
2. **Day-0 detection:** the role contract works before any history exists
3. **D3COY layer:** decoy tripwires that cannot be mimicked
4. **Surgical response:** shrink the token, keep the work alive; rewind to a clean checkpoint
5. **Chain-safe:** authority only shrinks along delegation; taint travels with data
6. **Explainable by design:** score + reasons + evidence + OWASP mapping

**Future scope:**
- OAuth/SPIFFE production integration; MCP gateway plugin
- LLM-as-judge for ambiguous high-impact actions
- Federated role-level baselines across organizations
- Least-privilege recommender (auto-tighten contracts)
- Memory-poisoning guard; compliance exports (NIST 800-53 CA-7, ISO 42001)
- Continuous red-team autopilot

**Closing line:** *"A badge tells you who walked in. Warden tells you whether they're still doing the job."*

### Visual to draw
Left: numbered USP list. Bottom: roadmap arrow (Prototype → Pilot → Platform). Include GitHub/demo link or QR if you build one.

### Speaker notes
- End on the closing line, then stop talking.
- Mention that the hackathon's name inspired the decoy layer.

---

## Design tips for the dark template
- White/off-white body text; red only for key terms; max 2 fonts.
- No paragraph longer than 2 lines. Use icons and arrows.
- Keep diagram text at least 14 pt; if it doesn't fit, simplify the diagram.
- Export to PDF and check every slide on a phone screen.
