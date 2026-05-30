from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class JournalReport:
    rows: int
    symbols: Counter[str]
    strategies: Counter[str]
    actions: Counter[str]
    risk_approved: int
    agent_approved: int
    orders: int
    filter_blocks: int
    total_quantity: int

    def lines(self) -> list[str]:
        return [
            "Journal report",
            f"Rows: {self.rows}",
            f"Orders: {self.orders}",
            f"Risk approved: {self.risk_approved}",
            f"Agent approved: {self.agent_approved}",
            f"Filter blocks: {self.filter_blocks}",
            f"Total quantity: {self.total_quantity}",
            f"Symbols: {_format_counter(self.symbols)}",
            f"Strategies: {_format_counter(self.strategies)}",
            f"Actions: {_format_counter(self.actions)}",
        ]


def build_journal_report(path: Path, report_date: date | None = None) -> JournalReport:
    symbols: Counter[str] = Counter()
    strategies: Counter[str] = Counter()
    actions: Counter[str] = Counter()
    risk_approved = 0
    agent_approved = 0
    orders = 0
    filter_blocks = 0
    total_quantity = 0
    rows = 0

    if not path.exists():
        return JournalReport(0, symbols, strategies, actions, 0, 0, 0, 0, 0)

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            row = _normalise_mixed_schema_row(row)
            if report_date is not None and _row_date(row) != report_date:
                continue
            rows += 1
            symbols[_value(row, "symbol", "UNKNOWN")] += 1
            strategies[_value(row, "strategy_name", "legacy_or_manual")] += 1
            actions[_value(row, "action", "UNKNOWN")] += 1
            risk_approved += int(_as_bool(row.get("risk_approved", "")))
            agent_approved += int(_as_bool(row.get("agent_approved", "")))
            orders += int(bool(row.get("order_id")))
            filter_blocks += int(_as_bool(row.get("blocked_by_filters", "")))
            total_quantity += _as_int(row.get("quantity", "0"))

    return JournalReport(
        rows=rows,
        symbols=symbols,
        strategies=strategies,
        actions=actions,
        risk_approved=risk_approved,
        agent_approved=agent_approved,
        orders=orders,
        filter_blocks=filter_blocks,
        total_quantity=total_quantity,
    )


def _row_date(row: dict[str, str]) -> date | None:
    raw = row.get("timestamp", "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def _value(row: dict[str, str], key: str, fallback: str) -> str:
    return (row.get(key) or fallback).strip() or fallback


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y"}


def _as_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in counter.most_common())


def _normalise_mixed_schema_row(row: dict[str, str]) -> dict[str, str]:
    action_values = {"ENTER_LONG", "ENTER_SHORT", "EXIT", "WAIT"}
    extras = row.get(None)  # type: ignore[arg-type]
    if not extras or row.get("action") in action_values or row.get("entry") not in action_values:
        return row

    normalised = {
        "timestamp": row.get("timestamp", ""),
        "symbol": row.get("symbol", ""),
        "strategy_name": row.get("action", ""),
        "strategy_family": row.get("side", ""),
        "action": row.get("entry", ""),
        "side": row.get("stop_loss", ""),
        "entry": row.get("target", ""),
        "stop_loss": row.get("confidence", ""),
        "target": row.get("risk_approved", ""),
        "invalidation": row.get("quantity", ""),
        "expected_holding_minutes": row.get("agent_approved", ""),
        "blocked_by_filters": row.get("summary", ""),
        "filter_reasons": row.get("order_id", ""),
        "confidence": row.get("order_message", ""),
    }
    extra_names = ["risk_approved", "quantity", "agent_approved", "summary", "order_id", "order_message"]
    for name, value in zip(extra_names, extras, strict=False):
        normalised[name] = value
    return normalised
