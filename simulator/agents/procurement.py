from simulator.agents.base import SimAgent


class ProcurementAgent(SimAgent):
    role = "procurement_agent"
    start_state = "doc.read"
    chain = {
        "doc.read": [("supplier_api.get_price", 0.8), ("supplier_api.list_catalog", 0.2)],
        "supplier_api.list_catalog": [("supplier_api.get_price", 1.0)],
        "supplier_api.get_price": [("purchase.create_request", 0.6), ("supplier_api.get_price", 0.2),
                                   ("erp.read_orders", 0.2)],
        "purchase.create_request": [("doc.read", 0.5), ("erp.read_orders", 0.2),
                                    ("supplier_api.list_catalog", 0.3)],
        "erp.read_orders": [("supplier_api.get_price", 0.7), ("doc.read", 0.3)],
    }

    def args_for(self, tool: str) -> dict:
        sku = self.rng.choice(["SKU-100", "SKU-200", "SKU-300"])
        return {
            "doc.read": {"path": self.rng.choice(["supplier/quote_1.pdf", "supplier/quote_2.pdf"])},
            "supplier_api.get_price": {"sku": sku},
            "supplier_api.list_catalog": {"supplier": "Supplier A"},
            "purchase.create_request": {"sku": sku, "qty": self.rng.randint(1, 20)},
            "erp.read_orders": {},
        }[tool]
