"""Secret per-agent threshold jitter.

If every deployment used identical band thresholds, a hijacked agent could
probe for the exact score at which it gets stopped and stay one point
below. Shifting each agent's thresholds by a secret, deterministic amount
(+/- amplitude points) removes that certainty. Combined with hiding scores
from agents (`expose_scores=False`), probing yields almost nothing.

The offset is an HMAC of the agent id under a server-side secret, so it is
stable across restarts but unpredictable to the agent.
"""
from __future__ import annotations

import hashlib
import hmac


def threshold_offset(agent_id: str, secret: str, amplitude: float) -> float:
    if amplitude <= 0:
        return 0.0
    digest = hmac.new(secret.encode(), agent_id.encode(), hashlib.sha256).digest()
    unit = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF      # 0..1
    return round((unit * 2.0 - 1.0) * amplitude, 2)            # -amp..+amp
