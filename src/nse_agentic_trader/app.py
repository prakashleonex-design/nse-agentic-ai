from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from nse_agentic_trader.agent import TradeReviewer
from nse_agentic_trader.broker import PaperBroker
from nse_agentic_trader.broker.angel import AngelSmartApiBroker
from nse_agentic_trader.checklist import build_premarket_checklist, checklist_lines
from nse_agentic_trader.config import load_settings
from nse_agentic_trader.config_tools import init_env_file, settings_lines
from nse_agentic_trader.data_quality import validate_candles
from nse_agentic_trader.execution import build_angel_order_params, validate_order_request
from nse_agentic_trader.filters import AvoidTradeFilterEngine, apply_filter_block
from nse_agentic_trader.instruments import AngelInstrumentMaster, OptionQuery, ensure_instrument_master, instrument_master_info
from nse_agentic_trader.journal import Journal
from nse_agentic_trader.market_data import AngelHistoricalCandleProvider, CsvCandleProvider
from nse_agentic_trader.models import MarketSnapshot, OptionContract, OptionType, OrderRequest, RiskDecision, Side, SignalAction, TradeSignal
from nse_agentic_trader.postmarket import build_postmarket_summary
from nse_agentic_trader.risk import RiskManager
from nse_agentic_trader.risk.state import RiskStateStore
from nse_agentic_trader.reports import build_journal_report
from nse_agentic_trader.session import load_bars as load_session_bars
from nse_agentic_trader.session import run_paper_session
from nse_agentic_trader.strategy import available_strategy_names, build_strategy


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
    strategy_name: str = "opening_range_breakout",
    data_source: str = "sample",
    csv_path=None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    interval: str = "ONE_MINUTE",
    data_exchange: str = "NSE",
    data_token: str | None = None,
    data_option_type: OptionType = OptionType.CE,
) -> None:
    settings = load_settings()
    broker = build_broker(mode)
    strategy = build_strategy(strategy_name)
    filters = AvoidTradeFilterEngine()
    risk_manager = RiskManager(settings)
    reviewer = TradeReviewer()
    journal = Journal(settings.journal_path)
    if refresh_instruments:
        ensure_instrument_master(
            settings.instrument_master_url,
            settings.instrument_master_cache,
            settings.instrument_master_max_age_hours,
        )

    bars = _load_bars(
        settings,
        symbol,
        data_source,
        csv_path,
        from_date,
        to_date,
        interval,
        data_exchange,
        data_token,
        data_option_type,
        option_strike,
        option_expiry,
    )

    for bar in bars:
        filters.on_bar(bar)
        signal = strategy.on_bar(bar)
        if signal.action == SignalAction.WAIT:
            continue
        filter_decision = filters.evaluate(signal, bar)
        if filter_decision.blocked:
            blocked_signal = apply_filter_block(signal, filter_decision)
            risk = RiskDecision(False, 0, "Avoid-trade filters blocked this setup")
            review = reviewer.review(blocked_signal, risk)
            journal.write(blocked_signal, risk, review, None)
            print(review.summary)
            break

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
            strategy_name=signal.strategy_name,
            strategy_family=signal.strategy_family,
            invalidation=signal.invalidation,
            expected_holding_minutes=signal.expected_holding_minutes,
        ),
        contract,
    )


def _estimate_option_premium(option_type: OptionType, spot_price: float, strike: float) -> float:
    intrinsic = max(0.0, spot_price - strike) if option_type == OptionType.CE else max(0.0, strike - spot_price)
    return round(max(50.0, intrinsic + spot_price * 0.004), 2)


def _load_bars(
    settings,
    symbol: str,
    data_source: str,
    csv_path,
    from_date: datetime | None,
    to_date: datetime | None,
    interval: str,
    data_exchange: str,
    data_token: str | None,
    data_option_type: OptionType,
    option_strike: float | None,
    option_expiry: datetime | None,
) -> list[MarketSnapshot]:
    if data_source == "sample":
        bars = sample_bars(symbol)
        _raise_if_invalid_candles(bars)
        return bars
    if data_source == "csv":
        if csv_path is None:
            raise SystemExit("--csv-path is required when --data-source csv")
        bars = list(CsvCandleProvider(csv_path, symbol).candles())
        _raise_if_invalid_candles(bars)
        return bars
    if data_source == "angel":
        if from_date is None or to_date is None:
            raise SystemExit("--from-date and --to-date are required when --data-source angel")
        exchange = data_exchange
        token = data_token
        candle_symbol = symbol
        if token is None and option_strike is not None:
            contract = AngelInstrumentMaster(settings.instrument_master_cache).find_index_option(
                OptionQuery(symbol, data_option_type, option_strike, option_expiry)
            )
            exchange = contract.instrument.exchange
            token = contract.instrument.token
            candle_symbol = contract.instrument.trading_symbol
        if token is None:
            raise SystemExit("--data-token is required for Angel candles unless --option-strike maps to a cached option contract")
        bars = list(
            AngelHistoricalCandleProvider(
                settings,
                candle_symbol,
                exchange,
                token,
                interval,
                from_date,
                to_date,
            ).candles()
        )
        _raise_if_invalid_candles(bars)
        return bars
    raise SystemExit(f"Unknown data source: {data_source}")


def _raise_if_invalid_candles(bars: list[MarketSnapshot]) -> None:
    report = validate_candles(bars)
    if not report.ok:
        raise SystemExit("\n".join(report.lines()))


def validate_instrument(
    symbol: str,
    option_type: OptionType,
    strike: float,
    expiry: datetime | None,
    refresh_instruments: bool,
) -> None:
    settings = load_settings()
    if refresh_instruments:
        ensure_instrument_master(
            settings.instrument_master_url,
            settings.instrument_master_cache,
            settings.instrument_master_max_age_hours,
        )
    info = instrument_master_info(settings.instrument_master_cache)
    if not info.exists:
        raise SystemExit(f"Instrument cache missing at {info.path}. Run with --refresh-instruments.")
    contract = AngelInstrumentMaster(settings.instrument_master_cache).find_index_option(
        OptionQuery(symbol, option_type, strike, expiry)
    )
    print(f"Cache: {info.path}")
    print(f"Cache age hours: {info.age_hours:.2f}" if info.age_hours is not None else "Cache age hours: unknown")
    print(f"Instrument count: {info.instrument_count}")
    print(f"Trading symbol: {contract.instrument.trading_symbol}")
    print(f"Token: {contract.instrument.token}")
    print(f"Exchange: {contract.instrument.exchange}")
    print(f"Expiry: {contract.expiry.date().isoformat()}")
    print(f"Strike: {contract.strike:g}")
    print(f"Option type: {contract.option_type.value}")
    print(f"Lot size: {contract.instrument.lot_size}")
    print(f"Tick size: {contract.instrument.tick_size}")


def risk_status() -> None:
    settings = load_settings()
    state = RiskStateStore(settings.risk_state_path).load()
    print(f"Risk state: {settings.risk_state_path}")
    print(f"Date: {state.trade_date}")
    print(f"Trades today: {state.trades_today}")
    print(f"Realized P&L: {state.realized_pnl:.2f}")
    print(f"Kill switch: {'ON' if state.kill_switch else 'OFF'}")
    if state.kill_reason:
        print(f"Kill reason: {state.kill_reason}")


def risk_kill(reason: str) -> None:
    settings = load_settings()
    state = RiskStateStore(settings.risk_state_path).kill(reason)
    print(f"Kill switch ON: {state.kill_reason}")


def risk_reset() -> None:
    settings = load_settings()
    state = RiskStateStore(settings.risk_state_path).reset()
    print(f"Risk state reset for {state.trade_date}")


def run_backtest(args) -> None:
    settings = load_settings()
    if args.refresh_instruments:
        ensure_instrument_master(
            settings.instrument_master_url,
            settings.instrument_master_cache,
            settings.instrument_master_max_age_hours,
        )
    bars = load_session_bars(
        settings,
        args.symbol,
        args.data_source,
        args.csv_path,
        args.from_date,
        args.to_date,
        args.interval,
        args.data_exchange,
        args.data_token,
        OptionType(args.data_option_type),
        args.option_strike,
        args.option_expiry,
    )
    summary = run_paper_session(
        settings,
        bars,
        args.strategy,
        args.symbol,
        args.option_strike,
        args.option_expiry,
        args.max_entries,
        not args.no_option_mapping,
        not args.no_filters,
    )
    print("Backtest summary")
    print(f"Bars seen: {summary.bars_seen}")
    print(f"Signals seen: {summary.signals_seen}")
    print(f"Orders accepted: {summary.orders_accepted}")
    print(f"Exits: {summary.exits}")
    print(f"Winning exits: {summary.winning_exits}")
    print(f"Losing exits: {summary.losing_exits}")
    print(f"Gross realized P&L: {summary.gross_realized_pnl:.2f}")
    print(f"Estimated costs: {summary.estimated_costs:.2f}")
    print(f"Net realized P&L: {summary.net_realized_pnl:.2f}")


def run_report(args) -> None:
    settings = load_settings()
    report = build_journal_report(args.journal_path or settings.journal_path, args.date.date() if args.date else None)
    for line in report.lines():
        print(line)


def validate_order(args) -> None:
    settings = load_settings()
    order = OrderRequest(
        symbol=args.trading_symbol,
        side=Side(args.side),
        quantity=args.quantity,
        order_type=args.order_type,
        product_type=args.product_type,
        price=args.price,
        stop_loss=args.stop_loss,
        target=args.target,
        exchange=args.exchange,
        symboltoken=args.symboltoken,
        tick_size=args.tick_size,
        lot_size=args.lot_size,
    )
    validation = validate_order_request(order, settings, args.manual_approval == "APPROVE")
    print(f"Validation: {'APPROVED' if validation.approved else 'REJECTED'}")
    if validation.reasons:
        for reason in validation.reasons:
            print(f"- {reason}")
    print("Angel payload:")
    for key, value in build_angel_order_params(order, settings).items():
        print(f"{key}: {value}")


def config_show() -> None:
    for line in settings_lines(load_settings()):
        print(line)


def config_init(args) -> None:
    print(init_env_file(overwrite=args.overwrite))


def run_premarket() -> None:
    for line in checklist_lines(build_premarket_checklist(load_settings())):
        print(line)


def run_postmarket(args) -> None:
    settings = load_settings()
    report_date = args.date.date() if args.date else date.today()
    report = build_journal_report(args.journal_path or settings.journal_path, report_date)
    risk_state = RiskStateStore(settings.risk_state_path).load()
    summary = build_postmarket_summary(report, risk_state, report_date)
    text = summary.as_markdown()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote post-market summary to {args.output}")
    else:
        print(text, end="")


def validate_data(args) -> None:
    bars = _load_bars(
        load_settings(),
        args.symbol,
        args.data_source,
        args.csv_path,
        args.from_date,
        args.to_date,
        args.interval,
        args.data_exchange,
        args.data_token,
        OptionType(args.data_option_type),
        args.option_strike,
        args.option_expiry,
    )
    for line in validate_candles(bars, min_bars=args.min_bars).lines():
        print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE agentic trader starter")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one paper/live strategy pass")
    _add_run_args(run_parser)

    backtest_parser = subparsers.add_parser("backtest", help="Replay candles through paper session simulation")
    _add_run_args(backtest_parser)
    backtest_parser.add_argument("--max-entries", type=int, default=None)
    backtest_parser.add_argument("--no-option-mapping", action="store_true", help="Keep signals on the input symbol instead of mapping to options")
    backtest_parser.add_argument("--no-filters", action="store_true", help="Disable avoid-trade filters for strategy mechanics testing")

    instruments_parser = subparsers.add_parser("instruments", help="Instrument master utilities")
    instrument_subparsers = instruments_parser.add_subparsers(dest="instrument_command")
    validate_parser = instrument_subparsers.add_parser("validate", help="Validate an NSE index option contract")
    validate_parser.add_argument("--symbol", required=True, choices=["NIFTY", "BANKNIFTY"])
    validate_parser.add_argument("--option-type", required=True, choices=[item.value for item in OptionType])
    validate_parser.add_argument("--strike", required=True, type=float)
    validate_parser.add_argument("--expiry", type=lambda value: datetime.strptime(value, "%Y-%m-%d"))
    validate_parser.add_argument("--refresh-instruments", action="store_true")

    risk_parser = subparsers.add_parser("risk", help="Risk state and kill-switch utilities")
    risk_subparsers = risk_parser.add_subparsers(dest="risk_command")
    risk_subparsers.add_parser("status", help="Show current risk state")
    kill_parser = risk_subparsers.add_parser("kill", help="Turn on the kill switch")
    kill_parser.add_argument("--reason", default="Manual kill switch")
    risk_subparsers.add_parser("reset", help="Reset today's paper risk state")

    report_parser = subparsers.add_parser("report", help="Summarize journal decisions and orders")
    report_parser.add_argument("--journal-path", type=Path)
    report_parser.add_argument("--date", type=lambda value: datetime.strptime(value, "%Y-%m-%d"))

    order_parser = subparsers.add_parser("order", help="Order dry-run validation utilities")
    order_subparsers = order_parser.add_subparsers(dest="order_command")
    validate_order_parser = order_subparsers.add_parser("validate", help="Validate an Angel order payload without placing it")
    validate_order_parser.add_argument("--trading-symbol", required=True)
    validate_order_parser.add_argument("--symboltoken", required=True)
    validate_order_parser.add_argument("--exchange", default="NFO")
    validate_order_parser.add_argument("--side", choices=[item.value for item in Side], required=True)
    validate_order_parser.add_argument("--quantity", type=int, required=True)
    validate_order_parser.add_argument("--lot-size", type=int)
    validate_order_parser.add_argument("--order-type", default="MARKET")
    validate_order_parser.add_argument("--product-type", default="INTRADAY")
    validate_order_parser.add_argument("--price", type=float)
    validate_order_parser.add_argument("--stop-loss", type=float, required=True)
    validate_order_parser.add_argument("--target", type=float)
    validate_order_parser.add_argument("--tick-size", type=float, default=0.05)
    validate_order_parser.add_argument("--manual-approval", default="", help="Pass APPROVE only for explicit live-mode approval")

    config_parser = subparsers.add_parser("config", help="Configuration helpers")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show effective settings with secrets masked")
    config_init_parser = config_subparsers.add_parser("init", help="Create .env from .env.example")
    config_init_parser.add_argument("--overwrite", action="store_true")

    subparsers.add_parser("premarket", help="Run daily pre-market safety checklist")

    postmarket_parser = subparsers.add_parser("postmarket", help="Build an end-of-day journal and risk summary")
    postmarket_parser.add_argument("--journal-path", type=Path)
    postmarket_parser.add_argument("--date", type=lambda value: datetime.strptime(value, "%Y-%m-%d"))
    postmarket_parser.add_argument("--output", type=Path, help="Optional Markdown output path")

    data_parser = subparsers.add_parser("data", help="Market-data utilities")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    validate_data_parser = data_subparsers.add_parser("validate", help="Validate candle data quality")
    _add_run_args(validate_data_parser)
    validate_data_parser.add_argument("--min-bars", type=int, default=1)

    _add_run_args(parser)
    args = parser.parse_args()
    if args.command in (None, "run"):
        run_once(
            args.symbol,
            args.mode,
            args.option_strike,
            args.option_expiry,
            args.refresh_instruments,
            args.strategy,
            args.data_source,
            args.csv_path,
            args.from_date,
            args.to_date,
            args.interval,
            args.data_exchange,
            args.data_token,
            OptionType(args.data_option_type),
        )
        return
    if args.command == "backtest":
        run_backtest(args)
        return
    if args.command == "instruments" and args.instrument_command == "validate":
        validate_instrument(args.symbol, OptionType(args.option_type), args.strike, args.expiry, args.refresh_instruments)
        return
    if args.command == "risk" and args.risk_command == "status":
        risk_status()
        return
    if args.command == "risk" and args.risk_command == "kill":
        risk_kill(args.reason)
        return
    if args.command == "risk" and args.risk_command == "reset":
        risk_reset()
        return
    if args.command == "report":
        run_report(args)
        return
    if args.command == "order" and args.order_command == "validate":
        validate_order(args)
        return
    if args.command == "config" and args.config_command == "show":
        config_show()
        return
    if args.command == "config" and args.config_command == "init":
        config_init(args)
        return
    if args.command == "premarket":
        run_premarket()
        return
    if args.command == "postmarket":
        run_postmarket(args)
        return
    if args.command == "data" and args.data_command == "validate":
        validate_data(args)
        return
    parser.print_help()


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", default="NIFTY", help="Trading symbol label")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument("--option-strike", type=float, help="NIFTY/BANKNIFTY option strike to paper trade")
    parser.add_argument("--option-expiry", type=lambda value: datetime.strptime(value, "%Y-%m-%d"))
    parser.add_argument("--refresh-instruments", action="store_true", help="Download/cache Angel instrument master before lookup")
    parser.add_argument("--data-source", choices=["sample", "csv", "angel"], default="sample")
    parser.add_argument("--csv-path", type=Path, help="CSV candle file with timestamp,open,high,low,close,volume columns")
    parser.add_argument("--from-date", type=lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M"))
    parser.add_argument("--to-date", type=lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M"))
    parser.add_argument("--interval", default="ONE_MINUTE", help="Angel candle interval, e.g. ONE_MINUTE")
    parser.add_argument("--data-exchange", default="NSE", help="Exchange for Angel candle data")
    parser.add_argument("--data-token", help="Angel symbol token for historical candle data")
    parser.add_argument("--data-option-type", choices=[item.value for item in OptionType], default=OptionType.CE.value)
    parser.add_argument(
        "--strategy",
        choices=available_strategy_names(),
        default="opening_range_breakout",
        help="Strategy module to run",
    )


if __name__ == "__main__":
    main()
