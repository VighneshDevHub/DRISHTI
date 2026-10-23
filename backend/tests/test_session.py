import unittest
from app.models.events import ToolCallRequest
from app.risk.session import SessionTracker
from helpers import make_services

NORMAL = [("doc.read", {"path": "supplier/quote_1.pdf"}), ("supplier_api.get_price", {"sku": "SKU-100"}),
          ("purchase.create_request", {"sku": "SKU-100", "qty": 1}), ("erp.read_orders", {})]


def call(svc, agent, tool, args=None):
    return svc.gateway.handle_tool_call(ToolCallRequest(agent, tool, args or {}))


def isolated(**kw):      # role + provenance + decoy only, so the numbers are exact
    return make_services(enable_baseline=False, enable_drift=False, **kw)


class SessionUnitTests(unittest.TestCase):
    def test_accumulation_math(self):
        t = SessionTracker()
        a = t.apply("x", 55.0)
        self.assertEqual((a["session"], a["raised_by_session"]), (27.5, False))     # 1-(1-0)(1-0.5*0.55)
        b = t.apply("x", 55.0)
        expected = (1 - (1 - 0.275 * 0.85) * (1 - 0.275)) * 100                     # decay the old level, then add
        self.assertAlmostEqual(b["session"], expected, delta=0.1)

    def test_quiet_events_neither_feed_nor_inherit(self):
        t = SessionTracker()
        for _ in range(5):
            t.apply("x", 55.0)
        a = t.apply("x", 10.0)                                                       # below the minimum
        self.assertEqual(a["effective_risk"], 10.0)
        self.assertFalse(a["raised_by_session"])

    def test_session_decays_when_nothing_happens(self):
        t = SessionTracker()
        t.apply("x", 90.0)
        peak = t.level("x")
        for _ in range(10):
            t.apply("x", 1.0)
        self.assertLess(t.level("x"), peak * 0.25)

    def test_agents_are_independent(self):
        t = SessionTracker()
        for _ in range(5):
            t.apply("a", 55.0)
        self.assertEqual(t.level("b"), 0.0)


class SessionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.s = isolated()
        self.s.gateway.register_agent("a", "procurement_agent")

    def repeat(self, svc, n, agent="a"):
        return [call(svc, agent, "hr_files.list", {"path": "hr/"}) for _ in range(n)]

    def test_a_single_event_is_not_raised(self):
        d = self.repeat(self.s, 1)[0]
        self.assertEqual((d.risk, d.band), (55.0, "WATCH"))
        self.assertFalse(d.lens["session"]["raised_by_session"])

    def test_repeated_mid_level_suspicion_escalates_to_step_up(self):
        ds = self.repeat(self.s, 6)
        self.assertEqual([d.band for d in ds[:3]], ["WATCH"] * 3)
        self.assertEqual(ds[3].band, "ELEVATED")                       # the 4th repeat crosses 60
        self.assertTrue(ds[3].lens["session"]["raised_by_session"])
        self.assertGreater(ds[5].risk, ds[3].risk)                     # and keeps climbing

    def test_without_the_session_the_same_behaviour_stays_at_watch_forever(self):
        off = isolated(enable_session=False)
        off.gateway.register_agent("a", "procurement_agent")
        self.assertEqual({d.band for d in self.repeat(off, 8)}, {"WATCH"})

    def test_ordinary_work_is_never_penalised_by_a_hot_session(self):
        self.repeat(self.s, 6)                                          # session is now hot
        fresh = isolated(); fresh.gateway.register_agent("a", "procurement_agent")
        for tool, args in NORMAL:
            hot, cold = call(self.s, "a", tool, args), call(fresh, "a", tool, args)
            self.assertEqual(hot.band, "LOW", tool)
            self.assertEqual(hot.risk, cold.risk, tool)                 # identical to an agent with no incident
            self.assertFalse(hot.lens["session"]["raised_by_session"])

    def test_suspicion_fades_after_a_quiet_period(self):
        """After enough ordinary work, an agent that WAS under suspicion is scored exactly like
        an identical agent that never was (both ingested the same untrusted data meanwhile)."""
        self.repeat(self.s, 6)
        control = isolated(); control.gateway.register_agent("a", "procurement_agent")
        for svc in (self.s, control):
            for _ in range(4):
                for tool, args in NORMAL:
                    call(svc, "a", tool, args)
        after_incident = self.repeat(self.s, 1)[0]
        never_suspected = self.repeat(control, 1)[0]
        self.assertEqual(after_incident.risk, never_suspected.risk)
        self.assertFalse(after_incident.lens["session"]["raised_by_session"])

    def test_other_agents_are_unaffected(self):
        self.s.gateway.register_agent("b", "procurement_agent")
        self.repeat(self.s, 6)
        d = self.repeat(self.s, 1, agent="b")[0]
        self.assertEqual(d.band, "WATCH")


if __name__ == "__main__":
    unittest.main()
