import unittest
from app.config import Settings
from app.gateway.token_service import TokenBroker
from app.gateway.tool_registry import ToolRegistry
from app.contracts.loader import ContractStore
from app.response.policies import ISOLATED, NORMAL, RESTRICTED, restricted_scope, scopes_for
from helpers import FakeClock


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.b = TokenBroker(self.clock, ttl=300)

    def test_issue_and_validate(self):
        rec = self.b.issue("a", {"*"})
        ok, reason, got = self.b.validate(rec.token, "a")
        self.assertEqual((ok, reason, got), (True, None, rec))

    def test_failure_reasons(self):
        rec = self.b.issue("a", {"*"})
        self.assertEqual(self.b.validate(None, "a")[1], "token_missing")
        self.assertEqual(self.b.validate("wt_nonsense", "a")[1], "token_invalid")
        self.assertEqual(self.b.validate(rec.token, "someone-else")[1], "token_invalid")   # tokens are not transferable
        self.b.revoke_all("a")
        self.assertEqual(self.b.validate(rec.token, "a")[1], "token_revoked")

    def test_tokens_are_short_lived(self):
        rec = self.b.issue("a", {"*"})
        self.clock.advance(299)
        self.assertTrue(self.b.validate(rec.token, "a")[0])
        self.clock.advance(2)
        self.assertEqual(self.b.validate(rec.token, "a")[1], "token_expired")

    def test_a_new_token_revokes_the_old_one(self):
        """Nobody can keep clinging to a wide token after a narrower one was issued."""
        wide = self.b.issue("a", {"*"})
        narrow = self.b.issue("a", {"doc.read"})
        self.assertEqual(self.b.validate(wide.token, "a")[1], "token_revoked")
        self.assertTrue(self.b.validate(narrow.token, "a")[0])

    def test_narrow_takes_effect_immediately_on_live_tokens(self):
        rec = self.b.issue("a", {"*"})
        self.assertTrue(self.b.allows(rec, "http.post"))
        self.assertEqual(self.b.narrow("a", {"doc.read"}), 1)
        self.assertTrue(self.b.allows(rec, "doc.read"))
        self.assertFalse(self.b.allows(rec, "http.post"))

    def test_agents_are_independent(self):
        a, b = self.b.issue("a", {"*"}), self.b.issue("b", {"*"})
        self.b.revoke_all("a")
        self.assertTrue(self.b.validate(b.token, "b")[0])

    def test_active_returns_the_newest_live_token(self):
        self.assertIsNone(self.b.active("a"))
        rec = self.b.issue("a", {"*"})
        self.assertEqual(self.b.active("a"), rec)
        self.clock.advance(1000)
        self.assertIsNone(self.b.active("a"))


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.reg = ToolRegistry()
        self.contracts = ContractStore(); self.contracts.load_dir(Settings().contracts_dir)

    def test_normal_is_the_wide_credential_and_isolated_is_nothing(self):
        c = self.contracts.get("procurement_agent")
        self.assertEqual(scopes_for(NORMAL, c, self.reg, set()), {"*"})
        self.assertEqual(scopes_for(ISOLATED, c, self.reg, set()), set())

    def test_restricted_is_the_routine_without_egress(self):
        scope = restricted_scope(self.contracts.get("procurement_agent"), self.reg, set())
        self.assertEqual(scope, {"doc.read", "supplier_api.get_price", "supplier_api.list_catalog",
                                 "purchase.create_request", "erp.read_orders"})
        self.assertNotIn("http.post", scope)
        self.assertNotIn("hr_files.read", scope)

    def test_restricted_never_exceeds_the_contract(self):
        scope = restricted_scope(self.contracts.get("procurement_agent"), self.reg, {"hr_files.read", "http.post"})
        self.assertNotIn("hr_files.read", scope)          # learned, but the contract does not allow it

    def test_restricted_keeps_a_roles_legitimately_sensitive_routine(self):
        """A support agent reads customer records for a living; restricting it must not cut that off."""
        scope = restricted_scope(self.contracts.get("support_agent"), self.reg, set())
        self.assertIn("crm.read_customer", scope)
        self.assertIn("support.reply_ticket", scope)

    def test_egress_is_always_removed_even_for_a_contract_that_allows_it(self):
        from app.models.contracts import RoleContract
        c = RoleContract.from_dict({"role": "r", "version": 1, "purpose": "x", "allowed_tools": ["http.post", "doc.read"],
                                    "allowed_resource_classes": ["documents"], "typical_sequences": [["doc.read", "http.post"]]})
        self.assertEqual(restricted_scope(c, self.reg, set()), {"doc.read"})


if __name__ == "__main__":
    unittest.main()
