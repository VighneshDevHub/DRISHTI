from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..gateway.interceptor import MissingContract, UnknownAgent

router = APIRouter(tags=["agents"])


class AgentIn(BaseModel):
    agent_id: str
    role: str
    owner: Optional[str] = None
    role_version: Optional[int] = None


@router.post("/agents")
async def register_agent(body: AgentIn, request: Request):
    svc = request.app.state.services
    try:
        return svc.gateway.register_agent(body.agent_id, body.role, body.owner, body.role_version)
    except MissingContract as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/agents")
async def list_agents(request: Request):
    return request.app.state.services.repo.list_agents()


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    repo = request.app.state.services.repo
    agent = repo.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return {**agent, "recent_events": repo.list_events(agent_id, limit=50)}


@router.get("/agents/{agent_id}/behavior")
async def agent_behavior(agent_id: str, request: Request):
    """What Warden has learned about this agent: top transitions, anchor state, novel capabilities."""
    try:
        return request.app.state.services.gateway.behavior(agent_id)
    except UnknownAgent:
        raise HTTPException(status_code=404, detail="agent not found")
