"""POST /gateway/tool-call - the one endpoint every agent action goes through."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..gateway.interceptor import MissingContract, UnknownAgent
from ..models.events import ToolCallRequest

router = APIRouter(tags=["gateway"])


class ContextLabelIn(BaseModel):
    source: str
    trust: str = Field(pattern="^(owner|system|peer_agent|untrusted)$")
    age_steps: int = 0


class ToolCallIn(BaseModel):
    agent_id: str
    tool: str
    args: dict = {}
    context_labels: list[ContextLabelIn] = []
    token: Optional[str] = None


@router.post("/gateway/tool-call")
async def tool_call(body: ToolCallIn, request: Request):
    svc = request.app.state.services
    req = ToolCallRequest.from_dict(body.model_dump())
    try:
        decision = svc.gateway.handle_tool_call(req)
    except UnknownAgent as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MissingContract as e:
        raise HTTPException(status_code=422, detail=str(e))

    hub = request.app.state.hub
    await hub.broadcast({"type": "event", "data": decision.event})
    if decision.approval_id:
        await hub.broadcast({"type": "approval", "data": {"id": decision.approval_id, "status": "pending",
                                                          "agent_id": req.agent_id, "tool": req.tool}})
    if decision.posture != "normal":
        await hub.broadcast({"type": "posture", "data": {"agent_id": req.agent_id, "posture": decision.posture}})
    if decision.alert_id:
        await hub.broadcast({"type": "alert", "data": {
            "id": decision.alert_id, "agent_id": req.agent_id, "risk": decision.risk,
            "band": decision.band, "shadow_action": decision.shadow_action,
            "message": decision.message, "event_id": decision.event_id, "decision": decision.decision}})
    # Operators see everything over the websocket above; the AGENT sees a bare verdict
    # unless expose_scores is on (prototype default, so the simulator can print scores).
    return decision.to_dict() if svc.settings.expose_scores else decision.agent_view()


class ContextIn(BaseModel):
    agent_id: str
    source: str
    trust: str = Field(pattern="^(owner|system|peer_agent|untrusted)$")


@router.post("/gateway/context")
async def register_context(body: ContextIn, request: Request):
    """Tell Warden an agent ingested content outside the gateway (email, web page, peer message)."""
    svc = request.app.state.services
    try:
        return svc.gateway.register_context(body.agent_id, body.source, body.trust)
    except UnknownAgent as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents/{agent_id}/context")
async def current_context(agent_id: str, request: Request):
    """The live provenance labels for an agent (what it has recently read)."""
    svc = request.app.state.services
    if svc.repo.get_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    step = svc.provenance._step.get(agent_id, 0) + 1
    return [l.__dict__ for l in svc.provenance.context_for(agent_id, step)]
