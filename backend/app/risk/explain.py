"""Alert explanations: every alert says what happened, why, how sure we are, and what would change it.

An explanation contains
  headline          one sentence a human can read in two seconds
  top_reasons       up to 3, plain English, strongest first; each shows its
                    MEASURED effect: the score if that evidence were removed
  leave_one_out     the full table behind that: score with each lens removed
  evidence_timeline the agent's last actions, with the untrusted sources
                    that were in context when the alert fired (the causal chain)
  owasp             OWASP Agentic Top 10 (2026) categories, each with a "because"
  what_would_change_the_verdict
                    template-based, honest about being a hint, not a proof
  impact, session, floors, recommended_action

"Leave one out" is the rigorous part: we re-run the fusion without a lens
and report the difference, so a reason's weight is a measurement.
"""
from __future__ import annotations

from typing import Optional

from ..models.events import Event, LensResult
from .engine import Fusion, fuse
from .owasp_map import owasp_tags


def leave_one_out(lens: dict, impact: float, base_risk: float) -> dict:
    """{lens: {'risk_without': r, 'delta': base - r}} for every lens that contributed."""
    out = {}
    for name, result in lens.items():
        if result.score <= 0 or name not in ("role", "provenance", "decoy", "baseline", "drift"):
            continue
        rest = {k: v for k, v in lens.items() if k != name}
        r = fuse(rest, impact).risk
        out[name] = {"risk_without": r, "delta": round(base_risk - r, 1)}
    return out


def _counterfactuals(event: Event, lens: dict) -> list:
    hints = []
    role, prov, decoy = lens.get("role"), lens.get("provenance"), lens.get("decoy")
    drift, base = lens.get("drift"), lens.get("baseline")
    if decoy is not None and decoy.score > 0:
        hints.append("No legitimate change explains touching a decoy or leaking a watermark, "
                     "so there is no counterfactual for that evidence.")
    if role is not None and role.score > 0:
        if any("denied" in e for e in role.evidence):
            hints.append(f"Role-fit would drop to 0 only if the owner deliberately changed the contract "
                         f"to permit '{event.resource_class}' for role '{event.role}'.")
        else:
            hints.append(f"Role-fit would drop to 0 if '{event.tool}' were added to the contract for "
                         f"'{event.role}' (a new contract version).")
        if event.destination_class in ("external", "unknown"):
            hints.append(f"The destination check clears if '{event.destination}' is on the egress allowlist.")
    if prov is not None and prov.score > 0:
        src = prov.details.get("source")
        hints.append(f"Provenance would be near 0 if the action were inside the role contract; the contract, "
                     f"not what the agent read, is what authorises actions"
                     + (f" (untrusted source was '{src}')." if src else "."))
    if drift is not None and drift.score > 0:
        hints.append("The drift evidence stops accumulating if an owner sanctions the new capability "
                     "(approve & declare, which re-freezes the baseline).")
    if base is not None and base.score >= 0.5:
        hints.append("The habit score falls as this behaviour becomes part of the agent's trusted routine "
                     "(it only learns from actions judged safe).")
    return hints


def build(event: Event, lens: dict, fusion: Fusion, impact: float, sess: dict, band: str,
          action: str, recent_events: list, mode: str, threshold_offset: float = 0.0,
          enforcement: Optional[dict] = None) -> dict:
    # --- top reasons, strongest first; floors (conclusive) lead -------------------
    loo = leave_one_out(lens, impact, fusion.risk)
    reasons, seen = [], set()
    for name, minimum, text in fusion.floors:
        if text not in seen:
            seen.add(text)
            reasons.append({"lens": name, "kind": "conclusive", "text": text, "minimum_risk": minimum})
    for name, weighted in fusion.contributions:
        res: LensResult = lens[name]
        if res.score > 0 and res.reason not in seen:
            seen.add(res.reason)
            entry = {"lens": name, "kind": "signal", "text": res.reason, "score": res.score,
                     "weighted": weighted}
            if name in loo:
                entry.update(risk_without=loo[name]["risk_without"], delta=loo[name]["delta"])
            reasons.append(entry)
    target = f" on {event.resource}" if event.resource else (f" to {event.destination}" if event.destination else "")
    headline = (f"{event.agent_id} ({event.role}) used {event.tool}{target}: "
                f"{band} risk {sess['effective_risk']:.0f}, recommended action {action}")

    # --- timeline: the agent's recent actions as a CAUSAL CHAIN ----------------------
    # Only the influence that matters is annotated: which action ingested the untrusted
    # source the provenance lens blamed, and which action it triggered. Listing every
    # ordinary lookup as "untrusted" on every row would bury the cause.
    prov = lens.get("provenance")
    culprit = prov.details.get("source") if prov is not None and prov.score > 0 else None
    timeline = []
    for e in reversed(recent_events):               # list_events is newest-first
        key = f"{e['tool']}:{e.get('resource') or ''}"
        role_in_chain = None
        if e["id"] == event.id:
            role_in_chain = "action that triggered this alert"
        elif culprit and key == culprit:
            role_in_chain = "ingested the untrusted source blamed for this alert"
        timeline.append({"event_id": e["id"], "tool": e["tool"], "resource": e.get("resource"),
                         "risk": e["risk"], "band": e["band"], "role_in_chain": role_in_chain,
                         "is_trigger": e["id"] == event.id})
    return {
        "headline": headline,
        "risk": sess["effective_risk"], "event_risk": sess["event_risk"],
        "band": band, "recommended_action": action, "mode": mode,
        "top_reasons": reasons[:3],
        "more_reasons": len(reasons) - 3 if len(reasons) > 3 else 0,
        "leave_one_out": loo,
        "lens_scores": {k: v.score for k, v in lens.items()},
        "impact": {"value": round(impact, 3), "sensitivity": event.sensitivity,
                   "destination_class": event.destination_class, "irreversible": event.is_irreversible},
        "session": sess,
        "floors": [{"name": n, "minimum_risk": m} for n, m, _ in fusion.floors],
        "owasp": owasp_tags(lens, event),
        "evidence_timeline": timeline,
        "what_would_change_the_verdict": _counterfactuals(event, lens),
        "threshold_offset": threshold_offset,
        "action_taken": enforcement or {"mode": mode, "decision": "ALLOW"},
    }


def describe_action(a: Optional[dict]) -> str:
    if not a or a.get("mode") == "shadow":
        return "none (shadow mode: observed only, nothing was blocked)"
    d, post = a.get("decision"), a.get("posture_after")
    if d == "PENDING_APPROVAL":
        return f"action PAUSED for human approval ({a.get('approval_id')}); the agent itself keeps working"
    if d == "BLOCK":
        extra = {"restricted": "; agent RESTRICTED (token shrunk to its routine, no egress)",
                 "isolated": "; agent ISOLATED (tokens revoked)"}.get(post, "")
        return f"action BLOCKED ({a.get('block_reason')}){extra}"
    return "allowed"


def render_text(x: dict) -> str:
    """A readable report for terminals, tickets and slides."""
    L = [x["headline"], ""]
    L.append("Why (strongest first):")
    for i, r in enumerate(x["top_reasons"], 1):
        tail = ""
        if r["kind"] == "conclusive":
            tail = f"   [conclusive: risk is at least {r['minimum_risk']:.0f}]"
        elif "delta" in r:
            tail = f"   [without this: {r['risk_without']:.0f}, so it adds {r['delta']:.0f}]"
        L.append(f"  {i}. {r['text']}{tail}")
    if x["more_reasons"]:
        L.append(f"  (+{x['more_reasons']} more)")
    if x["session"]["raised_by_session"]:
        L.append(f"  * raised from {x['event_risk']:.0f} by session risk "
                 f"(repeated suspicious actions, session level {x['session']['session']:.0f})")
    L += ["", "Action taken: " + describe_action(x.get("action_taken")), "", "Evidence timeline:"]
    for t in x["evidence_timeline"]:
        mark = ">>" if t["is_trigger"] else "  "
        note = f"   <- {t['role_in_chain']}" if t["role_in_chain"] else ""
        L.append(f"  {mark} {t['event_id']} {t['band']:<8}{t['risk']:>5.0f}  {t['tool']} {t['resource'] or ''}{note}")
    L += ["", "OWASP Agentic Top 10 (2026):"]
    L += [f"  {o['id']} {o['name']}: {o['because']}" for o in x["owasp"]]
    L += ["", "What would change the verdict:"]
    L += [f"  - {h}" for h in x["what_would_change_the_verdict"]]
    return "\n".join(L)
