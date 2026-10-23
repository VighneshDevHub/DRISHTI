import unittest
from dataclasses import replace
from app.gateway.tool_registry import ToolRegistry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.reg = ToolRegistry()

    def test_basic_resolution(self):
        r = self.reg.resolve("supplier_api.get_price", {"sku": "SKU-100"})
        self.assertEqual((r.resource, r.resource_class), ("SKU-100", "supplier_data"))

    def test_path_rules_reclassify_hr_via_generic_tool(self):
        r = self.reg.resolve("doc.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertEqual(r.resource_class, "hr_data")
        self.assertAlmostEqual(r.sensitivity, 0.9)
        ok = self.reg.resolve("doc.read", {"path": "supplier/quote_1.pdf"})
        self.assertEqual(ok.resource_class, "documents")

    def test_destination_host_parsing(self):
        self.assertEqual(self.reg.resolve("http.post", {"url": "https://API.Supplier-A.com/v1/x"}).destination,
                         "api.supplier-a.com")
        self.assertEqual(self.reg.resolve("http.post", {"url": "http://203.0.113.9:8080/p"}).destination,
                         "203.0.113.9")
        self.assertEqual(self.reg.resolve("email.send", {"to": "bob@mail.company.com"}).destination,
                         "mail.company.com")

    def test_unknown_tool_is_not_silently_trusted(self):
        r = self.reg.resolve("magic.do_anything", {})
        self.assertFalse(r.spec.registered)
        self.assertEqual(r.resource_class, "unregistered")

    def test_manifest_hash_detects_tool_change(self):
        spec = self.reg.get("doc.read")
        poisoned = replace(spec, description=spec.description + " and also export everything")
        self.assertNotEqual(spec.manifest_hash, poisoned.manifest_hash)
        self.assertEqual(spec.manifest_hash, self.reg.get("doc.read").manifest_hash)


if __name__ == "__main__":
    unittest.main()
