from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib

from .detectors.containers import analyze_zip
from .detectors.image import analyze_image
from .detectors.pdf import analyze_pdf
from .scoring import clamp

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff",
    ".webp", ".ico", ".ppm", ".pgm", ".pbm", ".pnm", ".jp2",
}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".docx", ".zip"}


def _mime(filename: str, supplied: str) -> str:
    return supplied or "application/octet-stream"


def _header_matches(data: bytes, extension: str) -> bool:
    if not data:
        return False
    if extension in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if extension == ".bmp":
        return data.startswith(b"BM")
    if extension in {".tif", ".tiff"}:
        return data.startswith((b"II*\x00", b"MM\x00*"))
    if extension == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if extension == ".pdf":
        return data.startswith(b"%PDF-")
    if extension in {".zip", ".docx"}:
        return data.startswith(b"PK")
    return True


def _base(filename: str, data: bytes, mime_type: str) -> dict[str, Any]:
    size = len(data)
    return {
        "fileName": filename,
        "extension": Path(filename).suffix.lower(),
        "mimeType": _mime(filename, mime_type),
        "size": size,
        "sizeFormatted": _human_size(size),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def _attach_ai_signals(base: dict[str, Any], data: bytes) -> None:
    """Attach advisory ML signals and an explainable evidence priority.

    The deterministic format validators remain authoritative for integrity.
    The ML models were trained on synthetic fragment data, so their output is
    deliberately presented as supporting evidence rather than a replacement
    for parser validation.
    """
    try:
        from ml.inference.service import analyze_with_models
        ai = analyze_with_models(data)
    except Exception as exc:
        ai = {
            "available": False,
            "models": {},
            "note": f"ML advisory signals unavailable: {exc}",
        }

    analysis = base.get("analysis") or {}
    assessment = analysis.get("assessment") or {}
    recovery = assessment.get("recovery") or {}
    corruption = float(assessment.get("corruptionPercent", 100.0) or 0.0)
    recoverable = float(recovery.get("recoverablePercent", 0.0) or 0.0)
    integrity = clamp(100.0 - corruption)
    validation_bonus = 100.0 if analysis.get("status") == "healthy" else 60.0 if analysis.get("status") == "suspected" else 20.0
    priority_score = round((0.45 * recoverable) + (0.35 * integrity) + (0.20 * validation_bonus), 1)
    priority = "high" if priority_score >= 75 else "medium" if priority_score >= 45 else "low"

    assessment["priority"] = {
        "level": priority,
        "score": priority_score,
        "basis": [
            "Recovery potential from the format-aware analyzer.",
            "Observed integrity/structural health.",
            "Validation outcome of the supported file parser.",
        ],
    }
    analysis["assessment"] = assessment
    analysis["ai"] = ai
    base["analysis"] = analysis


def analyze_file(filename: str, data: bytes, mime_type: str) -> dict[str, Any]:
    base = _base(filename, data, mime_type)
    extension = base["extension"]

    if extension not in SUPPORTED_EXTENSIONS:
        base["analysis"] = {
            "status": "unsupported",
            "corrupted": False,
            "signatureValid": False,
            "details": {"error": "Unsupported file type."},
            "assessment": {
                "classification": "unknown",
                "corruptionPercent": 0.0,
                "recovery": {
                    "corruption_percent": 0.0,
                    "recoverable_percent": 0.0,
                    "unrecoverable_percent": 100.0,
                    "confidence": "low",
                    "basis": ["The format is not supported by the current engine."],
                },
                "findings": [],
                "regions": [],
            },
        }
        _attach_ai_signals(base, data)
        return base

    if not data:
        base["analysis"] = {
            "status": "corrupted",
            "corrupted": True,
            "signatureValid": False,
            "details": {"error": "The uploaded file is empty."},
            "assessment": {
                "classification": "confirmed",
                "corruptionPercent": 100.0,
                "recovery": {
                    "corruption_percent": 100.0,
                    "recoverable_percent": 0.0,
                    "unrecoverable_percent": 100.0,
                    "confidence": "high",
                    "basis": ["The file contains no bytes."],
                },
                "findings": [],
                "regions": [],
            },
        }
        _attach_ai_signals(base, data)
        return base

    if not _header_matches(data, extension):
        base["analysis"] = {
            "status": "corrupted",
            "corrupted": True,
            "signatureValid": False,
            "details": {"error": f"The file signature does not match the expected {extension.upper()} format."},
            "assessment": {
                "classification": "confirmed",
                "corruptionPercent": 100.0,
                "recovery": {
                    "corruption_percent": 100.0,
                    "recoverable_percent": 0.0,
                    "unrecoverable_percent": 100.0,
                    "confidence": "high",
                    "basis": ["The file header/signature does not match the declared extension."],
                },
                "findings": [],
                "regions": [],
            },
        }
        _attach_ai_signals(base, data)
        return base

    if extension in IMAGE_EXTENSIONS:
        analysis, _, _ = analyze_image(data, extension)
    elif extension == ".pdf":
        analysis, _ = analyze_pdf(data)
    elif extension == ".docx":
        analysis, _ = analyze_zip(data, is_docx=True)
    elif extension == ".zip":
        analysis, _ = analyze_zip(data, is_docx=False)
    else:
        analysis = {"status": "unsupported", "corrupted": False, "details": {}}

    base["analysis"] = analysis
    _attach_ai_signals(base, data)
    return base
