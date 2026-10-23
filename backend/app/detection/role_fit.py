"""L1 - Role Fit lens.

Question it answers: "Is this action inside the job this agent was hired for?"

It needs NO history, so it works on an agent's very first action (cold
start). Its hard limits (denied classes, egress allowlist, sensitivity
ceiling) also apply no matter how 'normal' the traffic looks statistically,
which is what defeats mimicry attacks.

Scoring (see docs/lenses.md):
    denied resource class ............................ 1.0
    unlisted, semantically unrelated to the role ..... 0.6
    unlisted, semantically close to the role ......... 0.3
    sensitivity above contract ceiling ............... >= 0.7
    destination not in egress allowlist .............. >= 0.8
    inside the contract .............................. 0.0
The lens score is the MAX of everything that triggered.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from ..gateway.tool_registry import ToolRegistry
from ..models.contracts import RoleContract
from ..models.events import Event, LensResult

# Generic words carry no role meaning and would inflate similarity between
# unrelated actions ("read X" vs "read Y"), so they are ignored.
_STOP = {
    "the", "and", "for", "from", "with", "that", "this", "into", "such", "any",
    "get", "list", "read", "create", "send", "post", "run", "api", "file", "files",
    "data", "check", "answer",
}


def tokenize(text: str) -> list:
    words = re.findall(r"[a-z]+", text.lower().replace("_", " ").replace(".", " "))
    out = []
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.append(w)
    return out


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class RoleFitLens:
    name = "role"

    def __init__(self, registry: ToolRegistry, similarity_tau: float = 0.10):
        self.registry = registry
        self.tau = similarity_tau
        self._ref_cache: dict = {}

    # The "reference document" describes the role in words: its purpose, the
    # descriptions of every tool it may use, and its allowed resource classes.
    def _reference(self, contract: RoleContract) -> Counter:
        key = (contract.role, contract.version)
        if key not in self._ref_cache:
            parts = [contract.purpose]
            for spec in self.registry.matching(contract.allowed_tools):
                parts.append(spec.description)
            parts.extend(contract.allowed_resource_classes)
            self._ref_cache[key] = Counter(tokenize(" ".join(parts)))
        return self._ref_cache[key]

    def similarity(self, contract: RoleContract, event: Event) -> float:
        spec = self.registry.get(event.tool)
        description = spec.description if spec else ""
        action_doc = f"{event.tool} {description} {event.resource_class}"
        return cosine(self._reference(contract), Counter(tokenize(action_doc)))

    def evaluate(self, event: Event, contract: RoleContract) -> LensResult:
        findings = []  # (score, message)
        cls = event.resource_class

        if cls in contract.denied_resource_classes:
            findings.append((1.0, f"resource class '{cls}' is explicitly denied for role "
                                  f"'{contract.role}' (tool {event.tool})"))
        elif contract.tool_allowed(event.tool) and cls in contract.allowed_resource_classes:
            pass  # squarely inside the contract
        else:
            sim = self.similarity(contract, event)
            if sim >= self.tau:
                findings.append((0.3, f"'{event.tool}' on '{cls}' is not in the contract for "
                                      f"'{contract.role}' but is close to its purpose "
                                      f"(similarity {sim:.2f})"))
            else:
                findings.append((0.6, f"'{event.tool}' on '{cls}' is not in the contract for "
                                      f"'{contract.role}' and unrelated to its purpose "
                                      f"(similarity {sim:.2f})"))

        if event.sensitivity > contract.sensitivity_ceiling_value + 1e-9:
            findings.append((0.7, f"data sensitivity {event.sensitivity:.1f} exceeds the "
                                  f"contract ceiling '{contract.data_sensitivity_ceiling}' "
                                  f"({contract.sensitivity_ceiling_value:.1f})"))

        if event.destination_class in ("external", "unknown"):
            findings.append((0.8, f"destination '{event.destination}' is "
                                  f"{event.destination_class} and not in the egress allowlist"))

        if not findings:
            return LensResult(self.name, 0.0, "action is inside the role contract",
                              evidence=[f"tool={event.tool}", f"resource_class={cls}"])

        score = max(s for s, _ in findings)
        top = max(findings, key=lambda f: f[0])[1]
        return LensResult(
            self.name, score, top,
            evidence=[m for _, m in sorted(findings, key=lambda f: -f[0])],
            details={"tool": event.tool, "resource_class": cls,
                     "components": [round(s, 2) for s, _ in findings]},
        )
