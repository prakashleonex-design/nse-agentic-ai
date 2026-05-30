from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from nse_agentic_trader.agent.reviewer import AgentReview
from nse_agentic_trader.models import OrderResult, RiskDecision, TradeSignal


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(
        self,
        signal: TradeSignal,
        risk: RiskDecision,
        review: AgentReview,
        order: OrderResult | None,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._fields())
            if is_new:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "side": signal.side.value if signal.side else "",
                    "entry": signal.entry_price or "",
                    "stop_loss": signal.stop_loss or "",
                    "target": signal.target or "",
                    "confidence": signal.confidence,
                    "risk_approved": risk.approved,
                    "quantity": risk.quantity,
                    "agent_approved": review.approved,
                    "summary": review.summary,
                    "order_id": order.order_id if order else "",
                    "order_message": order.message if order else "",
                }
            )

    @staticmethod
    def _fields() -> list[str]:
        return [
            "timestamp",
            "symbol",
            "action",
            "side",
            "entry",
            "stop_loss",
            "target",
            "confidence",
            "risk_approved",
            "quantity",
            "agent_approved",
            "summary",
            "order_id",
            "order_message",
        ]
