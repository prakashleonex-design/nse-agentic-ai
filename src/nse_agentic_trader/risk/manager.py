from __future__ import annotations

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import RiskDecision, TradeSignal
from nse_agentic_trader.risk.state import RiskStateStore


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state_store = RiskStateStore(settings.risk_state_path)
        self.state = self.state_store.load()
        self.realized_pnl = self.state.realized_pnl
        self.trades_today = self.state.trades_today

    def evaluate(self, signal: TradeSignal, lot_size: int = 1) -> RiskDecision:
        if self.state.kill_switch:
            return RiskDecision(False, 0, f"Kill switch active: {self.state.kill_reason or 'manual stop'}")
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
        self.state.trades_today = self.trades_today
        self.state.realized_pnl = self.realized_pnl
        self.state_store.save(self.state)

    def record_realized_pnl(self, pnl: float) -> None:
        self.realized_pnl += pnl
        self.state.realized_pnl = self.realized_pnl
        if self.realized_pnl <= -abs(self.settings.max_daily_loss):
            self.state.kill_switch = True
            self.state.kill_reason = "Daily loss limit reached"
        self.state_store.save(self.state)
