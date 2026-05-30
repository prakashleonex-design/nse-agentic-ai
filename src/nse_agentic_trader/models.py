from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalAction(str, Enum):
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"
    WAIT = "WAIT"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


class StrategyFamily(str, Enum):
    SCALPING_MOMENTUM = "scalping_momentum"
    BREAKOUT = "breakout"
    OPTION_BUYING = "option_buying"
    OPTION_SELLING = "option_selling"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    action: SignalAction
    side: Side | None
    entry_price: float | None
    stop_loss: float | None
    target: float | None
    confidence: float
    reason: str
    strategy_name: str = ""
    strategy_family: StrategyFamily | None = None
    invalidation: str = ""
    expected_holding_minutes: int | None = None
    blocked_by_filters: bool = False
    filter_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: Side
    quantity: int
    order_type: str
    product_type: str
    price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    exchange: str | None = None
    symboltoken: str | None = None
    tick_size: float | None = None
    lot_size: int | None = None


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    order_id: str | None
    message: str


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    quantity: int
    reason: str


@dataclass(frozen=True)
class Instrument:
    exchange: str
    token: str
    trading_symbol: str
    name: str
    instrument_type: str
    expiry: datetime | None
    strike: float | None
    lot_size: int
    tick_size: float


@dataclass(frozen=True)
class OptionContract:
    underlying: str
    option_type: OptionType
    strike: float
    expiry: datetime
    instrument: Instrument
