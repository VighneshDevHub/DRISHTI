"""Core data shapes that flow through Agent Warden.

These are plain dataclasses on purpose: the detection engine has zero
third-party dependencies, so it is easy to unit-test and reason about.
The FastAPI layer (api/) uses pydantic only at the HTTP boundary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ContextLabel:
    """Where a piece of the agent's context came from (used from Phase 3)."""
    source: str
    trust: str  # owner | system | peer_agent | untrusted
    age_steps: int = 0


@dataclass
class ChainInfo:
    """Delegation envelope (used from Phase 7)."""
    depth: int = 0
    origin: Optional[str] = None
    ceiling: list = field(default_factory=list)
    inherited_taint: list = field(default_factory=list)


@dataclass
class Fingerprint:
    """How the token is being used (used from Phase 7)."""
    workload_id: Optional[str] = None
    net_origin: Optional[str] = None
    inter_call_ms: Optional[int] = None


@dataclass
class ToolCallRequest:
    """What an agent sends to the gateway."""
    agent_id: str
    tool: str
    args: dict = field(default_factory=dict)
    context_labels: list = field(default_factory=list)  # list[ContextLabel]
    chain: ChainInfo = field(default_factory=ChainInfo)
    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    token: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ToolCallRequest":
        return cls(
            agent_id=d["agent_id"],
            tool=d["tool"],
            args=d.get("args") or {},
            context_labels=[ContextLabel(**c) for c in d.get("context_labels", [])],
            chain=ChainInfo(**d["chain"]) if d.get("chain") else ChainInfo(),
            fingerprint=Fingerprint(**d["fingerprint"]) if d.get("fingerprint") else Fingerprint(),
            token=d.get("token"),
        )


@dataclass
class Event:
    """A normalised, security-meaningful record of one tool call."""
    ts: str
    agent_id: str
    role: str
    role_version: int
    tool: str
    resource: Optional[str]
    resource_class: str
    sensitivity: float
    sink_type: str  # benign | write | read_sensitive | egress | unknown_tool
    destination: Optional[str]
    destination_class: str  # internal | allowlisted | external | unknown
    bytes_out: int
    is_irreversible: bool
    registered_tool: bool = True
    context_labels: list = field(default_factory=list)
    chain: ChainInfo = field(default_factory=ChainInfo)
    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LensResult:
    """Every detection lens returns this, so explanations are automatic."""
    name: str
    score: float  # 0..1
    reason: str
    evidence: list = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    """What the gateway returns to the agent."""
    decision: str  # ALLOW | BLOCK | PENDING_APPROVAL   (shadow mode always ALLOW)
    mode: str  # shadow | enforce
    risk: float
    band: str
    shadow_action: str  # what Warden WOULD do once enforcement exists
    message: str
    event_id: str
    alert_id: Optional[str] = None
    lens: dict = field(default_factory=dict)
    result: Optional[dict] = None
    event: dict = field(default_factory=dict)
    block_reason: Optional[str] = None    # machine-readable: policy_critical, policy_high, scope_denied, token_*, agent_isolated
    approval_id: Optional[str] = None     # set when decision == PENDING_APPROVAL
    posture: str = "normal"               # the agent's standing state AFTER this decision

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def agent_view(self) -> dict[str, Any]:
        """What a (possibly compromised) agent is allowed to see: a bare verdict.
        No score, no lens detail, no reasons: nothing to probe thresholds with."""
        if self.decision == "PENDING_APPROVAL":
            message = "awaiting approval"
        elif self.decision == "BLOCK":
            message = "blocked by policy"
        else:
            message = "ok" if self.band == "LOW" else "flagged for review"
        view = {"decision": self.decision, "mode": self.mode, "event_id": self.event_id,
                "message": message, "result": self.result}
        if self.approval_id:
            view["approval_id"] = self.approval_id            # so the agent knows what to wait for
        if self.block_reason in ("token_expired", "token_revoked", "token_invalid", "token_missing"):
            view["block_reason"] = self.block_reason          # lets a well-behaved client renew its token
        return view
