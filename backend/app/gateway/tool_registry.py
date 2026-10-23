"""Tool registry: turns raw tool names into security-meaningful facts.

Every tool the gateway can see is described once here: what class of
resource it touches, how sensitive that is, and what kind of 'sink' it is
(benign / write / read_sensitive / egress). Detection lenses never guess
these facts - they read them from here. To support a new tool, add one
ToolSpec.

The manifest hash lets us notice a tool being silently changed
(tool poisoning / "rug-pull", scenario S3 in Phase 7).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    resource_class: str
    sensitivity: float
    sink_type: str  # benign | write | read_sensitive | egress
    resource_arg: Optional[str] = None  # which arg names the resource
    destination_arg: Optional[str] = None  # which arg names the destination
    irreversible: bool = False
    registered: bool = True
    # Who wrote the text this tool returns? system = our own trusted data;
    # untrusted = third parties / customers / documents; peer_agent = another agent.
    output_trust: str = "system"
    # Path-prefix reclassification: {"hr/": ("hr_data", 0.9)}. Stops an agent
    # reading HR files through a generic tool like doc.read.
    path_rules: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def manifest_hash(self) -> str:
        blob = json.dumps(
            [self.name, self.description, self.resource_arg, self.destination_arg],
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class Resolved:
    """A tool call after the registry has interpreted its arguments."""
    spec: ToolSpec
    resource: Optional[str]
    resource_class: str
    sensitivity: float
    destination: Optional[str]  # host only, e.g. 'api.supplier-a.com'


def _host_of(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value)
    if "@" in value and "://" not in value:  # email address -> domain
        return value.rsplit("@", 1)[1].lower()
    parsed = urlparse(value if "://" in value else f"//{value}")
    return (parsed.hostname or "").lower() or None


_HR_RULES = {
    "hr/": ("hr_data", 0.9),
    "payroll/": ("payroll", 1.0),
    "src/": ("source_code", 0.7),
}


def _default_specs() -> list:
    S = ToolSpec
    return [
        S("supplier_api.get_price", "Get the current price of a product from a supplier",
          "supplier_data", 0.2, "benign", resource_arg="sku", output_trust="untrusted"),
        S("supplier_api.list_catalog", "List the products offered by a supplier catalog",
          "supplier_data", 0.2, "benign", resource_arg="supplier", output_trust="untrusted"),
        S("purchase.create_request", "Create a purchase request for a product and quantity",
          "purchase_requests", 0.3, "write", resource_arg="sku"),
        S("erp.read_orders", "Read open purchase orders from the ERP system",
          "purchase_requests", 0.3, "benign", resource_arg="order_id"),
        S("doc.read", "Read a document from the document store",
          "documents", 0.2, "benign", resource_arg="path", path_rules=_HR_RULES,
          output_trust="untrusted"),
        S("hr_files.read", "Read a human resources file such as salaries or reviews",
          "hr_data", 0.9, "read_sensitive", resource_arg="path"),
        S("hr_files.list", "List files in the human resources directory",
          "hr_data", 0.5, "read_sensitive", resource_arg="path"),
        S("http.post", "Send data to an external web address",
          "external_network", 0.0, "egress", resource_arg="url",
          destination_arg="url", irreversible=True),
        S("email.send", "Send an email message to a recipient",
          "email", 0.0, "egress", resource_arg="to",
          destination_arg="to", irreversible=True),
        S("support.get_ticket", "Fetch a customer support ticket",
          "tickets", 0.4, "benign", resource_arg="ticket_id", output_trust="untrusted"),
        S("support.reply_ticket", "Reply to a customer support ticket",
          "tickets", 0.4, "write", resource_arg="ticket_id", irreversible=True),
        S("crm.read_customer", "Read a customer account record with contact details",
          "customer_pii", 0.7, "read_sensitive", resource_arg="customer_id"),
        # Near-purpose tools a procurement agent is NOT contracted for. They are
        # deliberately plausible: a patient attacker drifts through exactly these.
        S("supplier_api.get_quote_history", "Get past price quotes from a supplier",
          "supplier_data", 0.2, "benign", resource_arg="supplier", output_trust="untrusted"),
        S("erp.read_invoices", "Read supplier invoices from the ERP system",
          "invoices", 0.4, "benign", resource_arg="invoice_id"),
        S("supplier_api.get_contacts", "Get the contact persons of a supplier",
          "supplier_contacts", 0.4, "benign", resource_arg="supplier", output_trust="untrusted"),
        S("purchase.list_requests", "List all purchase requests across the company",
          "purchase_requests", 0.3, "benign", resource_arg="status"),
        S("erp.read_vendor_terms", "Read the payment terms agreed with a supplier",
          "vendor_terms", 0.3, "benign", resource_arg="vendor"),
        S("devops.read_logs", "Read logs of an internal service",
          "logs", 0.3, "benign", resource_arg="service", output_trust="untrusted"),
        S("devops.restart_service", "Restart an internal service",
          "infrastructure", 0.4, "write", resource_arg="service", irreversible=True),
    ]


class ToolRegistry:
    def __init__(self, specs: Optional[list] = None):
        self._specs = {s.name: s for s in (specs if specs is not None else _default_specs())}

    def register(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._specs.get(name)

    def all(self) -> list:
        return list(self._specs.values())

    def matching(self, patterns: list) -> list:
        """Expand contract tool patterns (globs allowed) to registered specs."""
        import fnmatch
        return [s for s in self._specs.values()
                if any(fnmatch.fnmatchcase(s.name, p) for p in patterns)]

    def resolve(self, tool: str, args: dict) -> Resolved:
        spec = self._specs.get(tool)
        if spec is None:
            # Unknown tool: never silently trusted. Treated as an unregistered,
            # moderately sensitive, unclassified sink so L1 scores it.
            spec = ToolSpec(tool, tool.replace(".", " ").replace("_", " "),
                            "unregistered", 0.5, "unknown_tool", registered=False)
        resource = None
        if spec.resource_arg and args.get(spec.resource_arg) is not None:
            resource = str(args[spec.resource_arg])
        rclass, sens = spec.resource_class, spec.sensitivity
        if resource:
            for prefix, (cls_, sens_) in spec.path_rules.items():
                if resource.startswith(prefix):
                    rclass, sens = cls_, sens_
                    break
        destination = _host_of(args.get(spec.destination_arg)) if spec.destination_arg else None
        return Resolved(spec, resource, rclass, sens, destination)
