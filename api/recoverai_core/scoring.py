from __future__ import annotations

from .models import Finding, RecoveryEstimate


def clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def make_recovery(
    corruption_percent: float,
    recoverable_percent: float,
    unrecoverable_percent: float,
    confidence: str,
    basis: list[str],
) -> RecoveryEstimate:
    return RecoveryEstimate(
        corruption_percent=round(clamp(corruption_percent), 1),
        recoverable_percent=round(clamp(recoverable_percent), 1),
        unrecoverable_percent=round(clamp(unrecoverable_percent), 1),
        confidence=confidence,
        basis=basis,
    )


def healthy_assessment() -> RecoveryEstimate:
    return make_recovery(
        corruption_percent=0,
        recoverable_percent=100,
        unrecoverable_percent=0,
        confidence="high",
        basis=["All implemented validation checks passed."],
    )


def structural_failure_assessment(
    *,
    recoverable_percent: float,
    corruption_percent: float,
    basis: list[str],
    confidence: str = "medium",
) -> RecoveryEstimate:
    recoverable = clamp(recoverable_percent)
    unrecoverable = clamp(100.0 - recoverable)
    return make_recovery(
        corruption_percent=corruption_percent,
        recoverable_percent=recoverable,
        unrecoverable_percent=unrecoverable,
        confidence=confidence,
        basis=basis,
    )
