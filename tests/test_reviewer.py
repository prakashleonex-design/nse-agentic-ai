from nse_agentic_trader.agent.reviewer import ReviewVerdict, TradeReviewer
from nse_agentic_trader.models import RiskDecision, Side, SignalAction, StrategyFamily, TradeSignal


def test_reviewer_approves_clean_trade_with_risk_reward():
    signal = TradeSignal(
        "NIFTY",
        SignalAction.ENTER_LONG,
        Side.BUY,
        100,
        95,
        110,
        0.65,
        "clean setup",
        "opening_range_breakout",
        StrategyFamily.BREAKOUT,
        "back inside range",
        20,
    )

    review = TradeReviewer().review(signal, RiskDecision(True, 50, "Risk approved"))

    assert review.approved
    assert review.verdict == ReviewVerdict.APPROVED
    assert review.risk_reward == 2
    assert review.checklist


def test_reviewer_rejects_missing_invalidation():
    signal = TradeSignal("NIFTY", SignalAction.ENTER_LONG, Side.BUY, 100, 95, 110, 0.65, "missing invalidation")

    review = TradeReviewer().review(signal, RiskDecision(True, 50, "Risk approved"))

    assert not review.approved
    assert review.verdict == ReviewVerdict.CAUTION
    assert "Trade has no explicit invalidation condition" in review.concerns
