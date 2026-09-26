"""Format-aware image integrity and damage estimation.

This module intentionally separates *provable structural errors* from
*suspected pixel damage*.  Pixel damage is estimated from decoded image
statistics; without a known-good reference image it cannot be measured
exactly.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any
import zlib

import numpy as np
from PIL import Image, ImageFile, UnidentifiedImageError

from ..models import Finding
from ..scoring import healthy_assessment, make_recovery

JPEG_EXTENSIONS = {".jpg", ".jpeg"}
PNG_EXTENSIONS = {".png"}

# Pillow normally rejects truncated images. We never enable truncated loading
# globally; a temporary salvage pass is used only after strict decoding fails.


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _jpeg_structure(data: bytes) -> dict[str, Any]:
    """Parse JPEG markers, including the entropy-coded scan safely."""
    result: dict[str, Any] = {
        "startOfImage": data.startswith(b"\xff\xd8"),
        "startOfScanSeen": False,
        "endOfImageSeen": False,
        "markerCount": 0,
        "scanCount": 0,
        "malformed": False,
        "entropyBytes": 0,
    }
    if not result["startOfImage"]:
        result["malformed"] = True
        return result

    i = 2
    n = len(data)
    while i < n:
        # Find marker prefix. Outside entropy this should be immediate.
        while i < n and data[i] != 0xFF:
            i += 1
        if i >= n:
            break
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            result["malformed"] = True
            break

        marker = data[i]
        i += 1
        if marker == 0x00:
            continue
        if marker == 0xD9:
            result["endOfImageSeen"] = True
            break
        if marker == 0xDA:
            result["startOfScanSeen"] = True
            result["scanCount"] += 1
            if i + 2 > n:
                result["malformed"] = True
                break
            length = int.from_bytes(data[i:i + 2], "big")
            if length < 2 or i + length > n:
                result["malformed"] = True
                break
            i += length
            scan_start = i
            # Entropy data ends at the next non-stuffed marker. Restart
            # markers are legal inside the scan and are skipped.
            while i < n - 1:
                if data[i] != 0xFF:
                    i += 1
                    continue
                nxt = data[i + 1]
                if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                    i += 2
                    continue
                if nxt == 0xD9:
                    result["entropyBytes"] += i - scan_start
                    i += 1
                    result["endOfImageSeen"] = True
                    break
                # Another marker starts here. Let outer loop process it.
                result["entropyBytes"] += i - scan_start
                break
            continue

        result["markerCount"] += 1
        # Standalone markers do not have a length.
        if marker in range(0xD0, 0xD8) or marker == 0x01:
            continue
        if i + 2 > n:
            result["malformed"] = True
            break
        length = int.from_bytes(data[i:i + 2], "big")
        if length < 2 or i + length > n:
            result["malformed"] = True
            break
        i += length

    return result


def _png_structure(data: bytes) -> dict[str, Any]:
    """Validate PNG chunk boundaries and CRCs without decoding pixels."""
    signature = b"\x89PNG\r\n\x1a\n"
    result: dict[str, Any] = {
        "signature": data.startswith(signature),
        "chunkCount": 0,
        "crcErrors": 0,
        "truncated": False,
        "endSeen": False,
        "idatBytes": 0,
        "idatChunks": 0,
    }
    if not result["signature"]:
        return result

    pos = 8
    n = len(data)
    while pos < n:
        if pos + 12 > n:
            result["truncated"] = True
            break
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > n:
            result["truncated"] = True
            break
        payload = data[pos + 8:pos + 8 + length]
        stored_crc = int.from_bytes(data[pos + 8 + length:end], "big")
        calculated_crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        result["chunkCount"] += 1
        if stored_crc != calculated_crc:
            result["crcErrors"] += 1
        if kind == b"IDAT":
            result["idatChunks"] += 1
            result["idatBytes"] += length
        if kind == b"IEND":
            result["endSeen"] = True
            break
        pos = end
    return result


def _decode_frames(data: bytes) -> tuple[list[np.ndarray], dict[str, Any]]:
    frames: list[np.ndarray] = []
    info: dict[str, Any] = {"strict": True, "strictError": None, "framesDecoded": 0}
    try:
        with Image.open(BytesIO(data)) as image:
            count = getattr(image, "n_frames", 1)
            for index in range(count):
                image.seek(index)
                frames.append(np.asarray(image.convert("RGB"), dtype=np.float32))
            info["framesDecoded"] = len(frames)
            return frames, info
    except Exception as exc:
        info["strict"] = False
        info["strictError"] = str(exc)

    # Salvage pass: only local to this call. This lets us measure a partially
    # decodable image without weakening normal integrity validation.
    try:
        old = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            with Image.open(BytesIO(data)) as image:
                count = getattr(image, "n_frames", 1)
                for index in range(count):
                    image.seek(index)
                    image.load()
                    frames.append(np.asarray(image.convert("RGB"), dtype=np.float32))
        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = old
        info["framesDecoded"] = len(frames)
    except Exception as exc:
        info["salvageError"] = str(exc)
    return frames, info


def _robust_z(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    scale = max(1.4826 * mad, 1e-6)
    return np.abs(values - median) / scale


def _pixel_damage_map(frame: np.ndarray) -> dict[str, Any]:
    """Find persistent local discontinuities while suppressing normal texture.

    The image is divided into blocks. Each block is compared with its
    immediate neighbors using mean color, luminance variance, edge strength,
    and color-channel balance. A block is suspicious only when multiple
    signals agree and the anomaly persists over neighboring blocks.
    """
    h, w = frame.shape[:2]
    if h < 32 or w < 32:
        return {"suspected": False, "reason": "image too small"}

    # Keep the workload bounded for very large photographs.
    scale = min(1.0, 1600.0 / max(h, w))
    if scale < 0.999:
        small = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).resize(
            (max(32, int(w * scale)), max(32, int(h * scale))), Image.Resampling.BILINEAR
        )
        frame = np.asarray(small, dtype=np.float32)
        h, w = frame.shape[:2]

    # 16-32 px cells give useful localization without exploding runtime.
    target_cells = 32
    bh = max(8, h // target_cells)
    bw = max(8, w // target_cells)
    rows = h // bh
    cols = w // bw
    if rows < 4 or cols < 4:
        return {"suspected": False, "reason": "insufficient analysis grid"}

    gray = frame.mean(axis=2)
    # Simple gradient magnitude. No OpenCV required.
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edge = np.sqrt(gx * gx + gy * gy)

    feats = np.zeros((rows, cols, 6), dtype=np.float64)
    for r in range(rows):
        y0, y1 = r * bh, min((r + 1) * bh, h)
        for c in range(cols):
            x0, x1 = c * bw, min((c + 1) * bw, w)
            patch = frame[y0:y1, x0:x1]
            feats[r, c, 0:3] = patch.mean(axis=(0, 1)) / 255.0
            feats[r, c, 3] = patch.std() / 128.0
            feats[r, c, 4] = edge[y0:y1, x0:x1].mean() / 128.0
            feats[r, c, 5] = (patch[:, :, 1].mean() - (patch[:, :, 0].mean() + patch[:, :, 2].mean()) / 2) / 255.0

    # Horizontal and vertical neighbor distances.
    hdiff = np.linalg.norm(feats[:, 1:, :] - feats[:, :-1, :], axis=2)
    vdiff = np.linalg.norm(feats[1:, :, :] - feats[:-1, :, :], axis=2)
    hscore = _robust_z(hdiff.ravel()).reshape(hdiff.shape)
    vscore = _robust_z(vdiff.ravel()).reshape(vdiff.shape)

    # Candidate boundary = unusually strong neighbor discontinuity.
    h_candidates = hscore > 6.0
    v_candidates = vscore > 6.0

    # Count support: a genuine broad corruption boundary tends to span many
    # adjacent blocks rather than being a single natural edge.
    horizontal_support = h_candidates.sum(axis=1)
    vertical_support = v_candidates.sum(axis=0)
    best_h = int(horizontal_support.argmax()) if horizontal_support.size else -1
    best_v = int(vertical_support.argmax()) if vertical_support.size else -1
    hs = int(horizontal_support[best_h]) if best_h >= 0 else 0
    vs = int(vertical_support[best_v]) if best_v >= 0 else 0

    # Detect a large region whose color/variance statistics are collectively
    # different from the rest of the image.
    row_features = feats.mean(axis=1)
    col_features = feats.mean(axis=0)
    # Standardize each feature across rows/columns independently. This avoids
    # declaring high-texture images corrupt simply because their natural
    # statistics differ from a global scalar distribution.
    row_z_matrix = np.column_stack([_robust_z(row_features[:, k]) for k in range(row_features.shape[1])])
    col_z_matrix = np.column_stack([_robust_z(col_features[:, k]) for k in range(col_features.shape[1])])
    row_z = np.linalg.norm(row_z_matrix, axis=1) / np.sqrt(row_features.shape[1])
    col_z = np.linalg.norm(col_z_matrix, axis=1) / np.sqrt(col_features.shape[1])
    row_suspicious = row_z > 5.0
    col_suspicious = col_z > 5.0

    # Strong color cast is particularly useful for green/blue/red corruption.
    color_shift_rows = np.abs(row_features[:, 5])
    color_threshold = max(float(np.median(color_shift_rows) * 3.0), 0.08)
    color_rows = color_shift_rows > color_threshold

    row_votes = row_suspicious.astype(int) + color_rows.astype(int)
    row_votes = np.convolve(row_votes, np.ones(3, dtype=int), mode="same")
    suspicious_rows = row_votes >= 2

    # Convert suspicious cells/rows to image coordinates.
    region = None
    confidence = "low"
    score = 0.0
    if hs >= max(4, int(cols * 0.55)) and ((rows - best_h - 1) / max(rows, 1) <= 0.45):
        boundary = (best_h + 1) * bh
        affected_cells = max(1, rows - best_h - 1) * cols
        affected_percent = affected_cells / (rows * cols) * 100.0
        score = min(1.0, hs / max(cols, 1))
        region = {
            "type": "horizontal_decoded_region",
            "startRow": int(boundary),
            "endRow": int(h),
            "affectedRowsPercent": round((h - boundary) / h * 100.0, 1),
            "gridCoveragePercent": round(affected_percent, 1),
        }
        confidence = "high" if hs >= int(cols * 0.75) else "medium"
    elif vs >= max(4, int(rows * 0.55)) and ((cols - best_v - 1) / max(cols, 1) <= 0.45):
        boundary = (best_v + 1) * bw
        affected_percent = max(1, cols - best_v - 1) * rows / (rows * cols) * 100.0
        score = min(1.0, vs / max(rows, 1))
        region = {
            "type": "vertical_decoded_region",
            "startColumn": int(boundary),
            "endColumn": int(w),
            "affectedColumnsPercent": round((w - boundary) / w * 100.0, 1),
            "gridCoveragePercent": round(affected_percent, 1),
        }
        confidence = "high" if vs >= int(rows * 0.75) else "medium"
    elif rows >= 6 and cols >= 6:
        # Strong uniform-block detector for zeroed/painted-over regions.
        # These regions can be internally consistent, so boundary-only
        # statistics may miss them. We only accept compact interior blocks
        # whose mean intensity is near an extreme and whose variance is far
        # below the image's normal block variance.
        intensity = feats[:, :, 0:3].mean(axis=2)
        variance = feats[:, :, 3]
        extreme = (intensity < 0.035) & (variance < 0.015)
        if int(extreme.sum()) >= 6:
            rr, cc = np.where(extreme)
            r0, r1 = int(rr.min()), int(rr.max()) + 1
            c0, c1 = int(cc.min()), int(cc.max()) + 1
            # Keep the mask away from image borders; border regions have their
            # own safe continuation strategy.
            density = extreme.sum() / max(1, (r1 - r0) * (c1 - c0))
            area_percent = ((r1 - r0) * (c1 - c0)) / float(rows * cols) * 100.0
            if r0 > 0 and c0 > 0 and r1 < rows and c1 < cols and area_percent >= 1.0 and density >= 0.55:
                region = {
                    "type": "interior_uniform_corruption",
                    "startRow": r0 * bh,
                    "endRow": min(h, r1 * bh),
                    "startColumn": c0 * bw,
                    "endColumn": min(w, c1 * bw),
                    "affectedAreaPercent": round(area_percent, 2),
                    "candidateDensity": round(float(density), 3),
                }
                score = min(1.0, float(density) * 0.9)
                confidence = "high"

    if region is None and rows >= 6 and cols >= 6:
        # Interior rectangular anomaly detection. This catches common
        # "painted-over", zeroed, or block-corrupted regions that do not touch
        # an image boundary and therefore have no long boundary support.
        local_scores = np.zeros((rows, cols), dtype=np.float64)
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                neighbors = feats[r - 1:r + 2, c - 1:c + 2].reshape(-1, feats.shape[-1])
                center = feats[r, c]
                neighbors = np.delete(neighbors, 4, axis=0)
                local_scores[r, c] = np.linalg.norm(center - np.median(neighbors, axis=0))
        z = _robust_z(local_scores[1:-1, 1:-1].ravel()).reshape(rows - 2, cols - 2)
        candidates = z > 7.0
        # Require at least a small compact cluster so ordinary texture does not
        # become a repair mask.
        if int(candidates.sum()) >= 4:
            rr, cc = np.where(candidates)
            r0, r1 = int(rr.min()) + 1, int(rr.max()) + 2
            c0, c1 = int(cc.min()) + 1, int(cc.max()) + 2
            area_percent = ((r1 - r0) * (c1 - c0)) / float(rows * cols) * 100.0
            density = candidates.sum() / max(1, (r1 - r0) * (c1 - c0))
            if 0.5 <= area_percent <= 25.0 and density >= 0.30:
                score = min(1.0, float(z[candidates].mean()) / 12.0)
                region = {
                    "type": "interior_decoded_anomaly",
                    "startRow": r0 * bh,
                    "endRow": min(h, r1 * bh),
                    "startColumn": c0 * bw,
                    "endColumn": min(w, c1 * bw),
                    "affectedAreaPercent": round(area_percent, 2),
                    "candidateDensity": round(float(density), 3),
                }
                confidence = "high" if density >= 0.65 else "medium"
    elif suspicious_rows.sum() >= max(3, int(rows * 0.25)) and suspicious_rows.sum() < int(rows * 0.80):
        ys = np.where(suspicious_rows)[0]
        y0, y1 = int(ys.min() * bh), int(min(h, (ys.max() + 1) * bh))
        affected_percent = (y1 - y0) / h * 100.0
        score = min(1.0, float(suspicious_rows.mean()) * 1.8)
        if affected_percent >= 5.0:
            region = {
                "type": "decoded_statistical_region",
                "startRow": y0,
                "endRow": y1,
                "affectedRowsPercent": round(affected_percent, 1),
            }
            confidence = "medium"

    return {
        "suspected": region is not None,
        "confidence": confidence,
        "score": round(float(score), 3),
        "region": region,
        "grid": {"rows": rows, "columns": cols, "blockHeight": bh, "blockWidth": bw},
        "horizontalBoundarySupport": hs,
        "verticalBoundarySupport": vs,
        "method": "multi-signal block discontinuity and persistent-region analysis",
    }


def _structure_findings(extension: str, data: bytes) -> tuple[dict[str, Any], list[Finding]]:
    details: dict[str, Any] = {}
    findings: list[Finding] = []

    if extension in JPEG_EXTENSIONS:
        info = _jpeg_structure(data)
        details["jpegStructure"] = info
        if not info["startOfImage"]:
            findings.append(Finding("JPEG_SOI_INVALID", "high", "JPEG start-of-image marker is invalid."))
        if not info["endOfImageSeen"]:
            findings.append(Finding(
                "JPEG_EOI_MISSING", "high",
                "JPEG end-of-image marker is missing; the encoded stream may be truncated.",
                info,
            ))
        if info["malformed"]:
            findings.append(Finding(
                "JPEG_MARKER_STRUCTURE_INVALID", "high",
                "JPEG marker structure contains a truncated or invalid segment.", info,
            ))

    elif extension in PNG_EXTENSIONS:
        info = _png_structure(data)
        details["pngStructure"] = info
        if info["truncated"] or not info["endSeen"]:
            findings.append(Finding(
                "PNG_STRUCTURE_TRUNCATED", "high",
                "PNG chunk structure is truncated or missing IEND.", info,
            ))
        if info["crcErrors"]:
            findings.append(Finding(
                "PNG_CRC_ERROR", "high",
                f"{info['crcErrors']} PNG chunk CRC error(s) were detected.", info,
            ))

    return details, findings


def analyze_image(data: bytes, extension: str) -> tuple[dict[str, Any], list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    details: dict[str, Any] = {}

    try:
        with Image.open(BytesIO(data)) as image:
            detected_format = image.format or "unknown"
            width, height = image.size
            mode = image.mode
            frames = getattr(image, "n_frames", 1)
            details.update({
                "format": detected_format,
                "width": width,
                "height": height,
                "colorMode": mode,
                "frames": frames,
                "animated": frames > 1,
                "hasTransparency": "transparency" in image.info or "A" in mode,
                "metadataKeys": sorted(str(k) for k in image.info.keys()),
            })

        structure, structural_findings = _structure_findings(extension, data)
        details.update(structure)
        findings.extend(structural_findings)

        frames, decode = _decode_frames(data)
        details["decode"] = decode

        strict_ok = bool(decode.get("strict")) and bool(frames)
        if not strict_ok and not frames:
            findings.append(Finding(
                "IMAGE_DECODE_FAILURE", "high",
                decode.get("strictError") or "The image could not be decoded or salvaged.", decode,
            ))

        visual = None
        if frames:
            # Analyze first frame. For animations, additional frames are checked
            # and the strongest anomaly is retained.
            analyses = [_pixel_damage_map(frame) for frame in frames[:8]]
            visual = max(analyses, key=lambda item: float(item.get("score", 0.0)))
            visual["framesAnalyzed"] = len(analyses)
            details["pixelAnalysis"] = visual
            if visual.get("suspected"):
                findings.append(Finding(
                    "VISUAL_REGION_ANOMALY",
                    "high" if visual.get("confidence") == "high" else "medium",
                    "Decoded pixels contain a persistent multi-signal anomaly consistent with a damaged region.",
                    visual,
                ))

        structural_confirmed = any(
            f.code in {"JPEG_EOI_MISSING", "JPEG_MARKER_STRUCTURE_INVALID", "PNG_STRUCTURE_TRUNCATED", "PNG_CRC_ERROR"}
            for f in findings
        )
        visual_suspected = bool(visual and visual.get("suspected"))

        if not findings:
            recovery = healthy_assessment()
            assessment = {
                "classification": "none",
                "corruptionPercent": 0.0,
                "recovery": {
                    "corruptionPercent": 0.0,
                    "recoverablePercent": 100.0,
                    "unrecoverablePercent": 0.0,
                    "confidence": recovery.confidence,
                    "basis": [
                        "Image decoded successfully.",
                        "Format-specific structural checks passed.",
                        "No statistically significant persistent pixel anomaly was detected.",
                    ],
                },
                "findings": [],
                "regions": [],
            }
            return {
                "status": "healthy", "corrupted": False, "signatureValid": True,
                "details": details, "assessment": assessment,
            }, findings, details

        # Estimate affected decoded area when available. Structural errors are
        # measured separately and never inflated by an arbitrary 100% default
        # merely because strict decoding failed.
        region_percent = 0.0
        if visual and visual.get("region"):
            region = visual["region"]
            region_percent = _safe_float(
                region.get("affectedRowsPercent", region.get("affectedColumnsPercent", region.get("affectedAreaPercent", region.get("gridCoveragePercent", 0.0))))
            )

        # For a missing JPEG EOI, the exact missing tail length is measurable
        # only at byte level. We expose a conservative byte-tail estimate in
        # the basis, while using decoded-region evidence if present.
        if extension in JPEG_EXTENSIONS and details.get("jpegStructure", {}).get("endOfImageSeen") is False:
            # The exact amount of missing JPEG tail data is unknowable without
            # the original file. Use a small structural-damage floor rather
            # than pretending that the missing marker represents a measured
            # percentage of the original image.
            region_percent = max(region_percent, 5.0)

        corruption = min(100.0, max(region_percent, 1.0 if structural_confirmed else 0.0))

        if structural_confirmed and not visual_suspected:
            # Structural damage without a localizable pixel map: don't pretend
            # the whole image is destroyed. Mark the estimate as low-confidence.
            recoverable = max(0.0, 100.0 - corruption * 0.65)
            confidence = "medium" if frames else "low"
        elif visual_suspected:
            # A localized decoded region can often remain partially useful.
            # Only the affected region is uncertain; intact pixels are retained.
            recoverable = max(0.0, 100.0 - corruption * 0.40)
            confidence = visual.get("confidence", "medium")
        else:
            recoverable = 0.0 if not frames else max(0.0, 100.0 - corruption * 0.50)
            confidence = "low"

        unrecoverable = max(0.0, 100.0 - recoverable)
        recovery = make_recovery(
            corruption_percent=corruption,
            recoverable_percent=recoverable,
            unrecoverable_percent=unrecoverable,
            confidence=confidence,
            basis=[
                "Strict decoder validation and a local salvage decode were attempted.",
                "Format-specific byte-structure checks were applied.",
                "Pixel damage is estimated from persistent block/row/column statistical anomalies when decoding succeeds.",
                "Without an original known-good image, pixel corruption percentages are estimates rather than exact byte-loss measurements.",
            ],
        )

        classification = "confirmed" if structural_confirmed else "suspected"
        regions = [visual["region"]] if visual and visual.get("region") else []
        assessment = {
            "classification": classification,
            "corruptionPercent": recovery.corruption_percent,
            "recovery": {
                "corruptionPercent": recovery.corruption_percent,
                "recoverablePercent": recovery.recoverable_percent,
                "unrecoverablePercent": recovery.unrecoverable_percent,
                "confidence": recovery.confidence,
                "basis": recovery.basis,
            },
            "findings": [f.__dict__ for f in findings],
            "regions": regions,
        }
        return {
            "status": "corrupted" if structural_confirmed else "suspected",
            "corrupted": True,
            "signatureValid": True,
            "details": details,
            "assessment": assessment,
        }, findings, details

    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        findings.append(Finding("IMAGE_ANALYSIS_FAILURE", "high", str(exc)))
        recovery = make_recovery(
            corruption_percent=100.0,
            recoverable_percent=0.0,
            unrecoverable_percent=100.0,
            confidence="low",
            basis=["The image could not be decoded sufficiently for regional measurement."],
        )
        return {
            "status": "corrupted", "corrupted": True, "signatureValid": True,
            "details": {"error": str(exc)},
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
        }, findings, details
