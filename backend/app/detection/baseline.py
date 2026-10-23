"""L2 - Behavioral baseline lens.

Question: "Is this a normal thing for THIS agent (and agents like it) to do
right now?"  It learns tool-to-tool transitions and how sensitive the
agent's usual data is, and scores how surprising a new action is.

Cold start (the PS lists "little or no history" as a core challenge):
the model never starts empty. Probabilities blend three sources,

    P = w * P_own + (1 - w) * P_prior            w = n_ctx / (n_ctx + K)

  P_own    the agent's own transition counts (smoothed)
  P_prior  50% typical sequences from the role contract
         + 50% uniform over tools the contract allows,
           optionally mixed with POOLED counts from same-role peer agents
  n_ctx    how often this agent has been in this context (previous tool)

A brand-new agent has w = 0 and is judged purely by its role + its peers.
As history builds, its own behaviour takes over. A tool the contract does
not allow gets only PRIOR_OOV_PROB, so it is "surprising" from action one.

Anti-poisoning: the model only learns from events the system judged LOW
(see interceptor). An attacker cannot teach it that bad behaviour is normal.
"""
from __future__ import annotations

import math
import threading
from collections import Counter, defaultdict
from typing import Optional

from ..config import (BASELINE_K, OWN_SMOOTHING, PEER_MIN_OBS, PEER_MIX, PRIOR_OOV_PROB,
                      PRIOR_TYPICAL_MIX, SENS_STD_FLOOR, SENS_Z_MIN_N, SURPRISE_A, SURPRISE_B)
from ..gateway.tool_registry import ToolRegistry
from ..models.contracts import RoleContract
from ..models.events import Event, LensResult

START = "<START>"


class _Welford:
    """Running mean / variance without storing history."""
    def __init__(self):
        self.n, self.mean, self.m2 = 0, 0.0, 0.0

    def add(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    @property
    def std(self) -> float:
        return math.sqrt(self.m2 / self.n) if self.n > 1 else 0.0


class _AgentModel:
    def __init__(self, role: str):
        self.role = role
        self.counts: dict = defaultdict(Counter)   # previous tool -> Counter(next tool)
        self.prev = START
        self.n = 0
        self.sensitivity = _Welford()


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class BaselineStore:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._models: dict = {}
        self._prior_cache: dict = {}
        self._lock = threading.RLock()

    # -- prior from the contract -----------------------------------------------
    def _prior(self, contract: RoleContract) -> tuple:
        key = (contract.role, contract.version)
        if key not in self._prior_cache:
            vocab = {s.name for s in self.registry.matching(contract.allowed_tools)}
            pairs: dict = defaultdict(Counter)
            for seq in contract.typical_sequences:
                vocab.update(seq)
                full = [START] + list(seq)
                for a, b in zip(full, full[1:]):
                    pairs[a][b] += 1
            self._prior_cache[key] = (vocab, pairs)
        return self._prior_cache[key]

    def model(self, agent_id: str, role: str) -> _AgentModel:
        with self._lock:
            if agent_id not in self._models:
                self._models[agent_id] = _AgentModel(role)
            return self._models[agent_id]

    def _peer_counts(self, role: str, exclude: str, prev: str) -> Counter:
        pooled: Counter = Counter()
        for aid, m in self._models.items():
            if aid != exclude and m.role == role:
                pooled.update(m.counts.get(prev, Counter()))
        return pooled

    # -- probability -----------------------------------------------------------
    def probability(self, agent_id: str, contract: RoleContract, tool: str) -> dict:
        with self._lock:
            m = self.model(agent_id, contract.role)
            vocab, pairs = self._prior(contract)
            prev = m.prev
            size = max(1, len(vocab))

            # prior: typical sequences mixed with a uniform floor over allowed tools
            ctx = pairs.get(prev, Counter())
            total = sum(ctx.values())
            typical = (ctx[tool] / total) if total else (1.0 / size if tool in vocab else 0.0)
            floor = (1.0 / size) if tool in vocab else PRIOR_OOV_PROB
            prior_p = PRIOR_TYPICAL_MIX * typical + (1 - PRIOR_TYPICAL_MIX) * floor

            # peer pooling: same-role agents' own behaviour, once they have enough data
            peers = self._peer_counts(contract.role, agent_id, prev)
            peer_n = sum(peers.values())
            if peer_n >= PEER_MIN_OBS:
                peer_p = (peers[tool] + OWN_SMOOTHING) / (peer_n + OWN_SMOOTHING * size)
                prior_p = (1 - PEER_MIX) * prior_p + PEER_MIX * peer_p

            own = m.counts.get(prev, Counter())
            n_ctx = sum(own.values())
            own_p = (own[tool] + OWN_SMOOTHING) / (n_ctx + OWN_SMOOTHING * size)
            w = n_ctx / (n_ctx + BASELINE_K)
            p = w * own_p + (1 - w) * prior_p
            return {"p": p, "prev": prev, "w": w, "n_ctx": n_ctx, "prior_p": prior_p,
                    "own_p": own_p, "peer_obs": peer_n}

    # -- scoring ---------------------------------------------------------------
    def evaluate(self, event: Event, contract: RoleContract) -> LensResult:
        info = self.probability(event.agent_id, contract, event.tool)
        surprise = -math.log(max(info["p"], 1e-9))
        m = self.model(event.agent_id, contract.role)
        z = 0.0
        if m.sensitivity.n >= SENS_Z_MIN_N:
            z = max(0.0, (event.sensitivity - m.sensitivity.mean) / max(m.sensitivity.std, SENS_STD_FLOOR))
        x = max(surprise, z)
        score = sigmoid(SURPRISE_A * (x - SURPRISE_B))
        details = {"probability": round(info["p"], 5), "surprise": round(surprise, 2),
                   "previous_tool": info["prev"], "own_weight": round(info["w"], 2),
                   "context_observations": info["n_ctx"], "peer_observations": info["peer_obs"],
                   "sensitivity_z": round(z, 2), "learned_events": m.n}
        if score < 0.05:
            return LensResult("baseline", round(score, 3), "behaviour is typical for this agent and role",
                              details=details)
        why = (f"transition '{info['prev']}' -> '{event.tool}' has probability {info['p']:.3f} "
               f"for this agent/role ({surprise:.1f} nats of surprise, "
               f"{info['w']:.0%} own history / {1 - info['w']:.0%} role prior)")
        if z >= SURPRISE_B:
            why += f"; data sensitivity is {z:.1f} standard deviations above this agent's norm"
        return LensResult("baseline", round(score, 3), why, evidence=[why], details=details)

    # -- learning --------------------------------------------------------------
    def observe(self, event: Event, contract: RoleContract, learn: bool) -> None:
        """Record the event. Only events judged trustworthy shape the baseline."""
        if not learn:
            return
        with self._lock:
            m = self.model(event.agent_id, contract.role)
            m.counts[m.prev][event.tool] += 1
            m.prev = event.tool
            m.n += 1
            m.sensitivity.add(event.sensitivity)

    def summary(self, agent_id: str) -> dict:
        with self._lock:
            m = self._models.get(agent_id)
            if m is None:
                return {"learned_events": 0, "transitions": []}
            flat = [(a, b, c) for a, ctr in m.counts.items() for b, c in ctr.items()]
            flat.sort(key=lambda t: -t[2])
            return {"learned_events": m.n, "last_tool": m.prev,
                    "mean_sensitivity": round(m.sensitivity.mean, 3),
                    "transitions": [{"from": a, "to": b, "count": c} for a, b, c in flat[:12]]}
