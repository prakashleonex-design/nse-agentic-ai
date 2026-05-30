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

        approved = risk.approved and not concerns
        summary = (
            f"{signal.action.value} {signal.symbol}: {signal.reason}. "
            f"Risk decision: {risk.reason}, quantity={risk.quantity}."
        )
        return AgentReview(approved, summary, concerns)

