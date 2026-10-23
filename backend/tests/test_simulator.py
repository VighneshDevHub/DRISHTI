"""Normal traffic must not raise alerts: the false-positive guard for Phases 1-2."""
import unittest
from app.config import Settings
from app.services import build_services
from simulator.agents.procurement import ProcurementAgent
from simulator.agents.support import SupportAgent
from simulator.client import WardenClient


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.svc = build_services(Settings(db_path=":memory:"))
        self.client = WardenClient(service=self.svc)

    def test_normal_traffic_raises_zero_alerts(self):
        agents = [ProcurementAgent(f"proc-{i}", self.client, seed=1) for i in range(3)] + \
                 [SupportAgent(f"supp-{i}", self.client, seed=1) for i in range(3)]
        for a in agents:
            a.register()
            for d in a.run(300):
                self.assertEqual(d["band"], "LOW", d["message"])
        self.assertEqual(self.svc.repo.list_alerts(), [])
        self.assertEqual(sum(a["event_count"] for a in self.svc.repo.list_agents()), 1800)

    def test_same_seed_gives_identical_traffic(self):
        def trace(seed):
            svc = build_services(Settings(db_path=":memory:"))
            c = WardenClient(service=svc)
            a = ProcurementAgent("p", c, seed=seed); a.register()
            return [d["event"]["tool"] + str(d["event"]["resource"]) for d in a.run(50)]
        self.assertEqual(trace(5), trace(5))
        self.assertNotEqual(trace(5), trace(6))

    def test_hijacked_agent_is_flagged_on_first_out_of_role_action(self):
        a = ProcurementAgent("p", self.client, seed=3); a.register()   # zero history
        d = a.act("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertGreaterEqual(d["risk"], 30)
        self.assertIsNotNone(d["alert_id"])


if __name__ == "__main__":
    unittest.main()
