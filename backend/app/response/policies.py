"""What each posture allows. One place, so "restrict" has a single, auditable meaning.

  normal      token scope {"*"}: everything the underlying credential can do.
              Warden judges each ACTION by risk. This is the PS's premise: the
              credential is valid and broad.
  restricted  the agent's REAL ROUTINE only: tools it demonstrably used while
              trusted, plus the tools in its contract's typical sequences, minus
              anything that sends data out. Legitimate work keeps flowing;
              everything else (sensitive reads, egress, new tools) is cut off.
  isolated    nothing.

Why "demonstrated routine" and not "everything in the contract"? A support
agent legitimately reads customer records, so restricting it must not cut
that off; a procurement agent never does, so there it is cut. The anchor
learned in Phase 4 already knows the difference.
"""
from __future__ import annotations

from ..gateway.token_service import WILDCARD
from ..gateway.tool_registry import ToolRegistry
from ..models.contracts import RoleContract

NORMAL, RESTRICTED, ISOLATED = "normal", "restricted", "isolated"


def restricted_scope(contract: RoleContract, registry: ToolRegistry, learned_tools: set) -> set:
    routine = {t for seq in contract.typical_sequences for t in seq} | set(learned_tools)
    routine = {t for t in routine if contract.tool_allowed(t)}
    egress = {s.name for s in registry.all() if s.sink_type == "egress"}
    return routine - egress


def scopes_for(posture: str, contract: RoleContract, registry: ToolRegistry, learned_tools: set) -> set:
    if posture == ISOLATED:
        return set()
    if posture == RESTRICTED:
        return restricted_scope(contract, registry, learned_tools)
    return {WILDCARD}
