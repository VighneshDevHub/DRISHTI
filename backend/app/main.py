"""FastAPI entry point.

Run:  cd backend && uvicorn app.main:create_app --factory --reload --port 8000
(`make api` does this for you.)
"""
from __future__ import annotations

import threading
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_agents, routes_contracts, routes_events, routes_gateway, routes_response, routes_sim, ws
from .config import Settings
from .services import build_services


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Agent Warden", version="0.6.0",
                  description="Behavioral identity layer for autonomous AI agents")
    app.state.services = build_services(settings)
    app.state.hub = ws.Hub()
    app.state.scenario_lock = threading.Lock()

    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])

    for module in (routes_gateway, routes_agents, routes_events, routes_contracts, routes_response, routes_sim, ws):
        app.include_router(module.router)

    @app.get("/health")
    async def health():
        svc = app.state.services
        return {"status": "ok", "service": "agent-warden", "version": app.version,
                "mode": settings.mode, "roles": svc.contracts.roles(),
                "tools": len(svc.registry.all())}

    return app
