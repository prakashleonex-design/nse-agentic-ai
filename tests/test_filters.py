from datetime import datetime

from nse_agentic_trader.filters import AvoidTradeFilterEngine, apply_filter_block
from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal


def test_low_volume_filter_blocks_executable_signal():
    engine = AvoidTradeFilterEngine(min_volume=1000)
    bar = MarketSnapshot("NIFTY", datetime(2026, 5, 30, 10, 0), 100, 105, 99, 104, volume=100)
    engine.on_bar(bar)
    signal = TradeSignal(
        "NIFTY",
        SignalAction.ENTER_LONG,
        Side.BUY,
        104,
        99,
        112,
        0.6,
        "test",
        "test_strategy",
        StrategyFamily.BREAKOUT,
        "below low",
        10,
    )

    decision = engine.evaluate(signal, bar)
    blocked = apply_filter_block(signal, decision)

    assert decision.blocked
    assert blocked.action == SignalAction.WAIT
    assert blocked.blocked_by_filters
    assert "Low volume filter" in blocked.filter_reasons


def test_late_entry_filter_blocks_after_cutoff():
    engine = AvoidTradeFilterEngine()
    bar = MarketSnapshot("NIFTY", datetime(2026, 5, 30, 15, 5), 100, 105, 99, 104, volume=5000)
    engine.on_bar(bar)
    signal = TradeSignal("NIFTY", SignalAction.ENTER_LONG, Side.BUY, 104, 99, 112, 0.6, "test")

    decision = engine.evaluate(signal, bar)

    assert decision.blocked
    assert "Late entry filter" in decision.reasons
