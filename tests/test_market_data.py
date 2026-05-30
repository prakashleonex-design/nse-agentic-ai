from datetime import datetime

from nse_agentic_trader.market_data import CsvCandleProvider


def test_csv_candle_provider_reads_standard_columns(tmp_path):
    path = tmp_path / "candles.csv"
    path.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-05-30 09:15,NIFTY,100,105,99,104,1200\n",
        encoding="utf-8",
    )

    candles = list(CsvCandleProvider(path, "NIFTY").candles())

    assert len(candles) == 1
    assert candles[0].timestamp == datetime(2026, 5, 30, 9, 15)
    assert candles[0].symbol == "NIFTY"
    assert candles[0].close == 104
    assert candles[0].volume == 1200
