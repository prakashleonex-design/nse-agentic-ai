from __future__ import annotations

from collections import deque

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class TrendFollowingStrategy:
    spec = StrategySpec(
        name="trend_following",
        family=StrategyFamily.TREND_FOLLOWING,
        description="Follows sustained intraday direction after a moving-average trend forms.",
        enabled_by_default=False,
    )

    def __init__(self, fast: int = 5, slow: int = 12, rr: float = 1.6) -> None:
        self.fast = fast
        self.slow = slow
        self.rr = rr
        self._closes: deque[float] = deque(maxlen=slow)

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        self._closes.append(bar.close)
        if len(self._closes) < self.slow:
            return wait_signal(bar.symbol, "Waiting for trend moving averages", self.spec.name, self.spec.family)

        values = list(self._closes)
        fast_ma = sum(values[-self.fast :]) / self.fast
        slow_ma = sum(values) / self.slow
        slope = values[-1] - values[-4]
        if fast_ma > slow_ma and slope > 0:
            stop = min(values[-self.fast :])
            risk = bar.close - stop
            if risk <= 0:
                return wait_signal(bar.symbol, "Trend stop distance invalid", self.spec.name, self.spec.family)
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                bar.close + risk * self.rr,
                0.6,
                "Fast average is above slow average with positive slope",
                self.spec.name,
                self.spec.family,
                "Fast average loses slow average or trailing stop is hit",
                45,
            )

        if fast_ma < slow_ma and slope < 0:
            stop = max(values[-self.fast :])
            risk = stop - bar.close
            if risk <= 0:
                return wait_signal(bar.symbol, "Trend stop distance invalid", self.spec.name, self.spec.family)
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_SHORT,
                Side.SELL,
                bar.close,
                stop,
                bar.close - risk * self.rr,
                0.6,
                "Fast average is below slow average with negative slope",
                self.spec.name,
                self.spec.family,
                "Fast average regains slow average or trailing stop is hit",
                45,
            )

        return wait_signal(bar.symbol, "No clean trend alignment", self.spec.name, self.spec.family)


class TrendContinuationStrategy(TrendFollowingStrategy):
    spec = StrategySpec(
        name="trend_continuation",
        family=StrategyFamily.TREND_FOLLOWING,
        description="Continuation variant that enters when a formed trend resumes after a shallow pause.",
        enabled_by_default=False,
    )

    def __init__(self) -> None:
        super().__init__(fast=4, slow=10, rr=1.5)
