"""Loads, validates and versions role contracts; builds blast-radius reports."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from ..gateway.tool_registry import ToolRegistry
from ..models.contracts import ContractError, RoleContract


class ContractStore:
    """In-memory store: role -> {version: RoleContract}."""

    def __init__(self):
        self._by_role: dict = {}

    def register(self, contract: RoleContract) -> None:
        versions = self._by_role.setdefault(contract.role, {})
        if versions and contract.version <= max(versions):
            raise ContractError(
                f"{contract.role}: version {contract.version} must be greater than "
                f"current {max(versions)} (contracts are append-only)"
            )
        versions[contract.version] = contract

    def load_dir(self, path: Path) -> int:
        count = 0
        for f in sorted(Path(path).glob("*.yaml")):
            data = yaml.safe_load(f.read_text())
            try:
                self.register(RoleContract.from_dict(data))
            except ContractError as e:
                raise ContractError(f"{f.name}: {e}") from e
            count += 1
        return count

    def roles(self) -> list:
        return sorted(self._by_role)

    def latest_version(self, role: str) -> Optional[int]:
        v = self._by_role.get(role)
        return max(v) if v else None

    def get(self, role: str, version: Optional[int] = None) -> Optional[RoleContract]:
        versions = self._by_role.get(role)
        if not versions:
            return None
        return versions.get(version if version is not None else max(versions))


def blast_radius(contract: RoleContract, registry: ToolRegistry) -> dict:
    """What can an agent with this contract actually do if it is hijacked?

    Returns the capabilities plus plain-language warnings about over-broad
    contracts. This is the 'least privilege recommender' seed.
    """
    tools = registry.matching(contract.allowed_tools)
    warnings = []
    if any(p == "*" for p in contract.allowed_tools):
        warnings.append("allowed_tools contains '*': every tool is permitted")
    if any("*" in p and p != "*" for p in contract.allowed_tools):
        warnings.append("allowed_tools uses wildcards: new tools are auto-permitted")
    egress_tools = [t.name for t in tools if t.sink_type == "egress"]
    if egress_tools and not contract.egress_allowlist:
        warnings.append("egress tools allowed but egress_allowlist is empty")
    if any(h == "*" for h in contract.egress_allowlist):
        warnings.append("egress_allowlist contains '*': any destination is permitted")
    if contract.budgets.actions_per_hour == 0:
        warnings.append("no actions_per_hour budget set")
    max_sens = max((t.sensitivity for t in tools), default=0.0)
    if max_sens > contract.sensitivity_ceiling_value:
        warnings.append("an allowed tool is more sensitive than the contract's own ceiling")
    return {
        "role": contract.role,
        "version": contract.version,
        "tools": sorted(t.name for t in tools),
        "resource_classes": sorted(contract.allowed_resource_classes),
        "max_sensitivity": max_sens,
        "can_egress": bool(egress_tools),
        "egress_destinations": list(contract.egress_allowlist),
        "warnings": warnings,
    }
