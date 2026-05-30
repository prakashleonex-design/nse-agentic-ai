from datetime import datetime, timedelta

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import MarketSnapshot
from nse_agentic_trader.session import run_paper_session


def test_paper_session_processes_full_bars_and_records_exit(tmp_path):
    start = datetime(2026, 5, 30, 9, 15)
    bars: list[MarketSnapshot] = []
    price = 100.0
    for index in range(16):
        close = price + 0.2
        bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=index), price, price + 1, price - 1, close, 2000))
        price = close
    bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=16), price, price + 10, price - 1, price + 8, 2000))
    bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=17), price + 8, price + 35, price + 5, price + 30, 2000))

    settings = Settings(
        risk_state_path=tmp_path / "risk_state.json",
        journal_path=tmp_path / "journal.csv",
        max_qty=10,
        risk_per_trade=100,
        paper_option_slippage_bps=0,
        paper_option_min_slippage=0,
    )

    summary = run_paper_session(
        settings,
        bars,
        "opening_range_breakout",
        "NIFTY",
        option_strike=None,
        option_expiry=None,
        max_entries=1,
        map_options=False,
        apply_filters=False,
    )

    assert summary.bars_seen == len(bars)
    assert summary.orders_accepted == 1
    assert summary.exits == 1
    assert summary.realized_pnl > 0
