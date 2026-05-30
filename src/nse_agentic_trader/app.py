from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from nse_agentic_trader.agent import TradeReviewer
from nse_agentic_trader.broker import PaperBroker
from nse_agentic_trader.broker.angel import AngelSmartApiBroker
from nse_agentic_trader.config import load_settings
from nse_agentic_trader.instruments import AngelInstrumentMaster, OptionQuery, ensure_instrument_master
from nse_agentic_trader.journal import Journal
from nse_agentic_trader.models import MarketSnapshot, OptionContract, OptionType, OrderRequest, Side, SignalAction, TradeSignal
from nse_agentic_trader.risk import RiskManager
from nse_agentic_trader.strategy import OpeningRangeBreakout


def sample_bars(symbol: str) -> list[MarketSnapshot]:
    start = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    bars: list[MarketSnapshot] = []
    price = 22500.0
    for i in range(20):
        drift = 3 if i > 15 else 0.4
        open_price = price
        close = price + drift
        bars.append(
            MarketSnapshot(
                symbol=symbol,
                timestamp=start + timedelta(minutes=i),
                open=open_price,
                high=max(open_price, close) + 2,
                low=min(open_price, close) - 2,
                close=close,
                volume=1000 + i,
            )
        )
        price = close
    return bars


def build_broker(mode: str):
    settings = load_settings()
    if mode == "live":
        return AngelSmartApiBroker(settings)
    return PaperBroker(settings.paper_option_slippage_bps, settings.paper_option_min_slippage)


def run_once(
    symbol: str,
    mode: str,
    option_strike: float | None = None,
    option_expiry: datetime | None = None,
    refresh_instruments: bool = False,
) -> None:
    settings = load_settings()
    broker = build_broker(mode)
    strategy = OpeningRangeBreakout()
    risk_manager = RiskManager(settings)
    reviewer = TradeReviewer()
    journal = Journal(settings.journal_path)
    if refresh_instruments:
        ensure_instrument_master(
            settings.instrument_master_url,
            settings.instrument_master_cache,
            settings.instrument_master_max_age_hours,
        )

    for bar in sample_bars(symbol):
        signal = strategy.on_bar(bar)
        if signal.action == SignalAction.WAIT:
            continue

        order_signal, contract = _option_signal_if_available(signal, bar.close, option_strike, option_expiry, settings.instrument_master_cache)
        lot_size = contract.instrument.lot_size if contract else 1
        risk = risk_manager.evaluate(order_signal, lot_size=lot_size)
        review = reviewer.review(order_signal, risk)
        order_result = None

        if review.approved and order_signal.side:
            order = OrderRequest(
                symbol=order_signal.symbol,
                side=order_signal.side,
                quantity=risk.quantity,
                order_type="MARKET",
                product_type=settings.default_product_type,
                price=order_signal.entry_price,
                stop_loss=order_signal.stop_loss,
                target=order_signal.target,
                exchange=contract.instrument.exchange if contract else settings.default_exchange,
                symboltoken=contract.instrument.token if contract else None,
                tick_size=contract.instrument.tick_size if contract else 0.05,
                lot_size=lot_size,
            )
            order_result = broker.place_order(order)
            if order_result.accepted:
                risk_manager.record_trade()

        journal.write(order_signal, risk, review, order_result)
        print(review.summary)
        if contract:
            print(f"Contract: {contract.instrument.trading_symbol} token={contract.instrument.token} lot={contract.instrument.lot_size}")
        if order_result:
            print(f"Order: {order_result.order_id} - {order_result.message}")
        break


def _option_signal_if_available(
    signal: TradeSignal,
    spot_price: float,
    option_strike: float | None,
    option_expiry: datetime | None,
    cache_path,
) -> tuple[TradeSignal, OptionContract | None]:
    if signal.side is None or signal.entry_price is None or signal.stop_loss is None:
        return signal, None
    option_type = OptionType.CE if signal.side == Side.BUY else OptionType.PE
    strike = option_strike or round(spot_price / 50) * 50
    try:
        contract = AngelInstrumentMaster(cache_path).find_index_option(
            OptionQuery(signal.symbol, option_type, float(strike), option_expiry)
        )
    except (FileNotFoundError, LookupError, ValueError):
        return signal, None

    premium = _estimate_option_premium(option_type, spot_price, contract.strike)
    index_risk = abs(signal.entry_price - signal.stop_loss)
    delta = 0.45
    option_risk = max(index_risk * delta, contract.instrument.tick_size * 10)
    option_reward = option_risk * 1.5
    return (
        TradeSignal(
            symbol=contract.instrument.trading_symbol,
            action=signal.action,
            side=Side.BUY,
            entry_price=premium,
            stop_loss=max(contract.instrument.tick_size, premium - option_risk),
            target=premium + option_reward,
            confidence=signal.confidence,
            reason=f"{signal.reason}; mapped to {contract.underlying} {contract.strike:g}{contract.option_type.value}",
        ),
        contract,
    )


def _estimate_option_premium(option_type: OptionType, spot_price: float, strike: float) -> float:
    intrinsic = max(0.0, spot_price - strike) if option_type == OptionType.CE else max(0.0, strike - spot_price)
    return round(max(50.0, intrinsic + spot_price * 0.004), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE agentic trader starter")
    parser.add_argument("--symbol", default="NIFTY", help="Trading symbol label")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument("--option-strike", type=float, help="NIFTY/BANKNIFTY option strike to paper trade")
    parser.add_argument("--option-expiry", type=lambda value: datetime.strptime(value, "%Y-%m-%d"))
    parser.add_argument("--refresh-instruments", action="store_true", help="Download/cache Angel instrument master before lookup")
    args = parser.parse_args()
    run_once(args.symbol, args.mode, args.option_strike, args.option_expiry, args.refresh_instruments)


if __name__ == "__main__":
    main()
