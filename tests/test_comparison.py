from datetime import datetime, timedelta

from nse_agentic_trader.comparison import build_strategy_comparison_report, compare_strategies, comparison_lines
from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import MarketSnapshot


def test_compare_strategies_uses_isolated_paper_state(tmp_path):
    bars = _breakout_bars()
    settings = Settings(
        journal_path=tmp_path / "journal.csv",
        risk_state_path=tmp_path / "risk_state.json",
        max_qty=10,
        risk_per_trade=100,
        paper_underlying_slippage_bps=0,
        paper_underlying_min_slippage=0,
        paper_brokerage_per_order=1,
        paper_transaction_cost_bps=0,
    )

    rows = compare_strategies(
        settings,
        bars,
        ["option_selling", "opening_range_breakout"],
        "NIFTY",
        max_entries=1,
        map_options=False,
        apply_filters=False,
    )

    assert [row.strategy for row in rows] == ["opening_range_breakout", "option_selling"]
    assert rows[0].summary.orders_accepted == 1
    assert rows[1].summary.orders_accepted == 0
    assert not settings.journal_path.exists()
    assert not settings.risk_state_path.exists()


def test_comparison_output_includes_ranked_metrics():
    rows = compare_strategies(
        Settings(max_qty=10, risk_per_trade=100, paper_underlying_slippage_bps=0, paper_underlying_min_slippage=0),
        _breakout_bars(),
        ["opening_range_breakout"],
        "NIFTY",
        max_entries=1,
        map_options=False,
        apply_filters=False,
    )

    text_lines = "\n".join(comparison_lines(rows))
    markdown = build_strategy_comparison_report(rows, "NIFTY", "csv", map_options=False, apply_filters=False)

    assert "Strategy comparison" in text_lines
    assert "opening_range_breakout" in text_lines
    assert "# Strategy Comparison" in markdown
    assert "| opening_range_breakout |" in markdown
    assert "isolated paper simulations" in markdown


def _breakout_bars() -> list[MarketSnapshot]:
    start = datetime(2026, 5, 30, 9, 15)
    bars: list[MarketSnapshot] = []
    price = 100.0
    for index in range(16):
        close = price + 0.2
        bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=index), price, price + 1, price - 1, close, 2000))
        price = close
    bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=16), price, price + 10, price - 1, price + 8, 2000))
    bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=17), price + 8, price + 35, price + 5, price + 30, 2000))
    return bars
