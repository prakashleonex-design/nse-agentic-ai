from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from nse_agentic_trader.agent import TradeReviewer
from nse_agentic_trader.broker.paper import PaperBroker
from nse_agentic_trader.config import Settings
from nse_agentic_trader.costs import CostModel
from nse_agentic_trader.data_quality import validate_candles
from nse_agentic_trader.filters import AvoidTradeFilterEngine, apply_filter_block
from nse_agentic_trader.instruments import AngelInstrumentMaster, OptionQuery
from nse_agentic_trader.journal import Journal
from nse_agentic_trader.market_data import AngelHistoricalCandleProvider, CsvCandleProvider
from nse_agentic_trader.models import MarketSnapshot, OptionContract, OptionType, OrderRequest, RiskDecision, Side, SignalAction, TradeSignal
from nse_agentic_trader.risk import RiskManager
from nse_agentic_trader.strategy import build_strategy


@dataclass(frozen=True)
class SessionSummary:
    bars_seen: int
    signals_seen: int
    orders_accepted: int
    exits: int
    gross_realized_pnl: float
    estimated_costs: float
    net_realized_pnl: float
    winning_exits: int
    losing_exits: int

    @property
    def realized_pnl(self) -> float:
        return self.gross_realized_pnl

    @property
    def win_rate(self) -> float:
        closed_trades = self.winning_exits + self.losing_exits
        if closed_trades == 0:
            return 0.0
        return round((self.winning_exits / closed_trades) * 100, 2)


def load_bars(
    settings: Settings,
    symbol: str,
    data_source: str,
    csv_path: Path | None,
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
        from nse_agentic_trader.app import sample_bars

        bars = sample_bars(symbol)
        _raise_if_invalid(bars)
        return bars
    if data_source == "csv":
        if csv_path is None:
            raise SystemExit("--csv-path is required when --data-source csv")
        try:
            bars = list(CsvCandleProvider(csv_path, symbol).candles())
        except FileNotFoundError as exc:
            raise SystemExit(str(exc)) from exc
        _raise_if_invalid(bars)
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
        _raise_if_invalid(bars)
        return bars
    raise SystemExit(f"Unknown data source: {data_source}")


def _raise_if_invalid(bars: list[MarketSnapshot]) -> None:
    report = validate_candles(bars)
    if not report.ok:
        raise SystemExit("\n".join(report.lines()))


def run_paper_session(
    settings: Settings,
    bars: list[MarketSnapshot],
    strategy_name: str,
    symbol: str,
    option_strike: float | None,
    option_expiry: datetime | None,
    max_entries: int | None = None,
    map_options: bool = True,
    apply_filters: bool = True,
) -> SessionSummary:
    if map_options:
        broker = PaperBroker(settings.paper_option_slippage_bps, settings.paper_option_min_slippage)
    else:
        broker = PaperBroker(settings.paper_underlying_slippage_bps, settings.paper_underlying_min_slippage)
    strategy = build_strategy(strategy_name)
    filters = AvoidTradeFilterEngine()
    risk_manager = RiskManager(settings)
    reviewer = TradeReviewer()
    journal = Journal(settings.journal_path)
    cost_model = CostModel(settings.paper_brokerage_per_order, settings.paper_transaction_cost_bps)
    active_contracts: dict[str, OptionContract] = {}
    signals_seen = 0
    orders_accepted = 0
    exits = 0
    last_realized_pnl = 0.0
    estimated_costs = 0.0
    winning_exits = 0
    losing_exits = 0

    for bar in bars:
        filters.on_bar(bar)
        for exit_bar in _exit_bars_for_positions(bar, active_contracts, broker):
            for result in broker.simulate_intrabar_exits(exit_bar):
                exits += 1
                exit_fill = broker.fills[-1]
                estimated_costs += cost_model.estimate_fill_cost(exit_fill)
                pnl_delta = broker.realized_pnl - last_realized_pnl
                last_realized_pnl = broker.realized_pnl
                risk_manager.record_realized_pnl(pnl_delta)
                if pnl_delta > 0:
                    winning_exits += 1
                elif pnl_delta < 0:
                    losing_exits += 1
                print(result.message)

        if _has_open_position(broker):
            continue
        if max_entries is not None and orders_accepted >= max_entries:
            continue

        signal = strategy.on_bar(bar)
        if signal.action == SignalAction.WAIT:
            continue
        signals_seen += 1

        filter_decision = filters.evaluate(signal, bar)
        if apply_filters and filter_decision.blocked:
            blocked_signal = apply_filter_block(signal, filter_decision)
            risk = RiskDecision(False, 0, "Avoid-trade filters blocked this setup")
            review = reviewer.review(blocked_signal, risk)
            journal.write(blocked_signal, risk, review, None)
            print(review.summary)
            continue

        order_signal, contract = _option_signal_if_available(
            signal,
            bar.close,
            option_strike,
            option_expiry,
            settings.instrument_master_cache,
            map_options,
        )
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
                estimated_costs += cost_model.estimate_fill_cost(broker.fills[-1])
                orders_accepted += 1
                risk_manager.record_trade()
                if contract:
                    active_contracts[contract.instrument.trading_symbol] = contract

        journal.write(order_signal, risk, review, order_result)
        print(review.summary)
        if contract:
            print(f"Contract: {contract.instrument.trading_symbol} token={contract.instrument.token} lot={contract.instrument.lot_size}")
        if order_result:
            print(f"Order: {order_result.order_id} - {order_result.message}")

    gross_realized_pnl = broker.realized_pnl
    return SessionSummary(
        bars_seen=len(bars),
        signals_seen=signals_seen,
        orders_accepted=orders_accepted,
        exits=exits,
        gross_realized_pnl=gross_realized_pnl,
        estimated_costs=round(estimated_costs, 2),
        net_realized_pnl=round(gross_realized_pnl - estimated_costs, 2),
        winning_exits=winning_exits,
        losing_exits=losing_exits,
    )


def _option_signal_if_available(
    signal: TradeSignal,
    spot_price: float,
    option_strike: float | None,
    option_expiry: datetime | None,
    cache_path: Path,
    map_options: bool,
) -> tuple[TradeSignal, OptionContract | None]:
    if not map_options or signal.side is None or signal.entry_price is None or signal.stop_loss is None:
        return signal, None
    option_type = OptionType.CE if signal.side == Side.BUY else OptionType.PE
    strike = option_strike or round(spot_price / 50) * 50
    try:
        contract = AngelInstrumentMaster(cache_path).find_index_option(
            OptionQuery(signal.symbol, option_type, float(strike), option_expiry)
        )
    except (FileNotFoundError, LookupError, ValueError):
        return signal, None

    premium = estimate_option_premium(option_type, spot_price, contract.strike)
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


def estimate_option_premium(option_type: OptionType, spot_price: float, strike: float) -> float:
    intrinsic = max(0.0, spot_price - strike) if option_type == OptionType.CE else max(0.0, strike - spot_price)
    return round(max(50.0, intrinsic + spot_price * 0.004), 2)


def _has_open_position(broker: PaperBroker) -> bool:
    return any(position.quantity != 0 for position in broker.positions.values())


def _exit_bars_for_positions(
    underlying_bar: MarketSnapshot,
    active_contracts: dict[str, OptionContract],
    broker: PaperBroker,
) -> list[MarketSnapshot]:
    bars: list[MarketSnapshot] = [underlying_bar]
    for symbol, position in broker.positions.items():
        if position.quantity == 0 or symbol == underlying_bar.symbol:
            continue
        contract = active_contracts.get(symbol)
        if contract is None:
            continue
        bars.append(_estimated_option_bar(underlying_bar, contract))
    return bars


def _estimated_option_bar(bar: MarketSnapshot, contract: OptionContract) -> MarketSnapshot:
    option_type = contract.option_type
    strike = contract.strike
    open_price = estimate_option_premium(option_type, bar.open, strike)
    close = estimate_option_premium(option_type, bar.close, strike)
    if option_type == OptionType.CE:
        high = estimate_option_premium(option_type, bar.high, strike)
        low = estimate_option_premium(option_type, bar.low, strike)
    else:
        high = estimate_option_premium(option_type, bar.low, strike)
        low = estimate_option_premium(option_type, bar.high, strike)
    return MarketSnapshot(
        symbol=contract.instrument.trading_symbol,
        timestamp=bar.timestamp,
        open=open_price,
        high=max(high, open_price, close),
        low=min(low, open_price, close),
        close=close,
        volume=bar.volume,
    )
