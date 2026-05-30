from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import time

from nse_agentic_trader.models import MarketSnapshot, SignalAction, TradeSignal


@dataclass(frozen=True)
class FilterDecision:
    blocked: bool
    reasons: tuple[str, ...]


class AvoidTradeFilterEngine:
    def __init__(
        self,
        min_volume: int = 1000,
        choppy_lookback: int = 8,
        min_trend_range: float = 12.0,
        spike_lookback: int = 10,
        news_spike_multiple: float = 3.0,
        last_entry_time: time = time(15, 0),
    ) -> None:
        self.min_volume = min_volume
        self.choppy_lookback = choppy_lookback
        self.min_trend_range = min_trend_range
        self.spike_lookback = spike_lookback
        self.news_spike_multiple = news_spike_multiple
        self.last_entry_time = last_entry_time
        self._closes: deque[float] = deque(maxlen=max(choppy_lookback, 2))
        self._ranges: deque[float] = deque(maxlen=spike_lookback)

    def on_bar(self, bar: MarketSnapshot) -> None:
        self._closes.append(bar.close)
        self._ranges.append(max(0.0, bar.high - bar.low))

    def evaluate(self, signal: TradeSignal, bar: MarketSnapshot) -> FilterDecision:
        if signal.action == SignalAction.WAIT:
            return FilterDecision(False, ())

        reasons: list[str] = []
        if bar.volume < self.min_volume:
            reasons.append("Low volume filter")
        if bar.timestamp.time() > self.last_entry_time:
            reasons.append("Late entry filter")
        if self._is_choppy():
            reasons.append("Choppy market filter")
        if self._is_news_spike(bar):
            reasons.append("News/spike candle filter")

        return FilterDecision(bool(reasons), tuple(reasons))

    def _is_choppy(self) -> bool:
        if len(self._closes) < self.choppy_lookback:
            return False
        values = list(self._closes)
        net_move = abs(values[-1] - values[0])
        total_move = sum(abs(values[index] - values[index - 1]) for index in range(1, len(values)))
        if total_move <= 0:
            return True
        efficiency = net_move / total_move
        return net_move < self.min_trend_range and efficiency < 0.35

    def _is_news_spike(self, bar: MarketSnapshot) -> bool:
        if len(self._ranges) < self.spike_lookback:
            return False
        prior_ranges = list(self._ranges)[:-1]
        if not prior_ranges:
            return False
        average_range = sum(prior_ranges) / len(prior_ranges)
        return average_range > 0 and (bar.high - bar.low) > average_range * self.news_spike_multiple


def apply_filter_block(signal: TradeSignal, decision: FilterDecision) -> TradeSignal:
    if not decision.blocked:
        return signal
    return TradeSignal(
        symbol=signal.symbol,
        action=SignalAction.WAIT,
        side=signal.side,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        target=signal.target,
        confidence=signal.confidence,
        reason=f"{signal.reason}; blocked by avoid-trade filters",
        strategy_name=signal.strategy_name,
        strategy_family=signal.strategy_family,
        invalidation=signal.invalidation,
        expected_holding_minutes=signal.expected_holding_minutes,
        blocked_by_filters=True,
        filter_reasons=decision.reasons,
    )
