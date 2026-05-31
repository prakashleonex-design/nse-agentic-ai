from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nse_agentic_trader.agent.decision import AgentDecision, AgentVerdict
from nse_agentic_trader.models import MarketSnapshot


class MarketRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHOPPY = "CHOPPY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLUME = "LOW_VOLUME"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class MarketRegimeResult:
    regime: MarketRegime
    decision: AgentDecision
    bars_analyzed: int
    net_move: float
    total_move: float
    efficiency: float
    average_range: float
    latest_volume: int
    average_volume: float

    def lines(self) -> list[str]:
        return [
            "Market regime analysis",
            f"Regime: {self.regime.value}",
            f"Bars analyzed: {self.bars_analyzed}",
            f"Net move: {self.net_move:.2f}",
            f"Total move: {self.total_move:.2f}",
            f"Efficiency: {self.efficiency:.2f}",
            f"Average range: {self.average_range:.2f}",
            f"Latest volume: {self.latest_volume}",
            f"Average volume: {self.average_volume:.2f}",
            *self.decision.lines(),
        ]


class MarketRegimeAgent:
    name = "market_regime_agent"

    def __init__(
        self,
        lookback: int = 30,
        min_bars: int = 12,
        choppy_efficiency: float = 0.35,
        trend_efficiency: float = 0.55,
        high_volatility_multiple: float = 2.2,
        low_volume_ratio: float = 0.6,
    ) -> None:
        self.lookback = lookback
        self.min_bars = min_bars
        self.choppy_efficiency = choppy_efficiency
        self.trend_efficiency = trend_efficiency
        self.high_volatility_multiple = high_volatility_multiple
        self.low_volume_ratio = low_volume_ratio

    def analyze(self, bars: list[MarketSnapshot]) -> MarketRegimeResult:
        window = bars[-self.lookback :]
        if len(window) < self.min_bars:
            decision = AgentDecision(
                self.name,
                AgentVerdict.CAUTION,
                0.2,
                "Not enough candles to classify the market regime.",
                concerns=("Wait for more market data before selecting a strategy.",),
                required_checks=("Collect more bars",),
            )
            return MarketRegimeResult(MarketRegime.INSUFFICIENT_DATA, decision, len(window), 0, 0, 0, 0, 0, 0)

        closes = [bar.close for bar in window]
        ranges = [max(0.0, bar.high - bar.low) for bar in window]
        volumes = [bar.volume for bar in window]
        net_move = closes[-1] - closes[0]
        total_move = sum(abs(closes[index] - closes[index - 1]) for index in range(1, len(closes)))
        efficiency = abs(net_move) / total_move if total_move > 0 else 0.0
        average_range = sum(ranges) / len(ranges)
        baseline_ranges = ranges[:-1] or ranges
        baseline_range = sum(baseline_ranges) / len(baseline_ranges)
        latest_range = ranges[-1]
        average_volume = sum(volumes) / len(volumes)
        latest_volume = volumes[-1]

        if average_volume > 0 and latest_volume < average_volume * self.low_volume_ratio:
            return self._result(
                MarketRegime.LOW_VOLUME,
                AgentVerdict.VETO,
                0.82,
                "Latest candle volume is materially below the recent average.",
                window,
                net_move,
                total_move,
                efficiency,
                average_range,
                latest_volume,
                average_volume,
                concerns=("Low participation can make breakouts and reversals unreliable.",),
            )

        if baseline_range > 0 and latest_range > baseline_range * self.high_volatility_multiple:
            return self._result(
                MarketRegime.HIGH_VOLATILITY,
                AgentVerdict.CAUTION,
                0.78,
                "Latest candle range is unusually large versus recent candles.",
                window,
                net_move,
                total_move,
                efficiency,
                average_range,
                latest_volume,
                average_volume,
                concerns=("Possible news/spike behavior; avoid late entries and widen validation.",),
            )

        if efficiency < self.choppy_efficiency:
            return self._result(
                MarketRegime.CHOPPY,
                AgentVerdict.VETO,
                0.76,
                "Price movement is inefficient and choppy.",
                window,
                net_move,
                total_move,
                efficiency,
                average_range,
                latest_volume,
                average_volume,
                concerns=("Avoid forcing momentum or breakout trades in chop.",),
            )

        if efficiency >= self.trend_efficiency and net_move > 0:
            return self._result(
                MarketRegime.TREND_UP,
                AgentVerdict.SUPPORT,
                min(0.9, 0.55 + efficiency / 2),
                "Market is trending upward with directional efficiency.",
                window,
                net_move,
                total_move,
                efficiency,
                average_range,
                latest_volume,
                average_volume,
                reasons=("Trend-following, breakout, and pullback strategies may be suitable.",),
            )

        if efficiency >= self.trend_efficiency and net_move < 0:
            return self._result(
                MarketRegime.TREND_DOWN,
                AgentVerdict.SUPPORT,
                min(0.9, 0.55 + efficiency / 2),
                "Market is trending downward with directional efficiency.",
                window,
                net_move,
                total_move,
                efficiency,
                average_range,
                latest_volume,
                average_volume,
                reasons=("Downside momentum, failed-breakout, or bearish pullback strategies may be suitable.",),
            )

        return self._result(
            MarketRegime.RANGE,
            AgentVerdict.CAUTION,
            0.62,
            "Market is neither strongly trending nor extremely choppy.",
            window,
            net_move,
            total_move,
            efficiency,
            average_range,
            latest_volume,
            average_volume,
            concerns=("Prefer mean-reversion or wait for a cleaner breakout confirmation.",),
        )

    def _result(
        self,
        regime: MarketRegime,
        verdict: AgentVerdict,
        confidence: float,
        summary: str,
        window: list[MarketSnapshot],
        net_move: float,
        total_move: float,
        efficiency: float,
        average_range: float,
        latest_volume: int,
        average_volume: float,
        reasons: tuple[str, ...] = (),
        concerns: tuple[str, ...] = (),
    ) -> MarketRegimeResult:
        decision = AgentDecision(
            self.name,
            verdict,
            confidence,
            summary,
            reasons=reasons,
            concerns=concerns,
            required_checks=("Confirm with current candle close", "Check event/news calendar", "Respect risk limits"),
        )
        return MarketRegimeResult(
            regime,
            decision,
            len(window),
            net_move,
            total_move,
            efficiency,
            average_range,
            latest_volume,
            average_volume,
        )
