from datetime import datetime, timedelta

from nse_agentic_trader.agent import AgentVerdict, MarketRegime, MarketRegimeAgent
from nse_agentic_trader.models import MarketSnapshot


def test_market_regime_agent_identifies_uptrend():
    result = MarketRegimeAgent().analyze(_trend_bars(step=3))

    assert result.regime == MarketRegime.TREND_UP
    assert result.decision.verdict == AgentVerdict.SUPPORT
    assert result.efficiency > 0.55


def test_market_regime_agent_vetoes_chop():
    result = MarketRegimeAgent().analyze(_choppy_bars())

    assert result.regime == MarketRegime.CHOPPY
    assert result.decision.verdict == AgentVerdict.VETO
    assert "choppy" in result.decision.summary.lower()


def test_market_regime_agent_vetoes_low_volume():
    bars = _trend_bars(step=2)
    bars[-1] = MarketSnapshot("NIFTY", bars[-1].timestamp, bars[-1].open, bars[-1].high, bars[-1].low, bars[-1].close, 100)

    result = MarketRegimeAgent().analyze(bars)

    assert result.regime == MarketRegime.LOW_VOLUME
    assert result.decision.verdict == AgentVerdict.VETO


def test_market_regime_agent_handles_insufficient_data():
    result = MarketRegimeAgent().analyze(_trend_bars(step=1, count=5))

    assert result.regime == MarketRegime.INSUFFICIENT_DATA
    assert result.decision.verdict == AgentVerdict.CAUTION
    assert "Collect more bars" in result.decision.required_checks


def test_market_regime_lines_include_agent_decision():
    result = MarketRegimeAgent().analyze(_trend_bars(step=-3))
    rendered = "\n".join(result.lines())

    assert "Market regime analysis" in rendered
    assert "Regime: TREND_DOWN" in rendered
    assert "Agent: market_regime_agent" in rendered


def _trend_bars(step: float, count: int = 30) -> list[MarketSnapshot]:
    start = datetime(2026, 5, 31, 9, 15)
    price = 22500.0
    bars: list[MarketSnapshot] = []
    for index in range(count):
        close = price + step
        bars.append(
            MarketSnapshot(
                "NIFTY",
                start + timedelta(minutes=index),
                price,
                max(price, close) + 1,
                min(price, close) - 1,
                close,
                2000,
            )
        )
        price = close
    return bars


def _choppy_bars(count: int = 30) -> list[MarketSnapshot]:
    start = datetime(2026, 5, 31, 9, 15)
    price = 22500.0
    bars: list[MarketSnapshot] = []
    for index in range(count):
        close = price + (2 if index % 2 == 0 else -2)
        bars.append(MarketSnapshot("NIFTY", start + timedelta(minutes=index), price, price + 3, price - 3, close, 2000))
        price = close
    return bars
