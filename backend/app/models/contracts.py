"""Role contract: the machine-readable 'job description' of an agent."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import SENSITIVITY_LEVELS


class ContractError(ValueError):
    """Raised when a contract file/dict is invalid."""


_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)?\s*$", re.I)
_MULT = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}


def parse_size(value: Any) -> int:
    """'5MB' -> 5242880. Plain ints pass through."""
    if isinstance(value, (int, float)):
        return int(value)
    m = _SIZE.match(str(value))
    if not m:
        raise ContractError(f"invalid size value: {value!r}")
    return int(float(m.group(1)) * _MULT[(m.group(2) or "B").upper()])


@dataclass
class Budgets:
    actions_per_hour: int = 0
    new_resource_classes_per_week: int = 0
    bytes_out_per_hour: int = 0


@dataclass
class RoleContract:
    role: str
    version: int
    purpose: str
    allowed_tools: list
    allowed_resource_classes: list
    denied_resource_classes: list = field(default_factory=list)
    data_sensitivity_ceiling: str = "internal"
    egress_allowlist: list = field(default_factory=list)
    typical_sequences: list = field(default_factory=list)
    budgets: Budgets = field(default_factory=Budgets)

    # -- construction / validation ------------------------------------------
    @classmethod
    def from_dict(cls, d: dict) -> "RoleContract":
        for key in ("role", "version", "purpose", "allowed_tools", "allowed_resource_classes"):
            if key not in d:
                raise ContractError(f"contract missing required field '{key}'")
        if not isinstance(d["version"], int) or d["version"] < 1:
            raise ContractError("version must be an integer >= 1")
        for key in ("allowed_tools", "allowed_resource_classes"):
            if not isinstance(d[key], list) or not d[key]:
                raise ContractError(f"'{key}' must be a non-empty list")
        ceiling = d.get("data_sensitivity_ceiling", "internal")
        if ceiling not in SENSITIVITY_LEVELS:
            raise ContractError(
                f"data_sensitivity_ceiling must be one of {sorted(SENSITIVITY_LEVELS)}"
            )
        allowed, denied = set(d["allowed_resource_classes"]), set(d.get("denied_resource_classes", []))
        if allowed & denied:
            raise ContractError(f"classes both allowed and denied: {sorted(allowed & denied)}")
        b = d.get("budgets", {}) or {}
        budgets = Budgets(
            actions_per_hour=int(b.get("actions_per_hour", 0)),
            new_resource_classes_per_week=int(b.get("new_resource_classes_per_week", 0)),
            bytes_out_per_hour=parse_size(b.get("bytes_out_per_hour", 0)),
        )
        return cls(
            role=d["role"],
            version=d["version"],
            purpose=d["purpose"],
            allowed_tools=list(d["allowed_tools"]),
            allowed_resource_classes=list(d["allowed_resource_classes"]),
            denied_resource_classes=list(d.get("denied_resource_classes", [])),
            data_sensitivity_ceiling=ceiling,
            egress_allowlist=list(d.get("egress_allowlist", [])),
            typical_sequences=[list(s) for s in d.get("typical_sequences", [])],
            budgets=budgets,
        )

    # -- helpers --------------------------------------------------------------
    @property
    def sensitivity_ceiling_value(self) -> float:
        return SENSITIVITY_LEVELS[self.data_sensitivity_ceiling]

    def tool_allowed(self, tool: str) -> bool:
        """Exact match or glob (e.g. 'supplier_api.*')."""
        return any(fnmatch.fnmatchcase(tool, pat) for pat in self.allowed_tools)

    def host_allowlisted(self, host: str) -> bool:
        return any(fnmatch.fnmatchcase(host, pat) for pat in self.egress_allowlist)

    def to_dict(self) -> dict:
        return asdict(self)
