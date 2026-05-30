from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nse_agentic_trader.reports import JournalReport
from nse_agentic_trader.risk.state import RiskState


@dataclass(frozen=True)
class PostMarketSummary:
    report_date: date
    lines: list[str]

    def as_markdown(self) -> str:
        return "\n".join(self.lines) + "\n"


def build_postmarket_summary(report: JournalReport, risk_state: RiskState, report_date: date) -> PostMarketSummary:
    title = f"# Post-Market Summary - {report_date.isoformat()}"
    discipline = _discipline_note(report, risk_state)
    lines = [
        title,
        "",
        "## Session Snapshot",
        f"- Decisions journaled: {report.rows}",
        f"- Orders placed: {report.orders}",
        f"- Risk approvals: {report.risk_approved}",
        f"- Agent approvals: {report.agent_approved}",
        f"- Filter blocks: {report.filter_blocks}",
        f"- Total quantity: {report.total_quantity}",
        "",
        "## Risk State",
        f"- Trades today: {risk_state.trades_today}",
        f"- Realized P&L: {risk_state.realized_pnl:.2f}",
        f"- Kill switch: {'ON' if risk_state.kill_switch else 'OFF'}",
    ]
    if risk_state.kill_reason:
        lines.append(f"- Kill reason: {risk_state.kill_reason}")
    lines.extend(
        [
            "",
            "## Activity Mix",
            f"- Symbols: {_format_counter_text(report.symbols)}",
            f"- Strategies: {_format_counter_text(report.strategies)}",
            f"- Actions: {_format_counter_text(report.actions)}",
            f"- Review verdicts: {_format_counter_text(report.verdicts)}",
            "",
            "## Assistant Notes",
            f"- {discipline}",
            f"- {_next_step_note(report)}",
        ]
    )
    return PostMarketSummary(report_date, lines)


def _discipline_note(report: JournalReport, risk_state: RiskState) -> str:
    if risk_state.kill_switch:
        return "Kill switch is active; do not resume trading until the reason is reviewed."
    if report.rows == 0:
        return "No decisions were journaled; verify whether the system was running during the session."
    if report.filter_blocks > 0:
        return "Avoid-trade filters blocked setups; review whether those blocks protected you from poor conditions."
    if report.orders == 0:
        return "No orders were placed; review whether the strategy was too selective or market conditions were unsuitable."
    return "Session had executable activity; review whether each order followed the plan and stop-loss discipline."


def _next_step_note(report: JournalReport) -> str:
    if report.verdicts.get("REJECTED", 0) > 0 or report.verdicts.get("CAUTION", 0) > 0:
        return "Study rejected/caution reviews first; they usually contain the highest-value process feedback."
    if report.orders > 0:
        return "Compare entries against screenshots or candles and record whether execution matched the trade thesis."
    return "Run a backtest or replay on the same market window before changing strategy parameters."


def _format_counter_text(counter) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in counter.most_common())
