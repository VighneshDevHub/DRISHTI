"""Map what fired to the OWASP Top 10 for Agentic Applications 2026 (ASI01-ASI10).

Names verified against the published list (Dec 2025). The mapping from our
lenses to categories is OUR judgement, not an OWASP artefact, and is shown
with a plain-language "because" so a reviewer can disagree with it.
"""
from __future__ import annotations

ASI = {
    "ASI01": "Agent Goal Hijack",
    "ASI02": "Tool Misuse and Exploitation",
    "ASI03": "Identity and Privilege Abuse",
    "ASI04": "Agentic Supply Chain Vulnerabilities",
    "ASI05": "Unexpected Code Execution",
    "ASI06": "Memory and Context Poisoning",
    "ASI07": "Insecure Inter-Agent Communication",
    "ASI08": "Cascading Failures",
    "ASI09": "Human-Agent Trust Exploitation",
    "ASI10": "Rogue Agents",
}


def owasp_tags(lens: dict, event) -> list:
    tags: dict = {}

    def add(code: str, because: str) -> None:
        tags.setdefault(code, because)

    role, prov, decoy = lens.get("role"), lens.get("provenance"), lens.get("decoy")
    base, drift = lens.get("baseline"), lens.get("drift")

    if prov is not None and prov.score > 0:
        add("ASI01", "untrusted content was ingested shortly before an action the role does not authorise")
    if role is not None and role.score > 0:
        denied = event.resource_class and any("denied" in e for e in role.evidence)
        ceiling = any("ceiling" in e for e in role.evidence)
        if denied or ceiling:
            add("ASI03", "the agent reached for data its role is explicitly not entitled to")
        if not event.registered_tool or not denied:
            add("ASI02", f"'{event.tool}' is outside the tools granted to this role")
    if decoy is not None and decoy.score > 0:
        kind = decoy.details.get("kind")
        add("ASI10", "the agent touched a resource no legitimate task uses" if kind != "canary_exfil"
            else "watermarked protected data was found leaving the organisation")
    if base is not None and base.score >= 0.5:
        add("ASI10", "behaviour departs sharply from this agent's and its peers' normal pattern")
    if drift is not None and drift.score > 0:
        add("ASI03", "capability surface has grown beyond what this agent was trusted with")
        add("ASI10", "gradual behavioural drift from the agent's trusted baseline")
    return [{"id": c, "name": ASI[c], "because": b} for c, b in sorted(tags.items())]
