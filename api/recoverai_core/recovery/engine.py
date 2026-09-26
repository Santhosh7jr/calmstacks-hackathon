"""Safe, format-aware recovery engine for RecoverAI.

Recovery is deliberately non-destructive: the input bytes are never modified.
Each strategy validates its output with the same analyzer used for detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import html
import re
import zipfile
import shutil
import subprocess
import tempfile
from typing import Any

import numpy as np
from PIL import Image, ImageFile

from ..analyzer import analyze_file

try:
    import cv2  # type: ignore
except Exception:  # optional acceleration
    cv2 = None


@dataclass
class RecoveryOutput:
    file_name: str
    data: bytes
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.report


def _extension(name: str) -> str:
    return Path(name).suffix.lower()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate(name: str, data: bytes, mime: str) -> dict[str, Any]:
    return analyze_file(name, data, mime)


def _repair_image(name: str, data: bytes, mime: str, analysis: dict[str, Any]) -> tuple[bytes, list[str], list[str], dict[str, Any] | None]:
    """Repair decoded visual regions or salvage a truncated decodable image."""
    extension = _extension(name)
    if extension not in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
        raise ValueError("This image format does not currently have a safe automatic repair strategy.")

    warnings: list[str] = []
    with Image.open(BytesIO(data)) as source:
        width, height = source.size
        original_mode = source.mode
        alpha_channel = source.convert("RGBA").getchannel("A").copy() if "A" in source.mode or "transparency" in source.info else None
        frame_images: list[Image.Image] = []
        frame_durations: list[int] = []
        loop = int(source.info.get("loop", 0) or 0)
        animated = getattr(source, "n_frames", 1) > 1
        metadata = {
            key: source.info[key]
            for key in ("exif", "icc_profile", "dpi")
            if key in source.info
        }
        try:
            source.load()
            frame = source.convert("RGB")
            strict_decoded = True
            if animated:
                for frame_number in range(source.n_frames):
                    source.seek(frame_number)
                    frame_images.append(source.convert("RGBA" if alpha_channel is not None else "RGB").copy())
                    frame_durations.append(int(source.info.get("duration", 0) or 0))
                source.seek(0)
        except Exception:
            # Local, opt-in salvage pass. This is never enabled globally.
            old = ImageFile.LOAD_TRUNCATED_IMAGES
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            try:
                source.seek(0)
                source.load()
                frame = source.convert("RGB")
                strict_decoded = False
            finally:
                ImageFile.LOAD_TRUNCATED_IMAGES = old
            warnings.append("The source image was only partially decodable; Pillow truncated-image salvage was used.")

        arr = np.asarray(frame, dtype=np.uint8).copy()

    if animated and (not strict_decoded or analysis.get("analysis", {}).get("assessment", {}).get("regions")):
        raise ValueError("Localized repair of animated images is not attempted without a frame-specific damage map.")

    regions = analysis.get("analysis", {}).get("assessment", {}).get("regions", [])
    mask = np.zeros((height, width), dtype=np.uint8)
    applied = []
    for region in regions:
        if "startRow" in region:
            y0 = max(0, min(height, int(region["startRow"])))
            y1 = max(y0, min(height, int(region.get("endRow", height))))
            if y1 > y0:
                mask[y0:y1, :] = 255
                applied.append(f"rows {y0}:{y1}")
        elif "startColumn" in region:
            x0 = max(0, min(width, int(region["startColumn"])))
            x1 = max(x0, min(width, int(region.get("endColumn", width))))
            if x1 > x0:
                mask[:, x0:x1] = 255
                applied.append(f"columns {x0}:{x1}")

    # A truncated image with no localized pixel map can still be salvaged by
    # re-encoding the pixels that the decoder successfully produced.
    purification_report = None
    if not np.any(mask):
        if not strict_decoded:
            repaired = arr
            method = "Truncated-image pixel salvage and lossless-format re-encode"
        else:
            # Structural damage can be independent of the decoded pixels. If
            # Pillow can read the pixels strictly, rebuilding the container
            # is a safe repair when no visual damage was localized.
            repaired = arr
            method = "Validated pixel decode and format container re-encode"
    else:
        ys, xs = np.where(mask > 0)
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        damaged_fraction = float(np.count_nonzero(mask)) / float(mask.size)

        # The trained purifier is the first repair strategy for localized visual
        # damage. It predicts damaged RGB pixels from its learned local neighborhood.
        # If the model cannot safely handle the region, the deterministic
        # boundary/inpainting strategies below remain available.
        # First choice for localized image damage: an open-source deep-learning
        # inpainting model. It is optional and downloaded separately so GitHub
        # repositories do not contain an ~88 MB binary.
        try:
            from ml.inference.lama_inpainting import available as lama_available, inpaint as lama_inpaint
            if lama_available():
                repaired, purification_report = lama_inpaint(arr, mask)
                method = "LaMa deep-learning image inpainting (ONNX)"
            else:
                raise RuntimeError("LaMa weights are not installed")
        except Exception as lama_error:
            warnings.append(f"LaMa deep-learning inpainting unavailable: {lama_error}")
            try:
                from ml.inference.service import purify_image_array
                repaired, purification_report = purify_image_array(arr, mask, passes=2)
                method = "Trained ML image purification model (masked-pixel RGB restoration)"
            except Exception as purifier_error:
                warnings.append(f"Trained ML image purification was not applied: {purifier_error}")
                repaired = None

        # Very large masks are better served by a format-aware local inpainting
        # fallback than by the small-patch purifier. Never silently replace a
        # successful LaMa candidate with a weaker fallback.
        if repaired is not None and damaged_fraction > 0.35 and cv2 is not None and purification_report and purification_report.get("backend") != "LaMa ONNX":
            kernel = np.ones((3, 3), np.uint8)
            fallback_mask = cv2.dilate(mask, kernel, iterations=1)
            repaired = cv2.inpaint(arr, fallback_mask, 5.0, cv2.INPAINT_TELEA)
            method += " + OpenCV Telea fallback for very large damage region"
            purification_report["fallback"] = "OpenCV Telea edge-aware inpainting"

        if repaired is None and y1 >= height - 8 and y0 > 0 and (height - y0) / height >= 0.12:
            band_h = max(12, min(48, y0 // 2))
            band = arr[max(0, y0 - band_h):y0].astype(np.float32)
            repaired = arr.astype(np.float32).copy()
            target_h = height - y0
            seq = np.concatenate([band, band[::-1]], axis=0)
            reps = int(np.ceil(target_h / max(1, len(seq))))
            texture = np.tile(seq, (reps, 1, 1))[:target_h]
            seam = min(12, target_h)
            for i in range(seam):
                alpha = (i + 1) / (seam + 1)
                texture[i] = (1 - alpha) * band[-1] + alpha * texture[i]
            repaired[y0:] = texture
            repaired = np.clip(repaired, 0, 255).astype(np.uint8)
            method = "Boundary texture continuation with mirrored intact-strip synthesis"
        elif repaired is None and x1 >= width - 8 and x0 > 0 and (width - x0) / width >= 0.12:
            band_w = max(12, min(48, x0 // 2))
            band = arr[:, max(0, x0 - band_w):x0].astype(np.float32)
            target_w = width - x0
            seq = np.concatenate([band, band[:, ::-1]], axis=1)
            reps = int(np.ceil(target_w / max(1, seq.shape[1])))
            texture = np.tile(seq, (1, reps, 1))[:, :target_w]
            seam = min(12, target_w)
            for i in range(seam):
                alpha = (i + 1) / (seam + 1)
                texture[:, i] = (1 - alpha) * band[:, -1] + alpha * texture[:, i]
            repaired = arr.astype(np.float32).copy()
            repaired[:, x0:] = texture
            repaired = np.clip(repaired, 0, 255).astype(np.uint8)
            method = "Boundary texture continuation with mirrored intact-strip synthesis"
        elif repaired is None and cv2 is not None:
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
            repaired = cv2.inpaint(arr, mask, 5.0, cv2.INPAINT_TELEA)
            method = "OpenCV Telea edge-aware inpainting"
        elif repaired is None:
            repaired = _numpy_boundary_fill(arr, mask)
            method = "NumPy boundary interpolation fallback"

        # A generative candidate is not automatically a good candidate.
        # Compare it with an independent, deterministic OpenCV Telea candidate
        # and keep the candidate that actually reduces the forensic corruption
        # score. This is especially important for interior blocks where a small
        # local ML purifier can leave the same anomaly behind.
        if np.any(mask) and cv2 is not None:
            try:
                candidate_mask = mask.copy()
                telea = cv2.inpaint(arr, candidate_mask, 9.0, cv2.INPAINT_TELEA)

                def _encode_rgb_candidate(candidate: np.ndarray) -> bytes:
                    candidate_image = Image.fromarray(np.clip(candidate, 0, 255).astype(np.uint8), "RGB")
                    if alpha_channel is not None:
                        candidate_image.putalpha(alpha_channel)
                    candidate_buffer = BytesIO()
                    if extension in {".jpg", ".jpeg"}:
                        candidate_image.convert("RGB").save(candidate_buffer, format="JPEG", quality=95, subsampling=0, optimize=True)
                    elif extension == ".png":
                        candidate_image.save(candidate_buffer, format="PNG", optimize=True)
                    elif extension == ".webp":
                        candidate_image.save(candidate_buffer, format="WEBP", quality=95, method=6)
                    elif extension == ".bmp":
                        candidate_image.save(candidate_buffer, format="BMP")
                    else:
                        candidate_image.save(candidate_buffer, format="TIFF", compression="tiff_deflate")
                    return candidate_buffer.getvalue()

                current_bytes = _encode_rgb_candidate(repaired)
                telea_bytes = _encode_rgb_candidate(telea)
                current_check = _validate(name, current_bytes, mime)
                telea_check = _validate(name, telea_bytes, mime)
                current_score = float(current_check.get("analysis", {}).get("assessment", {}).get("corruptionPercent", 100.0))
                telea_score = float(telea_check.get("analysis", {}).get("assessment", {}).get("corruptionPercent", 100.0))
                if telea_score + 0.05 < current_score:
                    repaired = telea
                    method += " + OpenCV Telea candidate selected by post-repair forensic score"
                    if purification_report is None:
                        purification_report = {}
                    purification_report["candidateSelection"] = {
                        "selected": "OpenCV Telea",
                        "mlCorruptionPercent": round(current_score, 2),
                        "teleaCorruptionPercent": round(telea_score, 2),
                    }
                else:
                    if purification_report is None:
                        purification_report = {}
                    purification_report["candidateSelection"] = {
                        "selected": "primary-model-candidate",
                        "mlCorruptionPercent": round(current_score, 2),
                        "teleaCorruptionPercent": round(telea_score, 2),
                    }
            except Exception as candidate_error:
                warnings.append(f"Alternative image candidate comparison was unavailable: {candidate_error}")

    output = Image.fromarray(np.clip(repaired, 0, 255).astype(np.uint8), "RGB")
    if alpha_channel is not None:
        output.putalpha(alpha_channel)
    out = BytesIO()
    save_kwargs = {key: value for key, value in metadata.items() if value is not None}
    if animated:
        save_kwargs.update({"save_all": True, "append_images": frame_images[1:], "duration": frame_durations, "loop": loop})
    if extension in {".jpg", ".jpeg"}:
        output = output.convert("RGB")
        output.save(out, format="JPEG", quality=95, subsampling=0, optimize=True, **save_kwargs)
    elif extension == ".png":
        output.save(out, format="PNG", optimize=True, **save_kwargs)
    elif extension == ".webp":
        output.save(out, format="WEBP", quality=95, method=6, **save_kwargs)
    elif extension == ".bmp":
        output.save(out, format="BMP")
    else:
        output.save(out, format="TIFF", compression="tiff_deflate", **save_kwargs)
    return out.getvalue(), [method], warnings + ([f"Localized repair region: {', '.join(applied)}"] if applied else []), purification_report


def _numpy_boundary_fill(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fast fallback for large rectangular damage at an image boundary.

    It propagates the nearest intact scanline/column and blends the boundary
    gradually. This is intentionally conservative: it never claims to recover
    information that is absent from the input.
    """
    result = arr.astype(np.float32).copy()
    damaged = mask > 0
    ys, xs = np.where(damaged)
    if len(ys) == 0:
        return arr

    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    if y0 == 0 and y1 < arr.shape[0] - 1:
        boundary = result[y1 + 1].copy()
        depth = y1 - y0 + 1
        for i, y in enumerate(range(y0, y1 + 1)):
            alpha = (i + 1) / max(depth + 1, 2)
            result[y, x0:x1 + 1] = (1 - alpha) * boundary[x0:x1 + 1] + alpha * result[y1 + 1, x0:x1 + 1]
    elif y1 == arr.shape[0] - 1 and y0 > 0:
        boundary = result[y0 - 1].copy()
        depth = y1 - y0 + 1
        for i, y in enumerate(range(y0, y1 + 1)):
            alpha = (i + 1) / max(depth + 1, 2)
            result[y, x0:x1 + 1] = (1 - alpha) * boundary[x0:x1 + 1] + alpha * result[y0 - 1, x0:x1 + 1]
    elif x0 == 0 and x1 < arr.shape[1] - 1:
        boundary = result[:, x1 + 1].copy()
        depth = x1 - x0 + 1
        for i, x in enumerate(range(x0, x1 + 1)):
            alpha = (i + 1) / max(depth + 1, 2)
            result[y0:y1 + 1, x] = (1 - alpha) * boundary[y0:y1 + 1] + alpha * result[y0:y1 + 1, x1 + 1]
    elif x1 == arr.shape[1] - 1 and x0 > 0:
        boundary = result[:, x0 - 1].copy()
        depth = x1 - x0 + 1
        for i, x in enumerate(range(x0, x1 + 1)):
            alpha = (i + 1) / max(depth + 1, 2)
            result[y0:y1 + 1, x] = (1 - alpha) * boundary[y0:y1 + 1] + alpha * result[y0:y1 + 1, x0 - 1]
    else:
        # Interior rectangle: bilinear blend of its four borders.
        top = result[y0 - 1, x0:x1 + 1] if y0 > 0 else result[y1 + 1, x0:x1 + 1]
        bottom = result[y1 + 1, x0:x1 + 1] if y1 < arr.shape[0] - 1 else top
        for i, y in enumerate(range(y0, y1 + 1)):
            t = i / max(y1 - y0, 1)
            result[y, x0:x1 + 1] = (1 - t) * top + t * bottom
    return np.clip(result, 0, 255).astype(np.uint8)


_PDF_OBJECT_HEADER = re.compile(rb"(?m)^(\d+)\s+(\d+)\s+obj(?:[ \t]*)(?:\r?\n|$)")


def _scan_pdf_objects(data: bytes) -> dict[int, tuple[int, int]]:
    """Return surviving indirect-object offsets and generations.

    This intentionally scans only line-anchored object headers. It avoids
    treating strings such as ``\"12 0 obj\"`` inside streams as objects.
    The result is enough to rebuild a classic PDF xref table for files whose
    object bodies are still present but whose xref/trailer was damaged.
    """
    objects: dict[int, tuple[int, int]] = {}
    for match in _PDF_OBJECT_HEADER.finditer(data):
        number = int(match.group(1))
        generation = int(match.group(2))
        # Keep the first occurrence. Duplicate object numbers are ambiguous
        # and should not be silently overwritten during recovery.
        objects.setdefault(number, (match.start(), generation))
    return objects


def _find_pdf_root_and_pages(data: bytes, objects: dict[int, tuple[int, int]]) -> tuple[int | None, int | None]:
    """Infer Catalog and Pages object numbers from surviving object bodies."""
    root: int | None = None
    pages: int | None = None

    ordered = sorted(objects.items(), key=lambda item: item[1][0])
    for number, (offset, _generation) in ordered:
        end = data.find(b"endobj", offset)
        if end == -1:
            end = len(data)
        body = data[offset:end]
        if root is None and re.search(rb"/Type\s*/Catalog\b", body):
            root = number
        if pages is None and re.search(rb"/Type\s*/Pages\b", body):
            pages = number
    return root, pages


def _rebuild_pdf_xref(data: bytes) -> tuple[bytes, dict[str, Any]]:
    """Rebuild a classic xref/trailer from surviving indirect objects.

    This is a byte-preserving structural repair: object bodies and streams are
    not decoded or rewritten. Only the missing index/trailer/EOF structures
    are appended. It therefore works well when page/content objects survived
    but the original xref table was lost.
    """
    objects = _scan_pdf_objects(data)
    if not objects:
        raise ValueError("No surviving PDF indirect objects were found.")

    root, pages = _find_pdf_root_and_pages(data, objects)
    if root is None:
        raise ValueError("Surviving PDF objects were found, but no /Catalog object could be identified.")

    max_object = max(objects)
    size = max_object + 1
    prefix = data.rstrip(b"\x00\x09\x0a\x0c\x0d\x20")
    if not prefix.endswith(b"\n"):
        prefix += b"\n"

    xref_offset = len(prefix)
    lines = [f"xref\n0 {size}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for number in range(1, size):
        entry = objects.get(number)
        if entry is None:
            lines.append(b"0000000000 00000 f \n")
            continue
        offset, generation = entry
        lines.append(f"{offset:010d} {generation:05d} n \n".encode("ascii"))

    trailer = [f"trailer\n<<\n/Size {size}\n/Root {root} 0 R\n".encode("ascii")]
    if pages is not None:
        # /Pages is not a required trailer key; it is included as a recovery
        # hint for human inspection and is ignored by PDF readers.
        trailer.append(f"/RecoverAI-Pages {pages} 0 R\n".encode("ascii"))
    trailer.append(b">>\n")
    trailer.append(f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii"))

    repaired = prefix + b"".join(lines) + b"".join(trailer)
    return repaired, {
        "objectsFound": len(objects),
        "objectCount": size,
        "rootObject": root,
        "pagesObject": pages,
        "xrefOffset": xref_offset,
    }


def _qpdf_repair(data: bytes) -> tuple[bytes, str]:
    """Use qpdf when installed; qpdf performs robust cross-reference repair."""
    executable = shutil.which("qpdf")
    if not executable:
        raise RuntimeError("qpdf is not installed")
    with tempfile.TemporaryDirectory(prefix="recoverai_qpdf_") as tmp:
        source = Path(tmp) / "source.pdf"
        target = Path(tmp) / "repaired.pdf"
        source.write_bytes(data)
        completed = subprocess.run(
            [executable, str(source), str(target)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0 or not target.exists():
            detail = (completed.stderr or completed.stdout or "unknown qpdf error").strip()
            raise RuntimeError(detail[:500])
        repaired = target.read_bytes()
        if not repaired or repaired == data:
            raise RuntimeError("qpdf did not produce a changed output")
        return repaired, "qpdf structural repair (xref/object recovery)"


def _repair_pdf(name: str, data: bytes, mime: str) -> tuple[bytes, list[str], list[str]]:
    from pypdf import PdfReader, PdfWriter

    warnings: list[str] = []
    methods: list[str] = []

    def rebuild_with_reader(candidate: bytes, label: str) -> tuple[bytes, int]:
        reader = PdfReader(BytesIO(candidate), strict=False)
        if reader.is_encrypted:
            raise ValueError("The PDF is encrypted; automatic recovery without its password is not attempted.")
        writer = PdfWriter()
        copied = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                writer.add_page(page)
                copied += 1
            except Exception as exc:
                warnings.append(f"Skipped unreadable PDF page {page_number}: {exc}")
        if copied == 0:
            raise ValueError("No readable PDF pages were recovered.")
        output = BytesIO()
        writer.write(output)
        methods.append(f"Rebuilt PDF from {copied} readable page(s) after {label}")
        return output.getvalue(), copied

    # Prefer qpdf when the optional forensic utility is installed. It is a
    # mature structural PDF repairer and is much stronger than re-saving only
    # the pages that pypdf happens to parse. The output is still validated
    # below before being returned to the user.
    try:
        repaired, method = _qpdf_repair(data)
        check = rebuild_with_reader(repaired, "qpdf structural repair")
        methods.append(method)
        methods.append(f"Validated {check[1]} readable page(s) after qpdf repair")
        return repaired, methods, warnings
    except Exception as qpdf_error:
        warnings.append(f"Optional qpdf repair unavailable or unsuccessful: {qpdf_error}")

    # Next attempt the least invasive Python route. This preserves normal PDFs
    # and also handles files whose xref is usable despite minor parser warnings.
    try:
        repaired, _ = rebuild_with_reader(data, "lenient parsing")
        return repaired, methods, warnings
    except Exception as first_error:
        warnings.append(f"Lenient PDF reconstruction failed: {first_error}")

    # Final route: rebuild the missing/corrupt classic xref table directly
    # from the surviving indirect-object headers. This is the important path
    # for PDFs such as our damaged test file where page streams survive but
    # the xref/trailer was removed.
    rebuilt, evidence = _rebuild_pdf_xref(data)
    methods.append(
        "Reconstructed PDF xref/trailer from surviving indirect objects "
        f"({evidence['objectsFound']} objects; catalog {evidence['rootObject']})"
    )

    try:
        repaired, copied = rebuild_with_reader(rebuilt, "xref/trailer reconstruction")
        methods.append(f"Validated {copied} recovered page(s) after xref reconstruction")
        return repaired, methods, warnings
    except Exception as second_error:
        raise ValueError(
            "PDF object recovery reconstructed the index, but the surviving page streams "
            f"could not be rebuilt into a readable PDF: {second_error}"
        ) from second_error


def _seven_zip_repair(data: bytes, is_docx: bool) -> tuple[bytes, str, list[str]]:
    """Salvage readable archive members with 7-Zip when available."""
    executable = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")
    if not executable:
        raise RuntimeError("7-Zip is not installed")
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="recoverai_7z_") as tmp:
        source = Path(tmp) / ("source.docx" if is_docx else "source.zip")
        extracted = Path(tmp) / "extracted"
        extracted.mkdir()
        source.write_bytes(data)
        completed = subprocess.run(
            [executable, "x", "-y", str(source), f"-o{extracted}"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        files = [path for path in extracted.rglob("*") if path.is_file()]
        if not files:
            detail = (completed.stderr or completed.stdout or "7-Zip could not extract any archive members").strip()
            raise RuntimeError(detail[:500])
        output = BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
            for path in files:
                arcname = path.relative_to(extracted).as_posix()
                target.write(path, arcname)
        if completed.returncode != 0:
            warnings.append("7-Zip reported archive errors, but readable members were salvaged into a new container.")
        return output.getvalue(), "7-Zip archive salvage and container rebuild", warnings


def _repair_zip(name: str, data: bytes, is_docx: bool) -> tuple[bytes, list[str], list[str]]:
    methods: list[str] = []
    warnings: list[str] = []
    output = BytesIO()
    kept = 0
    dropped = []
    try:
        source = zipfile.ZipFile(BytesIO(data), "r")
        infos = source.infolist()
    except Exception as exc:
        # Python's zipfile is intentionally strict about a broken central
        # directory.  If it cannot even enumerate the archive, ask 7-Zip to
        # salvage whatever members remain physically readable.
        try:
            repaired, method, salvage_warnings = _seven_zip_repair(data, is_docx)
            methods.append(method)
            warnings.extend(salvage_warnings)
            return repaired, methods, warnings
        except Exception as seven_zip_error:
            raise ValueError(
                f"The ZIP directory could not be opened ({exc}); optional 7-Zip salvage also failed: {seven_zip_error}"
            ) from exc

    with source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for info in infos:
            try:
                content = source.read(info.filename)
                if is_docx and info.filename == "word/document.xml":
                    try:
                        import xml.etree.ElementTree as ET
                        ET.fromstring(content)
                    except Exception:
                        # The package is still readable, but the main Word XML
                        # is malformed. Extract surviving text tokens and build
                        # a minimal valid document.xml rather than dropping the
                        # entire document. Formatting that depended on the
                        # damaged XML cannot be reconstructed exactly.
                        raw = content.decode("utf-8", errors="ignore")
                        texts = [html.unescape(re.sub(r"<[^>]+>", "", value)) for value in re.findall(r"<w:t\b[^>]*>(.*?)</w:t>", raw, flags=re.DOTALL)]
                        safe_parts = []
                        for value in texts:
                            value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            if value.strip():
                                safe_parts.append(f"<w:p><w:r><w:t xml:space=\"preserve\">{value}</w:t></w:r></w:p>")
                        body = "".join(safe_parts) or "<w:p><w:r><w:t>Recovered document text was unavailable.</w:t></w:r></w:p>"
                        content = (
                            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
                            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                            f"<w:body>{body}<w:sectPr/></w:body></w:document>"
                        ).encode("utf-8")
                        methods.append("Rebuilt malformed word/document.xml from surviving text nodes")
                target.writestr(info, content)
                kept += 1
            except Exception as exc:
                dropped.append(info.filename)
                warnings.append(f"Skipped corrupt archive member {info.filename}: {exc}")

        if is_docx:
            names = {item.filename for item in target.infolist()}
            required = {"[Content_Types].xml", "word/document.xml"}
            missing = required - names
            if missing:
                warnings.append("DOCX repair is incomplete because required package parts are missing: " + ", ".join(sorted(missing)))

    methods.append(f"Rebuilt ZIP container from {kept} readable member(s)")
    if dropped:
        methods.append(f"Excluded {len(dropped)} unreadable member(s) to keep the remaining archive usable")
    return output.getvalue(), methods, warnings


def recover_file(filename: str, data: bytes, mime_type: str = "application/octet-stream") -> RecoveryOutput:
    before = _validate(filename, data, mime_type)
    ext = _extension(filename)
    analysis = before.get("analysis", {})
    if not analysis.get("corrupted"):
        report = {
            "status": "not_needed",
            "fileName": filename,
            "message": "The analysis engine found no confirmed damage, so the original file was left unchanged.",
            "before": before,
            "after": before,
            "changed": False,
            "recoveryPercent": 0.0,
            "methods": [],
            "warnings": [],
        }
        return RecoveryOutput(filename, data, report)

    methods: list[str] = []
    warnings: list[str] = []
    purification_report: dict[str, Any] | None = None
    try:
        if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
            repaired, methods, warnings, purification_report = _repair_image(filename, data, mime_type, before)
        elif ext == ".pdf":
            repaired, methods, warnings = _repair_pdf(filename, data, mime_type)
        elif ext == ".docx":
            repaired, methods, warnings = _repair_zip(filename, data, True)
        elif ext == ".zip":
            repaired, methods, warnings = _repair_zip(filename, data, False)
        else:
            raise ValueError(f"No automatic recovery strategy exists for {ext}.")
    except Exception as exc:
        report = {
            "status": "failed",
            "fileName": filename,
            "message": str(exc),
            "before": before,
            "after": before,
            "changed": False,
            "recoveryPercent": 0.0,
            "methods": methods,
            "warnings": warnings + ["The original file was preserved because no validated repair was produced."],
        }
        raise RecoveryFailure(report) from exc

    after = _validate(filename, repaired, mime_type)
    after_analysis = after.get("analysis", {})
    before_corruption = float(analysis.get("assessment", {}).get("corruptionPercent", 100.0))
    after_corruption = float(after_analysis.get("assessment", {}).get("corruptionPercent", 100.0))
    improvement = max(0.0, min(100.0, before_corruption - after_corruption))
    changed = repaired != data

    # Preserve an explicit record of content that the format-specific repair
    # strategy could not carry forward. A candidate can be structurally valid
    # while still being incomplete (for example, a PDF with one unreadable
    # page or a ZIP with one bad member).
    partial_recovery = bool(warnings) and (
        any("Skipped unreadable PDF page" in warning for warning in warnings)
        or any("Excluded " in warning and "unreadable member" in warning for warning in warnings)
    )
    quality_status = "completed_partial" if partial_recovery else "completed"

    ai_before = analysis.get("ai")
    ai_after = after_analysis.get("ai")

    before_pages = analysis.get("details", {}).get("lenientPages") or analysis.get("details", {}).get("pages")
    after_pages = after_analysis.get("details", {}).get("pages")
    page_retention = None
    if isinstance(before_pages, int) and before_pages > 0 and isinstance(after_pages, int):
        page_retention = round(max(0.0, min(100.0, after_pages / before_pages * 100.0)), 1)

    if not changed or not repaired:
        raise RecoveryFailure({
            "status": "failed",
            "fileName": filename,
            "message": "The recovery strategy produced identical bytes.",
            "before": before,
            "after": after,
            "changed": False,
            "recoveryPercent": 0.0,
            "methods": methods,
            "warnings": warnings,
        })

    if not after_analysis.get("signatureValid") or after_analysis.get("status") != "healthy":
        raise RecoveryFailure({
            "status": "failed",
            "fileName": filename,
            "message": "The repaired candidate did not pass post-recovery validation.",
            "before": before,
            "after": after,
            "changed": True,
            "recoveryPercent": round(improvement, 1),
            "methods": methods,
            "warnings": warnings + ["The candidate was discarded because structural corruption remains."],
        })

    report = {
        "status": quality_status,
        "fileName": filename,
        "message": "A repaired candidate was generated and re-analyzed for validation.",
        "before": before,
        "after": after,
        "changed": True,
        "recoveryPercent": round(improvement, 1),
        "methods": methods,
        "warnings": warnings,
        "originalSha256": _sha256(data),
        "repairedSha256": _sha256(repaired),
        "quality": {
            "partial": partial_recovery,
            "pageRetentionPercent": page_retention,
            "sourceReadablePages": before_pages,
            "recoveredPages": after_pages,
        },
        "ai": {
            "before": ai_before,
            "after": ai_after,
        },
        "purification": purification_report,
    }
    return RecoveryOutput(filename, repaired, report)


class RecoveryFailure(Exception):
    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__(str(report.get("message", "Recovery failed.")))
