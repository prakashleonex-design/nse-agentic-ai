from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import count

from nse_agentic_trader.models import MarketSnapshot, OrderRequest, OrderResult, Side


@dataclass
class PaperFill:
    timestamp: datetime
    order_id: str
    symbol: str
    side: Side
    quantity: int
    requested_price: float
    fill_price: float
    realized_pnl: float = 0.0


@dataclass
class PaperPosition:
    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    stop_loss: float | None = None
    target: float | None = None
    realized_pnl: float = 0.0


class PaperBroker:
    def __init__(self, slippage_bps: float = 8.0, min_slippage: float = 0.05) -> None:
        self._ids = count(1)
        self.orders: list[tuple[datetime, OrderRequest]] = []
        self.fills: list[PaperFill] = []
        self.positions: dict[str, PaperPosition] = {}
        self.slippage_bps = slippage_bps
        self.min_slippage = min_slippage

    def place_order(self, order: OrderRequest) -> OrderResult:
        if order.quantity <= 0:
            return OrderResult(False, None, "Paper order rejected: quantity must be positive")
        if order.lot_size and order.quantity % order.lot_size != 0:
            return OrderResult(False, None, f"Paper order rejected: quantity must be a multiple of lot size {order.lot_size}")
        if order.order_type.upper() == "MARKET" and order.price is None:
            return OrderResult(False, None, "Paper market order requires a reference price for realistic fills")

        self.orders.append((datetime.now(), order))
        order_id = f"PAPER-{next(self._ids):06d}"
        requested_price = float(order.price or 0.0)
        fill_price = self._fill_price(order.side, requested_price, order.tick_size)
        fill = PaperFill(datetime.now(), order_id, order.symbol, order.side, order.quantity, requested_price, fill_price)
        self.fills.append(fill)
        fill.realized_pnl = self._apply_fill(fill, order.stop_loss, order.target)
        return OrderResult(True, order_id, f"Paper fill at {fill_price:.2f}")

    def simulate_intrabar_exits(self, bar: MarketSnapshot) -> list[OrderResult]:
        results: list[OrderResult] = []
        position = self.positions.get(bar.symbol)
        if position is None or position.quantity == 0:
            return results

        exit_price: float | None = None
        reason = ""
        if position.quantity > 0:
            if position.stop_loss is not None and bar.low <= position.stop_loss:
                exit_price = position.stop_loss
                reason = "stop loss"
            elif position.target is not None and bar.high >= position.target:
                exit_price = position.target
                reason = "target"
            if exit_price is not None:
                order = OrderRequest(
                    symbol=bar.symbol,
                    side=Side.SELL,
                    quantity=position.quantity,
                    order_type="MARKET",
                    product_type="INTRADAY",
                    price=exit_price,
                    tick_size=0.05,
                )
                result = self.place_order(order)
                results.append(OrderResult(result.accepted, result.order_id, f"Paper exit on {reason}: {result.message}"))
        return results

    @property
    def realized_pnl(self) -> float:
        return sum(position.realized_pnl for position in self.positions.values())

    def _fill_price(self, side: Side, reference_price: float, tick_size: float | None) -> float:
        slippage = max(reference_price * self.slippage_bps / 10000, self.min_slippage)
        raw = reference_price + slippage if side == Side.BUY else reference_price - slippage
        return _round_to_tick(raw, tick_size or 0.05)

    def _apply_fill(self, fill: PaperFill, stop_loss: float | None, target: float | None) -> float:
        position = self.positions.setdefault(fill.symbol, PaperPosition(fill.symbol))
        signed_qty = fill.quantity if fill.side == Side.BUY else -fill.quantity
        old_qty = position.quantity
        new_qty = old_qty + signed_qty

        if old_qty >= 0 and signed_qty > 0:
            total_cost = position.average_price * old_qty + fill.fill_price * fill.quantity
            position.quantity = new_qty
            position.average_price = total_cost / new_qty
            position.stop_loss = stop_loss
            position.target = target
            return 0.0

        if old_qty > 0 and signed_qty < 0:
            exit_qty = min(old_qty, fill.quantity)
            realized_pnl = (fill.fill_price - position.average_price) * exit_qty
            position.realized_pnl += realized_pnl
            position.quantity = old_qty - exit_qty
            if position.quantity == 0:
                position.average_price = 0.0
                position.stop_loss = None
                position.target = None
            return realized_pnl

        position.quantity = new_qty
        return 0.0


def _round_to_tick(price: float, tick_size: float) -> float:
    ticks = round(price / tick_size)
    return round(ticks * tick_size, 2)
