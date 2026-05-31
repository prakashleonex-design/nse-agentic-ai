from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.agent.decision import AgentDecision, AgentVerdict
from nse_agentic_trader.agent.regime import MarketRegime, MarketRegimeResult


@dataclass(frozen=True)
class StrategySelection:
    strategies: tuple[str, ...]
    decision: AgentDecision
    regime: MarketRegime

    def lines(self) -> list[str]:
        strategies = ", ".join(self.strategies) if self.strategies else "none"
        return [
            "Strategy selection",
            f"Regime: {self.regime.value}",
            f"Strategies: {strategies}",
            *self.decision.lines(),
        ]


class StrategySelectorAgent:
    name = "strategy_selector_agent"

    def select(self, regime_result: MarketRegimeResult) -> StrategySelection:
        regime = regime_result.regime
        if regime in {MarketRegime.CHOPPY, MarketRegime.LOW_VOLUME, MarketRegime.INSUFFICIENT_DATA}:
            decision = AgentDecision(
                self.name,
                AgentVerdict.VETO,
                regime_result.decision.confidence,
                "No strategy should be selected while the market-regime agent is vetoing participation.",
                concerns=(
                    f"Market regime is {regime.value}.",
                    "Wait for cleaner participation before evaluating entries.",
                ),
                required_checks=regime_result.decision.required_checks,
            )
            return StrategySelection((), decision, regime)

        if regime == MarketRegime.HIGH_VOLATILITY:
            strategies = ("failed_breakout_reversal", "opening_range_breakout")
            decision = AgentDecision(
                self.name,
                AgentVerdict.CAUTION,
                0.68,
                "High volatility allows only selective breakout/reversal research setups.",
                reasons=("Use confirmation candles and avoid late entries.",),
                concerns=("Spike candles can trigger false breakouts and poor fills.",),
                required_checks=("Confirm no news event", "Use paper mode", "Require stop loss"),
            )
            return StrategySelection(strategies, decision, regime)

        if regime == MarketRegime.TREND_UP:
            strategies = ("trend_following", "trend_continuation", "vwap_pullback", "opening_range_breakout", "option_buying")
            decision = AgentDecision(
                self.name,
                AgentVerdict.SUPPORT,
                0.78,
                "Uptrend regime supports trend-following, pullback, breakout, and defined-risk option buying setups.",
                reasons=("Directional efficiency supports momentum participation.",),
                concerns=("Do not chase extended candles; wait for valid entry location.",),
                required_checks=("Check reward/risk", "Check stop loss", "Check option liquidity"),
            )
            return StrategySelection(strategies, decision, regime)

        if regime == MarketRegime.TREND_DOWN:
            strategies = ("trend_following", "trend_continuation", "failed_breakout_reversal", "option_buying")
            decision = AgentDecision(
                self.name,
                AgentVerdict.SUPPORT,
                0.76,
                "Downtrend regime supports bearish continuation, failed-breakout, and defined-risk option buying setups.",
                reasons=("Directional efficiency supports downside participation.",),
                concerns=("Avoid countertrend option selling without advanced margin and exit controls.",),
                required_checks=("Check reward/risk", "Check stop loss", "Check option liquidity"),
            )
            return StrategySelection(strategies, decision, regime)

        strategies = ("mean_reversion", "vwap_pullback", "failed_breakout_reversal")
        decision = AgentDecision(
            self.name,
            AgentVerdict.CAUTION,
            0.62,
            "Range regime favors mean-reversion or failed-breakout research setups, not aggressive momentum.",
            reasons=("Directional efficiency is not strong enough for clean trend selection.",),
            concerns=("Breakouts need stronger confirmation in a range.",),
            required_checks=("Confirm range boundaries", "Avoid entries near the middle of the range", "Require stop loss"),
        )
        return StrategySelection(strategies, decision, regime)
