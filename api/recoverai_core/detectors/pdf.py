from __future__ import annotations

from io import BytesIO
from typing import Any

from pypdf import PdfReader

from ..models import Finding
from ..scoring import healthy_assessment, make_recovery


def analyze_pdf(data: bytes) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    details: dict[str, Any] = {
        "eofMarkerPresent": data.rstrip().endswith(b"%%EOF"),
    }

    try:
        reader = PdfReader(BytesIO(data), strict=True)
        encrypted = bool(reader.is_encrypted)
        details["pages"] = None if encrypted else len(reader.pages)
        details["encrypted"] = encrypted
        details["readableWithoutPassword"] = not encrypted
        details["metadata"] = {
            str(k).lstrip("/"): str(v)
            for k, v in (reader.metadata or {}).items()
        }

        if not details["eofMarkerPresent"]:
            findings.append(Finding(
                code="PDF_EOF_MISSING",
                severity="medium",
                message="The PDF end-of-file marker is missing.",
            ))

        if not findings:
            recovery = healthy_assessment()
            return {
                "status": "healthy",
                "corrupted": False,
                "signatureValid": True,
                "details": details,
                "assessment": {
                    "classification": "none",
                    "corruptionPercent": 0.0,
                    "recovery": {
                        "corruptionPercent": recovery.corruption_percent,
                        "recoverablePercent": recovery.recoverable_percent,
                        "unrecoverablePercent": recovery.unrecoverable_percent,
                        "confidence": recovery.confidence,
                        "basis": recovery.basis,
                    },
                    "findings": [],
                    "regions": [],
                },
            }, findings
    except Exception as strict_error:
        findings.append(Finding(
            code="PDF_STRICT_PARSE_FAILURE",
            severity="high",
            message=str(strict_error),
        ))
        details["strictParserError"] = str(strict_error)

        # pypdf's non-strict parser is useful as a salvage signal. It does not
        # guarantee a correct repair, but successful parsing means some content
        # remains structurally reachable.
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            details["lenientPages"] = len(reader.pages) if not reader.is_encrypted else None
            details["lenientParserSucceeded"] = True
            findings.append(Finding(
                code="PDF_LENIENT_PARSE_SUCCEEDED",
                severity="info",
                message="A lenient parser could still reach PDF objects; partial structural recovery may be possible.",
            ))
        except Exception as lenient_error:
            details["lenientParserSucceeded"] = False
            details["lenientParserError"] = str(lenient_error)

    lenient_ok = details.get("lenientParserSucceeded") is True
    recoverable = 80.0 if lenient_ok else 20.0
    corruption = 20.0 if lenient_ok else 80.0
    confidence = "medium" if lenient_ok else "low"
    recovery = make_recovery(
        corruption_percent=corruption,
        recoverable_percent=recoverable,
        unrecoverable_percent=100.0 - recoverable,
        confidence=confidence,
        basis=[
            "Strict PDF parsing failed.",
            "Lenient parsing success is treated as evidence that some structure remains reachable." if lenient_ok else "Both strict and lenient parsing failed; exact damaged extent cannot be measured from the file alone.",
        ],
    )
    return {
        "status": "corrupted",
        "corrupted": True,
        "signatureValid": True,
        "details": details,
        "assessment": {
            "classification": "confirmed",
            "corruptionPercent": recovery.corruption_percent,
            "recovery": {
                        "corruptionPercent": recovery.corruption_percent,
                        "recoverablePercent": recovery.recoverable_percent,
                        "unrecoverablePercent": recovery.unrecoverable_percent,
                        "confidence": recovery.confidence,
                        "basis": recovery.basis,
                    },
            "findings": [f.__dict__ for f in findings],
            "regions": [],
        },
    }, findings
