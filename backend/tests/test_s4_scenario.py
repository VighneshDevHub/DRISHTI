"""S4: slow drift. These assertions are the honest results, including the limits."""
import unittest
from app.config import Settings
from app.services import build_services
from simulator.client import WardenClient
from simulator.scenarios import s4_slow_drift as s4


def run(broad, **flags):
    svc = build_services(Settings(db_path=":memory:", **flags))
    return s4.run(WardenClient(service=svc), broad_contract=broad)


class S4TightContract(unittest.TestCase):
    def test_full_system_forces_a_decision_by_the_third_capability(self):
        r = run(False)
        self.assertEqual(r["first_watch_capability"], 1)       # each step is visible individually
        self.assertEqual(r["first_elevated_capability"], 3)    # cumulative growth forces step-up
        self.assertEqual(r["final_attack_band"], "ELEVATED")

    def test_rolling_baseline_alone_never_escalates(self):
        for flags in (dict(enable_drift=False, learn_gate=False), dict(enable_drift=False)):
            r = run(False, **flags)
            self.assertIsNone(r["first_elevated_capability"], flags)

    def test_a_rolling_baseline_habituates_to_the_attack(self):
        r = run(False, enable_drift=False, learn_gate=False)
        drops = [c["first_use_risk"] - c["last_use_risk"] for c in r["per_capability"]]
        self.assertGreater(max(drops), 5.0)                    # repeated use makes the attack look more normal

    def test_legitimate_work_is_never_disrupted(self):
        r = run(False)
        self.assertEqual(r["normal_alerts"], 0)
        self.assertLess(r["normal_max_risk"], 15)


class S4OverBroadContract(unittest.TestCase):
    """The hard case: every step is PERMITTED, so role-fit sees nothing."""

    def test_without_drift_the_attacker_is_completely_invisible(self):
        for flags in (dict(enable_drift=False, learn_gate=False), dict(enable_drift=False)):
            r = run(True, **flags)
            self.assertIsNone(r["first_watch_capability"], flags)
            self.assertLess(r["max_attack_risk"], 30)

    def test_full_system_catches_it_but_only_at_the_fifth_capability(self):
        r = run(True)
        self.assertEqual(r["first_elevated_capability"], 5)
        self.assertEqual(r["final_attack_band"], "ELEVATED")

    def test_documented_limit_early_steps_slip_through(self):
        """We do NOT claim to catch the first steps: doing so would flag normal exploration."""
        r = run(True)
        early = [c["max_risk"] for c in r["per_capability"][:2]]
        self.assertTrue(all(x < 30 for x in early), early)     # capabilities 1-2 stay LOW

    def test_legitimate_work_is_never_disrupted(self):
        r = run(True)
        self.assertEqual(r["normal_alerts"], 0)


if __name__ == "__main__":
    unittest.main()
