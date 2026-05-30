from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nse_agentic_trader.models import MarketSnapshot, StrategyFamily, TradeSignal


@dataclass(frozen=True)
class StrategySpec:
    name: str
    family: StrategyFamily
    description: str
    enabled_by_default: bool
    live_enabled: bool = False


class Strategy(Protocol):
    spec: StrategySpec

    def on_bar(self, bar: MarketSnapshot) -> TradeSignal:
        ...
