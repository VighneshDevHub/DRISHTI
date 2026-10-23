# D3COY 1.0 – Round 0 Master Pack
**Solution name (working): AGENT WARDEN – "Valid credentials. Invalid behavior."**
*(Rename freely. Keep the idea.)*

---

## 1. What is in this pack

| File | Use it for |
|---|---|
| `00_README_and_selection_strategy.md` | This file. How to win Round 0. |
| `01_problem_understanding.md` | PS in plain words, hidden requirements, what judges want |
| `02_research.md` | Standards, papers, gaps, what exists, what we do differently |
| `03_solution_design.md` | The full solution: concept, 6 innovations, risk logic, response |
| `04_architecture.md` | Diagrams (Mermaid), data flow, components |
| `05_ppt_content_slidewise.md` | **Exact text for your 6-slide template**, slide by slide |
| `06_story_and_pitch_script.md` | The story ("The Intern with a Valid Badge") + speaking script |
| `07_qa_prep.md` | 35 tough questions judges can ask, with answers |
| `08_threat_scenarios_and_evasion.md` | 8 attack scenarios + evasion handling + test plan |
| `09_risk_scoring_spec.md` | Exact scoring math, thresholds, explanation format |
| `10_build_plan_phases.md` | Phase-by-phase build plan, directory structure, feature specs |
| `11_demo_and_evaluation_plan.md` | Demo script, metrics, what to show on-site |

---

## 2. How Round 0 is judged (from the brief) and how this pack answers it

| Criterion | What we do |
|---|---|
| Quality & originality | Not "an anomaly detector". We combine **role contract + causal provenance + decoys + frozen-anchor drift + chain authority** |
| Technical understanding | Show we understand *why* credentials hide the attack, and map each of the 6 core challenges to a specific mechanism (table on slide 3) |
| Feasibility & impact | Gateway-based design, runs in 24 h, works with existing OAuth/MCP stack. Measurable metrics (detection time, data leaked before containment, false-block rate) |
| USP & future scope | USP = *"We ask WHY the behavior changed, not only WHETHER it changed."* Future: SPIFFE/OAuth integration, federated baselines, compliance mapping |

---

## 3. What YOU must do (checklist, in order)

### A. Before writing anything (1–2 hours)
- [ ] Read `01` and `03` fully. Everyone on the team must be able to explain the solution in 60 seconds without slides.
- [ ] Agree on the name, one-line pitch and the story.
- [ ] Decide who presents (best storyteller) and who answers technical Q&A.

### B. Build the PPT (3–4 hours)
- [ ] Use the official template (6 slides). **Do not change slide order or titles.**
- [ ] Copy text from `05`. Cut it down: max ~6 lines of text per box. Judges skim.
- [ ] Make **one strong visual** on slide 3 (architecture) and **one** on slide 2 (before/after story). Diagrams win over paragraphs.
- [ ] Put the 6-challenge → 6-mechanism table on slide 3 (this proves technical understanding).
- [ ] Fill slide 1 properly: team name, college, PS (one line), 4 members with contact.

### C. Submission package
- [ ] PPT (PDF + PPTX if allowed)
- [ ] Resumes of **all** members (the brief says this is mandatory – missing = risk of rejection)
- [ ] Join the WhatsApp group from the brief and watch for deadline/format updates
- [ ] Optional but powerful: a **public GitHub repo with README + architecture diagram** and a **60–90 s demo video/GIF** (even of a mock dashboard). Link it on slide 6. Most teams will not do this.

### D. Things that make teams get rejected (avoid)
1. Generic "we will use ML to detect anomalies" with no detail on *what features*, *what baseline*, *what response*.
2. Ignoring cold-start (new agents with no history). The PS lists it explicitly.
3. No answer for slow drift / mimicry. The PS lists it explicitly.
4. Block-everything response. The PS says "without disrupting legitimate work".
5. Wall of text slides.
6. Over-claiming ("100% detection"). Judges trust honest limits more.

### E. Standing out (cheap but high impact)
- Use the hackathon's name: **D3COY → decoys/canaries are a core feature.** Say it in the pitch: *"You named the hackathon after our best idea."*
- Quote real standards on slide 4/6: OWASP Top 10 for Agentic Apps 2026 (ASI01 Goal Hijack, ASI03 Identity & Privilege Abuse), NIST NCCoE agent identity concept paper (Feb 2026). Shows you are current.
- Show **numbers** you will measure (even as targets): time-to-detect, data leaked before containment, false-block rate.

---

## 4. 60-second version (memorize)

> "Today's security asks *'is this agent allowed?'* A hijacked agent is still allowed. Agent Warden asks *'is this agent still doing the job it was hired for – and what made it change?'*
> We turn each agent's declared role into a **role contract**, watch every tool call through a gateway, and score it through five lenses: role fit, behavioral baseline, causal provenance – did untrusted content trigger this? – decoy tripwires, and delegation-chain authority.
> Every alert has a 0–100 risk score and a plain-English reason. Response is graduated: we don't kill the agent, we **shrink its token** – block only the dangerous action, keep the rest of the job running."

---

## 5. Suggested timeline until the deadline
(Adjust to the real deadline from the WhatsApp group.)

| When | Task |
|---|---|
| T-5 days | Read pack, finalize idea, assign roles |
| T-4 | Draft slides from `05` |
| T-3 | Make diagrams (architecture + story), get feedback from a senior/friend |
| T-2 | Optional: tiny prototype/mock dashboard + GitHub README |
| T-1 | Proofread, rehearse Q&A from `07`, export PDF |
| T-0 | Submit early (not in the last hour). Confirm resumes are attached |

Teams of 4 – suggested roles: **Presenter/Story**, **Architecture/Detection lead**, **Backend/Gateway**, **Frontend/Demo**.
