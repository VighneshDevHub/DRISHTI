"""The Policy Gateway: every tool call passes through handle_tool_call().

Pipeline (Phase 6):

    [enforce only]  agent isolated?  token valid?                 -> BLOCK before any scoring
    begin step -> live context labels (provenance)
    resolve tool -> classify destination -> build Event
    L1 Role Fit -> L3 Provenance -> L4 Decoys -> L2 Baseline -> L2b Drift
    impact -> noisy-OR fusion + floors -> session risk -> jittered band
    DECIDE
        shadow mode   always ALLOW (record what Warden WOULD do)
        enforce mode  CRITICAL -> BLOCK + isolate agent
                      HIGH     -> BLOCK + restrict agent (token shrinks to its routine)
                      tool outside the token's scope -> BLOCK
                      ELEVATED -> PENDING_APPROVAL (one action waits for a human);
                                  BLOCK if the agent is already restricted
                      otherwise ALLOW
    store event (+ alert with explanation) -> [approval] -> posture change
    run the tool ONLY if allowed -> record what it returned (taint, sensitive reads)

The tool never runs for a blocked or pending action, so nothing it would have returned
(sensitive data, an exfiltration) ever exists. That is how the leak goes to zero.

Phase 7 adds chain/fingerprint and change declarations.
"""
from __future__ import annotations

import ipaddress
import json
import time
from typing import Callable, Optional

from ..config import SENSITIVE_READ_MIN, Settings
from ..contracts.loader import ContractStore
from ..detection.baseline import BaselineStore
from ..detection.decoys import DecoyLens, DecoyRegistry
from ..detection.drift import DriftTracker
from ..detection.provenance_lens import ProvenanceLens
from ..detection.role_fit import RoleFitLens
from ..models.contracts import RoleContract
from ..models.events import Decision, Event, ToolCallRequest
from ..response.approvals import ApprovalQueue
from ..response.orchestrator import Orchestrator
from ..response.policies import ISOLATED, NORMAL, RESTRICTED
from ..risk import explain
from ..risk.engine import apply_floor_bands, at_least, band_for, fuse
from ..risk.impact import impact_factor
from ..risk.jitter import threshold_offset
from ..risk.session import SessionTracker
from ..store.repo import Repo, now_iso
from .mock_tools import MockBackend
from .provenance import ProvenanceTracker
from .token_service import TokenBroker
from .tool_registry import ToolRegistry


class GatewayError(Exception):
    """Base class for errors the API turns into HTTP errors."""


class UnknownAgent(GatewayError):
    pass


class MissingContract(GatewayError):
    pass


class ApprovalError(GatewayError):
    """Approval not found, already resolved, or not allowed in the agent's current state."""


def classify_destination(host: Optional[str], contract: RoleContract) -> str:
    """internal | allowlisted | external | unknown (raw IP literals are 'unknown')."""
    if not host:
        return "internal"
    if contract.host_allowlisted(host):
        return "allowlisted"
    if host.endswith(".internal") or host == "localhost":
        return "internal"
    try:
        ipaddress.ip_address(host)
        return "unknown"
    except ValueError:
        return "external"


class GatewayService:
    def __init__(self, settings: Settings, repo: Repo, registry: ToolRegistry,
                 contracts: ContractStore, backend: MockBackend,
                 decoys: DecoyRegistry, provenance: ProvenanceTracker,
                 baseline: BaselineStore, drift: DriftTracker,
                 broker: TokenBroker, approvals: ApprovalQueue, orchestrator: Orchestrator,
                 clock: Callable[[], float] = time.time):
        self.settings = settings
        self.repo = repo
        self.registry = registry
        self.contracts = contracts
        self.backend = backend
        self.decoys = decoys
        self.provenance = provenance
        self.baseline = baseline
        self.drift = drift
        self.broker = broker
        self.approvals = approvals
        self.orchestrator = orchestrator
        self.clock = clock
        self.session = SessionTracker()
        self.role_fit = RoleFitLens(registry, settings.similarity_tau)
        self.provenance_lens = ProvenanceLens()
        self.decoy_lens = DecoyLens(decoys)

    @property
    def enforcing(self) -> bool:
        return self.settings.mode == "enforce"

    # -- agents and tokens --------------------------------------------------------
    def register_agent(self, agent_id: str, role: str, owner: Optional[str] = None,
                       role_version: Optional[int] = None) -> dict:
        version = role_version or self.contracts.latest_version(role)
        if version is None or self.contracts.get(role, version) is None:
            raise MissingContract(f"no contract for role '{role}' version {version}")
        agent = self.repo.register_agent(agent_id, role, version, owner)
        minted = self.mint_token(agent_id)
        return {**agent, "token": minted.get("token"), "token_expires_in": minted.get("expires_in")}

    def mint_token(self, agent_id: str) -> dict:
        """(Re)issue a token from the agent's CURRENT posture. A restricted agent gets a
        restricted token; an isolated agent gets none."""
        if self.repo.get_agent(agent_id) is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        rec = self.orchestrator.mint(agent_id)
        if rec is None:
            return {"ok": False, "reason": "agent_isolated"}
        return {"ok": True, "token": rec.token, "expires_in": int(rec.expires_at - rec.issued_at),
                "scopes": sorted(rec.scopes)}

    # -- the pipeline ---------------------------------------------------------------
    def handle_tool_call(self, req: ToolCallRequest) -> Decision:
        agent = self.repo.get_agent(req.agent_id)
        if agent is None:
            raise UnknownAgent(f"agent '{req.agent_id}' is not registered")
        contract = self.contracts.get(agent["role"], agent["role_version"])
        if contract is None:
            raise MissingContract(f"no contract for {agent['role']} v{agent['role_version']}")

        token_rec = None
        if self.enforcing:
            self.approvals.expire_due()
            if agent["status"] == ISOLATED:
                return self._deny_unscored(req, agent, contract, "agent_isolated")
            ok, reason, token_rec = self.broker.validate(req.token, req.agent_id)
            if not ok:
                return self._deny_unscored(req, agent, contract, reason)

        step = self.provenance.begin(req.agent_id)
        labels = self.provenance.context_for(req.agent_id, step, req.context_labels)
        sensitive_ctx = self.provenance.sensitive_recent(req.agent_id, step)
        event = self._build_event(req, agent, contract, labels)

        # ---- detection lenses (Phase 7 adds chain/fingerprint) --------------------------
        role = self.role_fit.evaluate(event, contract)
        prov = self.provenance_lens.evaluate(event, labels, justified=(role.score == 0.0),
                                             sensitive_in_context=sensitive_ctx)
        decoy = self.decoy_lens.evaluate(event, req.args)
        lens_results = {"role": role, "provenance": prov, "decoy": decoy}
        if self.settings.enable_baseline:
            lens_results["baseline"] = self.baseline.evaluate(event, contract)
        if self.settings.enable_drift:
            lens_results["drift"] = self.drift.evaluate(event, contract)

        impact = impact_factor(event.sensitivity, event.destination_class, event.is_irreversible)
        fusion = fuse(lens_results, impact)
        if self.settings.enable_session:
            sess = self.session.apply(req.agent_id, fusion.risk)
        else:
            sess = {"event_risk": fusion.risk, "session": 0.0, "effective_risk": fusion.risk,
                    "raised_by_session": False}
        risk = sess["effective_risk"]
        offset = threshold_offset(req.agent_id, self.settings.jitter_secret, self.settings.jitter_amplitude)
        band, action = band_for(risk, offset)
        band, action = apply_floor_bands(band, fusion.floors)

        # ---- DECIDE ---------------------------------------------------------------------
        decision, block_reason = "ALLOW", None
        if self.enforcing:
            if band == "CRITICAL":
                decision, block_reason = "BLOCK", "policy_critical"
            elif band == "HIGH":
                decision, block_reason = "BLOCK", "policy_high"
            elif not self.broker.allows(token_rec, req.tool):
                decision, block_reason = "BLOCK", "scope_denied"
            elif band == "ELEVATED":
                # Humans are asked about agents in good standing. An agent already under
                # restriction gets no benefit of the doubt: risky actions are simply refused.
                if agent["status"] == RESTRICTED:
                    decision, block_reason = "BLOCK", "restricted_posture"
                else:
                    decision = "PENDING_APPROVAL"

        lens_dict = {k: v.to_dict() for k, v in lens_results.items()}
        lens_dict["impact"] = round(impact, 3)
        lens_dict["fusion"] = {"combined": fusion.combined, "contributions": fusion.contributions,
                               "floors": [{"name": n, "minimum": m, "reason": r} for n, m, r in fusion.floors]}
        lens_dict["session"] = sess

        event_id = self.repo.insert_event(event, lens_dict, risk, band, decision, block_reason)

        approval_id = None
        if decision == "PENDING_APPROVAL":
            approval_id = self.approvals.create(req.agent_id, event_id,
                                                {"agent_id": req.agent_id, "tool": req.tool, "args": req.args})

        # Reasons: conclusive floors first, then lenses by weighted contribution.
        reasons = [r for _, _, r in fusion.floors]
        for name, _ in fusion.contributions:
            res = lens_results[name]
            if res.score > 0 and res.reason not in reasons:
                reasons.append(res.reason)

        # ---- response: change the agent's standing ----------------------------------------
        sources = sorted({l.source for l in labels if l.trust in ("untrusted", "peer_agent")})
        alert_id = None
        posture = agent["status"]
        enforcement = {"mode": self.settings.mode, "decision": decision, "block_reason": block_reason,
                       "approval_id": approval_id, "posture_after": posture}
        if at_least(band, "WATCH"):
            if self.enforcing and band in ("HIGH", "CRITICAL"):
                enforcement["posture_after"] = ISOLATED if band == "CRITICAL" else RESTRICTED
            recent = self.repo.list_events(req.agent_id, limit=8)        # includes this event
            explanation = explain.build(event, lens_results, fusion, impact, sess, band, action,
                                        recent, self.settings.mode, offset, enforcement)
            alert_id = self.repo.insert_alert(req.agent_id, event_id, risk, band, action,
                                              reasons, lens_dict, explanation, decision)
        if self.enforcing and band == "CRITICAL":
            posture = self.orchestrator.isolate(req.agent_id, alert_id, sources)["posture"]
        elif self.enforcing and band == "HIGH":
            posture = self.orchestrator.restrict(req.agent_id, alert_id, sources)["posture"]

        # Learn only from actions that were judged LOW AND actually allowed.
        learn = (band == "LOW" or not self.settings.learn_gate) and decision == "ALLOW"
        self.baseline.observe(event, contract, learn)
        if learn:
            self.drift.learn(event, contract)

        # ---- act ----------------------------------------------------------------------------
        result = None
        if decision == "ALLOW":
            result = self.backend.execute(req.tool, req.args)
            self._record_outputs(req.agent_id, req.tool, event.resource, event.sensitivity,
                                 event.sink_type, result, step)

        if decision == "ALLOW":
            message = "within role contract" if alert_id is None else f"{band}: {reasons[0]}"
        elif decision == "PENDING_APPROVAL":
            message = f"PAUSED for approval {approval_id}: {reasons[0]}"
        else:
            message = f"BLOCKED ({block_reason}): {reasons[0] if reasons else block_reason}"
        ev = event.to_dict()
        ev.update(risk=risk, band=band, lens=lens_dict, decision=decision, block_reason=block_reason,
                  posture=posture)
        return Decision(
            decision=decision, mode=self.settings.mode, risk=risk, band=band,
            shadow_action=action, message=message, event_id=event_id, alert_id=alert_id,
            lens=lens_dict, result=result, event=ev, block_reason=block_reason,
            approval_id=approval_id, posture=posture,
        )

    # -- approvals -------------------------------------------------------------------------
    def resolve_approval(self, approval_id: str, action: str, by: str = "operator") -> dict:
        """action: 'approve_once' (run the paused action) or 'deny'."""
        if action not in ("approve_once", "deny"):
            raise ApprovalError("action must be 'approve_once' or 'deny'")
        self.approvals.expire_due()
        ap = self.repo.get_approval(approval_id)
        if ap is None:
            raise ApprovalError(f"approval '{approval_id}' not found")
        if ap["status"] != "pending":
            raise ApprovalError(f"approval '{approval_id}' is already {ap['status']}")
        now = self.clock()
        if action == "deny":
            self.repo.resolve_approval(approval_id, "denied", by, now)
            self.repo.update_event_decision(ap["event_id"], "DENIED_BY_HUMAN")
            return {"id": approval_id, "status": "denied"}
        agent = self.repo.get_agent(ap["agent_id"])
        if agent["status"] == ISOLATED:
            raise ApprovalError("agent is isolated: restore it before approving its actions")
        req = ap["request"]
        result = self.backend.execute(req["tool"], req["args"])
        r = self.registry.resolve(req["tool"], req["args"])
        self._record_outputs(ap["agent_id"], req["tool"], r.resource, r.sensitivity, r.spec.sink_type,
                             result, self.provenance.current_step(ap["agent_id"]))
        self.repo.resolve_approval(approval_id, "approved", by, now, result)
        self.repo.update_event_decision(ap["event_id"], "ALLOWED_AFTER_APPROVAL")
        return {"id": approval_id, "status": "approved", "result": result}

    def approval_status(self, approval_id: str) -> dict:
        """What the AGENT may learn about its paused action: the status, and the result once approved."""
        self.approvals.expire_due()
        ap = self.repo.get_approval(approval_id)
        if ap is None:
            raise ApprovalError(f"approval '{approval_id}' not found")
        out = {"id": approval_id, "status": ap["status"]}
        if ap["status"] == "approved":
            out["result"] = ap["result"]
        return out

    # -- operator controls ---------------------------------------------------------------------
    def isolate_agent(self, agent_id: str) -> dict:
        if self.repo.get_agent(agent_id) is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        return self.orchestrator.isolate(agent_id, None, [])

    def restore_agent(self, agent_id: str) -> dict:
        if self.repo.get_agent(agent_id) is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        self.session.reset(agent_id)
        return self.orchestrator.restore(agent_id)

    def resume_agent(self, agent_id: str) -> dict:
        if self.repo.get_agent(agent_id) is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        self.session.reset(agent_id)
        return self.orchestrator.resume(agent_id)

    def behavior(self, agent_id: str) -> dict:
        """What Warden has learned about an agent (for the dashboard)."""
        agent = self.repo.get_agent(agent_id)
        if agent is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        return {"agent_id": agent_id, "posture": agent["status"],
                "baseline": self.baseline.summary(agent_id), "drift": self.drift.summary(agent_id)}

    def register_context(self, agent_id: str, source: str, trust: str) -> dict:
        """Explicit ingestion path: content the agent read OUTSIDE the gateway
        (inbound email, web page, another agent's message)."""
        if self.repo.get_agent(agent_id) is None:
            raise UnknownAgent(f"agent '{agent_id}' is not registered")
        self.provenance.add(agent_id, source, trust)
        return {"agent_id": agent_id, "source": source, "trust": trust}

    # -- internals ---------------------------------------------------------------------------
    def _record_outputs(self, agent_id: str, tool: str, resource: Optional[str], sensitivity: float,
                        sink_type: str, result: dict, step: int) -> None:
        """After a tool runs: remember tainted output and sensitive reads."""
        if not result.get("ok"):
            return
        spec = self.registry.get(tool)
        source = f"{tool}:{resource or ''}"
        if spec is not None and spec.output_trust in ("untrusted", "peer_agent"):
            self.provenance.add(agent_id, source, spec.output_trust, step)
        if sensitivity >= SENSITIVE_READ_MIN and sink_type != "egress":
            self.provenance.note_sensitive_read(agent_id, source, step)

    def _deny_unscored(self, req: ToolCallRequest, agent: dict, contract: RoleContract, reason: str) -> Decision:
        """Refused before any analysis: isolated agent, or no usable token. Still audited."""
        event = self._build_event(req, agent, contract, [])
        event_id = self.repo.insert_event(event, {}, 0.0, "LOW", "BLOCK", reason)
        ev = event.to_dict()
        ev.update(risk=0.0, band="LOW", lens={}, decision="BLOCK", block_reason=reason)
        return Decision(decision="BLOCK", mode=self.settings.mode, risk=0.0, band="LOW",
                        shadow_action="BLOCK", message=f"BLOCKED ({reason})", event_id=event_id,
                        event=ev, block_reason=reason, posture=agent["status"])

    def _build_event(self, req: ToolCallRequest, agent: dict, contract: RoleContract,
                     labels: list) -> Event:
        r = self.registry.resolve(req.tool, req.args)
        bytes_out = 0
        if r.spec.sink_type == "egress":
            bytes_out = len(json.dumps(req.args.get("body", "")).encode())
        return Event(
            ts=now_iso(),
            agent_id=req.agent_id,
            role=agent["role"],
            role_version=agent["role_version"],
            tool=req.tool,
            resource=r.resource,
            resource_class=r.resource_class,
            sensitivity=r.sensitivity,
            sink_type=r.spec.sink_type,
            destination=r.destination,
            destination_class=classify_destination(r.destination, contract),
            bytes_out=bytes_out,
            is_irreversible=r.spec.irreversible,
            registered_tool=r.spec.registered,
            context_labels=labels,
            chain=req.chain,
            fingerprint=req.fingerprint,
        )
