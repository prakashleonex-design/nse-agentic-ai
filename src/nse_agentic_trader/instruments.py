from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

from nse_agentic_trader.models import Instrument, OptionContract, OptionType


INDEX_LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
}


@dataclass(frozen=True)
class OptionQuery:
    underlying: str
    option_type: OptionType
    strike: float
    expiry: datetime | None = None


@dataclass(frozen=True)
class InstrumentMasterInfo:
    path: Path
    exists: bool
    modified_at: datetime | None
    age_hours: float | None
    instrument_count: int


class AngelInstrumentMaster:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self._instruments: list[Instrument] | None = None

    def load(self) -> list[Instrument]:
        if self._instruments is None:
            self._instruments = [_parse_instrument(item) for item in _read_json(self.cache_path)]
        return self._instruments

    def find_index_option(self, query: OptionQuery) -> OptionContract:
        underlying = query.underlying.upper()
        matches = [
            instrument
            for instrument in self.load()
            if instrument.exchange == "NFO"
            and instrument.name.upper() == underlying
            and instrument.instrument_type.upper() == "OPTIDX"
            and instrument.strike == query.strike
            and instrument.trading_symbol.upper().endswith(query.option_type.value)
        ]
        if query.expiry is not None:
            expiry_date = query.expiry.date()
            matches = [instrument for instrument in matches if instrument.expiry and instrument.expiry.date() == expiry_date]

        if not matches:
            expiry_hint = query.expiry.date().isoformat() if query.expiry else "nearest available"
            raise LookupError(
                f"No Angel NFO option found for {underlying} {query.strike:g} {query.option_type.value} "
                f"expiry={expiry_hint}. Refresh the instrument master or check strike/expiry."
            )

        matches.sort(key=lambda instrument: instrument.expiry or datetime.max)
        instrument = matches[0]
        if instrument.expiry is None:
            raise LookupError(f"Matched {instrument.trading_symbol}, but expiry is missing in Angel master")
        return OptionContract(underlying, query.option_type, query.strike, instrument.expiry, instrument)

    def nearest_index_option(
        self,
        underlying: str,
        option_type: OptionType,
        spot_price: float,
        expiry: datetime | None = None,
    ) -> OptionContract:
        strike_step = 100 if underlying.upper() == "BANKNIFTY" else 50
        strike = round(spot_price / strike_step) * strike_step
        return self.find_index_option(OptionQuery(underlying, option_type, float(strike), expiry))


def refresh_instrument_master(url: str, cache_path: Path) -> Path:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=30) as response:
        payload = response.read()
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, list) or not parsed:
        raise RuntimeError("Angel instrument master response was empty or invalid")
    cache_path.write_bytes(payload)
    return cache_path


def ensure_instrument_master(url: str, cache_path: Path, max_age_hours: int) -> Path:
    if cache_path.exists():
        modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - modified <= timedelta(hours=max_age_hours):
            return cache_path
    return refresh_instrument_master(url, cache_path)


def instrument_master_info(cache_path: Path) -> InstrumentMasterInfo:
    if not cache_path.exists():
        return InstrumentMasterInfo(cache_path, False, None, None, 0)
    modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age_hours = (datetime.now() - modified).total_seconds() / 3600
    try:
        count = len(_read_json(cache_path))
    except (json.JSONDecodeError, ValueError):
        count = 0
    return InstrumentMasterInfo(cache_path, True, modified, age_hours, count)


def _read_json(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Angel instrument master cache not found at {path}. "
            "Run with --refresh-instruments first, or set INSTRUMENT_MASTER_CACHE."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected Angel instrument master list in {path}")
    return data


def _parse_instrument(item: dict[str, object]) -> Instrument:
    return Instrument(
        exchange=str(item.get("exch_seg", "")).upper(),
        token=str(item.get("token", "")),
        trading_symbol=str(item.get("symbol", "")),
        name=str(item.get("name", "")).upper(),
        instrument_type=str(item.get("instrumenttype", "")).upper(),
        expiry=_parse_expiry(item.get("expiry")),
        strike=_normalise_money(item.get("strike")),
        lot_size=int(float(str(item.get("lotsize", "1") or "1"))),
        tick_size=_normalise_tick(item.get("tick_size")) or 0.05,
    )


def _parse_expiry(value: object) -> datetime | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    for fmt in ("%d%b%Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _normalise_money(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    amount = float(text)
    return amount / 100 if abs(amount) >= 100000 else amount


def _normalise_tick(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    amount = float(text)
    return amount / 100 if amount >= 1 else amount
