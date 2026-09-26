"""Optional OpenCV/LaMa deep-learning image inpainting backend.

The ONNX weights are intentionally not committed to the repository. Run
`python ml/download_models.py` to download the pinned OpenCV LaMa artifact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from functools import lru_cache

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "lama" / "inpainting_lama_2025jan.onnx"


def available() -> bool:
    return cv2 is not None and MODEL_PATH.exists()


@lru_cache(maxsize=1)
def _load_net():
    if cv2 is None:
        raise RuntimeError("OpenCV is not installed; LaMa backend is unavailable.")
    if not MODEL_PATH.exists():
        raise RuntimeError("LaMa model weights are not installed. Run: python ml/download_models.py")
    return cv2.dnn.readNetFromONNX(str(MODEL_PATH))

def inpaint(image_rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    if cv2 is None:
        raise RuntimeError("OpenCV is not installed; LaMa backend is unavailable.")
    if not MODEL_PATH.exists():
        raise RuntimeError("LaMa model weights are not installed. Run: python ml/download_models.py")
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("LaMa expects an RGB image.")

    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    mask_u8 = np.asarray(mask, dtype=np.uint8)
    if mask_u8.ndim != 2:
        raise ValueError("LaMa expects a single-channel mask.")

    # OpenCV's published LaMa wrapper uses a 512x512 network input and two
    # named inputs: image and mask. Keep the exact preprocessing contract.
    net = _load_net()
    image_blob = cv2.dnn.blobFromImage(
        image_bgr, 1.0 / 255.0, (512, 512), (0, 0, 0), False, False
    )
    mask_blob = cv2.dnn.blobFromImage(
        mask_u8, 1.0, (512, 512), (0,), False, False
    )
    mask_blob = (mask_blob > 0).astype(np.float32)
    net.setInput(image_blob, "image")
    net.setInput(mask_blob, "mask")
    output = net.forward()
    result_bgr = np.transpose(output[0], (1, 2, 0))
    result_bgr = np.clip(result_bgr, 0, 255).astype(np.uint8)
    result_bgr = cv2.resize(result_bgr, (image_rgb.shape[1], image_rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)

    # Preserve all unmasked pixels from the source. LaMa only supplies pixels
    # inside the forensic mask, which prevents generative drift elsewhere.
    repaired = image_rgb.copy()
    damaged = mask_u8 > 0
    repaired[damaged] = result_rgb[damaged]

    return repaired, {
        "backend": "LaMa ONNX",
        "model": MODEL_PATH.name,
        "pixelsInpainted": int(np.count_nonzero(damaged)),
        "networkSize": "512x512",
        "note": "Deep-learning inpainting was constrained to the forensic damage mask; untouched pixels were preserved from the source image.",
    }
