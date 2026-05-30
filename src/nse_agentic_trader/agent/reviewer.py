from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.models import RiskDecision, TradeSignal


@dataclass(frozen=True)
class AgentReview:
    approved: bool
    summary: str
    concerns: list[str]


class TradeReviewer:
    def review(self, signal: TradeSignal, risk: RiskDecision) -> AgentReview:
        concerns: list[str] = []
        if signal.confidence < 0.55:
            concerns.append("Signal confidence is low")
        if not risk.approved:
            concerns.append(risk.reason)
        if signal.stop_loss is None:
            concerns.append("Trade has no stop loss")
        if not signal.invalidation and signal.action.value != "WAIT":
            concerns.append("Trade has no explicit invalidation condition")
        if signal.strategy_family and signal.strategy_family.value == "option_selling":
            concerns.append("Option selling is research/paper-only until additional controls exist")

        approved = risk.approved and not concerns
        strategy_label = signal.strategy_name or "unclassified_strategy"
        summary = (
            f"{signal.action.value} {signal.symbol} via {strategy_label}: {signal.reason}. "
            f"Risk decision: {risk.reason}, quantity={risk.quantity}."
        )
        return AgentReview(approved, summary, concerns)
