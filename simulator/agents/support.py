from simulator.agents.base import SimAgent


class SupportAgent(SimAgent):
    role = "support_agent"
    start_state = "support.get_ticket"
    chain = {
        "support.get_ticket": [("crm.read_customer", 0.5), ("doc.read", 0.3), ("support.reply_ticket", 0.2)],
        "crm.read_customer": [("support.reply_ticket", 0.8), ("doc.read", 0.2)],
        "doc.read": [("support.reply_ticket", 0.9), ("support.get_ticket", 0.1)],
        "support.reply_ticket": [("support.get_ticket", 1.0)],
    }

    def args_for(self, tool: str) -> dict:
        tid = f"T-{self.rng.randint(1000, 1999)}"
        return {
            "support.get_ticket": {"ticket_id": tid},
            "support.reply_ticket": {"ticket_id": tid, "body": "Thanks for reaching out."},
            "crm.read_customer": {"customer_id": f"C-{self.rng.randint(1, 500)}"},
            "doc.read": {"path": "handbook/onboarding.pdf"},
        }[tool]
