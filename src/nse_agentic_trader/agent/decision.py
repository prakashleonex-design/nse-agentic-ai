from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentVerdict(str, Enum):
    SUPPORT = "SUPPORT"
    CAUTION = "CAUTION"
    VETO = "VETO"
    INFO = "INFO"


@dataclass(frozen=True)
class AgentDecision:
    agent_name: str
    verdict: AgentVerdict
    confidence: float
    summary: str
    reasons: tuple[str, ...] = ()
    concerns: tuple[str, ...] = ()
    required_checks: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        return self.verdict in {AgentVerdict.SUPPORT, AgentVerdict.INFO}

    def lines(self) -> list[str]:
        lines = [
            f"Agent: {self.agent_name}",
            f"Verdict: {self.verdict.value}",
            f"Confidence: {self.confidence:.2f}",
            f"Summary: {self.summary}",
        ]
        lines.extend(f"Reason: {reason}" for reason in self.reasons)
        lines.extend(f"Concern: {concern}" for concern in self.concerns)
        lines.extend(f"Required check: {check}" for check in self.required_checks)
        return lines
