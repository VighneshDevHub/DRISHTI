# Design decisions

1. **Stdlib core, pydantic only at the HTTP edge.** The engine is plain dataclasses + sqlite3 + PyYAML, so it is trivially testable and has no install risk. FastAPI is a thin wrapper.
2. **Shadow mode first.** Real deployments run detection in monitor-only mode before enforcing. We do the same and report `shadow_action`; Phase 6 flips it to enforcement. It also gives an honest "before" number for the demo.
3. **One tool registry.** Security facts (class, sensitivity, sink type) live in one table, not inside detectors. New tool = one `ToolSpec`.
4. **Path rules in the registry.** Stops "read HR via a generic doc tool" evasion.
5. **Unknown tools are scored, never trusted.** They get `unregistered` class, sensitivity 0.5, and land in L1's unlisted branch.
6. **Contracts are append-only and versioned.** A change is a new version, which later phases use to re-freeze the drift anchor.
7. **Provisional risk caps below CRITICAL on purpose.** One weak signal must not isolate an agent; CRITICAL needs corroboration (Phases 3-5).
8. **All tunables in `config.py`.**
9. **Seeded simulator.** Same seed → identical traffic → repeatable demos and evaluation.
10. **Blocking SQLite calls inside async routes.** Acceptable at prototype scale (sub-millisecond); move to a threadpool/queue/Postgres for production.
11. **Role contract = standing authorisation (Phase 3).** Provenance discounts actions that are inside the contract, because untrusted text cannot widen what the owner authorised. This is what keeps normal work after reading a document at zero risk.
12. **Noisy-OR fusion, not a weighted average.** An average lets many weak "clean" lenses drown one strong signal. Noisy-OR makes any strong lens raise the score, and independent signals compound.
13. **Floors for conclusive evidence.** A decoy touch or a canary leaving the building is proof, not a probability, so it sets a minimum score regardless of other lenses.
14. **Taint is recorded after the call, per agent, by call count.** Simple, deterministic, and testable; time-based expiry would make tests flaky.
15. **Watermark real data (honeytokens).** Canaries inside real HR/customer data prove exfiltration even when the destination is allowlisted or the path was disguised.
16. **Bug found by reading the numbers:** the first S1 run showed 34 leaked bytes and a score of 95, not 100, which revealed the canary lookup used the wrong id case. Lesson recorded: always sanity-check numbers, not just green tests.
17. **The baseline never starts empty.** A new agent is judged by its contract and its peers (`w = 0`); history takes over gradually. Cold start is a design input, not an edge case.
18. **Learn only from LOW events (learn-gate).** Otherwise repeating an attack teaches the model it is normal. Cost: a legitimate, unsanctioned change keeps alerting until an owner declares it (Phase 7 change declarations).
19. **Anchor = what the agent demonstrably did while trusted, not what the contract allows.** An anchor built from the contract makes drift redundant with role-fit and blind to over-broad contracts, the case that matters most.
20. **Drift scores new-capability use, not the agent.** A drifted agent's ordinary work is never penalised. Found by measurement: the first design pushed 59 normal actions into WATCH.
21. **Budget exhaustion is a floor, not a score.** Low-impact actions cannot reach ELEVATED through impact-scaled fusion alone (impact scaling caps them near 60), so a cumulative budget must be able to force a human decision directly.
22. **Parameters chosen by reasoning, then stress-tested.** DRIFT_H=2.5 was fixed before the sensitivity sweep; the sweep is reported in full, including where the system fails (budget too loose).
23. **Ablation switches in `Settings`.** `enable_baseline`, `enable_drift`, `learn_gate` let tests and Phase 9 evaluation prove each component earns its place.
24. **Order-1 transitions, no rate/hour features.** Order-1 was sufficient for every scenario; rate features need a controllable clock, deferred to Phase 9 rather than faked.
25. **Explanations contain measurements, not just prose.** Leave-one-out re-runs the fusion without each lens, so "adds 9" is a computed fact and "removing any one lens still leaves ELEVATED" is a testable claim.
26. **The timeline shows a causal chain, not a log.** Two annotations only (the source and the trigger). Annotating everything buried the cause; found by reading real output.
27. **Floors guarantee a band, not a number.** With threshold jitter a floor of "85" can fall below the shifted HIGH line; guaranteeing the band is the only jitter-proof formulation.
28. **Session risk only raises already-suspicious events.** Same lesson as the drift lens: a property of the agent must never slow its ordinary work. Verified against an identical control agent.
29. **Hide scores from agents.** A compromised agent that sees its score can probe the threshold. Operators and agents get different views of the same decision.
30. **Jitter defaults to off.** Research and evaluation need exact reproducibility; production turns it on. Documented rather than hidden.
31. **OWASP mapping is ours and says why.** Category names were verified against the published list; which of our lenses maps to which category is our judgement, so every tag carries its reason.
32. **Report what a feature did NOT do.** Session risk changed no S4 number (S4 spaces its steps); stating that beats implying it was decisive.
33. **The tool runs only if the action is allowed.** A blocked or paused action never executes, so the data it would have returned and the exfiltration it would have performed never exist. This, not detection speed, is what takes the leak to zero.
34. **Normal-posture tokens are wide on purpose.** The PS premise is a valid, over-permissioned credential, so Warden judges actions rather than pre-denying out-of-contract tools; the token only narrows when Warden acts on the agent. Pre-denying would convert every borderline-but-legitimate action into an outage.
35. **"Restricted" = the agent's demonstrated routine.** Not the whole contract, and not a fixed category list. A support agent keeps customer reads; a procurement agent loses them. It reuses the Phase 4 anchor.
36. **Tokens are minted from posture, and a new token revokes the old.** A restricted agent cannot renew its way out; a narrowed token cannot be shadowed by an older wide one.
37. **Step-up is for agents in good standing.** Asking a human about an agent already under restriction just creates noise; its risky actions are refused.
38. **Unanswered approvals fail closed.** Timeout means deny. An alert nobody reads can never become an unreviewed allow.
39. **Isolation is a trade, stated plainly.** The agent does no work until a human acts; `resume` exists so that the legitimate work is not lost with it.
40. **Shadow is the default; enforce is a switch.** Safe rollout is a feature, and every earlier test keeps its meaning.
41. **Injectable clock.** Token expiry and approval timeout are tested deterministically, not with sleeps.
42. **Mutation-check the safety claims.** The tests for "0 bytes leaked" were verified by breaking the system four ways and confirming they fail. One of my own mutations was wrong and showed a false pass; I redid it.
