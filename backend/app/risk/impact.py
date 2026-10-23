"""Impact factor: how bad would it be if THIS action were malicious?"""
from __future__ import annotations

from ..config import EGRESS_FACTOR


def impact_factor(sensitivity: float, destination_class: str, irreversible: bool) -> float:
    """I = 0.5*sensitivity + 0.3*egress + 0.2*irreversibility, clamped to 0..1."""
    egress = EGRESS_FACTOR.get(destination_class, 0.0)
    value = 0.5 * sensitivity + 0.3 * egress + 0.2 * (1.0 if irreversible else 0.0)
    return max(0.0, min(1.0, value))
