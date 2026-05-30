from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import MarketSnapshot
from nse_agentic_trader.session import SessionSummary, run_paper_session


@dataclass(frozen=True)
class StrategyComparisonRow:
    strategy: str
    summary: SessionSummary


@dataclass(frozen=True)
class StrategyRecommendation:
    action: str
    strategy: str | None
    reason: str
    concerns: tuple[str, ...]


def compare_strategies(
    settings: Settings,
    bars: list[MarketSnapshot],
    strategies: list[str],
    symbol: str,
    option_strike: float | None = None,
    option_expiry=None,
    max_entries: int | None = None,
    map_options: bool = True,
    apply_filters: bool = True,
) -> list[StrategyComparisonRow]:
    rows: list[StrategyComparisonRow] = []
    with TemporaryDirectory(prefix="nse-agentic-compare-") as temp_dir:
        base_path = Path(temp_dir)
        for strategy in strategies:
            isolated_settings = replace(
                settings,
                journal_path=base_path / f"{strategy}_journal.csv",
                risk_state_path=base_path / f"{strategy}_risk_state.json",
            )
            summary = run_paper_session(
                isolated_settings,
                bars,
                strategy,
                symbol,
                option_strike,
                option_expiry,
                max_entries,
                map_options,
                apply_filters,
                verbose=False,
            )
            rows.append(StrategyComparisonRow(strategy, summary))
    return sorted(rows, key=lambda row: (row.summary.net_realized_pnl, row.summary.win_rate), reverse=True)


def comparison_lines(rows: list[StrategyComparisonRow]) -> list[str]:
    if not rows:
        return ["No strategy comparison rows."]
    recommendation = recommend_strategy(rows)
    lines = [
        "Strategy comparison",
        "strategy | signals | orders | exits | wins | losses | win_rate | gross_pnl | costs | net_pnl",
    ]
    for row in rows:
        summary = row.summary
        lines.append(
            " | ".join(
                [
                    row.strategy,
                    str(summary.signals_seen),
                    str(summary.orders_accepted),
                    str(summary.exits),
                    str(summary.winning_exits),
                    str(summary.losing_exits),
                    f"{summary.win_rate:.2f}%",
                    f"{summary.gross_realized_pnl:.2f}",
                    f"{summary.estimated_costs:.2f}",
                    f"{summary.net_realized_pnl:.2f}",
                ]
            )
        )
    lines.extend(
        [
            "Recommendation",
            f"action: {recommendation.action}",
            f"strategy: {recommendation.strategy or 'none'}",
            f"reason: {recommendation.reason}",
        ]
    )
    for concern in recommendation.concerns:
        lines.append(f"concern: {concern}")
    return lines


def recommend_strategy(rows: list[StrategyComparisonRow]) -> StrategyRecommendation:
    traded_rows = [row for row in rows if row.summary.orders_accepted > 0]
    if not traded_rows:
        return StrategyRecommendation(
            "NO_TRADE",
            None,
            "No compared strategy produced an accepted paper trade.",
            ("Wait for a cleaner setup instead of forcing a trade.",),
        )

    best = max(traded_rows, key=lambda row: (row.summary.net_realized_pnl, row.summary.win_rate))
    concerns: list[str] = []
    if best.summary.exits == 0:
        concerns.append("Best strategy still has open/unresolved paper exposure in this replay.")
    if best.summary.net_realized_pnl <= 0:
        concerns.append("Best traded strategy is not profitable after estimated costs.")
        return StrategyRecommendation(
            "NO_TRADE",
            best.strategy,
            f"{best.strategy} was the best traded strategy, but net P&L is {best.summary.net_realized_pnl:.2f}.",
            tuple(concerns),
        )
    if best.summary.win_rate < 50:
        concerns.append("Win rate is below 50%; require stronger confirmation before considering this setup.")
    if best.summary.orders_accepted < 2:
        concerns.append("Evidence is thin because fewer than two trades were accepted.")
    action = "PAPER_CANDIDATE" if not concerns else "PAPER_CANDIDATE_WITH_CAUTION"
    return StrategyRecommendation(
        action,
        best.strategy,
        f"{best.strategy} has the strongest positive net result in this isolated paper comparison.",
        tuple(concerns),
    )


def build_strategy_comparison_report(
    rows: list[StrategyComparisonRow],
    symbol: str,
    data_source: str,
    map_options: bool,
    apply_filters: bool,
) -> str:
    recommendation = recommend_strategy(rows)
    lines = [
        "# Strategy Comparison",
        "",
        f"- Symbol: {symbol}",
        f"- Data source: {data_source}",
        f"- Option mapping: {'on' if map_options else 'off'}",
        f"- Avoid-trade filters: {'on' if apply_filters else 'off'}",
        "",
        "| Strategy | Signals | Orders | Exits | Wins | Losses | Win Rate | Gross P&L | Costs | Net P&L |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        summary = row.summary
        lines.append(
            "| "
            + " | ".join(
                [
                    row.strategy,
                    str(summary.signals_seen),
                    str(summary.orders_accepted),
                    str(summary.exits),
                    str(summary.winning_exits),
                    str(summary.losing_exits),
                    f"{summary.win_rate:.2f}%",
                    f"{summary.gross_realized_pnl:.2f}",
                    f"{summary.estimated_costs:.2f}",
                    f"{summary.net_realized_pnl:.2f}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Assistant Recommendation",
            "",
            f"- Action: {recommendation.action}",
            f"- Strategy: {recommendation.strategy or 'none'}",
            f"- Reason: {recommendation.reason}",
        ]
    )
    if recommendation.concerns:
        lines.extend(["", "### Concerns", ""])
        lines.extend(f"- {concern}" for concern in recommendation.concerns)
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Comparison runs are isolated paper simulations; they do not approve live trading.",
            "- Treat results as a filter for research, then review journal details and market regime fit.",
            "",
        ]
    )
    return "\n".join(lines)
