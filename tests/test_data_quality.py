from datetime import datetime, timedelta

from nse_agentic_trader.data_quality import validate_candles
from nse_agentic_trader.models import MarketSnapshot


def test_validate_candles_accepts_clean_bars():
    start = datetime(2026, 5, 30, 9, 15)
    bars = [
        MarketSnapshot("NIFTY", start, 100, 105, 99, 104, 1000),
        MarketSnapshot("NIFTY", start + timedelta(minutes=1), 104, 106, 103, 105, 1000),
    ]

    report = validate_candles(bars, min_bars=2)

    assert report.ok
    assert report.bars == 2


def test_validate_candles_rejects_bad_ohlc_and_timestamps():
    start = datetime(2026, 5, 30, 9, 15)
    bars = [
        MarketSnapshot("NIFTY", start, 100, 105, 99, 104, 1000),
        MarketSnapshot("NIFTY", start, 104, 103, 102, 105, 1000),
    ]

    report = validate_candles(bars)

    assert not report.ok
    messages = "\n".join(issue.message for issue in report.issues)
    assert "Timestamp is not strictly increasing" in messages
    assert "High is below" in messages


def test_validate_candles_warns_on_zero_volume():
    bar = MarketSnapshot("NIFTY", datetime(2026, 5, 30, 9, 15), 100, 105, 99, 104, 0)

    report = validate_candles([bar])

    assert report.ok
    assert report.issues[0].severity == "WARN"
