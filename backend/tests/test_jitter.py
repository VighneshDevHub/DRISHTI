import unittest
from app.models.events import ToolCallRequest
from app.risk.engine import apply_floor_bands, band_for
from app.risk.jitter import threshold_offset
from helpers import make_services


class JitterUnitTests(unittest.TestCase):
    def test_off_means_zero(self):
        self.assertEqual(threshold_offset("a", "secret", 0.0), 0.0)

    def test_deterministic_per_agent_and_secret(self):
        self.assertEqual(threshold_offset("a", "s", 3.0), threshold_offset("a", "s", 3.0))
        self.assertNotEqual(threshold_offset("a", "s1", 3.0), threshold_offset("a", "s2", 3.0))

    def test_bounded_and_well_spread(self):
        offs = [threshold_offset(f"agent-{i}", "s", 3.0) for i in range(400)]
        self.assertTrue(all(-3.0 <= o <= 3.0 for o in offs))
        self.assertLess(min(offs), -2.0)
        self.assertGreater(max(offs), 2.0)
        self.assertGreater(len(set(offs)), 200)

    def test_offset_shifts_every_threshold_but_not_low(self):
        self.assertEqual(band_for(58.0, 0.0)[0], "WATCH")
        self.assertEqual(band_for(58.0, -3.0)[0], "ELEVATED")        # threshold moved down to 57
        self.assertEqual(band_for(58.0, +3.0)[0], "WATCH")
        self.assertEqual(band_for(0.0, +3.0)[0], "LOW")

    def test_same_score_can_land_in_different_bands_for_different_agents(self):
        bands = {band_for(58.0, threshold_offset(f"agent-{i}", "s", 3.0))[0] for i in range(60)}
        self.assertEqual(bands, {"WATCH", "ELEVATED"})                # an attacker cannot learn one fixed line

    def test_floors_guarantee_a_minimum_band_whatever_the_jitter(self):
        for offset in (-3.0, 3.0):
            band, _ = band_for(85.0, offset)                          # may fall below HIGH when offset is +3
            band, action = apply_floor_bands(band, [("decoy_touch", 85.0, "x")])
            self.assertIn(band, ("HIGH", "CRITICAL"))
        band, action = apply_floor_bands("ELEVATED", [("canary_exfil", 100.0, "x")])
        self.assertEqual((band, action), ("CRITICAL", "ISOLATE"))


class JitterPipelineTests(unittest.TestCase):
    def setUp(self):
        self.s = make_services(jitter_amplitude=3.0)

    def test_conclusive_evidence_is_never_downgraded_by_jitter(self):
        for i in range(40):
            self.s.gateway.register_agent(f"j{i}", "procurement_agent")
            d = self.s.gateway.handle_tool_call(
                ToolCallRequest(f"j{i}", "hr_files.read", {"path": "hr/salaries_2026_final.xlsx"}))
            self.assertIn(d.band, ("HIGH", "CRITICAL"), f"agent j{i}")

    def test_the_same_borderline_action_gets_different_bands_across_agents(self):
        bands = set()
        for i in range(60):
            self.s.gateway.register_agent(f"p{i}", "procurement_agent")
            d = self.s.gateway.handle_tool_call(
                ToolCallRequest(f"p{i}", "hr_files.list", {"path": "hr/"}))
            bands.add(d.band)
        self.assertGreater(len(bands), 1)

    def test_normal_traffic_is_still_quiet_with_jitter_on(self):
        from simulator.agents.procurement import ProcurementAgent
        from simulator.client import WardenClient
        c = WardenClient(service=self.s)
        for i in range(4):
            a = ProcurementAgent(f"n{i}", c, seed=2); a.register()
            for d in a.run(200):
                self.assertEqual(d["band"], "LOW")

    def test_jitter_is_stable_for_an_agent(self):
        self.s.gateway.register_agent("same", "procurement_agent")
        bands = {self.s.gateway.handle_tool_call(
                    ToolCallRequest("same", "hr_files.read", {"path": "hr/salaries_2026.xlsx"})).band
                 for _ in range(1)}
        o1 = threshold_offset("same", self.s.settings.jitter_secret, 3.0)
        self.assertEqual(o1, threshold_offset("same", self.s.settings.jitter_secret, 3.0))


class ScoreHidingTests(unittest.TestCase):
    def test_agent_view_has_no_scores_or_reasons(self):
        s = make_services(expose_scores=False)
        s.gateway.register_agent("a", "procurement_agent")
        bad = s.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", {"path": "hr/salaries_2026.xlsx"}))
        view = bad.agent_view()
        self.assertEqual(set(view), {"decision", "mode", "event_id", "message", "result"})
        self.assertEqual(view["message"], "flagged for review")
        for leaked in ("risk", "band", "lens", "shadow_action", "alert_id", "event"):
            self.assertNotIn(leaked, view)
        self.assertNotIn("denied", str(view))                   # no reason text either
        ok = s.gateway.handle_tool_call(ToolCallRequest("a", "supplier_api.get_price", {"sku": "SKU-100"}))
        self.assertEqual(ok.agent_view()["message"], "ok")

    def test_operators_still_get_everything(self):
        s = make_services(expose_scores=False)
        s.gateway.register_agent("a", "procurement_agent")
        d = s.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", {"path": "hr/salaries_2026.xlsx"}))
        self.assertGreater(d.risk, 0)
        self.assertIn("explanation", s.repo.get_alert(d.alert_id))


if __name__ == "__main__":
    unittest.main()
