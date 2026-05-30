from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import Side, SignalAction, TradeSignal
from nse_agentic_trader.risk import RiskManager


def test_risk_manager_sizes_quantity_from_stop_distance():
    settings = Settings(risk_per_trade=1000, max_qty=50)
    risk = RiskManager(settings)
    signal = TradeSignal("NIFTY", SignalAction.ENTER_LONG, Side.BUY, 100, 90, 115, 0.7, "test")

    decision = risk.evaluate(signal)

    assert decision.approved
    assert decision.quantity == 50


def test_risk_manager_rejects_missing_stop():
    settings = Settings()
    risk = RiskManager(settings)
    signal = TradeSignal("NIFTY", SignalAction.ENTER_LONG, Side.BUY, 100, None, 115, 0.7, "test")

    decision = risk.evaluate(signal)

    assert not decision.approved
