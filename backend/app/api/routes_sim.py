"""Prototype/dev helpers: seed documents and read what leaked.

These exist ONLY because the tool backends are simulated. In production the
equivalents are real systems; remove this router (or protect it) there.
"""
from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/sim", tags=["simulation (dev only)"])


class DocIn(BaseModel):
    path: str
    content: str


@router.post("/docs")
async def seed_doc(body: DocIn, request: Request):
    request.app.state.services.backend.docs[body.path] = body.content
    return {"ok": True, "path": body.path}


@router.get("/outbox")
async def outbox(request: Request):
    box = request.app.state.services.backend.outbox
    return {"messages": len(box), "bytes": sum(len(m["body"]) for m in box), "items": box[-20:]}


@router.post("/reset-outbox")
async def reset_outbox(request: Request):
    request.app.state.services.backend.outbox.clear()
    return {"ok": True}


def _run_scenario(scenario_id: str, request: Request) -> dict:
    project_root = str(Path(__file__).resolve().parents[3])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from simulator.agents.procurement import ProcurementAgent
    from simulator.client import WardenClient
    from simulator.scenarios import s1_injection, s4_slow_drift, s5_mimicry

    svc = request.app.state.services
    client = WardenClient(service=svc)
    agent_id = f"demo-{scenario_id}-{uuid4().hex[:8]}"

    if scenario_id == "normal":
        agent = ProcurementAgent(agent_id, client, seed=7)
        agent.register()
        steps = [
            {
                "label": "normal procurement action",
                "tool": result["event"]["tool"],
                "risk": result["risk"],
                "band": result["band"],
                "decision": result["decision"],
                "block_reason": result.get("block_reason"),
            }
            for result in agent.run(8)
        ]
        summary = {"steps": steps, "agent_id": agent_id}
    elif scenario_id == "injection":
        summary = s1_injection.run(
            client, variant="plain", history=5, agent_id=agent_id, legit_after=4
        )
    elif scenario_id == "drift":
        summary = s4_slow_drift.run(
            client, history=30, repeats=3, normal_between=2, agent_id=agent_id
        )
    elif scenario_id == "mimicry":
        summary = s5_mimicry.run(
            client, history=15, normal_between=3, agent_id=agent_id, after=6
        )
    else:
        raise HTTPException(status_code=404, detail="unknown scenario")

    events = svc.repo.list_events(agent_id, limit=500)
    return {
        "scenario": scenario_id,
        "agent_id": agent_id,
        "mode": svc.settings.mode,
        "summary": summary,
        "events": events,
    }


@router.post("/scenarios/{scenario_id}/run")
def _run_locked_scenario(scenario_id: str, request: Request) -> dict:
    with request.app.state.scenario_lock:
        return _run_scenario(scenario_id, request)


async def run_scenario(scenario_id: str, request: Request):
    """Run one of the fixed, development-only scenarios against the active backend state."""
    if scenario_id not in {"normal", "injection", "drift", "mimicry"}:
        raise HTTPException(status_code=404, detail="unknown scenario")
    result = await run_in_threadpool(_run_locked_scenario, scenario_id, request)
    event_ids = {event["id"] for event in result["events"]}
    for event in reversed(result["events"]):
        await request.app.state.hub.broadcast({"type": "event", "data": event})
    alerts = request.app.state.services.repo.list_alerts(limit=500)
    for alert in reversed(alerts):
        if alert["event_id"] in event_ids:
            await request.app.state.hub.broadcast({"type": "alert", "data": alert})
    return result
