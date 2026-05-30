from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Protocol

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import MarketSnapshot


class MarketDataProvider(Protocol):
    def candles(self) -> Iterable[MarketSnapshot]:
        ...


class CsvCandleProvider:
    def __init__(self, path: Path, symbol: str) -> None:
        self.path = path
        self.symbol = symbol

    def candles(self) -> Iterable[MarketSnapshot]:
        with self.path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield MarketSnapshot(
                    symbol=row.get("symbol") or self.symbol,
                    timestamp=_parse_timestamp(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(float(row.get("volume") or 0)),
                )


class AngelHistoricalCandleProvider:
    def __init__(
        self,
        settings: Settings,
        symbol: str,
        exchange: str,
        symboltoken: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> None:
        self.settings = settings
        self.symbol = symbol
        self.exchange = exchange
        self.symboltoken = symboltoken
        self.interval = interval
        self.from_date = from_date
        self.to_date = to_date

    def candles(self) -> Iterable[MarketSnapshot]:
        client = self._connect()
        params = {
            "exchange": self.exchange,
            "symboltoken": self.symboltoken,
            "interval": self.interval,
            "fromdate": self.from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": self.to_date.strftime("%Y-%m-%d %H:%M"),
        }
        result = client.getCandleData(params)
        if not result.get("status"):
            raise RuntimeError(f"Angel historical candle fetch failed: {result}")
        for row in result.get("data") or []:
            timestamp, open_price, high, low, close, volume = row[:6]
            yield MarketSnapshot(
                symbol=self.symbol,
                timestamp=_parse_timestamp(str(timestamp)),
                open=float(open_price),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=int(float(volume or 0)),
            )

    def _connect(self):
        try:
            from SmartApi import SmartConnect
            import pyotp
        except ImportError as exc:
            raise RuntimeError("Install SmartAPI support with: pip install -e .[angel]") from exc

        if not all(
            [
                self.settings.angel_api_key,
                self.settings.angel_client_code,
                self.settings.angel_password,
                self.settings.angel_totp_secret,
            ]
        ):
            raise RuntimeError("Angel credentials are required for historical candle data")

        client = SmartConnect(api_key=self.settings.angel_api_key)
        otp = pyotp.TOTP(self.settings.angel_totp_secret).now()
        session = client.generateSession(
            self.settings.angel_client_code,
            self.settings.angel_password,
            otp,
        )
        if not session.get("status"):
            raise RuntimeError(f"Angel login failed for market data: {session}")
        return client


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return datetime.fromisoformat(text).replace(tzinfo=None)
