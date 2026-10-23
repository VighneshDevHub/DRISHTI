"""WebSocket hub: pushes live events/alerts to every connected dashboard."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class Hub:
    def __init__(self):
        self.clients: set = set()

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


@router.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    hub: Hub = ws.app.state.hub
    hub.clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # we only push; reading detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(ws)
