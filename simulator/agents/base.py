"""SimAgent: a scripted 'agent' that behaves like its role.

Normal behaviour is a seeded Markov chain over the role's tools, with
realistic argument generation. Same seed -> identical traffic, so demos
and evaluation are repeatable.
"""
from __future__ import annotations

import random
import time
from typing import Callable, Optional

from simulator.client import WardenClient


class SimAgent:
    role = "base"
    # state -> list of (next_state, probability)
    chain: dict = {}
    start_state: str = ""

    def __init__(self, agent_id: str, client: WardenClient, seed: int = 0, owner: str = "sim"):
        self.agent_id = agent_id
        self.client = client
        self.rng = random.Random(f"{seed}:{agent_id}")
        self.state = self.start_state
        self.owner = owner

    def register(self) -> dict:
        return self.client.register_agent(self.agent_id, self.role, self.owner)

    # subclasses define realistic arguments per tool
    def args_for(self, tool: str) -> dict:  # pragma: no cover
        return {}

    def next_tool(self) -> str:
        options = self.chain[self.state]
        r, acc = self.rng.random(), 0.0
        for tool, p in options:
            acc += p
            if r <= acc:
                self.state = tool
                return tool
        self.state = options[-1][0]
        return self.state

    def step(self) -> dict:
        tool = self.next_tool()
        return self.client.call_tool(self.agent_id, tool, self.args_for(tool))

    def act(self, tool: str, args: Optional[dict] = None, context_labels: Optional[list] = None) -> dict:
        """An explicit (e.g. attacker-driven) action, outside the normal chain."""
        return self.client.call_tool(self.agent_id, tool, args or {}, context_labels)

    def run(self, steps: int, delay: float = 0.0,
            on_decision: Optional[Callable[[str, dict], None]] = None) -> list:
        out = []
        for _ in range(steps):
            d = self.step()
            out.append(d)
            if on_decision:
                on_decision(self.agent_id, d)
            if delay:
                time.sleep(delay)
        return out
