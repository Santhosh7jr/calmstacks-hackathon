"""Runtime inference helpers for the RecoverAI trained models.

The models are trained on fragment-level forensic features. Runtime inference
therefore adds conservative context defaults when only a complete uploaded file
is available. These predictions are advisory signals and never replace the
format-aware validators in recoverai_core.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import warnings
import numpy as np
import pandas as pd

from ..features.feature_extractor import extract_features

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

ML_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ML_DIR / "models"

MODEL_PATHS = {
    "file_classification": MODELS_DIR / "file_classification" / "file_classifier.joblib",
    "corruption_detection": MODELS_DIR / "corruption_detection" / "corruption_detector.joblib",
    "recovery_confidence": MODELS_DIR / "recovery_confidence" / "recovery_model.joblib",
    "fragment_matching": MODELS_DIR / "fragment_matching" / "fragment_matcher.joblib",
    "image_purification": MODELS_DIR / "image_purification" / "image_purifier.joblib",
}


def _context_features(data: bytes) -> dict[str, Any]:
    features = extract_features(data)
    size = len(data)
    features.update(
        {
            "source_file_size": size,
            "total_fragments": 1,
            "fragment_position": 0,
            "offset": 0,
            "original_size": size,
        }
    )
    return features


@lru_cache(maxsize=8)
def _load(name: str) -> dict[str, Any] | None:
    path = MODEL_PATHS[name]
    if not path.exists():
        return None
    try:
        loaded = joblib.load(path)
    except Exception:
        return None
    if not isinstance(loaded, dict) or "model" not in loaded:
        return None
    return loaded


def _frame(features: dict[str, Any], columns: list[str]) -> pd.DataFrame:
    row = {column: features.get(column, 0) for column in columns}
    return pd.DataFrame([row], columns=columns).replace([np.inf, -np.inf], np.nan).fillna(0)


def analyze_with_models(data: bytes) -> dict[str, Any]:
    """Return advisory model predictions for a single uploaded file."""
    features = _context_features(data)
    result: dict[str, Any] = {"available": False, "models": {}}

    classifier = _load("file_classification")
    corruption = _load("corruption_detection")
    recovery = _load("recovery_confidence")

    if classifier:
        columns = list(classifier.get("features", []))
        try:
            frame = _frame(features, columns)
            model = classifier["model"]
            encoded = int(model.predict(frame)[0])
            encoder = classifier.get("label_encoder")
            label = str(encoder.inverse_transform([encoded])[0]) if encoder is not None else str(encoded)
            confidence = None
            if hasattr(model, "predict_proba"):
                confidence = float(np.max(model.predict_proba(frame)[0]) * 100.0)
            result["models"]["fileClassification"] = {
                "label": label,
                "confidencePercent": round(confidence, 1) if confidence is not None else None,
            }
        except Exception as exc:
            result["models"]["fileClassification"] = {"error": str(exc)}

    if corruption:
        columns = list(corruption.get("features", []))
        try:
            frame = _frame(features, columns)
            model = corruption["model"]
            probability = None
            if hasattr(model, "predict_proba"):
                classes = list(getattr(model, "classes_", []))
                probabilities = model.predict_proba(frame)[0]
                probability = float(probabilities[classes.index(1)] * 100.0) if 1 in classes else float(np.max(probabilities) * 100.0)
            prediction = int(model.predict(frame)[0])
            result["models"]["corruptionDetection"] = {
                "corrupted": bool(prediction),
                "probabilityPercent": round(probability, 1) if probability is not None else None,
            }
        except Exception as exc:
            result["models"]["corruptionDetection"] = {"error": str(exc)}

    if recovery:
        columns = list(recovery.get("features", []))
        try:
            frame = _frame(features, columns)
            prediction = float(np.clip(recovery["model"].predict(frame)[0], 0.0, 1.0) * 100.0)
            result["models"]["recoveryConfidence"] = {"percent": round(prediction, 1)}
        except Exception as exc:
            result["models"]["recoveryConfidence"] = {"error": str(exc)}

    result["available"] = any("error" not in value for value in result["models"].values())
    result["note"] = (
        "Model outputs are advisory fragment-trained signals. Format-aware structural validation remains the primary evidence source."
    )
    return result


def fragment_features(data: bytes, *, position: int = 0, total: int = 1, offset: int = 0, source_size: int | None = None) -> dict[str, Any]:
    features = extract_features(data)
    size = len(data)
    features.update(
        {
            "source_file_size": source_size if source_size is not None else size,
            "total_fragments": total,
            "fragment_position": position,
            "offset": offset,
            "original_size": size,
        }
    )
    return features


def score_fragment_pair(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Score the probability that b follows a using the trained pair model."""
    model_data = _load("fragment_matching")
    if not model_data:
        return 0.0
    columns = list(model_data.get("features", []))
    pair: dict[str, Any] = {}
    base_columns = [column[2:] for column in columns if column.startswith("a_")]
    for column in base_columns:
        av = float(a.get(column, 0) or 0)
        bv = float(b.get(column, 0) or 0)
        pair[f"a_{column}"] = av
        pair[f"b_{column}"] = bv
        pair[f"diff_{column}"] = abs(av - bv)
    pair["position_gap"] = abs(float(b.get("fragment_position", 0)) - float(a.get("fragment_position", 0)))
    pair["offset_gap"] = abs(float(b.get("offset", 0)) - float(a.get("offset", 0)))
    try:
        frame = pd.DataFrame([{column: pair.get(column, 0) for column in columns}], columns=columns)
        frame = frame.replace([np.inf, -np.inf], np.nan).fillna(0)
        model = model_data["model"]
        if hasattr(model, "predict_proba"):
            classes = list(getattr(model, "classes_", []))
            probs = model.predict_proba(frame)[0]
            if 1 in classes:
                return float(probs[classes.index(1)])
            return float(np.max(probs))
        return float(model.predict(frame)[0])
    except Exception:
        return 0.0



def purify_image_array(image_array: np.ndarray, mask: np.ndarray, passes: int = 2) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply the trained masked-pixel restoration model to a decoded image.

    The model predicts the RGB value of a damaged center pixel from its learned local neighborhood (11x11 in the bundled model). It is deliberately applied only to pixels supplied by
    the deterministic forensic damage map; untouched pixels are never sent
    through the model. This keeps purification conservative and auditable.
    """
    model_data = _load("image_purification")
    if not model_data:
        raise RuntimeError("The trained image purification model is not available.")

    if image_array.ndim != 3 or image_array.shape[2] != 3:
        raise ValueError("Purification expects an RGB image array.")
    if mask.shape[:2] != image_array.shape[:2]:
        raise ValueError("Purification mask dimensions do not match the image.")

    model = model_data["model"]
    patch_size = int(model_data.get("patch_size", 11) or 11)
    if patch_size < 3 or patch_size % 2 == 0:
        patch_size = 11
    radius = patch_size // 2
    work = np.asarray(image_array, dtype=np.uint8).copy()
    target = np.asarray(mask > 0, dtype=bool)
    ys, xs = np.where(target)
    if len(ys) == 0:
        return work, {"pixelsPurified": 0, "passes": 0, "model": "image_purifier"}

    # Avoid an accidental CPU explosion on enormous masks. Format-aware
    # inpainting remains available as a fallback for very large regions.
    max_pixels = 350_000
    if len(ys) > max_pixels:
        raise ValueError(f"Damage region contains {len(ys):,} pixels; model purification is limited to {max_pixels:,} pixels per request.")

    padded = np.pad(work.astype(np.float32) / 255.0, ((radius, radius), (radius, radius), (0, 0)), mode="reflect")
    coordinates = list(zip(ys.tolist(), xs.tolist()))
    total = 0

    effective_passes = max(1, min(int(passes), 3))
    batch_size = 2048
    for _ in range(effective_passes):
        # Predict in bounded batches. The previous implementation built one
        # enormous feature matrix for the entire mask, which could consume
        # hundreds of MB for large images and made the recovery page appear
        # hung.
        for start in range(0, len(coordinates), batch_size):
            batch_coords = coordinates[start:start + batch_size]
            features = np.empty((len(batch_coords), patch_size * patch_size * 3), dtype=np.float32)
            for i, (y, x) in enumerate(batch_coords):
                features[i] = padded[y:y + patch_size, x:x + patch_size].reshape(-1)

            predictions = np.clip(model.predict(features), 0.0, 1.0).reshape(-1, 3)
            alpha = 0.92 if len(coordinates) < 100_000 else 0.80
            for (y, x), prediction in zip(batch_coords, predictions):
                work[y, x] = np.clip(
                    (1.0 - alpha) * work[y, x].astype(np.float32) + alpha * prediction * 255.0,
                    0,
                    255,
                ).astype(np.uint8)

        padded = np.pad(work.astype(np.float32) / 255.0, ((radius, radius), (radius, radius), (0, 0)), mode="reflect")
        total += len(coordinates)

    return work, {
        "pixelsPurified": len(coordinates),
        "passes": effective_passes,
        "model": "image_purifier",
        "trainingSamples": model_data.get("training_samples"),
        "patchSize": patch_size,
        "note": "Predictions were applied only inside the forensic damage mask; untouched pixels were preserved byte-for-byte at the decoded pixel level.",
    }
