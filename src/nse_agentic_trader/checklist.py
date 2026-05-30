from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.config import Settings
from nse_agentic_trader.instruments import instrument_master_info
from nse_agentic_trader.risk.state import RiskStateStore
from nse_agentic_trader.strategy import available_strategy_names


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    status: str
    detail: str


def build_premarket_checklist(settings: Settings) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    items.append(
        ChecklistItem(
            "Trading mode",
            "PASS" if settings.trading_mode.lower() == "paper" else "WARN",
            f"TRADING_MODE={settings.trading_mode}",
        )
    )
    items.append(
        ChecklistItem(
            "Live order guard",
            "PASS" if not settings.live_orders_enabled else "FAIL",
            f"live_orders_enabled={settings.live_orders_enabled}",
        )
    )

    info = instrument_master_info(settings.instrument_master_cache)
    if not info.exists:
        items.append(ChecklistItem("Angel instrument cache", "FAIL", f"Missing: {info.path}"))
    elif info.instrument_count <= 0:
        items.append(ChecklistItem("Angel instrument cache", "FAIL", f"Unreadable or empty: {info.path}"))
    elif info.age_hours is not None and info.age_hours > settings.instrument_master_max_age_hours:
        items.append(ChecklistItem("Angel instrument cache", "WARN", f"Age {info.age_hours:.1f}h at {info.path}"))
    else:
        age = f"{info.age_hours:.1f}h" if info.age_hours is not None else "unknown age"
        items.append(ChecklistItem("Angel instrument cache", "PASS", f"{info.instrument_count} instruments, age {age}"))

    state = RiskStateStore(settings.risk_state_path).load()
    items.append(
        ChecklistItem(
            "Risk kill switch",
            "FAIL" if state.kill_switch else "PASS",
            state.kill_reason or "Kill switch is off",
        )
    )
    items.append(
        ChecklistItem(
            "Trade count",
            "WARN" if state.trades_today >= settings.max_trades_per_day else "PASS",
            f"{state.trades_today}/{settings.max_trades_per_day} trades used",
        )
    )
    items.append(
        ChecklistItem(
            "Daily loss",
            "WARN" if state.realized_pnl <= -abs(settings.max_daily_loss) else "PASS",
            f"realized_pnl={state.realized_pnl:.2f}, max_daily_loss={settings.max_daily_loss:.2f}",
        )
    )
    items.append(ChecklistItem("Journal path", "PASS", str(settings.journal_path)))
    items.append(
        ChecklistItem(
            "Strategies registered",
            "PASS",
            ", ".join(available_strategy_names()),
        )
    )
    return items


def checklist_lines(items: list[ChecklistItem]) -> list[str]:
    return [f"[{item.status}] {item.name}: {item.detail}" for item in items]
