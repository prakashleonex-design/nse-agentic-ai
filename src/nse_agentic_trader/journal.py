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
                    "strategy_name": signal.strategy_name,
                    "strategy_family": signal.strategy_family.value if signal.strategy_family else "",
                    "action": signal.action.value,
                    "side": signal.side.value if signal.side else "",
                    "entry": signal.entry_price or "",
                    "stop_loss": signal.stop_loss or "",
                    "target": signal.target or "",
                    "invalidation": signal.invalidation,
                    "expected_holding_minutes": signal.expected_holding_minutes or "",
                    "blocked_by_filters": signal.blocked_by_filters,
                    "filter_reasons": "; ".join(signal.filter_reasons),
                    "confidence": signal.confidence,
                    "risk_approved": risk.approved,
                    "quantity": risk.quantity,
                    "agent_approved": review.approved,
                    "review_verdict": review.verdict.value,
                    "review_concerns": "; ".join(review.concerns),
                    "review_checklist": "; ".join(review.checklist or []),
                    "risk_reward": f"{review.risk_reward:.2f}" if review.risk_reward is not None else "",
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
            "strategy_name",
            "strategy_family",
            "action",
            "side",
            "entry",
            "stop_loss",
            "target",
            "invalidation",
            "expected_holding_minutes",
            "blocked_by_filters",
            "filter_reasons",
            "confidence",
            "risk_approved",
            "quantity",
            "agent_approved",
            "review_verdict",
            "review_concerns",
            "review_checklist",
            "risk_reward",
            "summary",
            "order_id",
            "order_message",
        ]
