from datetime import datetime

from nse_agentic_trader.broker.paper import PaperBroker
from nse_agentic_trader.models import MarketSnapshot, OrderRequest, Side


def test_paper_broker_requires_reference_price_for_market_order():
    broker = PaperBroker()
    result = broker.place_order(OrderRequest("NIFTY30MAY2422500CE", Side.BUY, 75, "MARKET", "INTRADAY"))

    assert not result.accepted
    assert "reference price" in result.message


def test_paper_broker_fills_option_lots_and_exits_on_stop():
    broker = PaperBroker(slippage_bps=0, min_slippage=0)
    entry = broker.place_order(
        OrderRequest(
            "NIFTY30MAY2422500CE",
            Side.BUY,
            75,
            "MARKET",
            "INTRADAY",
            price=100,
            stop_loss=90,
            target=125,
            tick_size=0.05,
            lot_size=75,
        )
    )

    exits = broker.simulate_intrabar_exits(
        MarketSnapshot("NIFTY30MAY2422500CE", datetime.now(), 100, 104, 89, 92)
    )

    assert entry.accepted
    assert len(exits) == 1
    assert broker.positions["NIFTY30MAY2422500CE"].quantity == 0
    assert broker.positions["NIFTY30MAY2422500CE"].realized_pnl == -750
