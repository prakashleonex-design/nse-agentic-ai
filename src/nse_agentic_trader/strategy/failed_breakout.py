from __future__ import annotations

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class FailedBreakoutReversalStrategy:
    spec = StrategySpec(
        name="failed_breakout_reversal",
        family=StrategyFamily.MEAN_REVERSION,
        description="Fades failed range breakouts after price returns back inside the range.",
        enabled_by_default=False,
    )

    def __init__(self, range_minutes: int = 15, rr: float = 1.2) -> None:
        self.range_minutes = range_minutes
        self.rr = rr
        self._range_high: float | None = None
        self._range_low: float | None = None
        self._bars_seen = 0
        self._broke_high = False
        self._broke_low = False

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        self._bars_seen += 1
        if self._bars_seen <= self.range_minutes:
            self._range_high = max(self._range_high or bar.high, bar.high)
            self._range_low = min(self._range_low or bar.low, bar.low)
            return wait_signal(bar.symbol, "Building failed-breakout reference range", self.spec.name, self.spec.family)

        if self._range_high is None or self._range_low is None:
            return wait_signal(bar.symbol, "Reference range unavailable", self.spec.name, self.spec.family)

        if bar.high > self._range_high and bar.close <= self._range_high:
            self._broke_high = True
        if bar.low < self._range_low and bar.close >= self._range_low:
            self._broke_low = True

        if self._broke_high and bar.close < self._range_high:
            stop = max(bar.high, self._range_high + 4.0)
            risk = stop - bar.close
            self._broke_high = False
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_SHORT,
                Side.SELL,
                bar.close,
                stop,
                max(self._range_low, bar.close - risk * self.rr),
                0.58,
                "Upside breakout failed and price returned inside range",
                self.spec.name,
                self.spec.family,
                "Price reclaims failed breakout high",
                20,
            )

        if self._broke_low and bar.close > self._range_low:
            stop = min(bar.low, self._range_low - 4.0)
            risk = bar.close - stop
            self._broke_low = False
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                min(self._range_high, bar.close + risk * self.rr),
                0.58,
                "Downside breakout failed and price returned inside range",
                self.spec.name,
                self.spec.family,
                "Price loses failed breakout low",
                20,
            )

        return wait_signal(bar.symbol, "No failed breakout reversal", self.spec.name, self.spec.family)
