from __future__ import annotations

from nse_agentic_trader.models import MarketSnapshot, Side, SignalAction, StrategyFamily, TradeSignal
from nse_agentic_trader.strategy.base import StrategySpec
from nse_agentic_trader.strategy.helpers import wait_signal


class OptionBuyingStrategy:
    spec = StrategySpec(
        name="option_buying",
        family=StrategyFamily.OPTION_BUYING,
        description="Directional defined-risk option-buying template.",
        enabled_by_default=True,
    )

    def __init__(self, min_body: float = 8.0, rr: float = 1.4) -> None:
        self.min_body = min_body
        self.rr = rr

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        body = bar.close - bar.open
        if abs(body) < self.min_body:
            return wait_signal(bar.symbol, "Candle body too small for directional option buying", self.spec.name, self.spec.family)

        if body > 0:
            stop = min(bar.low, bar.open)
            risk = bar.close - stop
            return TradeSignal(
                bar.symbol,
                SignalAction.ENTER_LONG,
                Side.BUY,
                bar.close,
                stop,
                bar.close + risk * self.rr,
                0.57,
                "Bullish candle supports defined-risk CE buying",
                self.spec.name,
                self.spec.family,
                "Underlying loses trigger candle low",
                25,
            )

        stop = max(bar.high, bar.open)
        risk = stop - bar.close
        return TradeSignal(
            bar.symbol,
            SignalAction.ENTER_SHORT,
            Side.SELL,
            bar.close,
            stop,
            bar.close - risk * self.rr,
            0.57,
            "Bearish candle supports defined-risk PE buying",
            self.spec.name,
            self.spec.family,
            "Underlying regains trigger candle high",
            25,
        )


class OptionSellingStrategy:
    spec = StrategySpec(
        name="option_selling",
        family=StrategyFamily.OPTION_SELLING,
        description="Premium-selling research placeholder; paper-only and disabled by default.",
        enabled_by_default=False,
        live_enabled=False,
    )

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        return wait_signal(
            bar.symbol,
            "Option selling is disabled until margin checks, hedges, max-loss exits, and live controls exist",
            self.spec.name,
            self.spec.family,
        )
