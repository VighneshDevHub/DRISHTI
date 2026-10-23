"""SQLite connection + schema. Stdlib only; swap for Postgres later."""
from __future__ import annotations

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id     TEXT PRIMARY KEY,
    role         TEXT NOT NULL,
    role_version INTEGER NOT NULL,
    owner        TEXT,
    status       TEXT NOT NULL DEFAULT 'normal',
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    tool         TEXT NOT NULL,
    resource     TEXT,
    resource_class TEXT,
    sensitivity  REAL,
    destination  TEXT,
    destination_class TEXT,
    bytes_out    INTEGER,
    risk         REAL NOT NULL,
    band         TEXT NOT NULL,
    lens_json    TEXT NOT NULL,
    event_json   TEXT NOT NULL,
    decision     TEXT NOT NULL DEFAULT 'ALLOW',
    block_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id, seq);
CREATE TABLE IF NOT EXISTS alerts (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    event_id     TEXT NOT NULL,
    risk         REAL NOT NULL,
    band         TEXT NOT NULL,
    shadow_action TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    lens_json    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'open',
    explanation_json TEXT NOT NULL DEFAULT '{}',
    decision     TEXT NOT NULL DEFAULT 'ALLOW'
);
CREATE TABLE IF NOT EXISTS approvals (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    agent_id     TEXT NOT NULL,
    event_id     TEXT NOT NULL,
    request_json TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | denied | expired
    resolved_ts  REAL,
    resolved_by  TEXT,
    result_json  TEXT
);
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            # migrate databases created before alerts carried explanations
            cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(alerts)").fetchall()]
            if "explanation_json" not in cols:
                self.conn.execute("ALTER TABLE alerts ADD COLUMN explanation_json TEXT NOT NULL DEFAULT '{}'")
            if "decision" not in cols:
                self.conn.execute("ALTER TABLE alerts ADD COLUMN decision TEXT NOT NULL DEFAULT 'ALLOW'")
            ecols = [r["name"] for r in self.conn.execute("PRAGMA table_info(events)").fetchall()]
            if "decision" not in ecols:
                self.conn.execute("ALTER TABLE events ADD COLUMN decision TEXT NOT NULL DEFAULT 'ALLOW'")
            if "block_reason" not in ecols:
                self.conn.execute("ALTER TABLE events ADD COLUMN block_reason TEXT")
            self.conn.commit()
