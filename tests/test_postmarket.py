from collections import Counter
from datetime import date

from nse_agentic_trader.postmarket import build_postmarket_summary
from nse_agentic_trader.reports import JournalReport
from nse_agentic_trader.risk.state import RiskState


def test_postmarket_summary_includes_risk_and_activity():
    report = JournalReport(
        rows=2,
        symbols=Counter({"NIFTY": 2}),
        strategies=Counter({"opening_range_breakout": 2}),
        actions=Counter({"ENTER_LONG": 2}),
        risk_approved=1,
        agent_approved=1,
        orders=1,
        filter_blocks=1,
        total_quantity=65,
        verdicts=Counter({"APPROVED": 1, "REJECTED": 1}),
    )
    risk_state = RiskState("2026-05-30", realized_pnl=120.5, trades_today=1)

    summary = build_postmarket_summary(report, risk_state, date(2026, 5, 30)).as_markdown()

    assert "# Post-Market Summary - 2026-05-30" in summary
    assert "Orders placed: 1" in summary
    assert "Realized P&L: 120.50" in summary
    assert "Avoid-trade filters blocked setups" in summary


def test_postmarket_summary_warns_on_kill_switch():
    report = JournalReport(0, Counter(), Counter(), Counter(), 0, 0, 0, 0, 0, Counter())
    risk_state = RiskState("2026-05-30", kill_switch=True, kill_reason="daily stop")

    summary = build_postmarket_summary(report, risk_state, date(2026, 5, 30)).as_markdown()

    assert "Kill switch: ON" in summary
    assert "daily stop" in summary
    assert "do not resume trading" in summary
