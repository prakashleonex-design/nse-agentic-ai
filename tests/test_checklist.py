from nse_agentic_trader.checklist import build_premarket_checklist, checklist_lines
from nse_agentic_trader.config import Settings
from nse_agentic_trader.risk.state import RiskStateStore


def test_premarket_checklist_flags_live_orders_enabled(tmp_path):
    settings = Settings(
        trading_mode="live",
        allow_live_orders=True,
        instrument_master_cache=tmp_path / "missing.json",
        risk_state_path=tmp_path / "risk.json",
    )

    items = build_premarket_checklist(settings)
    statuses = {item.name: item.status for item in items}

    assert statuses["Trading mode"] == "WARN"
    assert statuses["Live order guard"] == "FAIL"
    assert statuses["Angel instrument cache"] == "FAIL"


def test_premarket_checklist_flags_kill_switch(tmp_path):
    risk_path = tmp_path / "risk.json"
    RiskStateStore(risk_path).kill("test stop")
    settings = Settings(instrument_master_cache=tmp_path / "missing.json", risk_state_path=risk_path)

    items = build_premarket_checklist(settings)
    lines = checklist_lines(items)

    assert any("[FAIL] Risk kill switch" in line for line in lines)
