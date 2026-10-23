"""Thin SDK agents use to talk to Warden.

Two transports, same interface:
  * in-process  (WardenClient(service=...))  - no server needed; used by tests
  * HTTP        (WardenClient(base_url=...)) - talks to the running FastAPI app
Stdlib only (urllib), so the simulator has no dependencies.

The client behaves like a well-written agent runtime: it keeps the token Warden
issued at registration, attaches it to every call, and if the token has expired or
been replaced it asks for a fresh one ONCE and retries. It cannot renew its way
out of a restriction: the broker mints from the agent's current posture.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

RENEWABLE = ("token_expired", "token_revoked", "token_invalid", "token_missing")


class WardenClient:
    def __init__(self, base_url: Optional[str] = None, service=None):
        if (base_url is None) == (service is None):
            raise ValueError("provide exactly one of base_url or service")
        self.base_url = base_url.rstrip("/") if base_url else None
        self.service = service  # app.services.Services
        self._tokens: dict = {}

    # -- agents -----------------------------------------------------------------
    def register_agent(self, agent_id: str, role: str, owner: Optional[str] = None) -> dict:
        if self.service:
            agent = self.service.gateway.register_agent(agent_id, role, owner)
        else:
            agent = self._post("/agents", {"agent_id": agent_id, "role": role, "owner": owner})
        if agent.get("token"):
            self._tokens[agent_id] = agent["token"]
        return agent

    def renew_token(self, agent_id: str) -> bool:
        if self.service:
            out = self.service.gateway.mint_token(agent_id)
        else:
            try:
                out = self._post(f"/agents/{agent_id}/token", {})
            except RuntimeError:
                return False
        if out.get("ok") and out.get("token"):
            self._tokens[agent_id] = out["token"]
            return True
        return False

    # -- tool calls ----------------------------------------------------------------
    def call_tool(self, agent_id: str, tool: str, args: Optional[dict] = None,
                  context_labels: Optional[list] = None) -> dict:
        d = self._send(agent_id, tool, args, context_labels)
        reason = d.get("block_reason") or (d.get("event") or {}).get("block_reason")
        if d.get("decision") == "BLOCK" and reason in RENEWABLE and self.renew_token(agent_id):
            d = self._send(agent_id, tool, args, context_labels)
        return d

    def _send(self, agent_id, tool, args, context_labels) -> dict:
        payload = {"agent_id": agent_id, "tool": tool, "args": args or {},
                   "context_labels": context_labels or [], "token": self._tokens.get(agent_id)}
        if self.service:
            from app.models.events import ToolCallRequest
            return self.service.gateway.handle_tool_call(ToolCallRequest.from_dict(payload)).to_dict()
        return self._post("/gateway/tool-call", payload)

    # -- operator actions (what a human or the dashboard does) -----------------------
    def resolve_approval(self, approval_id: str, action: str, by: str = "operator") -> dict:
        if self.service:
            return self.service.gateway.resolve_approval(approval_id, action, by)
        return self._post(f"/approvals/{approval_id}/resolve", {"action": action, "by": by})

    def approval_status(self, approval_id: str) -> dict:
        if self.service:
            return self.service.gateway.approval_status(approval_id)
        return self._get(f"/approvals/{approval_id}/status")

    def restore(self, agent_id: str) -> dict:
        if self.service:
            return self.service.gateway.restore_agent(agent_id)
        return self._post(f"/agents/{agent_id}/restore", {})

    def resume(self, agent_id: str) -> dict:
        if self.service:
            return self.service.gateway.resume_agent(agent_id)
        return self._post(f"/agents/{agent_id}/resume", {})

    # -- simulation helpers (dev only) --------------------------------------------
    def seed_doc(self, path: str, content: str) -> None:
        if self.service:
            self.service.backend.docs[path] = content
        else:
            self._post("/sim/docs", {"path": path, "content": content})

    def outbox(self) -> dict:
        """What escaped the organisation: {'messages': n, 'bytes': n, 'items': [...]}."""
        if self.service:
            box = self.service.backend.outbox
            return {"messages": len(box), "bytes": sum(len(m["body"]) for m in box), "items": list(box)}
        return self._get("/sim/outbox")

    def reset_outbox(self) -> None:
        if self.service:
            self.service.backend.outbox.clear()
        else:
            self._post("/sim/reset-outbox", {})

    # -- http -----------------------------------------------------------------
    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=10) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(self.base_url + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{path} -> HTTP {e.code}: {e.read().decode()}") from e
