# 07 – Q&A Prep (35 questions judges may ask)

Rule: answer in 2-4 sentences, then stop. If you don't know, say what you'd test.

---

## A. Problem and concept

**1. How is this different from normal anomaly detection / UEBA?**
UEBA learns what's unusual for a user. We compare behavior to a *declared role* (contract), add *causal provenance* (what triggered the action), plant decoys, and respond by shrinking tokens. Anomaly alone can't tell sanctioned change from hijack; our cause check can.

**2. Why not just give agents least-privilege permissions?**
We should, and our blast-radius report recommends it. But agents need *some* sensitive access to do their job, and permissions can't express "this read is fine in this context but not after reading an untrusted PDF." Least privilege reduces the damage; behavior monitoring catches what remains.

**3. Why not use a prompt-injection classifier on documents?**
Classifiers read text, and attackers can reword, encode or hide it. We watch the *effect*: untrusted content in context followed by a privileged action the task doesn't explain. That signal doesn't depend on how the injection is phrased.

**4. Why not use CaMeL / FIDES?**
They're strong, design-time defenses but require building the agent around them, and they don't monitor drift, roles or identity over time. Warden works with existing agents at the gateway, and it complements hardening: Warden detects and contains when hardening is missing or fails.

**5. What exactly is "identity drift"?**
The agent's identity (token, permissions) stays valid while its behavior moves away from the role it was created for. We measure that gap.

**6. What do you mean by "role contract" and who writes it?**
A machine-readable job description: allowed tools, data classes, destinations, typical sequences, budgets. Templates ship per common role; the owner reviews and signs; an LLM can draft one from a text role description.

---

## B. Detection mechanics

**7. How do you detect a hijack on step 1 of a brand-new agent?**
Role contract (hard limits) and decoys need no history. The baseline starts as the role prior plus peer-group stats and shifts to the agent's own history as it accumulates (weight n/(n+k)).

**8. What features do you use?**
Tool, resource class, sensitivity, destination, bytes, rate, hour, tool-transition, provenance labels in context, delegation depth, fingerprint (workload ID, timing, network origin).

**9. How does the taint/provenance tracking work?**
The gateway labels each context chunk with its source (owner instruction, trusted system, untrusted document/web/agent message). When a tool call is made, we look at labels in context in the recent window and classify the sink. Untrusted + sensitive read/write/egress + no owner-originated justification = high provenance score.

**10. Doesn't taint tracking fail because the LLM mixes everything in its context?**
Yes: we're conservative and can't prove which token caused what. That's why provenance is one lens, fused with role fit and baseline, and we only escalate hard for sensitive sinks. It's a signal, not a proof. We also reset taint on a clean checkpoint.

**11. What if the attacker copies normal behavior perfectly?**
Then the attacker is limited to *normal* behavior, which the contract bounds. Anything outside the contract is blocked regardless of how it looks statistically, and decoys catch exploration. Harm is bounded to what the role is allowed to do.

**12. What about slow drift (boiling frog)?**
Rolling baselines would adapt to the attacker, so we compare to a **frozen anchor** for each role version and track a **capability-surface budget** (cumulative count of new resource classes/destinations). CUSUM on that budget trips even when each step is tiny.

**13. How do you tell legitimate drift from adversarial drift?**
By cause and corroboration: matching change declaration (ticket/contract v2), owner-originated vs content-originated trigger, peer adoption, speed, and sensitivity. Sanctioned drift updates the baseline; content-triggered drift into sensitive territory is flagged.

**14. What if an owner approves something malicious?**
Change declarations are logged, signed and rate-limited; high-sensitivity expansions require a second approver. Insider abuse is outside this scope but our audit trail makes it traceable.

**15. How do decoys work in practice, and can an attacker detect them?**
We plant believable fake resources in each role's neighborhood (a salaries file, an admin key, an endpoint, a canary string in documents). Real tasks never use them. Attackers can't tell which are fake, and legit agents won't touch them, so false positives are near zero. Decoys are auto-generated and rotated.

**16. What stops decoys from triggering by accident, e.g. a legit file-listing?**
Decoys are placed so listing operations return them only in scopes the role doesn't need; a *list* gets low weight, a *read/use* gets high weight. Role scoping keeps legitimate agents away from them.

**17. How do you detect a stolen token?**
Fingerprint lens: the token's use differs from the agent's workload identity, network origin, timing rhythm, and tool habits. The attacker holds a valid token but not the agent's "hand." Combined with role fit, an attacker using the token for out-of-role actions is caught too.

**18. What about poisoned tools (tool poisoning/rug-pull)?**
We hash tool manifests (name, description, schema) and flag changes; tool outputs are labeled untrusted; and a tool suddenly requesting out-of-contract actions raises L1/L3.

**19. What about memory poisoning?**
Memory entries get provenance labels at write time. Entries from untrusted sources keep their taint when recalled. (Full memory guard is on the roadmap; prototype labels only.)

**20. What about multi-agent chains?**
Each delegation carries an envelope: origin, taint labels, authority ceiling. Effective permission is the intersection of the role contract, the parent's ceiling and the current scope. A worker can never exceed the manager. Child risk contributes to the parent's and downstream agents are notified.

---

## C. Risk score, explanation, response

**21. How do you compute the risk score?**
Lens scores (0-1) are fused with a noisy-OR, multiplied by an impact factor (sensitivity × egress × irreversibility), with floors for decoy hits and tainted-sensitive-egress. Details in `09_risk_scoring_spec.md`.

**22. How do you avoid alert fatigue?**
Dedupe retries, aggregate per-session, alert only on score thresholds with sensitive sinks, use graduated responses (step-up rather than block), and show a ranked list with reasons.

**23. What does "restrict without disrupting" mean concretely?**
The gateway issues a new short-lived token with fewer scopes: e.g. no sensitive reads, no external sends. The agent keeps doing price checks and purchase requests. For isolation, we checkpoint and allow resumption from the last clean state minus the tainted input.

**24. What if the agent is mid-transaction when you restrict it?**
Writes are wrapped in checkpoints; restriction takes effect at the next tool call. Irreversible actions (sends, deletes, payments) are the ones that get step-up checks first.

**25. How can a human verify an alert quickly?**
The alert shows score, three plain-English reasons, the evidence timeline with the taint chain, and a counterfactual ("would not have alerted if the owner had declared X"). Buttons: Approve once / Approve & declare change / Keep restricted / Isolate.

**26. Could Warden itself be attacked?**
Yes: via telemetry flooding, decoy discovery, or gateway bypass. Mitigations: tamper-evident logs, rate limits, jittered thresholds, no direct network path from agents to tools except through the gateway, and fail-closed for sensitive tools.

**27. What is the latency overhead?**
Rule-based path (contract, taint, decoys, budgets) is lightweight; statistical scoring is incremental. Heavy checks (embeddings, LLM judge) run only on escalations. We'll report measured p95 latency from the prototype rather than guess.

---

## D. Feasibility, scale, practicalities

**28. Is this realistic to build in 24 hours?**
Yes, with a scoped MVP: gateway wrapper, role contracts (YAML), five lens modules (simple and explainable), risk engine, orchestrator, React dashboard, and a simulator with 6 attacks + 1 legit change. Anything not built is labeled as future.

**29. Does it need to retrain models for each customer?**
No. Role priors + rules work Day-0; the baseline adapts online with lightweight statistics (no GPU, no heavy training).

**30. How does it plug into real systems?**
As an MCP gateway/HTTP proxy in front of tools; OAuth 2.0 token exchange for scoped short-lived tokens; SPIFFE for workload identity; OpenTelemetry GenAI spans for telemetry.

**31. How would it scale to thousands of agents?**
Events are stateless-per-agent plus small per-agent state; shard by agent_id, stream through a queue, store aggregates (transition counts, feature stats) rather than raw history for baselines.

**32. What about privacy of the logged data?**
We log metadata (tool, resource class, sizes, destinations, labels), not payload contents by default; payload capture is opt-in and redacted.

**33. What's the business model / who buys it?**
Enterprises deploying agents in regulated domains (banking, healthcare, government). Sold as a security layer/gateway; compliance reporting aligned to NIST/OWASP is a selling point.

---

## E. "Gotcha" questions

**34. What's the weakest part of your design?**
The quality of the role contract. A too-broad contract weakens L1. That's why we ship templates, show a blast-radius report and recommend tightening based on observed usage.

**35. What would you do with another month?**
Real MCP/OAuth integration, a benchmark against public agent-injection suites, LLM-judge for ambiguous high-impact actions, memory guard, and a pilot with a real agent framework.

---

## Answering style cheat-sheet
- **Start with the answer, then the reason.**
- Use the story: "Procu's token was valid, and that's exactly why…"
- Never claim 100%. Say "in our simulator" and give the number.
- If challenged: "Good point. Here's the limit, and here's how we mitigate it."
