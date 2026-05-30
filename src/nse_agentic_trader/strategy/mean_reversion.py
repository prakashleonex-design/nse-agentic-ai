from __future__ import annotations

from collections import deque

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class MeanReversionStrategy:
    spec = StrategySpec(
        name="mean_reversion",
        family=StrategyFamily.MEAN_REVERSION,
        description="Fades stretched intraday moves back toward a short rolling mean.",
        enabled_by_default=False,
    )

    def __init__(self, lookback: int = 12, stretch: float = 22.0, rr: float = 1.0) -> None:
        self.lookback = lookback
        self.stretch = stretch
        self.rr = rr
        self._closes: deque[float] = deque(maxlen=lookback)

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        self._closes.append(bar.close)
        if len(self._closes) < self.lookback:
            return wait_signal(bar.symbol, "Waiting for mean-reversion baseline", self.spec.name, self.spec.family)

        mean = sum(self._closes) / len(self._closes)
        distance = bar.close - mean
        if abs(distance) < self.stretch:
            return wait_signal(bar.symbol, "Price is not stretched enough from mean", self.spec.name, self.spec.family)

        if distance < 0:
            stop = bar.close - self.stretch * 0.6
            risk = bar.close - stop
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                min(mean, bar.close + risk * self.rr),
                0.56,
                "Price is stretched below rolling mean and may revert",
                self.spec.name,
                self.spec.family,
                "Price continues away from mean or trend filter turns directional",
                20,
            )

        stop = bar.close + self.stretch * 0.6
        risk = stop - bar.close
        return TradeSignal(
            bar.symbol,
            SignalAction.ENTER_SHORT,
            Side.SELL,
            bar.close,
            stop,
            max(mean, bar.close - risk * self.rr),
            0.56,
            "Price is stretched above rolling mean and may revert",
            self.spec.name,
            self.spec.family,
            "Price continues away from mean or trend filter turns directional",
            20,
        )
