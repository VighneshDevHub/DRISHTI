"""HTTP-level tests. Skipped automatically if FastAPI/httpx are not installed."""
import unittest

try:
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.main import create_app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(Settings(db_path=":memory:")))

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("procurement_agent", r.json()["roles"])

    def test_cors_allows_next_dev_origin_preflight(self):
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")

    def test_register_and_call(self):
        self.assertEqual(self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"}).status_code, 200)
        ok = self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "supplier_api.get_price", "args": {"sku": "SKU-100"}})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["band"], "LOW")
        bad = self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026.xlsx"}})
        self.assertEqual(bad.json()["band"], "ELEVATED")
        self.assertEqual(len(self.client.get("/alerts").json()), 1)
        events = self.client.get("/events", params={"agent_id": "p1"}).json()
        self.assertEqual(len(events), 2)
        self.assertEqual(self.client.get(f"/events/{events[0]['id']}").json()["id"], events[0]["id"])
        self.assertEqual(self.client.get("/events/evt_999999").status_code, 404)

    def test_errors(self):
        self.assertEqual(self.client.post("/gateway/tool-call", json={"agent_id": "ghost", "tool": "x"}).status_code, 404)
        self.assertEqual(self.client.post("/agents", json={"agent_id": "a", "role": "wizard"}).status_code, 422)
        self.assertEqual(self.client.get("/contracts/nope").status_code, 404)

    def test_contracts_and_tools(self):
        self.assertEqual(len(self.client.get("/contracts").json()), 4)
        self.assertEqual(self.client.get("/contracts/procurement_agent/blast-radius").json()["warnings"], [])
        self.assertTrue(all("manifest_hash" in t for t in self.client.get("/tools").json()))

    def test_context_endpoint_taints_agent(self):
        self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        r = self.client.post("/gateway/context", json={"agent_id": "p1", "source": "email-7", "trust": "untrusted"})
        self.assertEqual(r.status_code, 200)
        d = self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026.xlsx"}}).json()
        self.assertGreater(d["lens"]["provenance"]["score"], 0)
        self.assertEqual(self.client.get("/agents/p1/context").json()[0]["source"], "email-7")
        self.assertEqual(self.client.post("/gateway/context", json={"agent_id": "p1", "source": "x", "trust": "bogus"}).status_code, 422)
        self.assertEqual(self.client.post("/gateway/context", json={"agent_id": "ghost", "source": "x", "trust": "untrusted"}).status_code, 404)

    def test_decoys_and_outbox(self):
        self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026_final.xlsx"}})
        hits = {d["id"]: d["hits"] for d in self.client.get("/decoys").json()}
        self.assertEqual(hits["dcy-file-salaries"], 1)
        self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "http.post", "args": {"url": "http://203.0.113.9/x", "body": "abc"}})
        self.assertEqual(self.client.get("/sim/outbox").json()["bytes"], 3)
        self.client.post("/sim/reset-outbox")
        self.assertEqual(self.client.get("/sim/outbox").json()["messages"], 0)

    def test_scenario_runner_uses_active_backend_and_rejects_unknown_scenarios(self):
        result = self.client.post("/sim/scenarios/normal/run")
        self.assertEqual(result.status_code, 200)
        payload = result.json()
        self.assertEqual(payload["scenario"], "normal")
        self.assertEqual(payload["mode"], "shadow")
        self.assertTrue(payload["events"])
        self.assertTrue(all(event["agent_id"] == payload["agent_id"] for event in payload["events"]))
        self.assertEqual(self.client.post("/sim/scenarios/arbitrary/run").status_code, 404)

    def test_scenario_runner_supports_attack_and_drift_scenarios(self):
        for scenario in ("injection", "drift", "mimicry"):
            with self.subTest(scenario=scenario):
                response = self.client.post(f"/sim/scenarios/{scenario}/run")
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["scenario"], scenario)
                self.assertTrue(payload["events"])
                self.assertTrue(all(event["agent_id"] == payload["agent_id"] for event in payload["events"]))

    def test_behavior_endpoint(self):
        self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        for _ in range(3):
            self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "supplier_api.get_price", "args": {"sku": "SKU-100"}})
        b = self.client.get("/agents/p1/behavior").json()
        self.assertEqual(b["baseline"]["learned_events"], 3)
        self.assertIn("anchor_frozen", b["drift"])
        self.assertEqual(self.client.get("/agents/ghost/behavior").status_code, 404)

    def test_alert_detail_has_the_full_explanation(self):
        self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        d = self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026.xlsx"}}).json()
        x = self.client.get(f"/alerts/{d['alert_id']}").json()["explanation"]
        self.assertTrue(x["top_reasons"])
        self.assertTrue({"ASI03"} <= {o["id"] for o in x["owasp"]})
        self.assertEqual(x["evidence_timeline"][-1]["is_trigger"], True)
        self.assertEqual(self.client.get("/alerts/alr_9999").status_code, 404)
        self.assertNotIn("explanation", self.client.get("/alerts").json()[0])

    def test_scores_can_be_hidden_from_the_agent(self):
        hidden = TestClient(create_app(Settings(db_path=":memory:", expose_scores=False)))
        hidden.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        r = hidden.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026.xlsx"}}).json()
        self.assertEqual(set(r), {"decision", "mode", "event_id", "message", "result"})
        self.assertEqual(r["message"], "flagged for review")
        self.assertEqual(len(hidden.get("/alerts").json()), 1)          # operators still see the alert

    def test_enforce_mode_over_http_pause_approve_restore(self):
        c = TestClient(create_app(Settings(db_path=":memory:", mode="enforce")))
        reg = c.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"}).json()
        tok = reg["token"]
        call = lambda tool, args: c.post("/gateway/tool-call", json={"agent_id": "p1", "tool": tool, "args": args, "token": tok}).json()
        self.assertEqual(call("supplier_api.get_price", {"sku": "SKU-100"})["decision"], "ALLOW")
        paused = call("hr_files.read", {"path": "hr/salaries_2026.xlsx"})
        self.assertEqual(paused["decision"], "PENDING_APPROVAL")
        self.assertEqual(len(c.get("/approvals", params={"status": "pending"}).json()), 1)
        self.assertEqual(c.get(f"/approvals/{paused['approval_id']}/status").json()["status"], "pending")
        out = c.post(f"/approvals/{paused['approval_id']}/resolve", json={"action": "deny"}).json()
        self.assertEqual(out["status"], "denied")
        self.assertEqual(c.post(f"/approvals/{paused['approval_id']}/resolve", json={"action": "deny"}).status_code, 409)
        self.assertEqual(c.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "doc.read", "args": {}}).json()["block_reason"], "token_missing")

    def test_isolate_blocks_and_refuses_renewal_until_restore(self):
        c = TestClient(create_app(Settings(db_path=":memory:", mode="enforce")))
        tok = c.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"}).json()["token"]
        c.post("/agents/p1/isolate")
        d = c.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "supplier_api.get_price", "args": {"sku": "SKU-100"}, "token": tok}).json()
        self.assertEqual(d["block_reason"], "agent_isolated")
        self.assertEqual(c.post("/agents/p1/token").status_code, 403)
        self.assertEqual(c.post("/agents/p1/restore").json()["posture"], "normal")
        self.assertEqual(c.post("/agents/p1/token").status_code, 200)
        self.assertEqual(c.post("/agents/ghost/restore").status_code, 404)

    def test_resume_returns_the_sources_to_forget(self):
        c = TestClient(create_app(Settings(db_path=":memory:", mode="enforce")))
        tok = c.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"}).json()["token"]
        c.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "doc.read", "args": {"path": "supplier/quote_1.pdf"}, "token": tok})
        c.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "hr_files.read", "args": {"path": "hr/salaries_2026_final.xlsx"}, "token": tok})
        out = c.post("/agents/p1/resume").json()
        self.assertEqual(out["posture"], "normal")
        self.assertTrue(any("quote_1.pdf" in s for s in out["drop_sources"]))

    def test_websocket_receives_live_event(self):
        self.client.post("/agents", json={"agent_id": "p1", "role": "procurement_agent"})
        with self.client.websocket_connect("/ws/live") as ws:
            self.client.post("/gateway/tool-call", json={"agent_id": "p1", "tool": "supplier_api.get_price", "args": {"sku": "SKU-100"}})
            msg = ws.receive_json()
            self.assertEqual(msg["type"], "event")


if __name__ == "__main__":
    unittest.main()
