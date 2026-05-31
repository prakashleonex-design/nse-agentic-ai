from nse_agentic_trader.agent import AgentDecision, AgentVerdict, MarketRegime, MarketRegimeResult, StrategySelectorAgent


def test_strategy_selector_supports_uptrend_strategies():
    selection = StrategySelectorAgent().select(_regime(MarketRegime.TREND_UP, AgentVerdict.SUPPORT))

    assert selection.decision.verdict == AgentVerdict.SUPPORT
    assert "trend_following" in selection.strategies
    assert "option_buying" in selection.strategies
    assert "option_selling" not in selection.strategies


def test_strategy_selector_vetoes_choppy_market():
    selection = StrategySelectorAgent().select(_regime(MarketRegime.CHOPPY, AgentVerdict.VETO))

    assert selection.decision.verdict == AgentVerdict.VETO
    assert selection.strategies == ()
    assert "CHOPPY" in selection.decision.concerns[0]


def test_strategy_selector_is_cautious_in_range():
    selection = StrategySelectorAgent().select(_regime(MarketRegime.RANGE, AgentVerdict.CAUTION))

    assert selection.decision.verdict == AgentVerdict.CAUTION
    assert selection.strategies == ("mean_reversion", "vwap_pullback", "failed_breakout_reversal")


def test_strategy_selection_lines_are_cli_friendly():
    selection = StrategySelectorAgent().select(_regime(MarketRegime.TREND_DOWN, AgentVerdict.SUPPORT))
    rendered = "\n".join(selection.lines())

    assert "Strategy selection" in rendered
    assert "Regime: TREND_DOWN" in rendered
    assert "failed_breakout_reversal" in rendered
    assert "Agent: strategy_selector_agent" in rendered


def _regime(regime: MarketRegime, verdict: AgentVerdict) -> MarketRegimeResult:
    return MarketRegimeResult(
        regime=regime,
        decision=AgentDecision("market_regime_agent", verdict, 0.75, f"{regime.value} test"),
        bars_analyzed=30,
        net_move=30,
        total_move=45,
        efficiency=0.67,
        average_range=10,
        latest_volume=2000,
        average_volume=1900,
    )
