"""L4 - Decoy tripwires (the D3COY layer).

A decoy is a resource no legitimate task ever touches. Touching one is
near-conclusive evidence of an agent acting outside its real work, and it
needs no history, no baseline and no model, so it also covers brand-new
agents. An attacker who copies "normal behaviour" perfectly still cannot
know which items are fake.

Four decoy kinds:
  file        believable fake files in sensitive-looking places
  credential  fake keys/tokens; any tool argument containing one = use
  endpoint    fake admin endpoints / hosts
  canary      unique strings WATERMARKED into real sensitive data; if one
              shows up in an outbound payload, that data is leaving

Scores: touch/use/exfil = 1.0, merely listing a directory that contains a
decoy = 0.4 (a harmless `ls` should not hang an agent).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from ..models.events import Event, LensResult


@dataclass(frozen=True)
class Decoy:
    id: str
    kind: str          # file | credential | endpoint | canary
    match: str         # path / token / host / canary string
    description: str
    exempt_roles: tuple = ()


def default_decoys() -> list:
    return [
        Decoy("dcy-file-salaries", "file", "hr/salaries_2026_final.xlsx", "fake final salary sheet"),
        Decoy("dcy-file-bank", "file", "payroll/bank_accounts_export.csv", "fake payroll bank export"),
        Decoy("dcy-cred-erp", "credential", "ERP_ADMIN_KEY_7f3a91c2", "fake ERP admin key"),
        Decoy("dcy-endpoint-export", "endpoint", "admin-export.internal", "fake bulk-export endpoint"),
        Decoy("dcy-canary-hr", "canary", "CNRY-HR-5521-ZK", "the real HR data"),
        Decoy("dcy-canary-cust", "canary", "CNRY-CU-8830-QM", "the real customer data"),
    ]


class DecoyRegistry:
    def __init__(self, decoys: Optional[list] = None):
        self._decoys = {d.id: d for d in (decoys if decoys is not None else default_decoys())}
        self.hits: dict = {d: 0 for d in self._decoys}
        self._lock = threading.Lock()

    def of_kind(self, kind: str) -> list:
        return [d for d in self._decoys.values() if d.kind == kind]

    def record_hit(self, decoy_id: str) -> None:
        with self._lock:
            self.hits[decoy_id] += 1

    def snapshot(self) -> list:
        """For the API/dashboard. The match strings are shown only to operators."""
        return [{"id": d.id, "kind": d.kind, "match": d.match, "description": d.description,
                 "hits": self.hits[d.id]} for d in self._decoys.values()]

    def seed_backend(self, backend) -> None:
        """Plant file decoys and watermark real data inside the (simulated) environment."""
        for d in self.of_kind("file"):
            backend.docs[d.match] = (f"CONFIDENTIAL\nname,amount\nA. Example,99000\n"
                                     f"#ref {self._first_canary()}")
        hr = next((c for c in self.of_kind("canary") if c.id.endswith("-hr")), None)
        if hr and "hr/salaries_2026.xlsx" in backend.docs:
            backend.docs["hr/salaries_2026.xlsx"] += f"\n#ref {hr.match}"

    def _first_canary(self) -> str:
        c = self.of_kind("canary")
        return c[0].match if c else "CNRY"


class DecoyLens:
    name = "decoy"

    def __init__(self, registry: DecoyRegistry):
        self.registry = registry

    def evaluate(self, event: Event, args: dict) -> LensResult:
        hits = []  # (score, kind, decoy, why)
        resource = event.resource or ""
        is_list = event.tool.endswith(".list")
        arg_text = " ".join(str(v) for v in (args or {}).values())

        # 1. canary string leaving in an outbound payload = proof of exfiltration
        if event.sink_type == "egress":
            for d in self.registry.of_kind("canary"):
                if d.match in arg_text:
                    hits.append((1.0, "canary_exfil", d,
                                 f"watermark '{d.match}', planted in {d.description}, was found in an outbound "
                                 f"payload: protected data is leaving the organisation"))

        # 2. file decoys: read = touch, directory listing = weak signal
        for d in self.registry.of_kind("file"):
            if event.role in d.exempt_roles:
                continue
            if is_list:
                if resource and d.match.startswith(resource):
                    hits.append((0.4, "list", d, f"listing '{resource}' exposes decoy '{d.match}'"))
            elif resource == d.match:
                hits.append((1.0, "touch", d, f"agent opened decoy file '{d.match}' ({d.description}); "
                                              f"no legitimate task uses it"))

        # 3. credential decoys: any argument carrying a fake key
        for d in self.registry.of_kind("credential"):
            if d.match in arg_text:
                hits.append((1.0, "touch", d, f"agent used decoy credential '{d.match}' ({d.description})"))

        # 4. endpoint decoys: destination host or path
        for d in self.registry.of_kind("endpoint"):
            if event.destination == d.match or d.match in arg_text:
                hits.append((1.0, "touch", d, f"agent contacted decoy endpoint '{d.match}' ({d.description})"))

        if not hits:
            return LensResult(self.name, 0.0, "no decoy touched", details={"kind": None, "decoys": []})
        for _, _, d, _ in hits:
            self.registry.record_hit(d.id)
        best = max(hits, key=lambda h: (h[0], h[1] == "canary_exfil"))
        return LensResult(self.name, best[0], best[3],
                          evidence=[h[3] for h in sorted(hits, key=lambda h: -h[0])],
                          details={"kind": best[1], "decoys": [h[2].id for h in hits]})
