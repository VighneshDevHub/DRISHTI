"""Single source of truth for every tunable number in Agent Warden.

Rule: if a threshold, weight or window appears anywhere else in the code,
it is a bug. Tuning the system must be a one-file change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Named sensitivity ceilings used inside role contracts -> numeric 0..1
SENSITIVITY_LEVELS = {
    "public": 0.1,
    "internal": 0.4,
    "confidential": 0.7,
    "restricted": 1.0,
}

# How "far outside" a destination is. Used by the impact factor.
EGRESS_FACTOR = {
    "internal": 0.0,
    "allowlisted": 0.3,
    "external": 0.8,
    "unknown": 1.0,
}

# (minimum risk, band, recommended action) - checked top to bottom.
BAND_THRESHOLDS = [
    (95, "CRITICAL", "ISOLATE"),
    (80, "HIGH", "RESTRICT"),
    (60, "ELEVATED", "STEP_UP"),
    (30, "WATCH", "WATCH"),
    (0, "LOW", "ALLOW"),
]

# Alerts are stored for every event at or above this risk.
ALERT_MIN_RISK = 30

# Lens weights for noisy-OR fusion: R = 1 - prod(1 - w_i * s_i).
# A weight is "how much one lens at full score can move the result on its own".
LENS_WEIGHTS = {"role": 0.8, "provenance": 0.9, "decoy": 1.0, "baseline": 0.5, "drift": 0.5}

# Hard floors: some evidence is conclusive on its own, whatever else says.
FLOORS = {"decoy_touch": 85.0, "tainted_sensitive_egress": 95.0, "canary_exfil": 100.0,
          "drift_budget_exceeded": 60.0}

# Floors guarantee a MINIMUM BAND, not just a number, so they survive threshold jitter.
FLOOR_BANDS = {"decoy_touch": "HIGH", "tainted_sensitive_egress": "CRITICAL",
               "canary_exfil": "CRITICAL", "drift_budget_exceeded": "ELEVATED"}
BAND_ORDER = ["LOW", "WATCH", "ELEVATED", "HIGH", "CRITICAL"]

# --- Enforcement (Phase 6) ------------------------------------------------------
TOKEN_TTL_SECONDS = 300       # tokens are short-lived on purpose; the broker re-mints from CURRENT posture
APPROVAL_TTL_SECONDS = 300    # an unanswered step-up is auto-denied after this long

# --- Session risk --------------------------------------------------------------
SESSION_DECAY = 0.85         # accumulated suspicion fades by this factor on every tool call
SESSION_GAIN = 0.5           # how much of an event's risk is added to the session (noisy-OR style)
SESSION_MIN_EVENT_RISK = 20  # only events at least this risky feed, or inherit from, the session

# --- Provenance (L3) -----------------------------------------------------
PROVENANCE_WINDOW = 10      # a label stops mattering after this many tool calls
PROVENANCE_DECAY = 10.0     # strength = exp(-age / DECAY): fresher taint counts more
PEER_AGENT_FACTOR = 0.5     # messages from other agents are half as suspicious as raw untrusted input
# How dangerous an action is as a destination for tainted influence.
SINK_WEIGHTS = {"egress_external": 0.9, "read_sensitive": 0.7, "write": 0.6,
                "out_of_contract": 0.5, "benign": 0.0}
SENSITIVE_READ_MIN = 0.5    # sensitivity at/above which a read counts as "sensitive data in context"


# --- Baseline (L2) -----------------------------------------------------------
BASELINE_K = 20            # w = n_ctx / (n_ctx + K): how fast own history overtakes the prior
PRIOR_TYPICAL_MIX = 0.5    # prior = MIX * typical-sequence model + (1-MIX) * uniform over allowed tools
PRIOR_OOV_PROB = 0.004     # prior probability of a tool the contract does not allow
PEER_MIX = 0.5             # share of the prior taken from same-role peer agents (when they have data)
PEER_MIN_OBS = 20          # peers need this many observations in a context before they count
OWN_SMOOTHING = 0.5        # additive smoothing on the agent's own counts
SURPRISE_A = 1.2           # s_base = sigmoid(A * (x - B)), x in nats of surprise (or z-score)
SURPRISE_B = 3.5
SENS_Z_MIN_N = 10          # sensitivity z-score needs this many learned events
SENS_STD_FLOOR = 0.1       # never divide by less than this standard deviation

# --- Drift (L2b) -------------------------------------------------------------
ANCHOR_FREEZE_N = 30       # learned events after which the anchor is frozen for good
NOVELTY_BASE = 0.5         # weight of a new capability = BASE + its sensitivity
DRIFT_H = 2.5              # cumulative novelty weight at which the budget is spent (score 1.0)
IN_CONTRACT_NOVELTY = 0.75 # a new-to-this-agent but contract-permitted capability counts 75% (out-of-contract counts 100%)
CUSUM_DELTA = 0.25         # per-event forgiveness of the burst detector
CUSUM_H = 2.5              # burst-detector alarm level


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("WARDEN_DB", "warden.db")
    contracts_dir: Path = BASE_DIR / "contracts" / "templates"
    # Minimum cosine similarity for an unlisted action to count as
    # "semantically close to the role" (score 0.3 instead of 0.6).
    similarity_tau: float = 0.10
    # Phases 1-2 run in SHADOW mode: score and record everything, block nothing.
    # Enforcement (step-up / restrict / isolate) arrives in Phase 6.
    # "shadow": score and record, block nothing (safe rollout). "enforce": step-up / restrict / isolate.
    mode: str = os.getenv("WARDEN_MODE", "shadow")
    # Switches used by ablation studies (Phase 9) and by the S4 tests.
    enable_baseline: bool = True
    enable_drift: bool = True
    # Only learn from events judged LOW. Stops an attacker teaching the baseline
    # that malicious behaviour is normal ("poisoned learning").
    learn_gate: bool = True
    # Multi-step accumulation: repeated mid-level suspicious actions escalate (see risk/session.py).
    enable_session: bool = True
    # Secret per-agent shift of the band thresholds, +/- this many points, so an attacker
    # cannot probe for the exact boundary. 0 = off (reproducible research/evaluation mode).
    jitter_amplitude: float = float(os.getenv("WARDEN_JITTER", "0"))
    jitter_secret: str = os.getenv("WARDEN_JITTER_SECRET", "dev-secret-change-me")
    # False = agents get a bare verdict. A compromised agent must not see its own risk score.
    expose_scores: bool = os.getenv("WARDEN_EXPOSE_SCORES", "1") == "1"
    token_ttl: int = TOKEN_TTL_SECONDS
    approval_ttl: int = APPROVAL_TTL_SECONDS
    cors_origins: tuple = tuple(
        origin.strip()
        for origin in os.getenv(
            "WARDEN_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    )

    def __post_init__(self):
        if self.mode not in ("shadow", "enforce"):
            raise ValueError(f"mode must be 'shadow' or 'enforce', not {self.mode!r}")
