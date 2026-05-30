from __future__ import annotations

from dataclasses import dataclass

from nse_agentic_trader.models import MarketSnapshot


@dataclass(frozen=True)
class CandleValidationIssue:
    severity: str
    index: int
    message: str


@dataclass(frozen=True)
class CandleValidationReport:
    bars: int
    issues: tuple[CandleValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "ERROR" for issue in self.issues)

    def lines(self) -> list[str]:
        lines = [
            "Candle validation",
            f"Bars: {self.bars}",
            f"Status: {'OK' if self.ok else 'FAILED'}",
        ]
        for issue in self.issues:
            lines.append(f"[{issue.severity}] row {issue.index}: {issue.message}")
        return lines


def validate_candles(bars: list[MarketSnapshot], min_bars: int = 1) -> CandleValidationReport:
    issues: list[CandleValidationIssue] = []
    if len(bars) < min_bars:
        issues.append(CandleValidationIssue("ERROR", 0, f"Expected at least {min_bars} bars, got {len(bars)}"))

    previous = None
    for index, bar in enumerate(bars, start=1):
        if previous is not None and bar.timestamp <= previous.timestamp:
            issues.append(CandleValidationIssue("ERROR", index, "Timestamp is not strictly increasing"))
        previous = bar

        prices = [bar.open, bar.high, bar.low, bar.close]
        if any(price <= 0 for price in prices):
            issues.append(CandleValidationIssue("ERROR", index, "OHLC prices must be positive"))
        if bar.high < max(bar.open, bar.close, bar.low):
            issues.append(CandleValidationIssue("ERROR", index, "High is below one or more OHLC values"))
        if bar.low > min(bar.open, bar.close, bar.high):
            issues.append(CandleValidationIssue("ERROR", index, "Low is above one or more OHLC values"))
        if bar.volume < 0:
            issues.append(CandleValidationIssue("ERROR", index, "Volume cannot be negative"))
        elif bar.volume == 0:
            issues.append(CandleValidationIssue("WARN", index, "Volume is zero"))

    return CandleValidationReport(len(bars), tuple(issues))
