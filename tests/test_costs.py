from datetime import datetime

from nse_agentic_trader.broker.paper import PaperFill
from nse_agentic_trader.costs import CostModel
from nse_agentic_trader.models import Side


def test_cost_model_estimates_brokerage_and_variable_cost():
    fill = PaperFill(datetime.now(), "PAPER-1", "NIFTYCE", Side.BUY, 100, 50, 50)
    model = CostModel(brokerage_per_order=20, transaction_cost_bps=10)

    assert model.estimate_fill_cost(fill) == 25
