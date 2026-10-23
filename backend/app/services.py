"""Wires the pieces together. One place that builds the whole object graph."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from .config import Settings
from .contracts.loader import ContractStore
from .detection.baseline import BaselineStore
from .detection.decoys import DecoyRegistry
from .detection.drift import DriftTracker
from .gateway.interceptor import GatewayService
from .gateway.mock_tools import MockBackend
from .gateway.provenance import ProvenanceTracker
from .gateway.token_service import TokenBroker
from .gateway.tool_registry import ToolRegistry
from .response.approvals import ApprovalQueue
from .response.checkpoints import CheckpointStore
from .response.orchestrator import Orchestrator
from .store.repo import Repo


@dataclass
class Services:
    settings: Settings
    repo: Repo
    registry: ToolRegistry
    contracts: ContractStore
    backend: MockBackend
    decoys: DecoyRegistry
    provenance: ProvenanceTracker
    baseline: BaselineStore
    drift: DriftTracker
    broker: TokenBroker
    approvals: ApprovalQueue
    checkpoints: CheckpointStore
    orchestrator: Orchestrator
    gateway: GatewayService


def build_services(settings: Optional[Settings] = None,
                   clock: Callable[[], float] = time.time) -> Services:
    """`clock` is injectable so tests can move time (token expiry, approval timeout)."""
    settings = settings or Settings()
    repo = Repo(settings.db_path)
    registry = ToolRegistry()
    contracts = ContractStore()
    contracts.load_dir(settings.contracts_dir)
    backend = MockBackend()
    decoys = DecoyRegistry()
    decoys.seed_backend(backend)          # plant decoys + watermark real data
    provenance = ProvenanceTracker()
    baseline = BaselineStore(registry)
    drift = DriftTracker(registry)
    broker = TokenBroker(clock, settings.token_ttl)
    approvals = ApprovalQueue(repo, clock, settings.approval_ttl)
    checkpoints = CheckpointStore()
    orchestrator = Orchestrator(repo, broker, registry, contracts, drift, provenance, checkpoints)
    gateway = GatewayService(settings, repo, registry, contracts, backend, decoys, provenance,
                             baseline, drift, broker, approvals, orchestrator, clock)
    return Services(settings, repo, registry, contracts, backend, decoys, provenance, baseline,
                    drift, broker, approvals, checkpoints, orchestrator, gateway)
