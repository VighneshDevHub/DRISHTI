import unittest
from app.models.events import LensResult
from app.risk.engine import fuse


def L(name, score, **details):
    return LensResult(name, score, f"{name} reason", details=details)


class FusionTests(unittest.TestCase):
    def test_no_signal_is_zero(self):
        f = fuse({"role": L("role", 0), "provenance": L("provenance", 0), "decoy": L("decoy", 0)}, 0.5)
        self.assertEqual((f.risk, f.floors), (0.0, []))

    def test_single_lens_matches_phase2_formula(self):
        f = fuse({"role": L("role", 1.0)}, 0.45)
        self.assertEqual(f.risk, 58.0)

    def test_noisy_or_compounds_independent_signals(self):
        alone = fuse({"role": L("role", 1.0)}, 0.45).risk
        both = fuse({"role": L("role", 1.0), "provenance": L("provenance", 0.633)}, 0.45).risk
        self.assertGreater(both, alone)
        self.assertEqual(both, 66.3)

    def test_more_evidence_never_lowers_risk(self):
        base = fuse({"role": L("role", 0.6)}, 0.3).risk
        more = fuse({"role": L("role", 0.6), "provenance": L("provenance", 0.2)}, 0.3).risk
        self.assertGreaterEqual(more, base)

    def test_impact_scales_the_result(self):
        low = fuse({"role": L("role", 1.0)}, 0.0).risk
        high = fuse({"role": L("role", 1.0)}, 1.0).risk
        self.assertEqual((low, high), (40.0, 80.0))

    def test_unknown_lens_names_are_ignored(self):
        self.assertEqual(fuse({"mystery": L("mystery", 1.0)}, 1.0).risk, 0.0)

    def test_floors(self):
        touch = fuse({"decoy": L("decoy", 1.0, kind="touch")}, 0.0)
        self.assertEqual(touch.risk, 85.0)
        canary = fuse({"decoy": L("decoy", 1.0, kind="canary_exfil")}, 0.0)
        self.assertEqual(canary.risk, 100.0)
        listing = fuse({"decoy": L("decoy", 0.4, kind="list")}, 0.0)
        self.assertEqual(listing.floors, [])

    def test_tainted_sensitive_egress_floor_needs_all_three_conditions(self):
        base = dict(tainted=True, sink="egress_external", sensitive_in_context=["hr_files.read:hr/x"])
        self.assertEqual(fuse({"provenance": L("provenance", 0.1, **base)}, 0.0).risk, 95.0)
        for off in ({"tainted": False}, {"sink": "write"}, {"sensitive_in_context": []}):
            f = fuse({"provenance": L("provenance", 0.1, **{**base, **off})}, 0.0)
            self.assertLess(f.risk, 95.0, off)

    def test_contributions_sorted_strongest_first(self):
        f = fuse({"role": L("role", 0.3), "provenance": L("provenance", 0.9), "decoy": L("decoy", 0.0)}, 0.5)
        self.assertEqual(f.contributions[0][0], "provenance")


if __name__ == "__main__":
    unittest.main()
