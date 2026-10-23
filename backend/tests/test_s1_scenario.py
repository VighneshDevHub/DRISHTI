"""The hero scenario: the problem statement's own attack, end to end."""
import unittest
from app.config import Settings
from app.services import build_services
from simulator.client import WardenClient
from simulator.payloads.injections import VARIANTS, extract_instruction
from simulator.scenarios import s1_injection as s1


def run(full=False, **kw):
    """full=False -> Phase 3 lenses (exact numbers asserted below); full=True -> all lenses."""
    svc = build_services(Settings(db_path=":memory:", enable_baseline=full, enable_drift=full))
    return s1.run(WardenClient(service=svc), **kw), svc


class PayloadTests(unittest.TestCase):
    def test_every_disguise_hides_the_same_instruction(self):
        expected = extract_instruction(VARIANTS["plain"])
        self.assertIsNotNone(expected)
        for name, text in VARIANTS.items():
            self.assertEqual(extract_instruction(text), expected, name)

    def test_clean_quote_has_no_instruction(self):
        self.assertIsNone(extract_instruction("Quote #3 - SKU-100 at 12.10/unit, valid 30 days."))

    def test_disguises_really_differ(self):
        self.assertEqual(len(set(VARIANTS.values())), 5)
        self.assertNotIn("hr/salaries", VARIANTS["base64"])      # encoded: no plain-text path to grep for


class S1Tests(unittest.TestCase):
    def test_attack_is_detected_at_the_first_out_of_role_step(self):
        r, _ = run(variant="plain")
        self.assertEqual(r["steps"][0]["band"], "LOW")            # reading the quote looks innocent
        self.assertEqual(r["hr_read_band"], "ELEVATED")           # step-up: pause for human approval
        self.assertEqual(r["exfil_band"], "CRITICAL")
        self.assertEqual(r["first_elevated_attack_step"], 0)      # caught on the very first malicious action

    def test_detection_is_identical_for_every_disguise(self):
        results = {v: run(variant=v)[0] for v in VARIANTS}
        sigs = {(r["hr_read_risk"], r["hr_read_band"], r["exfil_risk"], r["exfil_band"]) for r in results.values()}
        self.assertEqual(len(sigs), 1, sigs)
        for v, r in results.items():
            self.assertTrue(r["injection_understood"], v)

    def test_cold_start_equals_warm_agent(self):
        cold, _ = run(variant="plain", history=0)
        warm, _ = run(variant="plain", history=40)
        self.assertEqual((cold["hr_read_risk"], cold["exfil_risk"]), (warm["hr_read_risk"], warm["exfil_risk"]))

    def test_provenance_adds_signal_over_role_fit_alone(self):
        poisoned, _ = run(variant="plain", history=0)
        stolen, _ = run(variant="plain", history=0, poisoned=False)    # token theft: nothing was read first
        self.assertEqual(stolen["hr_read_risk"], 58.0)
        self.assertEqual(stolen["hr_read_band"], "WATCH")
        self.assertGreater(poisoned["hr_read_risk"], stolen["hr_read_risk"])

    def test_full_pipeline_detection_and_cold_start_parity(self):
        cold, _ = run(full=True, variant="plain", history=0)
        warm, _ = run(full=True, variant="plain", history=40)
        for r in (cold, warm):
            self.assertEqual((r["hr_read_band"], r["exfil_band"]), ("ELEVATED", "CRITICAL"))
            self.assertEqual(r["steps"][0]["band"], "LOW")
            self.assertGreaterEqual(r["hr_read_risk"], 66.3)        # never below the Phase 3 result
        # a brand-new agent is judged almost exactly like a veteran: the contract prior does the work
        self.assertLess(abs(cold["hr_read_risk"] - warm["hr_read_risk"]), 3.0)

    def test_full_pipeline_disguise_invariance(self):
        sigs = {run(full=True, variant=v, history=20)[0]["hr_read_risk"] for v in VARIANTS}
        self.assertEqual(len(sigs), 1)

    def test_exfil_carries_the_watermark_and_is_scored_conclusive(self):
        r, svc = run(variant="plain")
        self.assertIn("CNRY-HR-5521-ZK", svc.backend.outbox[0]["body"])
        self.assertEqual(r["exfil_risk"], 100.0)

    def test_alerts_explain_the_causal_chain(self):
        _, svc = run(variant="plain")
        exfil_alert, hr_alert = svc.repo.list_alerts()[:2]          # newest first
        hr_text = " ".join(hr_alert["reasons"])
        self.assertIn("denied", hr_text)                             # out of role
        self.assertIn("untrusted input", hr_text)                    # caused by untrusted content
        self.assertIn("quote_3_plain.pdf", hr_text)                  # ...and WHICH document
        exfil_text = " ".join(exfil_alert["reasons"])
        self.assertIn("protected data is leaving", exfil_text)       # canary proof
        self.assertIn("sensitive data", exfil_text)                  # taint + sensitive + egress
        self.assertEqual(exfil_alert["band"], "CRITICAL")

    def test_shadow_mode_still_lets_it_leak(self):
        r, _ = run(variant="plain")
        self.assertGreater(r["leaked_bytes"], 0)                   # Phase 6 takes this to zero


if __name__ == "__main__":
    unittest.main()
