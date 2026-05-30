from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import OrderRequest


@dataclass(frozen=True)
class OrderValidation:
    approved: bool
    reasons: tuple[str, ...]


def validate_order_request(order: OrderRequest, settings: Settings, manual_approval: bool = False) -> OrderValidation:
    reasons: list[str] = []
    if order.quantity <= 0:
        reasons.append("Quantity must be positive")
    if order.lot_size and order.quantity % order.lot_size != 0:
        reasons.append(f"Quantity must be a multiple of lot size {order.lot_size}")
    if not order.stop_loss:
        reasons.append("Stop loss is required")
    if not order.symboltoken:
        reasons.append("Angel symbol token is required")
    if not (order.exchange or settings.default_exchange):
        reasons.append("Exchange is required")
    if settings.trading_mode.lower() == "live" and not manual_approval:
        reasons.append("Manual approval token is required for live mode")
    if settings.trading_mode.lower() == "live" and not settings.allow_live_orders:
        reasons.append("ALLOW_LIVE_ORDERS must be true for live mode")
    return OrderValidation(not reasons, tuple(reasons))


def build_angel_order_params(order: OrderRequest, settings: Settings) -> dict[str, str]:
    return {
        "variety": settings.default_order_variety,
        "tradingsymbol": order.symbol,
        "symboltoken": order.symboltoken or "",
        "transactiontype": order.side.value,
        "exchange": order.exchange or settings.default_exchange,
        "ordertype": order.order_type,
        "producttype": order.product_type,
        "duration": "DAY",
        "price": str(order.price or "0"),
        "squareoff": "0",
        "stoploss": "0",
        "quantity": str(order.quantity),
    }
