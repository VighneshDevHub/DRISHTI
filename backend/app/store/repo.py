"""All SQL lives here. The rest of the code never writes a query."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from ..models.events import Event
from .db import Database


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def event_id(seq: int) -> str:
    return f"evt_{seq:06d}"


def alert_id(seq: int) -> str:
    return f"alr_{seq:04d}"


def approval_id(seq: int) -> str:
    return f"apr_{seq:04d}"


class Repo:
    def __init__(self, path: str = ":memory:"):
        self.db = Database(path)

    # -- agents ---------------------------------------------------------------
    def register_agent(self, agent_id: str, role: str, role_version: int,
                       owner: Optional[str] = None) -> dict:
        with self.db.lock:
            self.db.conn.execute(
                "INSERT OR REPLACE INTO agents(agent_id, role, role_version, owner, status, created_at) "
                "VALUES (?,?,?,?, COALESCE((SELECT status FROM agents WHERE agent_id=?),'normal'), "
                "COALESCE((SELECT created_at FROM agents WHERE agent_id=?),?))",
                (agent_id, role, role_version, owner, agent_id, agent_id, now_iso()),
            )
            self.db.conn.commit()
        return self.get_agent(agent_id)

    def get_agent(self, agent_id: str) -> Optional[dict]:
        with self.db.lock:
            row = self.db.conn.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        return dict(row) if row else None

    def list_agents(self) -> list:
        """Agents plus live stats (event count, last and max risk)."""
        sql = """
        SELECT a.*,
          (SELECT COUNT(*) FROM events e WHERE e.agent_id=a.agent_id) AS event_count,
          COALESCE((SELECT risk FROM events e WHERE e.agent_id=a.agent_id ORDER BY seq DESC LIMIT 1),0) AS last_risk,
          COALESCE((SELECT MAX(risk) FROM events e WHERE e.agent_id=a.agent_id),0) AS max_risk
        FROM agents a ORDER BY a.agent_id
        """
        with self.db.lock:
            return [dict(r) for r in self.db.conn.execute(sql).fetchall()]

    # -- events ---------------------------------------------------------------
    def insert_event(self, event: Event, lens: dict, risk: float, band: str,
                     decision: str = "ALLOW", block_reason: Optional[str] = None) -> str:
        with self.db.lock:
            cur = self.db.conn.execute(
                "INSERT INTO events(ts, agent_id, tool, resource, resource_class, sensitivity, destination, "
                "destination_class, bytes_out, risk, band, lens_json, event_json, decision, block_reason) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (event.ts, event.agent_id, event.tool, event.resource, event.resource_class,
                 event.sensitivity, event.destination, event.destination_class, event.bytes_out,
                 risk, band, json.dumps(lens), "{}", decision, block_reason),
            )
            eid = event_id(cur.lastrowid)
            event.id = eid
            self.db.conn.execute("UPDATE events SET event_json=? WHERE seq=?",
                                 (json.dumps(event.to_dict()), cur.lastrowid))
            self.db.conn.commit()
        return eid

    @staticmethod
    def _event_row(row) -> dict:
        d = json.loads(row["event_json"])
        d.update(risk=row["risk"], band=row["band"], lens=json.loads(row["lens_json"]),
                 decision=row["decision"], block_reason=row["block_reason"])
        return d

    def update_event_decision(self, event_id_: str, decision: str) -> None:
        with self.db.lock:
            self.db.conn.execute("UPDATE events SET decision=? WHERE seq=?", (decision, int(event_id_.split("_")[1])))
            self.db.conn.commit()

    def get_event(self, event_id_: str) -> Optional[dict]:
        with self.db.lock:
            row = self.db.conn.execute("SELECT * FROM events WHERE seq=?", (int(event_id_.split("_")[1]),)).fetchone()
        return self._event_row(row) if row else None

    # -- posture (the agent's standing state) -------------------------------------
    def set_agent_status(self, agent_id: str, status: str) -> None:
        with self.db.lock:
            self.db.conn.execute("UPDATE agents SET status=? WHERE agent_id=?", (status, agent_id))
            self.db.conn.commit()

    # -- approvals ----------------------------------------------------------------
    def insert_approval(self, agent_id: str, event_id_: str, request: dict, now: float) -> str:
        with self.db.lock:
            cur = self.db.conn.execute(
                "INSERT INTO approvals(ts, agent_id, event_id, request_json) VALUES (?,?,?,?)",
                (now, agent_id, event_id_, json.dumps(request)))
            self.db.conn.commit()
        return approval_id(cur.lastrowid)

    @staticmethod
    def _approval_row(r) -> dict:
        return {"id": approval_id(r["seq"]), "ts": r["ts"], "agent_id": r["agent_id"], "event_id": r["event_id"],
                "request": json.loads(r["request_json"]), "status": r["status"],
                "resolved_ts": r["resolved_ts"], "resolved_by": r["resolved_by"],
                "result": json.loads(r["result_json"]) if r["result_json"] else None}

    def get_approval(self, approval_id_: str) -> Optional[dict]:
        try:
            seq = int(approval_id_.split("_")[1])
        except (IndexError, ValueError):
            return None
        with self.db.lock:
            row = self.db.conn.execute("SELECT * FROM approvals WHERE seq=?", (seq,)).fetchone()
        return self._approval_row(row) if row else None

    def list_approvals(self, status: Optional[str] = None, limit: int = 100) -> list:
        sql, params = "SELECT * FROM approvals", []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY seq DESC LIMIT ?"
        params.append(limit)
        with self.db.lock:
            return [self._approval_row(r) for r in self.db.conn.execute(sql, params).fetchall()]

    def resolve_approval(self, approval_id_: str, status: str, by: str, now: float,
                         result: Optional[dict] = None) -> None:
        with self.db.lock:
            self.db.conn.execute(
                "UPDATE approvals SET status=?, resolved_by=?, resolved_ts=?, result_json=? WHERE seq=?",
                (status, by, now, json.dumps(result) if result is not None else None, int(approval_id_.split("_")[1])))
            self.db.conn.commit()

    def expire_approvals(self, cutoff_ts: float, now: float) -> list:
        """Mark pending approvals created at or before cutoff_ts as expired (auto-deny). Returns their event ids."""
        with self.db.lock:
            rows = self.db.conn.execute(
                "SELECT seq, event_id FROM approvals WHERE status='pending' AND ts<=?", (cutoff_ts,)).fetchall()
            for r in rows:
                self.db.conn.execute("UPDATE approvals SET status='expired', resolved_by='system', resolved_ts=? "
                                     "WHERE seq=?", (now, r["seq"]))
            self.db.conn.commit()
        return [r["event_id"] for r in rows]

    def list_events(self, agent_id: Optional[str] = None, limit: int = 100) -> list:
        sql, params = "SELECT * FROM events", []
        if agent_id:
            sql += " WHERE agent_id=?"
            params.append(agent_id)
        sql += " ORDER BY seq DESC LIMIT ?"
        params.append(limit)
        with self.db.lock:
            rows = self.db.conn.execute(sql, params).fetchall()
        return [self._event_row(r) for r in rows]

    def count_events(self, agent_id: str) -> int:
        with self.db.lock:
            return self.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE agent_id=?", (agent_id,)).fetchone()[0]

    # -- alerts ---------------------------------------------------------------
    def insert_alert(self, agent_id: str, event_id_: str, risk: float, band: str,
                     shadow_action: str, reasons: list, lens: dict, explanation: Optional[dict] = None,
                     decision: str = "ALLOW") -> str:
        with self.db.lock:
            cur = self.db.conn.execute(
                "INSERT INTO alerts(ts, agent_id, event_id, risk, band, shadow_action, reasons_json, lens_json, "
                "explanation_json, decision) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (now_iso(), agent_id, event_id_, risk, band, shadow_action,
                 json.dumps(reasons), json.dumps(lens), json.dumps(explanation or {}), decision),
            )
            self.db.conn.commit()
        return alert_id(cur.lastrowid)

    @staticmethod
    def _alert_row(r, with_explanation: bool = False) -> dict:
        d = {"id": alert_id(r["seq"]), "ts": r["ts"], "agent_id": r["agent_id"],
             "event_id": r["event_id"], "risk": r["risk"], "band": r["band"],
             "shadow_action": r["shadow_action"], "status": r["status"], "decision": r["decision"],
             "reasons": json.loads(r["reasons_json"]), "lens": json.loads(r["lens_json"])}
        if with_explanation:
            d["explanation"] = json.loads(r["explanation_json"])
        return d

    def get_alert(self, alert_id_: str) -> Optional[dict]:
        try:
            seq = int(alert_id_.split("_")[1])
        except (IndexError, ValueError):
            return None
        with self.db.lock:
            row = self.db.conn.execute("SELECT * FROM alerts WHERE seq=?", (seq,)).fetchone()
        return self._alert_row(row, True) if row else None

    def list_alerts(self, limit: int = 100) -> list:
        with self.db.lock:
            rows = self.db.conn.execute(
                "SELECT * FROM alerts ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        out = [self._alert_row(r) for r in rows]
        return out
