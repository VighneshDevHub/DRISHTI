"""Provenance tracker: remembers WHERE each agent's recent context came from.

This is the heart of the indirect-prompt-injection defence. We never read
the text of a document. We only record that "this agent ingested content
from an untrusted source at step k", and later ask whether a risky action
happened soon after.

Steps are counted per agent, one per tool call. A label's age is the
number of calls since it was recorded; old labels expire (window) and fade
(exponential decay), so a document read 50 calls ago does not poison
everything forever.

Integration paths:
  * automatic - when a tool with output_trust != system returns data, the
    gateway records a label for it (gateway/interceptor.py)
  * explicit  - POST /gateway/context, for content an agent ingests outside
    the gateway (an inbound email, a web page, another agent's message)
"""
from __future__ import annotations

import threading
from typing import Optional

from ..config import PROVENANCE_WINDOW
from ..models.events import ContextLabel


class ProvenanceTracker:
    def __init__(self, window: int = PROVENANCE_WINDOW):
        self.window = window
        self._lock = threading.RLock()
        self._step: dict = {}          # agent_id -> int
        self._labels: dict = {}        # agent_id -> [(source, trust, added_step)]
        self._sensitive: dict = {}     # agent_id -> [(source, added_step)]

    # -- step counter -----------------------------------------------------------
    def begin(self, agent_id: str) -> int:
        """Start a new tool call for this agent; returns its step number."""
        with self._lock:
            self._step[agent_id] = self._step.get(agent_id, 0) + 1
            return self._step[agent_id]

    # -- recording ----------------------------------------------------------------
    def add(self, agent_id: str, source: str, trust: str, step: Optional[int] = None) -> None:
        with self._lock:
            step = step if step is not None else self._step.get(agent_id, 0)
            self._labels.setdefault(agent_id, []).append((source, trust, step))

    def note_sensitive_read(self, agent_id: str, source: str, step: int) -> None:
        with self._lock:
            self._sensitive.setdefault(agent_id, []).append((source, step))

    # -- querying -----------------------------------------------------------------
    def context_for(self, agent_id: str, step: int, extra: Optional[list] = None) -> list:
        """Live labels for this call (age filled in), merged with any the caller supplied."""
        with self._lock:
            merged: dict = {}
            for source, trust, added in self._labels.get(agent_id, []):
                age = step - added
                if 0 <= age <= self.window:
                    key = (source, trust)
                    if key not in merged or age < merged[key].age_steps:
                        merged[key] = ContextLabel(source, trust, age)
            for lab in extra or []:
                key = (lab.source, lab.trust)
                if key not in merged or lab.age_steps < merged[key].age_steps:
                    merged[key] = ContextLabel(lab.source, lab.trust, lab.age_steps)
            return sorted(merged.values(), key=lambda l: l.age_steps)

    def sensitive_recent(self, agent_id: str, step: int) -> list:
        """Sources of sensitive data this agent read within the window (before this call)."""
        with self._lock:
            return [s for s, added in self._sensitive.get(agent_id, [])
                    if 0 < step - added <= self.window]

    def current_step(self, agent_id: str) -> int:
        with self._lock:
            return self._step.get(agent_id, 0)

    def forget_sensitive(self, agent_id: str) -> None:
        with self._lock:
            self._sensitive.pop(agent_id, None)

    def clear(self, agent_id: str, source: Optional[str] = None) -> None:
        """Drop taint (all, or one source). Used by checkpoint/resume in Phase 6."""
        with self._lock:
            if source is None:
                self._labels.pop(agent_id, None)
                self._sensitive.pop(agent_id, None)
            else:
                self._labels[agent_id] = [l for l in self._labels.get(agent_id, []) if l[0] != source]
