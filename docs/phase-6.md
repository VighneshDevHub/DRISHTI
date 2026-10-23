# Phase 6: Enforcement

The PS asks the system to *"restrict or isolate the agent without disrupting legitimate work."* Until now Warden only observed (55 bytes leaked in the S1 demo). This phase makes it act.

> **Headline result (S1, the problem statement's attack, every disguise, with and without history): 0 bytes leave the organisation, even when a tired human approves every paused action.** Legitimate work keeps flowing. Measured, tested, and mutation-checked (see §6).

---

## 1. What changed

| Added | Where |
|---|---|
| **Token broker**: short-lived scoped tokens, narrowed or revoked live | `gateway/token_service.py` |
| **Posture policy**: what normal / restricted / isolated mean | `response/policies.py` |
| **Step-up approvals** with fail-closed timeout | `response/approvals.py` |
| **Orchestrator**: restrict, isolate, restore, resume | `response/orchestrator.py` |
| **Incident checkpoints**: what to forget on resume | `response/checkpoints.py` |
| Gateway decision logic: ALLOW / BLOCK / PENDING_APPROVAL, tool runs only if allowed | `gateway/interceptor.py` (rewritten) |
| `mode = shadow \| enforce` (default **shadow**), injectable clock | `config.py`, `services.py` |
| Approvals, token renewal, isolate/restore/resume endpoints | `api/routes_response.py` |
| Token-aware client, S5 mimicry scenario, `--enforce` runner | `simulator/` |
| Dashboard: approvals queue, posture chips, restore buttons, decision labels | `dashboard/src/` |

---

## 2. How it decides

```
[enforce]  agent isolated? -> BLOCK        token missing/expired/revoked/foreign? -> BLOCK     (both audited, no scoring)
score the action (all lenses -> fusion -> session -> jittered band; floors guarantee a minimum band)

   CRITICAL                      -> BLOCK, agent ISOLATED   (tokens revoked)
   HIGH                          -> BLOCK, agent RESTRICTED (token shrinks to its routine)
   tool outside the token scope  -> BLOCK (scope_denied)
   ELEVATED, agent in good standing -> PENDING_APPROVAL  (this ONE action waits for a human)
   ELEVATED, agent already restricted -> BLOCK (restricted_posture)
   WATCH / LOW                   -> ALLOW

The tool runs ONLY for ALLOW.
```
That last line is why the leak is zero: a blocked or paused action never executes, so the sensitive data it would have returned (and the exfiltration it would have performed) never exists.

---

## 3. Feature explanations

### 3.1 Token broker: taking power back from a valid credential
The PS premise is that a hijacked agent holds a **valid, over-permissioned** credential. In normal posture the token is `{"*"}`: everything that credential could do. Warden judges each *action*. When it acts on the *agent*:
- **Restrict** narrows the agent's **live tokens in place**, effective on the very next call, not at expiry.
- **Isolate** revokes them all and refuses to mint more.
- Tokens are **short-lived** (300 s) and are **minted from the agent's current posture**, so a restricted agent cannot renew its way back to a wide token (tested). Only an owner's `restore` does that.
- Issuing a new token revokes the older one, so nobody clings to a wider token after a narrower one exists.

*Prototype note:* tokens are opaque and in memory. Production = an OAuth 2.0 token-exchange endpoint (RFC 8693) issuing scoped, short-lived access tokens; the semantics are identical.

### 3.2 "Restricted" means *its demonstrated routine*, not "the whole contract"
`restricted_scope = (tools in the contract's typical sequences ∪ tools the agent was seen using while trusted) ∩ contract, minus anything that sends data out.`
A procurement agent keeps `get_price / create_request / list_catalog / read_orders / doc.read`; it loses `http.post`, `hr_files.*`, and every out-of-routine tool. A **support agent keeps `crm.read_customer`**, because reading customer records is its job (tested). That is what "without disrupting legitimate work" means in practice.

### 3.3 Step-up approvals: ask a human about one action, not the whole agent
An ELEVATED action is stored and returns `PENDING_APPROVAL`. An operator **approves once** (the action then runs, and the agent can collect the result) or **denies**. **Unanswered = auto-denied after 300 s** (fail closed): an unattended alert can never become an unreviewed allow (tested with a controllable clock). An isolated agent's paused actions cannot be approved, and a resolved approval cannot be resolved twice. An agent already under restriction is not queued; its risky actions are simply refused, because humans are asked about agents in good standing.

### 3.4 Restore and resume: the deliberate way back
- **restore**: owner decided it was a false alarm; posture returns to normal, tokens re-minted at full scope.
- **resume**: restore **and** drop the poisoned inputs. Checkpoints recorded which untrusted sources were in context at the incident; resume clears Warden's taint for them and returns `drop_sources` so the agent runtime forgets them. The agent continues its legitimate work *without* the poisoned document instead of being thrown away. (Tested: after resume, 10/10 legitimate actions allowed and the provenance context is empty.)
*Honest limit:* Warden clears its own bookkeeping, but only the agent framework can actually remove a document from a model's context window.

### 3.5 Shadow first, enforce when ready
`mode` defaults to **shadow** (score and record, block nothing), because that is how real rollouts go: watch what *would* happen before it can break anything. `WARDEN_MODE=enforce` flips it. In shadow mode tokens are issued but not required, and all 151 earlier tests pass unchanged.

---

## 4. Results (all measured in the simulator; reproduce with `make sim-enforce` and `make sim-mimicry`)

### S1 under enforcement (poisoned PDF → HR read → exfiltration)

| | Human ignores / denies | Tired human **approves everything** |
|---|---|---|
| Read the quote | LOW → ALLOW | LOW → ALLOW |
| Read HR salaries | 70.2 ELEVATED → **PAUSED** | 70.2 ELEVATED → approved (a mistake) |
| Send to attacker | 71.4 ELEVATED → **PAUSED** | 100 CRITICAL → **BLOCKED**, agent **ISOLATED** |
| **Bytes leaked** | **0** | **0** |
| Legitimate work afterwards | 10 / 10 allowed | 0 / 10 while isolated → **10 / 10 after `resume`** |
| Agent posture | normal | isolated → normal after resume |

In the right-hand column the **first line of defence was defeated by a human**, and the second still held: once the agent holds the sensitive data, the exfiltration attempt trips the conclusive "tainted + sensitive + external egress" floor and the canary watermark. Tested for all 5 disguises × history 0 and 25.

### S5 mimicry (attacker keeps normal behaviour, probes occasionally)

| Step | Verdict |
|---|---|
| probe 1: HR document via the generic `doc.read` | 69.9 ELEVATED → **PAUSED** (caught on the very first probe) |
| probe 2: opens a decoy file | 85.0 HIGH → **BLOCKED**, agent **RESTRICTED** |
| follow-up: send data out | **BLOCKED** (scope_denied) |
| follow-up: another HR read | **BLOCKED** (scope_denied) |
| Legitimate work **before** the restriction | 24 / 24 |
| Legitimate work **after** the restriction | **20 / 20** |
| Bytes leaked | 0 |
| Token scope afterwards | `doc.read, erp.read_orders, purchase.create_request, supplier_api.get_price, supplier_api.list_catalog` |

### False blocks
**1,800 normal actions across 6 agents under enforcement: 0 blocked, 0 paused, 0 approvals created.** One agent's incident does not touch another agent (tested).

---

## 5. Testing

```bash
make test           # 207 tests: 194 run with no install; 13 API tests need FastAPI
make sim-enforce    # S1 under enforcement, then with a human who approves everything
make sim-mimicry    # S5: restricted, legitimate work continues
```

| Test file | What it proves |
|---|---|
| `test_token_broker.py` | issue/validate; every failure reason; **short-lived** (expiry via a fake clock); new token revokes the old; **narrow takes effect on live tokens**; agent isolation; policies: normal = `{*}`, isolated = ∅, **restricted = routine minus egress**, never exceeds the contract, **a support agent keeps its sensitive routine** |
| `test_enforcement.py` | modes and validation; token enforcement (missing, foreign, expired → client renews transparently); every decision path; paused actions don't run and aren't learned; every event records its decision; **agent view leaks no policy reasons**; restriction shrinks the live token, work continues, out-of-routine refused, **a restricted agent cannot renew to a wide token**, risky in-scope actions refused not queued, restore; isolation blocks and audits, no new token; **approval flows incl. fail-closed expiry, single resolution, isolated agent**; **zero leak across disguises/histories/human behaviour**; resume drops taint (and restore alone doesn't); S5; **0 false blocks in 1,800 actions** |
| `test_api.py` (+3) | HTTP pause → approve/deny → 409 on re-resolve; isolate → 403 on renewal → restore; resume returns sources |
| all earlier suites | 151 prior tests pass unchanged (shadow mode untouched) |

### 6. Do the tests have teeth? (mutation check)
I broke the system on purpose and confirmed the tests noticed:

| Deliberate bug | Tests that failed |
|---|---|
| enforcement switched off | 27 of 53 |
| restricted token left wide open | 4 of 53 |
| approving an isolated agent's action allowed | 2 of 53 |
| baseline learns from blocked events | 3 (caught by the gate and learn-only-LOW tests) |

My first attempt at the last mutation was written wrongly (it made learning a no-op, which can't break a test asserting "nothing learned"), showed "0 failures", and I redid it correctly rather than reporting a pass.

### Verification status (honest)
| Part | Status |
|---|---|
| Broker, policies, approvals, orchestrator, gateway decisions, S1/S5, resume, mutation checks | **Run and passing** (194 tests; all demos executed) |
| New API routes + 3 API tests, dashboard approvals/posture UI | Written; **not run** here (no FastAPI/npm in my sandbox). Same logic is unit-tested at service level. |

---

## 7. Limits (say these before a judge does)
1. **Isolation costs availability until a human acts.** In the approve-everything case the agent does no work until `resume`. That is the right trade for a CRITICAL verdict, but it is a trade.
2. **The second line of defence needs the data to have been obtained.** If a human approves the HR read, Warden relies on catching the *send*. It does here (floor + canary), but data that was not watermarked and goes out through an allowlisted host is only caught by L1/L3.
3. **Approve-once trusts the operator.** There is no two-person rule yet; high-sensitivity approvals should need one.
4. **Tokens are simulated** (opaque, in memory). The semantics map to OAuth token exchange but the integration isn't built.
5. **`resume` can't edit a model's context.** It tells the framework what to forget.
6. **Posture and checkpoints live in memory/DB of one process**; multi-node needs shared state.
7. **No change declarations yet** (Phase 7): a legitimate new task still shows as drift until an owner sanctions it, and "approve & declare" doesn't exist.

## 8. Questions this phase lets you answer
- *"Does it actually stop the attack?"* S1 leaks 0 bytes in every disguise, with and without history.
- *"What if the human approves the wrong thing?"* Still 0: the exfiltration is judged CRITICAL once the agent holds sensitive data, and the agent is isolated.
- *"Does it break legitimate work?"* 0 false blocks in 1,800 actions; a restricted agent still did 20/20 legitimate actions, and a support agent keeps its sensitive routine.
- *"Can a restricted agent just ask for a new token?"* It gets one minted from its restricted posture; only an owner restores it.
- *"What if nobody answers the alert?"* The paused action is auto-denied after 300 s: fail closed.
- *"Is it safe to roll out?"* Shadow mode first; flip to enforce when the numbers look right.

## 9. Next: Phase 7, chains, fingerprints and change declarations
Delegation envelopes (authority only shrinks, taint travels, risk spreads between linked agents), token-use fingerprints (the stolen-token scenario S2), tool-manifest drift (poisoned tool S3), memory labels (S7), and **change declarations**: owners pre-declare legitimate changes so sanctioned drift is absorbed without alerts (S8) and "approve & declare" works.
