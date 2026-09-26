from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryEstimate:
    corruption_percent: float
    recoverable_percent: float
    unrecoverable_percent: float
    confidence: str
    basis: list[str] = field(default_factory=list)


@dataclass
class AnalysisAssessment:
    classification: str
    corruption_percent: float
    recovery: RecoveryEstimate
    findings: list[Finding] = field(default_factory=list)
    regions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "corruptionPercent": self.corruption_percent,
            "recovery": {
                "corruptionPercent": self.recovery.corruption_percent,
                "recoverablePercent": self.recovery.recoverable_percent,
                "unrecoverablePercent": self.recovery.unrecoverable_percent,
                "confidence": self.recovery.confidence,
                "basis": self.recovery.basis,
            },
            "findings": [asdict(item) for item in self.findings],
            "regions": self.regions,
        }
