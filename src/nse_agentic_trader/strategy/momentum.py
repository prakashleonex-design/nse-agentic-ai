from __future__ import annotations

from collections import deque

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class ScalpingMomentumStrategy:
    spec = StrategySpec(
        name="scalping_momentum",
        family=StrategyFamily.SCALPING_MOMENTUM,
        description="Trades short bursts of intraday momentum with tight stops.",
        enabled_by_default=False,
    )

    def __init__(self, lookback: int = 5, min_move: float = 18.0, rr: float = 1.2) -> None:
        self.lookback = lookback
        self.min_move = min_move
        self.rr = rr
        self._closes: deque[float] = deque(maxlen=lookback + 1)

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        self._closes.append(bar.close)
        if len(self._closes) <= self.lookback:
            return wait_signal(bar.symbol, "Waiting for momentum lookback", self.spec.name, self.spec.family)

        move = self._closes[-1] - self._closes[0]
        if abs(move) < self.min_move:
            return wait_signal(bar.symbol, "Momentum move below threshold", self.spec.name, self.spec.family)

        if move > 0:
            stop = min(bar.low, bar.close - self.min_move * 0.45)
            risk = bar.close - stop
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                bar.close + risk * self.rr,
                0.58,
                "Short-term upward momentum confirmed",
                self.spec.name,
                self.spec.family,
                "Momentum fades or price closes below the trigger candle low",
                10,
            )

        stop = max(bar.high, bar.close + self.min_move * 0.45)
        risk = stop - bar.close
        return TradeSignal(
            bar.symbol,
            SignalAction.ENTER_SHORT,
            Side.SELL,
            bar.close,
            stop,
            bar.close - risk * self.rr,
            0.58,
            "Short-term downward momentum confirmed",
            self.spec.name,
            self.spec.family,
            "Momentum fades or price closes above the trigger candle high",
            10,
        )
