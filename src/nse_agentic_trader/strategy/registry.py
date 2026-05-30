from __future__ import annotations

from collections.abc import Callable

from nse_agentic_trader.models import StrategyFamily
from nse_agentic_trader.strategy.base import Strategy
from nse_agentic_trader.strategy.mean_reversion import MeanReversionStrategy
from nse_agentic_trader.strategy.momentum import ScalpingMomentumStrategy
from nse_agentic_trader.strategy.opening_range import OpeningRangeBreakout
from nse_agentic_trader.strategy.options import OptionBuyingStrategy, OptionSellingStrategy
from nse_agentic_trader.strategy.trend import TrendFollowingStrategy


StrategyFactory = Callable[[], Strategy]


_REGISTRY: dict[str, StrategyFactory] = {
    OpeningRangeBreakout.spec.name: OpeningRangeBreakout,
    ScalpingMomentumStrategy.spec.name: ScalpingMomentumStrategy,
    OptionBuyingStrategy.spec.name: OptionBuyingStrategy,
    OptionSellingStrategy.spec.name: OptionSellingStrategy,
    TrendFollowingStrategy.spec.name: TrendFollowingStrategy,
    MeanReversionStrategy.spec.name: MeanReversionStrategy,
}


def available_strategy_names() -> list[str]:
    return sorted(_REGISTRY)


def build_strategy(name: str) -> Strategy:
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        names = ", ".join(available_strategy_names())
        raise ValueError(f"Unknown strategy '{name}'. Available strategies: {names}") from exc


def default_strategy_names() -> list[str]:
    return [name for name, factory in _REGISTRY.items() if factory().spec.enabled_by_default]


def strategies_by_family(family: StrategyFamily) -> list[str]:
    return [name for name, factory in _REGISTRY.items() if factory().spec.family == family]
