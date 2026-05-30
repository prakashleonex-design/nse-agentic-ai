from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    trading_mode: str = "paper"
    allow_live_orders: bool = False

    angel_client_code: str = ""
    angel_password: str = ""
    angel_api_key: str = ""
    angel_totp_secret: str = ""

    default_exchange: str = "NSE"
    default_product_type: str = "INTRADAY"
    default_order_variety: str = "NORMAL"

    instrument_master_url: str = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
    instrument_master_cache: Path = Path("data/angel_instruments.json")
    instrument_master_max_age_hours: int = 24

    paper_option_slippage_bps: float = 8.0
    paper_option_min_slippage: float = 0.05
    paper_brokerage_per_order: float = 20.0
    paper_transaction_cost_bps: float = 6.0

    max_daily_loss: float = 3000.0
    max_trades_per_day: int = 4
    max_qty: int = 50
    risk_per_trade: float = 1000.0
    journal_path: Path = Path("journal.csv")
    risk_state_path: Path = Path("data/risk_state.json")

    @property
    def live_orders_enabled(self) -> bool:
        return self.trading_mode.lower() == "live" and self.allow_live_orders


def load_settings() -> Settings:
    values = _read_dotenv(Path(".env"))
    values.update(os.environ)
    return Settings(
        trading_mode=values.get("TRADING_MODE", "paper"),
        allow_live_orders=_as_bool(values.get("ALLOW_LIVE_ORDERS", "false")),
        angel_client_code=values.get("ANGEL_CLIENT_CODE", ""),
        angel_password=values.get("ANGEL_PASSWORD", ""),
        angel_api_key=values.get("ANGEL_API_KEY", ""),
        angel_totp_secret=values.get("ANGEL_TOTP_SECRET", ""),
        default_exchange=values.get("DEFAULT_EXCHANGE", "NSE"),
        default_product_type=values.get("DEFAULT_PRODUCT_TYPE", "INTRADAY"),
        default_order_variety=values.get("DEFAULT_ORDER_VARIETY", "NORMAL"),
        instrument_master_url=values.get(
            "INSTRUMENT_MASTER_URL",
            "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json",
        ),
        instrument_master_cache=Path(values.get("INSTRUMENT_MASTER_CACHE", "data/angel_instruments.json")),
        instrument_master_max_age_hours=int(values.get("INSTRUMENT_MASTER_MAX_AGE_HOURS", 24)),
        paper_option_slippage_bps=float(values.get("PAPER_OPTION_SLIPPAGE_BPS", 8)),
        paper_option_min_slippage=float(values.get("PAPER_OPTION_MIN_SLIPPAGE", 0.05)),
        paper_brokerage_per_order=float(values.get("PAPER_BROKERAGE_PER_ORDER", 20)),
        paper_transaction_cost_bps=float(values.get("PAPER_TRANSACTION_COST_BPS", 6)),
        max_daily_loss=float(values.get("MAX_DAILY_LOSS", 3000)),
        max_trades_per_day=int(values.get("MAX_TRADES_PER_DAY", 4)),
        max_qty=int(values.get("MAX_QTY", 50)),
        risk_per_trade=float(values.get("RISK_PER_TRADE", 1000)),
        journal_path=Path(values.get("JOURNAL_PATH", "journal.csv")),
        risk_state_path=Path(values.get("RISK_STATE_PATH", "data/risk_state.json")),
    )


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
