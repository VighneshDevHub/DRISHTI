"""Session risk: suspicion that accumulates across several actions.

Some behaviour is only suspicious as a PATTERN: many mid-level signals in
a short span, none of which crosses a threshold alone. The session keeps a
running, decaying suspicion per agent:

    on every tool call:      S = S * DECAY
    if event_risk >= MIN:    S = 1 - (1 - S) * (1 - GAIN * event_risk / 100)    (noisy-OR style)
                             effective_risk = max(event_risk, S)

Crucial design rule (learned from the drift lens in Phase 4): the session
only RAISES events that are themselves at least mildly suspicious. Ordinary
actions (risk < MIN) are never penalised for happening near an incident, so
legitimate work continues undisturbed.
"""
from __future__ import annotations

import threading

from ..config import SESSION_DECAY, SESSION_GAIN, SESSION_MIN_EVENT_RISK


class SessionTracker:
    def __init__(self):
        self._s: dict = {}          # agent_id -> suspicion on a 0..100 scale
        self._lock = threading.Lock()

    def apply(self, agent_id: str, event_risk: float) -> dict:
        with self._lock:
            s = self._s.get(agent_id, 0.0) / 100.0 * SESSION_DECAY
            applied = False
            effective = event_risk
            if event_risk >= SESSION_MIN_EVENT_RISK:
                s = 1.0 - (1.0 - s) * (1.0 - SESSION_GAIN * event_risk / 100.0)
                if s * 100.0 > event_risk:
                    effective = round(s * 100.0, 1)
                    applied = True
            self._s[agent_id] = s * 100.0
            return {"event_risk": event_risk, "session": round(s * 100.0, 1),
                    "effective_risk": effective, "raised_by_session": applied}

    def reset(self, agent_id: str) -> None:
        with self._lock:
            self._s.pop(agent_id, None)

    def level(self, agent_id: str) -> float:
        with self._lock:
            return round(self._s.get(agent_id, 0.0), 1)
