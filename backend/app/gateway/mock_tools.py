"""SIMULATED tool backends (suppliers, ERP, HR, outside world).

In production these would be real systems behind MCP/HTTP. Here they are
in-memory fakes so the prototype is self-contained and the demo is
repeatable. `outbox` records every payload that 'left the building' - it
plays the role of the attacker's server, so tests can prove how many
bytes actually leaked.
"""
from __future__ import annotations

from typing import Any


class MockBackend:
    def __init__(self):
        self.prices = {
            "SKU-100": {"supplier": "Supplier A", "price": 12.50},
            "SKU-200": {"supplier": "Supplier B", "price": 48.00},
            "SKU-300": {"supplier": "Supplier A", "price": 7.25},
        }
        self.docs = {
            "supplier/quote_1.pdf": "Quote 1: SKU-100 at 12.50, valid 30 days.",
            "supplier/quote_2.pdf": "Quote 2: SKU-200 at 48.00, bulk discount available.",
            "handbook/onboarding.pdf": "Company onboarding handbook.",
            "hr/salaries_2026.xlsx": "name,salary\nAlice,120000\nBob,95000",
        }
        self.purchase_requests: list = []
        self.outbox: list = []  # what escaped the organisation

    def execute(self, tool: str, args: dict) -> dict:
        fn = getattr(self, "_" + tool.replace(".", "_"), None)
        if fn is None:
            return {"ok": False, "error": f"no backend for tool '{tool}'"}
        try:
            return {"ok": True, "data": fn(args)}
        except KeyError as e:
            return {"ok": False, "error": f"not found: {e}"}

    # -- procurement ----------------------------------------------------------
    def _supplier_api_get_price(self, a: dict) -> Any:
        return self.prices[a["sku"]]

    def _supplier_api_list_catalog(self, a: dict) -> Any:
        return sorted(self.prices)

    def _purchase_create_request(self, a: dict) -> Any:
        req = {"id": f"PR-{len(self.purchase_requests) + 1:04d}", "sku": a["sku"], "qty": a.get("qty", 1)}
        self.purchase_requests.append(req)
        return req

    def _erp_read_orders(self, a: dict) -> Any:
        return [r for r in self.purchase_requests][-5:]

    def _doc_read(self, a: dict) -> Any:
        return self.docs[a["path"]]

    def _supplier_api_get_quote_history(self, a: dict) -> Any:
        return [{"sku": k, **v} for k, v in self.prices.items()]

    def _erp_read_invoices(self, a: dict) -> Any:
        return {"invoice_id": a.get("invoice_id", "INV-1"), "amount": 1200.0}

    def _supplier_api_get_contacts(self, a: dict) -> Any:
        return [{"name": "A. Supplier", "email": "sales@supplier-a.com"}]

    def _purchase_list_requests(self, a: dict) -> Any:
        return list(self.purchase_requests)

    def _erp_read_vendor_terms(self, a: dict) -> Any:
        return {"vendor": a.get("vendor", "Supplier A"), "terms": "net 45"}

    # -- HR / sensitive -------------------------------------------------------
    def _hr_files_read(self, a: dict) -> Any:
        return self.docs[a["path"]]

    def _hr_files_list(self, a: dict) -> Any:
        return [p for p in self.docs if p.startswith("hr/")]

    # -- the outside world ----------------------------------------------------
    def _http_post(self, a: dict) -> Any:
        self.outbox.append({"channel": "http", "to": a["url"], "body": str(a.get("body", ""))})
        return {"status": 200}

    def _email_send(self, a: dict) -> Any:
        self.outbox.append({"channel": "email", "to": a["to"], "body": str(a.get("body", ""))})
        return {"sent": True}

    # -- support / devops -----------------------------------------------------
    def _support_get_ticket(self, a: dict) -> Any:
        return {"id": a["ticket_id"], "subject": "Where is my order?"}

    def _support_reply_ticket(self, a: dict) -> Any:
        return {"id": a["ticket_id"], "replied": True}

    def _crm_read_customer(self, a: dict) -> Any:
        return {"id": a["customer_id"], "name": "Test Customer"}

    def _devops_read_logs(self, a: dict) -> Any:
        return ["INFO service healthy"]

    def _devops_restart_service(self, a: dict) -> Any:
        return {"restarted": a["service"]}
