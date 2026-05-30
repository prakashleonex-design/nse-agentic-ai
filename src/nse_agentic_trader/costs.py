from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.broker.paper import PaperFill


@dataclass(frozen=True)
class CostModel:
    brokerage_per_order: float = 20.0
    transaction_cost_bps: float = 6.0

    def estimate_fill_cost(self, fill: PaperFill) -> float:
        turnover = abs(fill.fill_price * fill.quantity)
        variable_cost = turnover * self.transaction_cost_bps / 10000
        return round(self.brokerage_per_order + variable_cost, 2)
