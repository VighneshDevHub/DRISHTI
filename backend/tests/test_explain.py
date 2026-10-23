import os
import sqlite3
import tempfile
import unittest
from app.models.events import ToolCallRequest
from app.risk.explain import render_text
from app.risk.owasp_map import ASI
from app.store.repo import Repo
from helpers import make_services
from simulator.client import WardenClient
from simulator.scenarios import s1_injection as s1


def attack(**flags):
    svc = make_services(**flags)
    s1.run(WardenClient(service=svc), "plain", history=10)
    newest_first = svc.repo.list_alerts()
    hr, exfil = newest_first[1], newest_first[0]
    return svc, svc.repo.get_alert(hr["id"])["explanation"], svc.repo.get_alert(exfil["id"])["explanation"]


class ExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svc, cls.hr, cls.exfil = attack()

    def test_headline_is_a_readable_sentence(self):
        h = self.hr["headline"]
        for part in ("procurement_agent", "hr_files.read", "hr/salaries_2026.xlsx", "ELEVATED", "STEP_UP"):
            self.assertIn(part, h)

    def test_at_most_three_reasons_strongest_first_with_measured_effect(self):
        reasons = self.hr["top_reasons"]
        self.assertLessEqual(len(reasons), 3)
        self.assertEqual(reasons[0]["lens"], "role")
        deltas = [r["delta"] for r in reasons]
        self.assertEqual(deltas, sorted(deltas, reverse=True))
        for r in reasons:
            self.assertLessEqual(r["risk_without"], self.hr["event_risk"])
            self.assertAlmostEqual(r["delta"], self.hr["event_risk"] - r["risk_without"], delta=0.11)

    def test_detection_survives_losing_any_single_lens(self):
        """Defence in depth, measured: remove any one detector and the HR read is still a step-up."""
        worst = min(v["risk_without"] for v in self.hr["leave_one_out"].values())
        self.assertGreaterEqual(worst, 60.0)
        self.assertGreaterEqual(len(self.hr["leave_one_out"]), 3)

    def test_conclusive_evidence_leads_and_is_labelled(self):
        first = self.exfil["top_reasons"][0]
        self.assertEqual(first["kind"], "conclusive")
        self.assertIn("protected data is leaving", first["text"])
        self.assertEqual(self.exfil["band"], "CRITICAL")
        self.assertEqual(self.exfil["recommended_action"], "ISOLATE")

    def test_timeline_is_a_causal_chain_not_noise(self):
        t = self.hr["evidence_timeline"]
        self.assertLessEqual(len(t), 8)
        ids = [e["event_id"] for e in t]
        self.assertEqual(ids, sorted(ids))                                    # chronological
        self.assertEqual(sum(e["is_trigger"] for e in t), 1)
        annotated = [e for e in t if e["role_in_chain"]]
        self.assertEqual(len(annotated), 2)                                    # exactly: the source and the trigger
        self.assertIn("untrusted source", annotated[0]["role_in_chain"])
        self.assertIn("quote_3_plain.pdf", annotated[0]["resource"])
        self.assertTrue(annotated[1]["is_trigger"])

    def test_owasp_tags_use_the_real_taxonomy_and_say_why(self):
        ids = {o["id"] for o in self.hr["owasp"]}
        self.assertTrue({"ASI01", "ASI03"} <= ids)
        self.assertIn("ASI10", {o["id"] for o in self.exfil["owasp"]})
        for o in self.hr["owasp"] + self.exfil["owasp"]:
            self.assertEqual(o["name"], ASI[o["id"]])
            self.assertTrue(len(o["because"]) > 20)
        self.assertEqual(ASI["ASI01"], "Agent Goal Hijack")
        self.assertEqual(ASI["ASI03"], "Identity and Privilege Abuse")
        self.assertEqual(ASI["ASI10"], "Rogue Agents")
        self.assertEqual(len(ASI), 10)

    def test_counterfactuals_exist_and_are_honest_about_decoys(self):
        self.assertTrue(self.hr["what_would_change_the_verdict"])
        self.assertTrue(any("no counterfactual" in h for h in self.exfil["what_would_change_the_verdict"]))

    def test_text_report_contains_every_section(self):
        txt = render_text(self.hr)
        for section in ("Why (strongest first)", "Evidence timeline", "OWASP Agentic Top 10", "What would change"):
            self.assertIn(section, txt)

    def test_explanation_is_persisted_and_retrievable(self):
        alert = self.svc.repo.list_alerts()[1]
        self.assertNotIn("explanation", alert)                                # list stays light
        full = self.svc.repo.get_alert(alert["id"])
        self.assertEqual(full["explanation"]["risk"], alert["risk"])
        self.assertIsNone(self.svc.repo.get_alert("alr_9999"))
        self.assertIsNone(self.svc.repo.get_alert("nonsense"))

    def test_watch_level_alerts_are_explained_and_quiet_events_create_none(self):
        s = make_services()
        s.gateway.register_agent("a", "procurement_agent")
        quiet = s.gateway.handle_tool_call(ToolCallRequest("a", "supplier_api.get_price", {"sku": "SKU-100"}))
        self.assertIsNone(quiet.alert_id)
        d = s.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.list", {"path": "hr/"}))
        self.assertEqual(d.band, "ELEVATED") if d.band == "ELEVATED" else self.assertIn(d.band, ("WATCH", "ELEVATED"))
        self.assertTrue(s.repo.get_alert(d.alert_id)["explanation"]["top_reasons"])

    def test_session_boost_is_called_out_in_the_report(self):
        s = make_services(enable_baseline=False, enable_drift=False)
        s.gateway.register_agent("a", "procurement_agent")
        for _ in range(4):
            d = s.gateway.handle_tool_call(ToolCallRequest("a", "hr_files.list", {"path": "hr/"}))
        x = s.repo.get_alert(d.alert_id)["explanation"]
        self.assertTrue(x["session"]["raised_by_session"])
        self.assertIn("session risk", render_text(x))


class MigrationTests(unittest.TestCase):
    def test_old_database_without_explanations_is_upgraded(self):
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        con = sqlite3.connect(path)
        con.executescript("""CREATE TABLE alerts (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
            agent_id TEXT NOT NULL, event_id TEXT NOT NULL, risk REAL NOT NULL, band TEXT NOT NULL,
            shadow_action TEXT NOT NULL, reasons_json TEXT NOT NULL, lens_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open');
            INSERT INTO alerts(ts,agent_id,event_id,risk,band,shadow_action,reasons_json,lens_json)
            VALUES ('t','a','evt_000001',58,'WATCH','WATCH','[]','{}');""")
        con.commit(); con.close()
        repo = Repo(path)
        self.assertEqual(repo.get_alert("alr_0001")["explanation"], {})        # old row survives, gets an empty explanation
        self.assertEqual(len(repo.list_alerts()), 1)


if __name__ == "__main__":
    unittest.main()
