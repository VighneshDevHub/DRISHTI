import unittest
from app.config import Settings
from app.gateway.interceptor import classify_destination
from app.models.events import Event
from helpers import make_services


class RoleFitTests(unittest.TestCase):
    def setUp(self):
        self.s = make_services()
        self.lens = self.s.gateway.role_fit
        self.proc = self.s.contracts.get("procurement_agent")

    def event(self, tool, args, contract=None):
        contract = contract or self.proc
        r = self.s.registry.resolve(tool, args)
        return Event(ts="t", agent_id="a", role=contract.role, role_version=contract.version,
                     tool=tool, resource=r.resource, resource_class=r.resource_class,
                     sensitivity=r.sensitivity, sink_type=r.spec.sink_type, destination=r.destination,
                     destination_class=classify_destination(r.destination, contract),
                     bytes_out=0, is_irreversible=r.spec.irreversible, registered_tool=r.spec.registered)

    def test_inside_contract_scores_zero(self):
        for tool, args in [("supplier_api.get_price", {"sku": "SKU-100"}),
                           ("purchase.create_request", {"sku": "SKU-100", "qty": 2}),
                           ("doc.read", {"path": "supplier/quote_1.pdf"}),
                           ("erp.read_orders", {})]:
            res = self.lens.evaluate(self.event(tool, args), self.proc)
            self.assertEqual(res.score, 0.0, tool)

    def test_denied_class_scores_one(self):
        res = self.lens.evaluate(self.event("hr_files.read", {"path": "hr/salaries_2026.xlsx"}), self.proc)
        self.assertEqual(res.score, 1.0)
        self.assertIn("denied", res.reason)

    def test_hr_via_generic_doc_read_is_still_caught(self):
        res = self.lens.evaluate(self.event("doc.read", {"path": "hr/salaries_2026.xlsx"}), self.proc)
        self.assertEqual(res.score, 1.0)

    def test_unlisted_unrelated_scores_point_six(self):
        res = self.lens.evaluate(self.event("devops.restart_service", {"service": "web"}), self.proc)
        self.assertEqual(res.score, 0.6)

    def test_unlisted_but_close_scores_point_three(self):
        # A supplier-flavoured tool that is NOT in the contract.
        from app.gateway.tool_registry import ToolSpec
        self.s.registry.register(ToolSpec("supplier_api.get_quote_history",
            "Get past price quotes of a supplier", "supplier_data", 0.2, "benign"))
        ev = self.event("supplier_api.get_quote_history", {})
        res = self.lens.evaluate(ev, self.proc)
        self.assertEqual(res.score, 0.3, res.reason)

    def test_egress_to_unknown_host_scores_at_least_point_eight(self):
        res = self.lens.evaluate(self.event("http.post", {"url": "http://203.0.113.9/x"}), self.proc)
        self.assertGreaterEqual(res.score, 0.8)

    def test_allowlisted_destination_is_not_flagged_for_destination(self):
        ev = self.event("http.post", {"url": "https://api.supplier-a.com/orders"})
        self.assertEqual(ev.destination_class, "allowlisted")
        res = self.lens.evaluate(ev, self.proc)
        # still unlisted tool (0.6) but NOT escalated to 0.8 for destination
        self.assertEqual(res.score, 0.6)

    def test_sensitivity_ceiling(self):
        # support agent may read customer_pii (0.7 <= confidential 0.7) -> fine
        sup = self.s.contracts.get("support_agent")
        res = self.lens.evaluate(self.event("crm.read_customer", {"customer_id": "C1"}, sup), sup)
        self.assertEqual(res.score, 0.0)
        # procurement may not exceed 'internal'
        ev = self.event("crm.read_customer", {"customer_id": "C1"})
        self.assertGreaterEqual(self.lens.evaluate(ev, self.proc).score, 0.7)

    def test_cold_start_needs_no_history(self):
        # The very first event of a brand-new agent is already judged.
        self.s.gateway.register_agent("fresh-1", "procurement_agent")
        from app.models.events import ToolCallRequest
        d = self.s.gateway.handle_tool_call(ToolCallRequest("fresh-1", "hr_files.read", {"path": "hr/salaries_2026.xlsx"}))
        self.assertEqual(d.lens["role"]["score"], 1.0)
        self.assertGreaterEqual(d.risk, 30)


if __name__ == "__main__":
    unittest.main()
