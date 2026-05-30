from __future__ import annotations

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class OpeningRangeBreakout:
    spec = StrategySpec(
        name="opening_range_breakout",
        family=StrategyFamily.BREAKOUT,
        description="Trades confirmed breaks of the opening range.",
        enabled_by_default=True,
    )

    def __init__(self, range_minutes: int = 15, rr: float = 1.5) -> None:
        self.range_minutes = range_minutes
        self.rr = rr
        self._range_high: float | None = None
        self._range_low: float | None = None
        self._bars_seen = 0

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        self._bars_seen += 1
        if self._bars_seen <= self.range_minutes:
            self._range_high = max(self._range_high or bar.high, bar.high)
            self._range_low = min(self._range_low or bar.low, bar.low)
            return self._wait(bar.symbol, "Building opening range")

        if self._range_high is None or self._range_low is None:
            return self._wait(bar.symbol, "Opening range unavailable")

        if bar.close > self._range_high:
            risk = bar.close - self._range_low
            return TradeSignal(
                symbol=bar.symbol,
                action=SignalAction.ENTER_LONG,
                side=Side.BUY,
                entry_price=bar.close,
                stop_loss=self._range_low,
                target=bar.close + risk * self.rr,
                confidence=0.62,
                reason="Close broke above opening range high",
                strategy_name=self.spec.name,
                strategy_family=self.spec.family,
                invalidation="Price closes back inside the opening range",
                expected_holding_minutes=30,
            )

        if bar.close < self._range_low:
            risk = self._range_high - bar.close
            return TradeSignal(
                symbol=bar.symbol,
                action=SignalAction.ENTER_SHORT,
                side=Side.SELL,
                entry_price=bar.close,
                stop_loss=self._range_high,
                target=bar.close - risk * self.rr,
                confidence=0.62,
                reason="Close broke below opening range low",
                strategy_name=self.spec.name,
                strategy_family=self.spec.family,
                invalidation="Price closes back inside the opening range",
                expected_holding_minutes=30,
            )

        return self._wait(bar.symbol, "Price inside opening range")

    @staticmethod
    def _wait(symbol: str, reason: str) -> TradeSignal:
        return wait_signal(symbol, reason, OpeningRangeBreakout.spec.name, OpeningRangeBreakout.spec.family)
