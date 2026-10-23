"""Operator and agent endpoints for Phase 6: approvals, token renewal, posture controls."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..gateway.interceptor import ApprovalError, UnknownAgent

router = APIRouter(tags=["response"])


class ResolveIn(BaseModel):
    action: str = Field(pattern="^(approve_once|deny)$")
    by: str = "operator"


def _svc(request: Request):
    return request.app.state.services


@router.get("/approvals")
async def list_approvals(request: Request, status: Optional[str] = None):
    """Pending (default view for operators) or any status. Expired ones are auto-denied first."""
    svc = _svc(request)
    svc.approvals.expire_due()
    return svc.repo.list_approvals(status)


@router.get("/approvals/{approval_id}/status")
async def approval_status(approval_id: str, request: Request):
    """Agent-facing: the status of its paused action, and the result once approved."""
    try:
        return _svc(request).gateway.approval_status(approval_id)
    except ApprovalError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(approval_id: str, body: ResolveIn, request: Request):
    svc = _svc(request)
    try:
        out = svc.gateway.resolve_approval(approval_id, body.action, body.by)
    except ApprovalError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await request.app.state.hub.broadcast({"type": "approval", "data": {"id": approval_id, "status": out["status"]}})
    return out


@router.post("/agents/{agent_id}/token")
async def renew_token(agent_id: str, request: Request):
    """Re-mint a token from the agent's CURRENT posture. Isolated agents get none (403)."""
    try:
        out = _svc(request).gateway.mint_token(agent_id)
    except UnknownAgent as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not out["ok"]:
        raise HTTPException(status_code=403, detail=out["reason"])
    return out


async def _posture(request: Request, agent_id: str, fn_name: str):
    svc = _svc(request)
    try:
        out = getattr(svc.gateway, fn_name)(agent_id)
    except UnknownAgent as e:
        raise HTTPException(status_code=404, detail=str(e))
    await request.app.state.hub.broadcast({"type": "posture", "data": {"agent_id": agent_id, **out}})
    return out


@router.post("/agents/{agent_id}/isolate")
async def isolate(agent_id: str, request: Request):
    """Manual isolation by an operator."""
    return await _posture(request, agent_id, "isolate_agent")


@router.post("/agents/{agent_id}/restore")
async def restore(agent_id: str, request: Request):
    """Lift restrictions: the owner decided it was a false alarm."""
    return await _posture(request, agent_id, "restore_agent")


@router.post("/agents/{agent_id}/resume")
async def resume(agent_id: str, request: Request):
    """Restore AND drop the poisoned inputs; returns `drop_sources` for the agent framework to forget."""
    return await _posture(request, agent_id, "resume_agent")
