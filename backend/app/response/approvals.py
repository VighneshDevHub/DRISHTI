"""Step-up approvals: pause one risky action, ask a human, never block the whole agent.

An ELEVATED action is neither allowed nor refused outright. The gateway
stores the request, returns PENDING_APPROVAL to the agent, and waits.
An operator can approve it once or deny it. If nobody answers in time it is
auto-denied (fail closed), so an unattended alert can never become an
unreviewed allow.
"""
from __future__ import annotations

from typing import Callable, Optional

from ..store.repo import Repo


class ApprovalQueue:
    def __init__(self, repo: Repo, clock: Callable[[], float], ttl: int):
        self.repo = repo
        self.clock = clock
        self.ttl = ttl

    def create(self, agent_id: str, event_id: str, request: dict) -> str:
        return self.repo.insert_approval(agent_id, event_id, request, self.clock())

    def expire_due(self) -> list:
        """Auto-deny anything unanswered past the TTL. Returns the affected event ids."""
        now = self.clock()
        event_ids = self.repo.expire_approvals(now - self.ttl, now)
        for eid in event_ids:
            self.repo.update_event_decision(eid, "DENIED_EXPIRED")
        return event_ids

    def pending(self) -> list:
        self.expire_due()
        return self.repo.list_approvals("pending")
