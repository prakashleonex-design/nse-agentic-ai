from datetime import date

from nse_agentic_trader.reports import build_backtest_report, build_journal_report
from nse_agentic_trader.session import SessionSummary


def test_journal_report_summarizes_modern_rows(tmp_path):
    journal = tmp_path / "journal.csv"
    journal.write_text(
        "timestamp,symbol,strategy_name,strategy_family,action,side,entry,stop_loss,target,"
        "invalidation,expected_holding_minutes,blocked_by_filters,filter_reasons,confidence,"
        "risk_approved,quantity,agent_approved,review_verdict,review_concerns,review_checklist,risk_reward,summary,order_id,order_message\n"
        "2026-05-30T10:00:00,NIFTY,opening_range_breakout,breakout,ENTER_LONG,BUY,100,95,110,"
        "below range,20,False,,0.6,True,50,True,APPROVED,,check,2.0,ok,PAPER-1,filled\n"
        "2026-05-30T10:05:00,NIFTY,vwap_pullback,trend_following,WAIT,BUY,100,95,110,"
        "below vwap,20,True,Low volume,0.6,False,0,False,REJECTED,Low volume,check,2.0,blocked,,\n",
        encoding="utf-8",
    )

    report = build_journal_report(journal, date(2026, 5, 30))

    assert report.rows == 2
    assert report.orders == 1
    assert report.risk_approved == 1
    assert report.agent_approved == 1
    assert report.filter_blocks == 1
    assert report.verdicts["APPROVED"] == 1
    assert report.verdicts["REJECTED"] == 1
    assert report.strategies["opening_range_breakout"] == 1
    assert report.actions["WAIT"] == 1


def test_journal_report_tolerates_legacy_rows(tmp_path):
    journal = tmp_path / "journal.csv"
    journal.write_text(
        "timestamp,symbol,action,risk_approved,quantity,agent_approved,order_id\n"
        "2026-05-30T10:00:00,NIFTY,ENTER_LONG,True,50,True,PAPER-1\n",
        encoding="utf-8",
    )

    report = build_journal_report(journal)

    assert report.rows == 1
    assert report.strategies["legacy_or_manual"] == 1
    assert report.total_quantity == 50


def test_journal_report_normalizes_new_rows_written_after_legacy_header(tmp_path):
    journal = tmp_path / "journal.csv"
    journal.write_text(
        "timestamp,symbol,action,side,entry,stop_loss,target,confidence,risk_approved,quantity,agent_approved,summary,order_id,order_message\n"
        "2026-05-30T10:00:00,NIFTY,ENTER_LONG,BUY,100,95,110,0.6,True,50,True,ok,PAPER-1,filled\n"
        "2026-05-30T10:05:00,NIFTYCE,opening_range_breakout,breakout,ENTER_LONG,BUY,10,8,14,"
        "inside range,20,False,,0.6,True,75,True,modern row,PAPER-2,filled\n",
        encoding="utf-8",
    )

    report = build_journal_report(journal)

    assert report.rows == 2
    assert report.actions["ENTER_LONG"] == 2
    assert report.strategies["opening_range_breakout"] == 1
    assert report.total_quantity == 125


def test_build_backtest_report_includes_summary_and_safety_notes():
    summary = SessionSummary(
        bars_seen=100,
        signals_seen=3,
        orders_accepted=2,
        exits=2,
        gross_realized_pnl=500,
        estimated_costs=80,
        net_realized_pnl=420,
        winning_exits=1,
        losing_exits=1,
    )

    report = build_backtest_report(summary, "NIFTY", "opening_range_breakout", "csv")

    assert "# Backtest Report" in report
    assert "- Symbol: NIFTY" in report
    assert "- Strategy: opening_range_breakout" in report
    assert "- Net realized P&L: 420.00" in report
    assert "- Win rate: 50.00%" in report
    assert "not a live-trading approval" in report
