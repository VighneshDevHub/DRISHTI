import unittest
from app.config import ANCHOR_FREEZE_N, DRIFT_H
from app.models.events import ToolCallRequest
from helpers import make_services

NORMAL = [("doc.read", {"path": "supplier/quote_1.pdf"}), ("supplier_api.get_price", {"sku": "SKU-100"}),
          ("purchase.create_request", {"sku": "SKU-100", "qty": 1}), ("erp.read_orders", {}),
          ("supplier_api.list_catalog", {"supplier": "Supplier A"})]


def call(svc, agent, tool, args=None):
    return svc.gateway.handle_tool_call(ToolCallRequest(agent, tool, args or {}))


def warm_up(svc, agent, rounds=8):
    for _ in range(rounds):
        for tool, args in NORMAL:
            call(svc, agent, tool, args)


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.s = make_services()
        self.s.gateway.register_agent("a", "procurement_agent")

    def test_normal_work_never_drifts_even_before_the_anchor_freezes(self):
        for tool, args in NORMAL:
            d = call(self.s, "a", tool, args)
            self.assertEqual(d.lens["drift"]["score"], 0.0, tool)
            self.assertFalse(d.lens["drift"]["details"]["this_event_novel"])

    def test_anchor_freezes_after_enough_trusted_events(self):
        warm_up(self.s, "a", rounds=ANCHOR_FREEZE_N // 5 + 1)
        d = self.s.drift.summary("a")
        self.assertTrue(d["anchor_frozen"])
        self.assertGreaterEqual(d["learned_events"], ANCHOR_FREEZE_N)

    def test_out_of_contract_capability_is_novel_and_counted_once(self):
        warm_up(self.s, "a")
        first = call(self.s, "a", "erp.read_invoices", {"invoice_id": "INV-1"})
        again = call(self.s, "a", "erp.read_invoices", {"invoice_id": "INV-2"})
        f, g = first.lens["drift"]["details"], again.lens["drift"]["details"]
        self.assertTrue(f["first_sighting"])
        self.assertFalse(g["first_sighting"])
        self.assertEqual(f["surface_weight"], g["surface_weight"])      # repeats do not inflate the surface
        self.assertAlmostEqual(f["surface_weight"], 0.9, places=2)       # 0.5 base + 0.4 sensitivity, x1.0 out-of-contract

    def test_attacks_are_not_learned_into_the_anchor(self):
        warm_up(self.s, "a")
        for _ in range(40):                                              # repeat a novel capability many times
            call(self.s, "a", "erp.read_invoices", {"invoice_id": "INV-1"})
        d = call(self.s, "a", "erp.read_invoices", {"invoice_id": "INV-1"})
        self.assertTrue(d.lens["drift"]["details"]["this_event_novel"])  # still novel: never absorbed

    def test_in_contract_but_never_used_counts_after_freeze_at_a_discount(self):
        svc = make_services()
        svc.gateway.register_agent("b", "procurement_broad_agent")
        warm_up(svc, "b")                                                # never touches invoices/contacts
        d = call(svc, "b", "erp.read_invoices", {"invoice_id": "INV-1"})
        self.assertEqual(d.lens["role"]["score"], 0.0)                   # permitted by the broad contract
        det = d.lens["drift"]["details"]
        self.assertTrue(det["this_event_novel"])
        self.assertAlmostEqual(det["surface_weight"], 0.9 * 0.75, delta=0.01)   # reported rounded to 2dp

    def test_budget_exhaustion_forces_step_up_only_on_new_capabilities(self):
        svc = make_services()
        svc.gateway.register_agent("b", "procurement_broad_agent")
        warm_up(svc, "b")
        tools = [("supplier_api.get_quote_history", {"supplier": "A"}), ("erp.read_invoices", {"invoice_id": "I"}),
                 ("supplier_api.get_contacts", {"supplier": "A"}), ("purchase.list_requests", {"status": "all"}),
                 ("erp.read_vendor_terms", {"vendor": "A"})]
        last = None
        for tool, args in tools:
            last = call(svc, "b", tool, args)
        self.assertGreaterEqual(last.lens["drift"]["details"]["budget_score"], 1.0)
        self.assertEqual(last.band, "ELEVATED")
        self.assertEqual(last.lens["fusion"]["floors"][0]["name"], "drift_budget_exceeded")
        # ...but ordinary work right after is untouched: no disruption to legitimate work
        for tool, args in NORMAL:
            d = call(svc, "b", tool, args)
            self.assertEqual(d.band, "LOW", tool)
            self.assertEqual(d.lens["drift"]["score"], 0.0)

    def test_burst_detector_rises_on_many_new_things_and_decays(self):
        warm_up(self.s, "a")
        for tool, args in [("erp.read_invoices", {"invoice_id": "I"}), ("supplier_api.get_contacts", {"supplier": "A"}),
                           ("supplier_api.get_quote_history", {"supplier": "A"})]:
            d = call(self.s, "a", tool, args)
        peak = d.lens["drift"]["details"]["cusum"]
        self.assertGreater(peak, 1.0)
        for tool, args in NORMAL * 2:
            d = call(self.s, "a", tool, args)
        self.assertLess(self.s.drift.summary("a")["cusum"], peak)        # burst detector forgives; the budget does not
        self.assertGreater(self.s.drift.summary("a")["surface_weight"], 0)

    def test_sanctioned_change_resets_the_surface(self):
        warm_up(self.s, "a")
        call(self.s, "a", "erp.read_invoices", {"invoice_id": "I"})
        self.assertGreater(self.s.drift.summary("a")["surface_weight"], 0)
        self.s.drift.refreeze("a", self.s.contracts.get("procurement_agent"))
        d = call(self.s, "a", "erp.read_invoices", {"invoice_id": "I"})
        self.assertEqual(self.s.drift.summary("a")["surface_weight"], 0)
        self.assertFalse(d.lens["drift"]["details"]["this_event_novel"])

    def test_drift_budget_tolerance_constant_is_what_the_docs_say(self):
        self.assertEqual(DRIFT_H, 2.5)


if __name__ == "__main__":
    unittest.main()
