from datetime import datetime, timedelta

from nse_agentic_trader.models import MarketSnapshot, SignalAction, StrategyFamily
from nse_agentic_trader.strategy import available_strategy_names, build_strategy, strategies_by_family


def test_registry_exposes_required_strategy_families():
    names = set(available_strategy_names())

    assert {
        "scalping_momentum",
        "opening_range_breakout",
        "vwap_pullback",
        "option_buying",
        "option_selling",
        "trend_following",
        "trend_continuation",
        "mean_reversion",
        "failed_breakout_reversal",
    }.issubset(names)
    assert strategies_by_family(StrategyFamily.OPTION_SELLING) == ["option_selling"]


def test_opening_range_signal_carries_strategy_metadata():
    strategy = build_strategy("opening_range_breakout")
    start = datetime(2026, 5, 30, 9, 15)
    signal = None
    price = 22500.0

    for index in range(17):
        close = price + (25 if index == 16 else 0.5)
        signal = strategy.on_bar(
            MarketSnapshot("NIFTY", start + timedelta(minutes=index), price, max(price, close) + 2, min(price, close) - 2, close)
        )
        price = close

    assert signal is not None
    assert signal.action == SignalAction.ENTER_LONG
    assert signal.strategy_name == "opening_range_breakout"
    assert signal.strategy_family == StrategyFamily.BREAKOUT
    assert signal.invalidation


def test_option_selling_is_disabled_placeholder():
    strategy = build_strategy("option_selling")
    signal = strategy.on_bar(MarketSnapshot("NIFTY", datetime.now(), 22500, 22510, 22490, 22505))

    assert signal.action == SignalAction.WAIT
    assert signal.strategy_family == StrategyFamily.OPTION_SELLING
    assert "disabled" in signal.reason


def test_failed_breakout_reversal_emits_short_after_failed_upside_break():
    strategy = build_strategy("failed_breakout_reversal")
    start = datetime(2026, 5, 30, 9, 15)
    for index in range(15):
        strategy.on_bar(MarketSnapshot("NIFTY", start + timedelta(minutes=index), 100, 102, 98, 100))

    signal = strategy.on_bar(MarketSnapshot("NIFTY", start + timedelta(minutes=16), 100, 106, 99, 101))

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.strategy_name == "failed_breakout_reversal"
    assert signal.invalidation
