import json
from datetime import datetime

from nse_agentic_trader.instruments import AngelInstrumentMaster, OptionQuery
from nse_agentic_trader.models import OptionType


def test_finds_nifty_option_contract_from_angel_master(tmp_path):
    cache = tmp_path / "angel.json"
    cache.write_text(
        json.dumps(
            [
                {
                    "exch_seg": "NFO",
                    "token": "12345",
                    "symbol": "NIFTY30MAY2422500CE",
                    "name": "NIFTY",
                    "expiry": "30MAY2024",
                    "strike": "2250000.000000",
                    "lotsize": "75",
                    "instrumenttype": "OPTIDX",
                    "tick_size": "5.000000",
                }
            ]
        ),
        encoding="utf-8",
    )

    contract = AngelInstrumentMaster(cache).find_index_option(
        OptionQuery("NIFTY", OptionType.CE, 22500, datetime(2024, 5, 30))
    )

    assert contract.instrument.token == "12345"
    assert contract.instrument.strike == 22500
    assert contract.instrument.tick_size == 0.05
    assert contract.instrument.lot_size == 75


def test_missing_option_contract_raises_lookup_error(tmp_path):
    cache = tmp_path / "angel.json"
    cache.write_text("[]", encoding="utf-8")

    master = AngelInstrumentMaster(cache)

    try:
        master.find_index_option(OptionQuery("BANKNIFTY", OptionType.PE, 48000))
    except LookupError as exc:
        assert "No Angel NFO option found" in str(exc)
    else:
        raise AssertionError("Expected missing option lookup to fail")
