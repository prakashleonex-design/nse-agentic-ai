from __future__ import annotations

from collections import deque

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class VwapPullbackStrategy:
    spec = StrategySpec(
        name="vwap_pullback",
        family=StrategyFamily.TREND_FOLLOWING,
        description="Trades pullbacks toward VWAP when the intraday trend remains intact.",
        enabled_by_default=False,
    )

    def __init__(self, lookback: int = 6, rr: float = 1.4) -> None:
        self.lookback = lookback
        self.rr = rr
        self._typical_price_volume = 0.0
        self._volume = 0
        self._closes: deque[float] = deque(maxlen=lookback)

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        typical_price = (bar.high + bar.low + bar.close) / 3
        volume = max(1, bar.volume)
        self._typical_price_volume += typical_price * volume
        self._volume += volume
        self._closes.append(bar.close)

        if len(self._closes) < self.lookback:
            return wait_signal(bar.symbol, "Waiting for VWAP context", self.spec.name, self.spec.family)

        vwap = self._typical_price_volume / self._volume
        values = list(self._closes)
        slope = values[-1] - values[0]
        near_vwap = abs(bar.close - vwap) <= max(8.0, bar.close * 0.0005)

        if slope > 0 and bar.low <= vwap <= bar.close and near_vwap:
            stop = min(bar.low, vwap - 6.0)
            risk = bar.close - stop
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                bar.close + risk * self.rr,
                0.59,
                "Bull trend pulled back to VWAP and reclaimed it",
                self.spec.name,
                self.spec.family,
                "Price closes below VWAP after entry",
                25,
            )

        if slope < 0 and bar.high >= vwap >= bar.close and near_vwap:
            stop = max(bar.high, vwap + 6.0)
            risk = stop - bar.close
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_SHORT,
                Side.SELL,
                bar.close,
                stop,
                bar.close - risk * self.rr,
                0.59,
                "Bear trend pulled back to VWAP and rejected it",
                self.spec.name,
                self.spec.family,
                "Price closes above VWAP after entry",
                25,
            )

        return wait_signal(bar.symbol, "No qualified VWAP pullback", self.spec.name, self.spec.family)
