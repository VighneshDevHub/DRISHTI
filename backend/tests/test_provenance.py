import math
import unittest
from app.gateway.provenance import ProvenanceTracker
from app.models.events import ContextLabel, ToolCallRequest
from helpers import make_isolated, make_services


class TrackerTests(unittest.TestCase):
    def test_age_counts_tool_calls(self):
        t = ProvenanceTracker(window=10)
        s1 = t.begin("a"); t.add("a", "doc", "untrusted", s1)
        t.begin("a"); s3 = t.begin("a")
        labels = t.context_for("a", s3)
        self.assertEqual((labels[0].source, labels[0].age_steps), ("doc", 2))

    def test_labels_expire_after_window(self):
        t = ProvenanceTracker(window=3)
        s = t.begin("a"); t.add("a", "doc", "untrusted", s)
        for _ in range(3): t.begin("a")
        self.assertEqual(len(t.context_for("a", 4)), 1)      # age 3 = still in window
        t.begin("a")
        self.assertEqual(t.context_for("a", 5), [])           # age 4 = expired

    def test_agents_are_isolated(self):
        t = ProvenanceTracker()
        s = t.begin("a"); t.add("a", "doc", "untrusted", s)
        self.assertEqual(t.context_for("b", t.begin("b")), [])

    def test_caller_supplied_labels_merge_keeping_freshest(self):
        t = ProvenanceTracker()
        s = t.begin("a"); t.add("a", "mail", "untrusted", s)
        s2 = t.begin("a")
        merged = t.context_for("a", s2, [ContextLabel("mail", "untrusted", 0), ContextLabel("web", "untrusted", 4)])
        self.assertEqual({(l.source, l.age_steps) for l in merged}, {("mail", 0), ("web", 4)})

    def test_clear_all_or_one_source(self):
        t = ProvenanceTracker()
        s = t.begin("a"); t.add("a", "x", "untrusted", s); t.add("a", "y", "untrusted", s)
        t.clear("a", "x")
        self.assertEqual([l.source for l in t.context_for("a", s + 1)], ["y"])
        t.clear("a")
        self.assertEqual(t.context_for("a", s + 1), [])


class ProvenanceLensTests(unittest.TestCase):
    def setUp(self):
        self.s = make_isolated()      # exact Phase 3 numbers; L2 effects are tested in test_baseline.py
        self.gw = self.s.gateway
        self.gw.register_agent("p", "procurement_agent")

    def call(self, tool, args=None, labels=None):
        return self.gw.handle_tool_call(ToolCallRequest("p", tool, args or {}, context_labels=labels or []))

    def prov(self, d):
        return d.lens["provenance"]

    def test_normal_work_after_reading_a_document_is_not_flagged(self):
        self.call("doc.read", {"path": "supplier/quote_1.pdf"})            # untrusted output
        d = self.call("purchase.create_request", {"sku": "SKU-100", "qty": 3})  # in contract, write
        self.assertLess(self.prov(d)["score"], 0.15)
        self.assertEqual(d.band, "LOW")

    def test_out_of_contract_after_untrusted_input_is_amplified(self):
        self.call("doc.read", {"path": "supplier/quote_1.pdf"})
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertAlmostEqual(self.prov(d)["score"], 0.7 * math.exp(-1 / 10), places=2)
        self.assertEqual(self.prov(d)["details"]["sink"], "read_sensitive")
        self.assertFalse(self.prov(d)["details"]["justified"])
        self.assertIn("supplier/quote_1.pdf", self.prov(d)["reason"])
        self.assertGreater(d.risk, 58.0)                                     # more than role-fit alone

    def test_no_taint_means_zero_provenance_score(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertEqual(self.prov(d)["score"], 0.0)
        self.assertEqual(d.risk, 58.0)

    def test_taint_fades_with_age(self):
        self.call("doc.read", {"path": "supplier/quote_1.pdf"})
        near = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        for _ in range(6):
            self.call("erp.read_orders")                                      # trusted, in contract
        far = self.call("hr_files.list", {"path": "hr/"})
        self.assertLess(self.prov(far)["details"]["u_strength"], self.prov(near)["details"]["u_strength"])

    def test_explicit_context_registration(self):
        self.gw.register_context("p", "inbound-email-42", "untrusted")
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertGreater(self.prov(d)["score"], 0.0)
        self.assertEqual(self.prov(d)["details"]["source"], "inbound-email-42")

    def test_request_supplied_labels_count(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"},
                      [ContextLabel("web:evil.example", "untrusted", 1)])
        self.assertGreater(self.prov(d)["score"], 0.0)

    def test_owner_and_system_labels_never_taint(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"},
                      [ContextLabel("ticket-from-priya", "owner", 0), ContextLabel("sys", "system", 0)])
        self.assertEqual(self.prov(d)["score"], 0.0)

    def test_peer_agent_taint_counts_half(self):
        self.gw.register_context("p", "agent-b", "peer_agent")
        peer = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.gw.register_agent("q", "procurement_agent")
        self.gw.register_context("q", "web", "untrusted")
        raw = self.gw.handle_tool_call(ToolCallRequest("q", "hr_files.read", {"path": "hr/salaries_2026.xlsx"}))
        self.assertAlmostEqual(peer.lens["provenance"]["details"]["u_strength"] * 2,
                               raw.lens["provenance"]["details"]["u_strength"], places=2)

    def test_context_for_unknown_agent_rejected(self):
        from app.gateway.interceptor import UnknownAgent
        with self.assertRaises(UnknownAgent):
            self.gw.register_context("ghost", "x", "untrusted")


if __name__ == "__main__":
    unittest.main()
