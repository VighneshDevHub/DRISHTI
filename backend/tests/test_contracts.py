import unittest
from app.config import Settings
from app.contracts.loader import ContractStore, blast_radius
from app.gateway.tool_registry import ToolRegistry
from app.models.contracts import ContractError, RoleContract, parse_size


def valid(**over):
    d = {"role": "r", "version": 1, "purpose": "do things",
         "allowed_tools": ["a.b"], "allowed_resource_classes": ["x"]}
    d.update(over)
    return d


class ContractTests(unittest.TestCase):
    def test_templates_load(self):
        store = ContractStore()
        n = store.load_dir(Settings().contracts_dir)
        self.assertEqual(n, 4)
        self.assertEqual(store.roles(), ["devops_agent", "procurement_agent", "procurement_broad_agent", "support_agent"])
        c = store.get("procurement_agent")
        self.assertEqual(c.budgets.bytes_out_per_hour, 5 * 1024 ** 2)

    def test_parse_size(self):
        self.assertEqual(parse_size("5MB"), 5 * 1024 ** 2)
        self.assertEqual(parse_size(100), 100)
        with self.assertRaises(ContractError):
            parse_size("lots")

    def test_validation_errors(self):
        for bad in (valid(version=0), valid(allowed_tools=[]),
                    valid(data_sensitivity_ceiling="secret"),
                    valid(denied_resource_classes=["x"])):
            with self.assertRaises(ContractError):
                RoleContract.from_dict(bad)
        with self.assertRaises(ContractError):
            RoleContract.from_dict({"role": "r"})

    def test_wildcard_tool_match(self):
        c = RoleContract.from_dict(valid(allowed_tools=["supplier_api.*"]))
        self.assertTrue(c.tool_allowed("supplier_api.get_price"))
        self.assertFalse(c.tool_allowed("hr_files.read"))

    def test_versions_are_append_only(self):
        store = ContractStore()
        store.register(RoleContract.from_dict(valid()))
        store.register(RoleContract.from_dict(valid(version=2)))
        self.assertEqual(store.latest_version("r"), 2)
        self.assertEqual(store.get("r", 1).version, 1)
        with self.assertRaises(ContractError):
            store.register(RoleContract.from_dict(valid(version=2)))

    def test_the_deliberately_broad_example_is_flagged_by_blast_radius(self):
        store = ContractStore(); store.load_dir(Settings().contracts_dir)
        report = blast_radius(store.get("procurement_broad_agent"), ToolRegistry())
        self.assertTrue(any("wildcards" in w for w in report["warnings"]))
        self.assertGreater(len(report["tools"]), len(blast_radius(store.get("procurement_agent"), ToolRegistry())["tools"]))

    def test_blast_radius_flags_overbroad_contract(self):
        reg = ToolRegistry()
        wide = RoleContract.from_dict(valid(allowed_tools=["*"], egress_allowlist=["*"]))
        warnings = " ".join(blast_radius(wide, reg)["warnings"])
        self.assertIn("'*'", warnings)
        self.assertIn("egress_allowlist", warnings)
        tight = ContractStore(); tight.load_dir(Settings().contracts_dir)
        report = blast_radius(tight.get("procurement_agent"), reg)
        self.assertFalse(report["can_egress"])
        self.assertEqual(report["warnings"], [])


if __name__ == "__main__":
    unittest.main()
