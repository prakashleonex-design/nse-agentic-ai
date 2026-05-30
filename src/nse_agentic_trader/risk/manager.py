from __future__ import annotations

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import RiskDecision, TradeSignal


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.realized_pnl = 0.0
        self.trades_today = 0

    def evaluate(self, signal: TradeSignal, lot_size: int = 1) -> RiskDecision:
        if signal.entry_price is None or signal.stop_loss is None:
            return RiskDecision(False, 0, "No executable entry or stop loss")
        if self.realized_pnl <= -abs(self.settings.max_daily_loss):
            return RiskDecision(False, 0, "Daily loss limit reached")
        if self.trades_today >= self.settings.max_trades_per_day:
            return RiskDecision(False, 0, "Max trades per day reached")

        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            return RiskDecision(False, 0, "Invalid stop loss distance")

        quantity = int(self.settings.risk_per_trade / risk_per_unit)
        quantity = max(0, min(quantity, self.settings.max_qty))
        if lot_size > 1:
            quantity = (quantity // lot_size) * lot_size
        if quantity < 1:
            return RiskDecision(False, 0, "Quantity is below minimum after risk sizing")

        return RiskDecision(True, quantity, "Risk approved")

    def record_trade(self) -> None:
        self.trades_today += 1
