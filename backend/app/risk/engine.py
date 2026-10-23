"""Risk engine: fuse lens scores into one 0-100 number.

    R    = 1 - prod(1 - w_i * s_i)              noisy-OR: any strong signal raises R,
                                                independent signals compound
    risk = 100 * R * (0.5 + 0.5 * impact)       impact scales by how bad the action would be
    floors                                      conclusive evidence sets a minimum

Phase 3 fuses the lenses that exist so far (role, provenance, decoy) and
applies the hard floors. Phase 5 adds the remaining lenses, session
(multi-step) risk, threshold jitter and the full explanation format.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import BAND_ORDER, BAND_THRESHOLDS, FLOOR_BANDS, FLOORS, LENS_WEIGHTS


ACTION_FOR_BAND = {band: action for _, band, action in BAND_THRESHOLDS}


def band_for(risk: float, offset: float = 0.0) -> tuple:
    """Return (band, recommended_action) for a 0..100 risk score.
    `offset` is the agent's secret threshold jitter (0 when jitter is off)."""
    for minimum, band, action in BAND_THRESHOLDS:
        if minimum == 0 or risk >= minimum + offset:
            return band, action
    return "LOW", "ALLOW"


def at_least(band: str, minimum: str) -> bool:
    return BAND_ORDER.index(band) >= BAND_ORDER.index(minimum)


def apply_floor_bands(band: str, floors: list) -> tuple:
    """Conclusive evidence guarantees a minimum band, whatever jitter or scores say."""
    for name, _, _ in floors:
        needed = FLOOR_BANDS.get(name)
        if needed and not at_least(band, needed):
            band = needed
    return band, ACTION_FOR_BAND[band]


@dataclass
class Fusion:
    risk: float
    combined: float                       # R before impact scaling
    contributions: list = field(default_factory=list)   # [(lens, weighted score)] strongest first
    floors: list = field(default_factory=list)          # [(name, minimum, reason)]


def fuse(lens: dict, impact: float) -> Fusion:
    remaining = 1.0
    contributions = []
    for name, result in lens.items():
        weight = LENS_WEIGHTS.get(name)
        if weight is None:
            continue
        c = weight * result.score
        contributions.append((name, round(c, 3)))
        remaining *= (1.0 - c)
    combined = 1.0 - remaining
    risk = 100.0 * combined * (0.5 + 0.5 * impact)

    floors = []
    decoy = lens.get("decoy")
    if decoy is not None:
        kind = decoy.details.get("kind")
        if kind == "canary_exfil":
            floors.append(("canary_exfil", FLOORS["canary_exfil"], decoy.reason))
        elif kind == "touch":
            floors.append(("decoy_touch", FLOORS["decoy_touch"], decoy.reason))
    prov = lens.get("provenance")
    if (prov is not None and prov.details.get("tainted") and prov.details.get("sink") == "egress_external"
            and prov.details.get("sensitive_in_context")):
        floors.append(("tainted_sensitive_egress", FLOORS["tainted_sensitive_egress"],
                       "untrusted content influenced an external send while sensitive data "
                       f"({', '.join(prov.details['sensitive_in_context'])}) was in context"))
    drift = lens.get("drift")
    if drift is not None and drift.details.get("this_event_novel") and drift.details.get("budget_score", 0) >= 1.0:
        floors.append(("drift_budget_exceeded", FLOORS["drift_budget_exceeded"],
                       "capability budget exhausted: " + drift.reason))
    for _, minimum, _ in floors:
        risk = max(risk, minimum)

    contributions.sort(key=lambda c: -c[1])
    return Fusion(round(risk, 1), round(combined, 3), contributions, floors)
