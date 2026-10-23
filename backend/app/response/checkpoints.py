"""Incident checkpoints: remember WHAT to forget when an agent is let back in.

When Warden restricts or isolates an agent it records the untrusted sources
that were in the agent's context. Later, `resume` tells the agent runtime to
drop exactly those sources and clears Warden's own taint for them, so the
agent can continue its legitimate work WITHOUT the poisoned input instead of
being thrown away.

Honest limit: Warden can clear its own bookkeeping, but only the agent
framework can actually remove a document from the model's context window.
`resume` therefore returns `drop_sources` for the framework to act on.
"""
from __future__ import annotations

import threading
from typing import Optional


class CheckpointStore:
    def __init__(self):
        self._by_agent: dict = {}
        self._lock = threading.Lock()

    def record(self, agent_id: str, alert_id: Optional[str], posture: str, sources: list) -> dict:
        cp = {"alert_id": alert_id, "posture": posture, "untrusted_sources": sorted(set(sources))}
        with self._lock:
            self._by_agent.setdefault(agent_id, []).append(cp)
        return cp

    def latest(self, agent_id: str) -> Optional[dict]:
        with self._lock:
            history = self._by_agent.get(agent_id)
            return history[-1] if history else None

    def all_sources(self, agent_id: str) -> list:
        with self._lock:
            return sorted({s for cp in self._by_agent.get(agent_id, []) for s in cp["untrusted_sources"]})

    def history(self, agent_id: str) -> list:
        with self._lock:
            return list(self._by_agent.get(agent_id, []))
