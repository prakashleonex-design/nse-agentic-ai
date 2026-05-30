from datetime import datetime

import pytest

from nse_agentic_trader.market_data import CsvCandleProvider, write_sample_candle_csv


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


def test_csv_candle_provider_missing_file_suggests_sample_command(tmp_path):
    path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="data sample-csv"):
        list(CsvCandleProvider(path, "NIFTY").candles())


def test_write_sample_candle_csv_can_be_read_back(tmp_path):
    path = tmp_path / "data" / "nifty_1m.csv"

    written_path = write_sample_candle_csv(path, "NIFTY", bars=5)
    candles = list(CsvCandleProvider(written_path, "NIFTY").candles())

    assert written_path == path
    assert len(candles) == 5
    assert candles[0].symbol == "NIFTY"
    assert candles[-1].timestamp > candles[0].timestamp


def test_write_sample_candle_csv_requires_positive_bars(tmp_path):
    with pytest.raises(ValueError, match="greater than 0"):
        write_sample_candle_csv(tmp_path / "nifty_1m.csv", "NIFTY", bars=0)
