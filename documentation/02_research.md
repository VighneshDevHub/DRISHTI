# 02 – Research Notes

> Research compiled in Oct 2026 from public sources. Paraphrased, not copied. Verify any number before putting it on a slide, and cite the source name on the slide.

---

## 1. Standards and frameworks (shows we are current)

### 1.1 OWASP Top 10 for Agentic Applications 2026 (published 9 Dec 2025)
- Peer-reviewed taxonomy of ten risks specific to agents that plan, use tools, keep memory and act with delegated authority (100+ contributors).
- Most relevant to this PS:
  - **ASI01 – Agent Goal Hijack:** attacker redirects the agent's objective through content it reads (indirect prompt injection). The agent *believes* it is still doing the user's task.
  - **ASI03 – Identity & Privilege Abuse:** agent identity/permissions misused or escalated; weak identity boundaries and unscoped delegation/inherited credentials.
  - Also relevant: tool misuse, supply chain (poisoned tools), memory poisoning, inter-agent communication, cascading failures, rogue agents.
- Mitigation themes in OWASP-based guidance: per-agent identity, short-lived scoped credentials, treat retrieved content as untrusted, constrain objectives, continuous validation of actions.
- Source: OWASP GenAI Security Project; summaries by Cycode, Teleport, Astrix, Modulos.

**How we use it:** every alert is tagged with the ASI category it matches (ASI01, ASI03, ASI04, ASI06, ASI07, ASI08, ASI10). Judges see standards alignment immediately.

### 1.2 NIST NCCoE concept paper on AI agent identity & authorization (5 Feb 2026)
- "Accelerating the Adoption of Software and AI Agent Identity and Authorization": asks how existing IAM standards apply to agents.
- Open questions it raises: how to issue/update/revoke agent credentials; whether authorization should **adapt in real time as context changes**; how to enforce least privilege when behavior is unpredictable; logging/auditing/non-repudiation; controls against prompt injection.
- Comments closed 2 Apr 2026. NIST CAISI also launched an AI Agent Standards Initiative (17 Feb 2026).
- Community responses (e.g. SpruceID) call for persistent agent identity, capability-based authorization, and **continuous monitoring like intrusion detection, tailored to agent behavior**.

**How we use it:** our design *is* the "continuous monitoring + dynamic authorization" piece that NIST says is an open question. Say this on slide 6.

### 1.3 Others to mention briefly
- **OWASP Non-Human Identity Top 10** – same problems as service accounts, but agents decide at runtime.
- **NIST SP 800-53 CA-7 (continuous monitoring)** – guidance now says it should include agent-behavior drift, not just infrastructure.
- **OAuth 2.0 Token Exchange (RFC 8693)** and **SPIFFE/SPIRE workload identity** – the standard building blocks we plug into for scoped, short-lived tokens.
- **MCP (Model Context Protocol)** – the common tool-calling layer; a gateway at this layer is a natural interception point.

---

## 2. Academic / industry defenses already known

| Approach | Idea | Strength | Gap for our PS |
|---|---|---|---|
| **CaMeL (Google DeepMind)** | Split planner LLM (sees user query, no untrusted data) from quarantined LLM; custom interpreter tracks provenance + capabilities, checks policy before tool calls | Strong, by-design guarantee against many injections | Needs agent rebuilt around it; doesn't monitor *drift over time*, no role baseline, 2–3× token cost reported |
| **FIDES (Microsoft, information-flow control)** | Labels data with integrity/confidentiality; planner enforces policy on tool calls | Formal guarantees | Same: design-time integration; not behavioral drift |
| **Taint tracking at runtime** (e.g., proposals for `TaintedString`, MCP injection-guard prototypes) | Track where data came from; block when untrusted-origin data reaches a privileged sink | Style-independent (doesn't care how the injection is worded); low false positives | Session-global, literal matching; no baseline, no role, no chain |
| **Causal attribution guardrails (ICML 2026 slides)** | Check whether a *privileged tool call* is causally driven by earlier tool results; only score when tool is irreversible | Reduces "over-defense" (blocking everything) | Detection only; no identity/role layer |
| **TraceAegis (arXiv 2510.11203)** | Provenance + hierarchical execution-trace anomaly detection; benchmark on healthcare & procurement | Closest to us; procurement scenario | Learns from traces only; no declared-role contract, no decoys, no response layer |
| **SentinelAgent / graph-based multi-agent anomaly** | Graph anomaly detection for agent-to-agent interactions | Chains | Not tied to identity/role |
| **IPIGuard (tool dependency graph)** | Constrain tool-call order to a planned dependency graph | Prevents off-plan calls | Static plan; not learned/role-based |
| **Content classifiers (PIGuard, etc.)** | Detect injection text | Easy to deploy | Bypassable by rewording; over-defense |

### Key lessons from the literature (we design around these)
1. **Content filtering is not enough** – attackers re-phrase. Detect the *behavioral shape*: untrusted content read → privileged/outbound action not explained by the task.
2. **Over-defense is a real problem** – strict systems break legitimate work. Therefore: score only when a *sensitive sink* is involved, and respond *gradually*.
3. **Multi-agent provenance is unsolved** – labels must travel across agent boundaries; almost no framework does it.
4. **Memory stores persist injections across sessions** – need re-validation of memory.
5. **Plan for residual compromise** – design controls so that a successful injection is *survivable* (small blast radius).
6. **Alert double-counting on retries** – dedupe events (practical detail that shows maturity).
7. **Pure-read agent = confidentiality risk; agent with one outbound tool = exfiltration risk** – score by capability combination ("lethal trifecta": private data + untrusted content + external communication).

---

## 3. The gap we target (our "why us")

| Existing | Missing |
|---|---|
| IAM: "is this allowed?" | "is this still the job?" |
| Prompt-injection guards: "is the *text* evil?" | "did the *behavior* change, and *what caused it*?" |
| Anomaly detection: "is this unusual?" | "is this unusual **relative to the declared role**, and is it **sanctioned**?" |
| Kill switch: "stop the agent" | "shrink the agent's authority surgically so legit work continues" |

**Position:** Agent Warden is a *behavioral identity layer* that sits on top of IAM. It does not replace CaMeL/FIDES-style hardening; it **detects and contains** when hardening fails or when the agent was never hardened.

---

## 4. Insight that drives the design: *cause* separates good drift from bad drift

- **Sanctioned change** has a *human/owner-originated cause* (new ticket, new tool approved, role contract updated).
- **Adversarial change** has an *untrusted-content cause* (it started right after reading an external document/web page/agent message) or *no cause* (stolen token with different fingerprint).
- So we don't only measure "how far did behavior move" but "**what triggered the move**". This is how we reduce false alarms without lowering sensitivity. *(This is our central original claim; phrase it carefully as a design hypothesis, validated in our simulator.)*

---

## 5. Evasion research notes
- **Mimicry:** attacker copies normal traffic. Defense: role contract hard limits (can't do outside-role actions even if statistically "normal-looking"), decoys, data-class egress rules; harm is bounded to what the role is allowed.
- **Boiling frog (slow drift):** rolling baselines adapt to the attacker. Defense: **frozen anchor baseline** per role version + **cumulative capability-surface budget** (CUSUM) – count of new resource classes touched since anchor.
- **Threshold probing:** attacker learns the threshold. Defense: jittered thresholds, multi-lens fusion (attacker must evade all lenses), decoys that cannot be known.
- **Using other agents as proxy (confused deputy):** authority ceiling travels in delegation envelope; effective permission = intersection.

---

## 6. Source list (for slide footnotes)
- OWASP GenAI Security Project – Top 10 for Agentic Applications 2026 (genai.owasp.org)
- NIST NCCoE – Software and AI Agent Identity and Authorization concept paper (nccoe.nist.gov; nist.gov news, Feb 2026)
- Debenedetti et al. – "Defeating Prompt Injections by Design" (CaMeL), Google DeepMind
- Costa et al. – FIDES, information-flow control for AI agents (arXiv 2505.23643)
- TraceAegis – provenance-based anomaly detection for LLM agents (arXiv 2510.11203)
- IPIGuard (arXiv 2508.15310)
- ICML 2026 – Efficient Indirect Prompt Injection Guardrails via Causal Attribution
- Cloud Security Alliance research note on NIST AI agent standards
- SpruceID comments to NIST NCCoE
