"""L3 - Causal Provenance lens.

Question: "Did untrusted content just push this agent into a risky action
that its role does not authorise?"

    s_prov = U_strength x sink_weight x (1 - 0.8 x justified)

  U_strength  freshest untrusted label: exp(-age / DECAY). Peer-agent
              labels count PEER_AGENT_FACTOR as much.
  sink_weight how dangerous the action is as a place for tainted influence
              (egress 0.9, sensitive read 0.7, write 0.6, out-of-contract 0.5).
  justified   1 when the action is inside the role contract. The contract
              is the owner's standing authorisation; untrusted text cannot
              widen it. So normal work after reading a document scores ~0,
              while an out-of-role action right after reading one scores high.

The lens never inspects document text, so rewording, encoding or
translating an injection does not change the result.
"""
from __future__ import annotations

import math

from ..config import (PEER_AGENT_FACTOR, PROVENANCE_DECAY, SENSITIVE_READ_MIN,
                      SINK_WEIGHTS)
from ..models.events import Event, LensResult


def classify_sink(event: Event, justified: bool) -> str:
    if event.destination_class in ("external", "unknown"):
        return "egress_external"
    if event.sink_type == "read_sensitive" or event.sensitivity >= SENSITIVE_READ_MIN:
        return "read_sensitive"
    if event.sink_type == "write":
        return "write"
    if not justified or not event.registered_tool:
        return "out_of_contract"
    return "benign"


class ProvenanceLens:
    name = "provenance"

    def evaluate(self, event: Event, labels: list, justified: bool,
                 sensitive_in_context: list) -> LensResult:
        sink = classify_sink(event, justified)
        strength, source, trust = 0.0, None, None
        for lab in labels:
            if lab.trust == "untrusted":
                s = math.exp(-lab.age_steps / PROVENANCE_DECAY)
            elif lab.trust == "peer_agent":
                s = PEER_AGENT_FACTOR * math.exp(-lab.age_steps / PROVENANCE_DECAY)
            else:
                continue
            if s > strength:
                strength, source, trust = s, lab, lab.trust
        tainted = strength > 0.0
        score = strength * SINK_WEIGHTS[sink] * (1.0 - 0.8 * (1.0 if justified else 0.0))
        details = {"tainted": tainted, "sink": sink, "justified": justified,
                   "u_strength": round(strength, 3), "sensitive_in_context": list(sensitive_in_context),
                   "source": source.source if source else None}
        if score <= 0.0:
            why = ("no untrusted content in recent context" if not tainted
                   else "recent untrusted content, but this action is benign or inside the role contract")
            return LensResult(self.name, 0.0, why, details=details)
        reason = (f"untrusted input '{source.source}' was ingested {source.age_steps} step(s) earlier, "
                  f"then the agent attempted {sink.replace('_', ' ')} "
                  f"('{event.tool}') that its role contract does not authorise")
        return LensResult(self.name, round(score, 3), reason,
                          evidence=[f"label={source.source} trust={trust} age={source.age_steps}",
                                    f"sink={sink}", f"justified_by_contract={justified}"],
                          details=details)
