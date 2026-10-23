"""Response orchestrator: turns a verdict into a change of the agent's standing.

    ELEVATED   per-action only: pause for a human (approvals.py). Posture unchanged.
    HIGH       block this action AND restrict the agent: tokens shrink to its routine.
    CRITICAL   block this action AND isolate the agent: tokens revoked.

The agent's posture lives in the database (agents.status), so it survives restarts and is
the single source of truth the token broker mints from.

Restore and resume are the way back, and they are deliberate human acts.
"""
from __future__ import annotations

from typing import Optional

from ..detection.drift import DriftTracker
from ..gateway.provenance import ProvenanceTracker
from ..gateway.token_service import TokenBroker
from ..gateway.tool_registry import ToolRegistry
from ..contracts.loader import ContractStore
from ..store.repo import Repo
from .checkpoints import CheckpointStore
from .policies import ISOLATED, NORMAL, RESTRICTED, scopes_for


class Orchestrator:
    def __init__(self, repo: Repo, broker: TokenBroker, registry: ToolRegistry, contracts: ContractStore,
                 drift: DriftTracker, provenance: ProvenanceTracker, checkpoints: CheckpointStore):
        self.repo, self.broker, self.registry, self.contracts = repo, broker, registry, contracts
        self.drift, self.provenance, self.checkpoints = drift, provenance, checkpoints

    # -- helpers --------------------------------------------------------------------
    def _contract(self, agent: dict):
        return self.contracts.get(agent["role"], agent["role_version"])

    def scopes(self, agent: dict, posture: Optional[str] = None) -> set:
        return scopes_for(posture or agent["status"], self._contract(agent), self.registry,
                          self.drift.learned_tools(agent["agent_id"]))

    def mint(self, agent_id: str):
        agent = self.repo.get_agent(agent_id)
        if agent["status"] == ISOLATED:
            return None
        return self.broker.issue(agent_id, self.scopes(agent))

    # -- automatic responses -----------------------------------------------------------
    def restrict(self, agent_id: str, alert_id: Optional[str], sources: list) -> dict:
        agent = self.repo.get_agent(agent_id)
        if agent["status"] in (RESTRICTED, ISOLATED):
            return {"posture": agent["status"], "changed": False}
        self.repo.set_agent_status(agent_id, RESTRICTED)
        scope = self.scopes(agent, RESTRICTED)
        self.broker.narrow(agent_id, scope)
        self.checkpoints.record(agent_id, alert_id, RESTRICTED, sources)
        return {"posture": RESTRICTED, "changed": True, "scope": sorted(scope)}

    def isolate(self, agent_id: str, alert_id: Optional[str], sources: list) -> dict:
        agent = self.repo.get_agent(agent_id)
        if agent["status"] == ISOLATED:
            return {"posture": ISOLATED, "changed": False}
        self.repo.set_agent_status(agent_id, ISOLATED)
        self.broker.revoke_all(agent_id)
        self.checkpoints.record(agent_id, alert_id, ISOLATED, sources)
        return {"posture": ISOLATED, "changed": True}

    # -- the way back (human decisions) --------------------------------------------------
    def restore(self, agent_id: str) -> dict:
        """The owner decided it was a false alarm (or has dealt with it): back to normal."""
        self.repo.set_agent_status(agent_id, NORMAL)
        self.broker.revoke_all(agent_id)          # force a fresh, full-scope mint
        return {"posture": NORMAL}

    def resume(self, agent_id: str) -> dict:
        """Restore, and also drop the poisoned inputs so the agent continues WITHOUT them."""
        sources = self.checkpoints.all_sources(agent_id)
        for src in sources:
            self.provenance.clear(agent_id, src)
        self.provenance.forget_sensitive(agent_id)
        out = self.restore(agent_id)
        out["drop_sources"] = sources
        return out
