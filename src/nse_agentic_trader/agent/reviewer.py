from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nse_agentic_trader.models import RiskDecision, TradeSignal


class ReviewVerdict(str, Enum):
    APPROVED = "APPROVED"
    CAUTION = "CAUTION"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class AgentReview:
    approved: bool
    summary: str
    concerns: list[str]
    verdict: ReviewVerdict = ReviewVerdict.REJECTED
    checklist: list[str] | None = None
    risk_reward: float | None = None


class TradeReviewer:
    def review(self, signal: TradeSignal, risk: RiskDecision) -> AgentReview:
        concerns: list[str] = []
        checklist = [
            "Stop loss present",
            "Target present",
            "Invalidation defined",
            "Risk limits checked",
            "Avoid-trade filters checked",
        ]
        risk_reward = _risk_reward(signal)
        if signal.confidence < 0.55:
            concerns.append("Signal confidence is low")
        if risk_reward is not None and risk_reward < 1.0:
            concerns.append("Reward/risk is below 1.0")
        if not risk.approved:
            concerns.append(risk.reason)
        if signal.stop_loss is None:
            concerns.append("Trade has no stop loss")
        if not signal.invalidation and signal.action.value != "WAIT":
            concerns.append("Trade has no explicit invalidation condition")
        if signal.strategy_family and signal.strategy_family.value == "option_selling":
            concerns.append("Option selling is research/paper-only until additional controls exist")
        if signal.blocked_by_filters:
            concerns.extend(signal.filter_reasons)

        approved = risk.approved and not concerns
        verdict = ReviewVerdict.APPROVED if approved else ReviewVerdict.REJECTED
        if not approved and risk.approved and len(concerns) == 1 and signal.confidence >= 0.55:
            verdict = ReviewVerdict.CAUTION
        strategy_label = signal.strategy_name or "unclassified_strategy"
        rr_text = f", reward/risk={risk_reward:.2f}" if risk_reward is not None else ""
        summary = (
            f"{signal.action.value} {signal.symbol} via {strategy_label}: {signal.reason}. "
            f"Risk decision: {risk.reason}, quantity={risk.quantity}{rr_text}. "
            f"Verdict: {verdict.value}."
        )
        return AgentReview(approved, summary, concerns, verdict, checklist, risk_reward)


def _risk_reward(signal: TradeSignal) -> float | None:
    if signal.entry_price is None or signal.stop_loss is None or signal.target is None:
        return None
    risk = abs(signal.entry_price - signal.stop_loss)
    reward = abs(signal.target - signal.entry_price)
    if risk <= 0:
        return None
    return reward / risk
