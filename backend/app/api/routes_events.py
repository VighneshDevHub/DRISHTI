from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["events"])


@router.get("/events")
async def events(request: Request, agent_id: Optional[str] = None, limit: int = 100):
    return request.app.state.services.repo.list_events(agent_id, min(limit, 500))


@router.get("/events/{event_id}")
async def event_detail(event_id: str, request: Request):
    try:
        event = request.app.state.services.repo.get_event(event_id)
    except (IndexError, ValueError):
        event = None
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event


@router.get("/alerts")
async def alerts(request: Request, limit: int = 100):
    return request.app.state.services.repo.list_alerts(min(limit, 500))


@router.get("/alerts/{alert_id}")
async def alert_detail(alert_id: str, request: Request):
    """One alert with its full explanation: reasons, measured effect of each, timeline, OWASP tags."""
    alert = request.app.state.services.repo.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return alert
