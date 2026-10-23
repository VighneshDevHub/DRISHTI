"""Token broker: short-lived, scoped tokens that Warden can shrink or revoke instantly.

The premise of the problem statement is that a hijacked agent still holds a
VALID credential. The broker is how Warden takes power back without
touching the agent's identity provider:

  * Every token is short-lived (TOKEN_TTL_SECONDS) and is minted from the
    agent's CURRENT posture. A restricted agent cannot renew its way back to a
    wide token; only an owner's restore does that.
  * Restricting an agent narrows its LIVE tokens in place, so it takes effect
    on the very next call, not at expiry.
  * Isolating revokes them all.

A scope is a set of tool names, or {"*"} for "everything the underlying
credential could do" (the normal, over-permissioned state the PS describes).

Prototype note: tokens are opaque random strings held in memory. In
production this is an OAuth 2.0 token-exchange (RFC 8693) endpoint issuing
scoped, short-lived access tokens; the policy and the semantics are the same.
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

WILDCARD = "*"


@dataclass
class TokenRecord:
    token: str
    agent_id: str
    scopes: set
    issued_at: float
    expires_at: float
    revoked: bool = False


class TokenBroker:
    def __init__(self, clock: Callable[[], float], ttl: int = 300):
        self.clock = clock
        self.ttl = ttl
        self._tokens: dict = {}
        self._lock = threading.RLock()

    def issue(self, agent_id: str, scopes: set) -> TokenRecord:
        """Mint a token. Older tokens of the same agent are revoked, so nobody can keep
        clinging to a wider, older token after a narrower one was issued."""
        with self._lock:
            self._revoke_locked(agent_id)
            now = self.clock()
            rec = TokenRecord("wt_" + secrets.token_urlsafe(24), agent_id, set(scopes), now, now + self.ttl)
            self._tokens[rec.token] = rec
            return rec

    def validate(self, token: Optional[str], agent_id: str) -> tuple:
        """-> (ok, reason, record). Reasons: token_missing, token_invalid, token_revoked, token_expired."""
        if not token:
            return False, "token_missing", None
        with self._lock:
            rec = self._tokens.get(token)
            if rec is None or rec.agent_id != agent_id:
                return False, "token_invalid", None
            if rec.revoked:
                return False, "token_revoked", None
            if self.clock() >= rec.expires_at:
                return False, "token_expired", None
            return True, None, rec

    @staticmethod
    def allows(rec: Optional[TokenRecord], tool: str) -> bool:
        return rec is not None and (WILDCARD in rec.scopes or tool in rec.scopes)

    def narrow(self, agent_id: str, scopes: set) -> int:
        """Shrink every live token of this agent to `scopes`, effective immediately."""
        n = 0
        with self._lock:
            for rec in self._tokens.values():
                if rec.agent_id == agent_id and not rec.revoked:
                    rec.scopes = set(scopes)
                    n += 1
        return n

    def revoke_all(self, agent_id: str) -> int:
        with self._lock:
            return self._revoke_locked(agent_id)

    def _revoke_locked(self, agent_id: str) -> int:
        n = 0
        for rec in self._tokens.values():
            if rec.agent_id == agent_id and not rec.revoked:
                rec.revoked = True
                n += 1
        return n

    def active(self, agent_id: str) -> Optional[TokenRecord]:
        with self._lock:
            now = self.clock()
            live = [r for r in self._tokens.values()
                    if r.agent_id == agent_id and not r.revoked and now < r.expires_at]
            return max(live, key=lambda r: r.issued_at) if live else None
