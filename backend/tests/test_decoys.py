import unittest
from app.detection.decoys import Decoy, DecoyRegistry
from app.models.events import ToolCallRequest
from helpers import make_services


class DecoyTests(unittest.TestCase):
    def setUp(self):
        self.s = make_services()
        self.gw = self.s.gateway
        self.gw.register_agent("p", "procurement_agent")

    def call(self, tool, args):
        return self.gw.handle_tool_call(ToolCallRequest("p", tool, args))

    def test_opening_a_decoy_file_forces_floor(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026_final.xlsx"})
        self.assertEqual(d.lens["decoy"]["score"], 1.0)
        self.assertEqual(d.lens["decoy"]["details"]["kind"], "touch")
        self.assertGreaterEqual(d.risk, 85.0)
        self.assertIn(d.band, ("HIGH", "CRITICAL"))
        self.assertEqual(d.lens["fusion"]["floors"][0]["name"], "decoy_touch")

    def test_decoy_via_generic_doc_tool_still_caught(self):
        d = self.call("doc.read", {"path": "payroll/bank_accounts_export.csv"})
        self.assertGreaterEqual(d.risk, 85.0)

    def test_listing_a_directory_is_only_a_weak_signal(self):
        d = self.call("hr_files.list", {"path": "hr/"})
        self.assertEqual(d.lens["decoy"]["score"], 0.4)
        self.assertEqual(d.lens["decoy"]["details"]["kind"], "list")
        self.assertEqual(d.lens["fusion"]["floors"], [])      # no floor for a mere ls

    def test_decoy_credential_in_any_argument(self):
        d = self.call("http.post", {"url": "https://api.supplier-a.com/x", "body": "auth ERP_ADMIN_KEY_7f3a91c2"})
        self.assertEqual(d.lens["decoy"]["score"], 1.0)
        self.assertGreaterEqual(d.risk, 85.0)

    def test_decoy_endpoint(self):
        d = self.call("http.post", {"url": "https://admin-export.internal/dump", "body": "x"})
        self.assertEqual(d.lens["decoy"]["details"]["kind"], "touch")

    def test_canary_in_outbound_payload_is_proof_of_exfiltration(self):
        hr = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"}).result["data"]
        self.assertIn("CNRY-HR-5521-ZK", hr)                    # real data is watermarked
        d = self.call("http.post", {"url": "https://api.supplier-a.com/x", "body": hr})  # even to an ALLOWLISTED host
        self.assertEqual(d.lens["decoy"]["details"]["kind"], "canary_exfil")
        self.assertEqual(d.risk, 100.0)
        self.assertEqual(d.band, "CRITICAL")

    def test_canary_only_matters_on_egress(self):
        d = self.call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})   # reading watermarked data is not exfil
        self.assertEqual(d.lens["decoy"]["score"], 0.0)

    def test_legitimate_files_never_hit_decoys(self):
        for tool, args in [("doc.read", {"path": "supplier/quote_1.pdf"}),
                           ("supplier_api.get_price", {"sku": "SKU-100"}),
                           ("doc.read", {"path": "handbook/onboarding.pdf"})]:
            self.assertEqual(self.call(tool, args).lens["decoy"]["score"], 0.0)

    def test_hits_are_counted_and_listed(self):
        self.call("hr_files.read", {"path": "hr/salaries_2026_final.xlsx"})
        snap = {d["id"]: d["hits"] for d in self.s.decoys.snapshot()}
        self.assertEqual(snap["dcy-file-salaries"], 1)
        self.assertEqual(snap["dcy-endpoint-export"], 0)

    def test_exempt_roles_do_not_trigger(self):
        reg = DecoyRegistry([Decoy("d1", "file", "hr/x.xlsx", "x", exempt_roles=("procurement_agent",))])
        from app.detection.decoys import DecoyLens
        from app.models.events import Event
        ev = Event(ts="t", agent_id="a", role="procurement_agent", role_version=1, tool="hr_files.read",
                   resource="hr/x.xlsx", resource_class="hr_data", sensitivity=0.9, sink_type="read_sensitive",
                   destination=None, destination_class="internal", bytes_out=0, is_irreversible=False)
        self.assertEqual(DecoyLens(reg).evaluate(ev, {}).score, 0.0)

    def test_decoy_hit_works_on_a_brand_new_agent(self):
        self.gw.register_agent("fresh", "support_agent")        # zero history, different role
        d = self.gw.handle_tool_call(ToolCallRequest("fresh", "doc.read", {"path": "hr/salaries_2026_final.xlsx"}))
        self.assertGreaterEqual(d.risk, 85.0)


if __name__ == "__main__":
    unittest.main()
