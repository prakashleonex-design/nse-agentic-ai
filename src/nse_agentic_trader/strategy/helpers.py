from __future__ import annotations

from nse_agentic_trader.models import SignalAction, StrategyFamily, TradeSignal


def wait_signal(symbol: str, reason: str, strategy_name: str, family: StrategyFamily) -> TradeSignal:
    return TradeSignal(
        symbol=symbol,
        action=SignalAction.WAIT,
        side=None,
        entry_price=None,
        stop_loss=None,
        target=None,
        confidence=0.0,
        reason=reason,
        strategy_name=strategy_name,
        strategy_family=family,
    )
