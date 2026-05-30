from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class RiskState:
    trade_date: str
    realized_pnl: float = 0.0
    trades_today: int = 0
    kill_switch: bool = False
    kill_reason: str = ""
    updated_at: str = ""

    @classmethod
    def today(cls) -> "RiskState":
        return cls(trade_date=date.today().isoformat(), updated_at=datetime.now().isoformat(timespec="seconds"))


class RiskStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> RiskState:
        if not self.path.exists():
            return RiskState.today()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        state = RiskState(
            trade_date=str(raw.get("trade_date", "")),
            realized_pnl=float(raw.get("realized_pnl", 0.0)),
            trades_today=int(raw.get("trades_today", 0)),
            kill_switch=bool(raw.get("kill_switch", False)),
            kill_reason=str(raw.get("kill_reason", "")),
            updated_at=str(raw.get("updated_at", "")),
        )
        if state.trade_date != date.today().isoformat():
            return RiskState.today()
        return state

    def save(self, state: RiskState) -> None:
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def kill(self, reason: str) -> RiskState:
        state = self.load()
        state.kill_switch = True
        state.kill_reason = reason
        self.save(state)
        return state

    def reset(self) -> RiskState:
        state = RiskState.today()
        self.save(state)
        return state
