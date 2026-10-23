# 11 – Demo & Evaluation Plan

Goal: a 5-minute live demo that tells the story from `06_story_and_pitch_script.md`, plus numbers that prove it.

---

## 1. The 5-minute demo script (on-site or recorded)

| Time | Screen | Say | Action |
|---|---|---|---|
| 0:00 | Overview, 5 agents green | "Five agents, all with valid tokens, all behaving normally." | Point to the live feed |
| 0:30 | Replay → **S1 Injection** | "Mallory emails a supplier quote with a hidden instruction." | Click S1 |
| 0:45 | Feed shows PDF ingested (tagged untrusted) | "Warden labels it untrusted the moment it is read." | Highlight label |
| 1:00 | Agent tries HR read → alert appears | "Token valid. Old IAM says allow. Warden says no." | Open AlertDetail |
| 1:30 | AlertDetail | "Risk 82. Three reasons: out of role, caused by untrusted input, never seen before. Mapped to OWASP ASI01/ASI03." | Show lens bars + evidence |
| 2:00 | AgentDetail | "Token scope shrank. Price-checking still works." | Show purchase request still succeeding |
| 2:20 | Evil server panel: 0 bytes | "Nothing left the building." | Show counter = 0 |
| 2:40 | Replay → **S5 Mimicry / decoy** | "Smarter attacker, normal-looking behavior, pokes around." | Click S5 |
| 3:00 | Decoy alert | "Touched a fake salaries file. No history needed." | Show decoy chip |
| 3:20 | Replay → **S4 Slow drift** | "One tiny change at a time." | Fast-forward; capability chart rises |
| 3:40 | Alert at budget | "A rolling baseline would have adapted. The frozen anchor didn't." | Point at chart |
| 4:00 | Replay → **S8 Legit change** | "Now a real change, declared by the owner." | Click S8 |
| 4:15 | No alert; contract v2 | "No false alarm. We check the cause." | Show version bump |
| 4:30 | ChainGraph (S6) | "Authority only shrinks along the chain; taint travels." | Show red edge |
| 4:45 | Metrics table | "Detection, time-to-detect, leaked bytes, false blocks, all simulated." | Show table |
| 5:00 | Closing line | "A badge tells you who walked in. Warden tells you whether they're still doing the job." | Stop |

**Backup plan:** pre-record the screen capture; keep a seeded database so the demo is repeatable; run S1 first (most important), skip others if time is short.

---

## 2. Metrics (what to compute, how)

| Metric | Definition | Target |
|---|---|---|
| Detection rate | alerts at or above ELEVATED on attack runs / attack runs | ≥ 95% on S1-S7 |
| Time-to-detect (TTD) | actions between first malicious action and first ELEVATED+ alert | ≤ 2 |
| Data exposure | sensitive records/bytes reaching evil server | 0 |
| False-block rate | legit actions blocked or delayed / all legit actions | < 2% |
| Disruption score | % legit actions in the same session affected after restriction | < 10% |
| Cold-start detection | S1, S2, S5 with n = 0, 10, 100 prior actions | same detection at n=0 for S1/S5 |
| Latency | gateway overhead p50 / p95 | report real values |
| Ablation | detection per scenario with each lens off | shows every lens matters |

**Report table template (fill from `eval/results/`):**

| Scenario | Detected | TTD (actions) | Leaked | Legit blocked |
|---|---|---|---|---|
| S1 injection | | | | |
| S2 stolen token | | | | |
| S3 poisoned tool | | | | |
| S4 slow drift | | | | |
| S5 mimicry | | | | |
| S6 chain | | | | |
| S7 memory | | | | |
| S8 legit change | n/a (no alert expected) | n/a | n/a | |

**Ablation table template:**

| Lens disabled | Scenarios that now fail |
|---|---|
| L1 Role fit | |
| L2 Baseline/drift | |
| L3 Provenance | |
| L4 Decoys | |
| L5 Chain/fingerprint | |

> Numbers must come from your own runs. Label them "simulated, N seeds". Never present target numbers as results.

---

## 3. Pre-demo checklist
- [ ] `make demo` works from a clean clone
- [ ] Seeded RNG; same result every run
- [ ] Dashboard readable at projector resolution, dark theme with high contrast
- [ ] Backup recording and screenshots in the slide deck
- [ ] README has run steps, architecture picture, and the metrics table
- [ ] Everyone can explain: role contract, provenance, decoys, frozen anchor, cause-aware classifier

---

## 4. What to show Round 0 judges before the on-site event
- 1 architecture diagram, 1 story diagram, 1 results table (even if from an early simulator), and a link to the repo or demo clip on slide 6.
- Even a Phase 0-3 prototype (hero attack detected) is a major differentiator for screening.
