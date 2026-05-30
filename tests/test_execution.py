from nse_agentic_trader.config import Settings
from nse_agentic_trader.execution import build_angel_order_params, validate_order_request
from nse_agentic_trader.models import OrderRequest, Side


def test_validate_order_requires_token_and_stop_loss():
    order = OrderRequest("NIFTYCE", Side.BUY, 65, "MARKET", "INTRADAY")

    validation = validate_order_request(order, Settings())

    assert not validation.approved
    assert "Stop loss is required" in validation.reasons
    assert "Angel symbol token is required" in validation.reasons


def test_validate_order_requires_manual_approval_for_live_mode():
    settings = Settings(trading_mode="live", allow_live_orders=True)
    order = OrderRequest(
        "NIFTYCE",
        Side.BUY,
        65,
        "MARKET",
        "INTRADAY",
        stop_loss=90,
        symboltoken="123",
        exchange="NFO",
    )

    rejected = validate_order_request(order, settings, manual_approval=False)
    approved = validate_order_request(order, settings, manual_approval=True)

    assert not rejected.approved
    assert "Manual approval token is required for live mode" in rejected.reasons
    assert approved.approved


def test_build_angel_order_params_uses_token_and_exchange():
    order = OrderRequest(
        "NIFTYCE",
        Side.BUY,
        65,
        "MARKET",
        "INTRADAY",
        price=0,
        stop_loss=90,
        symboltoken="123",
        exchange="NFO",
    )

    params = build_angel_order_params(order, Settings())

    assert params["tradingsymbol"] == "NIFTYCE"
    assert params["symboltoken"] == "123"
    assert params["exchange"] == "NFO"
    assert params["quantity"] == "65"
