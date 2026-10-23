"""L2b - Drift lens: frozen anchor + capability budget + CUSUM.

Question: "Has this agent's CAPABILITY SURFACE grown beyond what it
demonstrably did while we trusted it, even if every single step looked fine?"

Why the baseline alone is not enough
------------------------------------
A rolling baseline adapts to whatever the agent does, so a patient attacker
can walk it somewhere dangerous one small step at a time (the "boiling
frog"). Worse, if the contract is over-broad, each step is *permitted*, so
role-fit sees nothing at all. This lens catches that:

1. FROZEN ANCHOR. A capability is a triple (tool, resource_class,
   destination_class). The anchor is the set of capabilities the agent was
   actually seen using in its first ANCHOR_FREEZE_N trusted events. Until
   the anchor freezes, the contract's own capabilities also count as
   "expected" (cold start: a new agent has no history). After the freeze the
   anchor never moves, except when an owner sanctions the change (refreeze).
2. CAPABILITY BUDGET. Every capability outside the anchor is remembered
   forever with weight (0.5 + sensitivity), x0.75 if the contract permits it.
   No decay, so slow staircases still add up. When the surface exceeds
   DRIFT_H the budget is spent and any further use of a new capability is
   floored at the step-up band: the owner must sanction or refuse.
3. CUSUM BURST DETECTOR. Catches many new things in a short time. It decays,
   which is exactly why it cannot be the only defence against slow drift.

Important: the score applies to events that USE a new capability. The agent's
ordinary in-anchor work is never penalised for the agent having drifted, so
legitimate work continues undisturbed.

Known limitation: the contract's `new_resource_classes_per_week` is a
tolerance here, not a true weekly window (needs a controllable clock; Phase 9).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from ..config import (ANCHOR_FREEZE_N, CUSUM_DELTA, CUSUM_H, DRIFT_H, IN_CONTRACT_NOVELTY,
                      NOVELTY_BASE)
from ..gateway.tool_registry import ToolRegistry
from ..models.contracts import RoleContract
from ..models.events import Event, LensResult


def capability(event: Event) -> tuple:
    return (event.tool, event.resource_class, event.destination_class)


@dataclass
class _AgentDrift:
    contract_key: tuple
    contract_caps: set = field(default_factory=set)
    learned: set = field(default_factory=set)      # capabilities seen while trusted
    n_learned: int = 0
    frozen: bool = False
    novel: dict = field(default_factory=dict)      # capability -> weight, in first-seen order
    cusum: float = 0.0

    def in_anchor(self, cap: tuple) -> bool:
        if cap in self.learned:
            return True
        return (not self.frozen) and cap in self.contract_caps   # contract prior only until freeze


class DriftTracker:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._state: dict = {}
        self._lock = threading.RLock()

    def _contract_capabilities(self, contract: RoleContract) -> set:
        caps = set()
        for spec in self.registry.matching(contract.allowed_tools):
            caps.add((spec.name, spec.resource_class, "internal"))
            if spec.sink_type == "egress":
                caps.add((spec.name, spec.resource_class, "allowlisted"))
        return caps

    def _get(self, agent_id: str, contract: RoleContract) -> _AgentDrift:
        st = self._state.get(agent_id)
        if st is None:
            st = _AgentDrift((contract.role, contract.version),
                             contract_caps=self._contract_capabilities(contract))
            self._state[agent_id] = st
        return st

    # -- scoring (call once per event) ------------------------------------------
    def evaluate(self, event: Event, contract: RoleContract) -> LensResult:
        with self._lock:
            st = self._get(event.agent_id, contract)
            cap = capability(event)
            novel_event = not st.in_anchor(cap)
            first_sighting = novel_event and cap not in st.novel
            if first_sighting:
                factor = IN_CONTRACT_NOVELTY if cap in st.contract_caps else 1.0
                st.novel[cap] = (NOVELTY_BASE + event.sensitivity) * factor
            x = st.novel[cap] if first_sighting else 0.0
            st.cusum = max(0.0, st.cusum + x - CUSUM_DELTA)

            surface = sum(st.novel.values())
            tolerance = DRIFT_H + contract.budgets.new_resource_classes_per_week
            budget_score = min(1.0, surface / tolerance)
            cusum_score = min(1.0, st.cusum / CUSUM_H)
            details = {"novel_capabilities": len(st.novel), "surface_weight": round(surface, 2),
                       "budget_score": round(budget_score, 3), "cusum": round(st.cusum, 2),
                       "cusum_score": round(cusum_score, 3), "anchor_frozen": st.frozen,
                       "anchor_size": len(st.learned), "this_event_novel": novel_event,
                       "first_sighting": first_sighting}
            if not novel_event:
                return LensResult("drift", 0.0, "capability is inside the agent's anchor", details=details)

            score = max(budget_score, cusum_score)
            recent = [f"{t} on {c}" for (t, c, _d) in list(st.novel)[-3:]]
            driver = "budget" if budget_score >= cusum_score else "burst"
            spent = " BUDGET EXHAUSTED." if budget_score >= 1.0 else ""
            why = (f"'{event.tool}' on '{event.resource_class}' is outside this agent's "
                   f"{'frozen ' if st.frozen else ''}baseline; it has now touched {len(st.novel)} "
                   f"capabilit{'y' if len(st.novel) == 1 else 'ies'} it never used while trusted "
                   f"(latest: {', '.join(recent)}), cumulative {surface:.1f} of {tolerance:.1f} "
                   f"allowed ({driver} detector).{spent}")
            return LensResult("drift", round(score, 3), why, evidence=[why], details=details)

    # -- learning -----------------------------------------------------------------
    def learn(self, event: Event, contract: RoleContract) -> None:
        """A TRUSTED event: its capability becomes part of the anchor, until the anchor freezes."""
        with self._lock:
            st = self._get(event.agent_id, contract)
            if st.frozen:
                return
            cap = capability(event)
            st.learned.add(cap)
            st.novel.pop(cap, None)          # benign adaptation during warm-up
            st.n_learned += 1
            if st.n_learned >= ANCHOR_FREEZE_N:
                st.frozen = True

    def refreeze(self, agent_id: str, contract: RoleContract) -> None:
        """An owner sanctioned the change: accept the current surface and the new
        contract version as the new anchor, reset the burst detector.
        (Wired to change declarations in Phase 7.)"""
        with self._lock:
            old = self._state.get(agent_id)
            learned = set(old.learned) if old else set()
            if old:
                learned |= set(old.novel)
            caps = self._contract_capabilities(contract)
            self._state[agent_id] = _AgentDrift((contract.role, contract.version), contract_caps=caps,
                                                learned=learned | caps, n_learned=ANCHOR_FREEZE_N,
                                                frozen=True)

    def learned_tools(self, agent_id: str) -> set:
        """Tool names this agent demonstrably used while trusted (its real routine)."""
        with self._lock:
            st = self._state.get(agent_id)
            return {t for (t, _c, _d) in st.learned} if st else set()

    def summary(self, agent_id: str) -> dict:
        with self._lock:
            st = self._state.get(agent_id)
            if st is None:
                return {"anchor_frozen": False, "anchor_size": 0, "novel": [], "surface_weight": 0, "cusum": 0}
            return {"anchor_frozen": st.frozen, "anchor_size": len(st.learned),
                    "learned_events": st.n_learned, "surface_weight": round(sum(st.novel.values()), 2),
                    "cusum": round(st.cusum, 2),
                    "novel": [{"tool": t, "resource_class": c, "destination_class": d, "weight": round(w, 2)}
                              for (t, c, d), w in st.novel.items()]}
