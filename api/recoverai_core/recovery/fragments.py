"""Fragment matching and reconstruction orchestration.

This module keeps fragment handling separate from single-file repair. It never
changes an uploaded fragment and returns the proposed ordering plus an evidence
report so an investigator can review the decision before export.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
import hashlib
import re

from ..analyzer import analyze_file
from ml.inference.service import fragment_features, score_fragment_pair


@dataclass
class Fragment:
    name: str
    data: bytes
    features: dict[str, Any]


def _prefix_suffix_overlap(a: bytes, b: bytes, maximum: int = 512) -> float:
    """Return a normalized suffix/prefix overlap signal."""
    limit = min(maximum, len(a), len(b))
    if limit < 8:
        return 0.0
    best = 0
    for size in range(8, limit + 1, 8):
        if a[-size:] == b[:size]:
            best = size
    return best / maximum


def _signature_bonus(data: bytes) -> float:
    signatures = (
        b"%PDF-",
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
        b"GIF87a",
        b"GIF89a",
        b"PK\x03\x04",
        b"PK\x05\x06",
        b"BM",
        b"RIFF",
    )
    return 1.0 if data.startswith(signatures) else 0.0


def _pair_score(a: Fragment, b: Fragment) -> tuple[float, dict[str, float]]:
    ml_score = score_fragment_pair(a.features, b.features)
    overlap = _prefix_suffix_overlap(a.data, b.data)
    # ML is advisory. A byte-continuity signal is deterministic and receives
    # equal weight so the system does not blindly trust a small synthetic model.
    combined = 0.55 * ml_score + 0.35 * overlap + 0.10 * _signature_bonus(a.data)
    return combined, {"ml": ml_score, "overlap": overlap}


def _filename_position_hint(name: str) -> int | None:
    """Extract a conservative fragment-position hint from common filenames.

    This is only used when every uploaded fragment exposes a consistent
    zero-based sequence in its filename (for example fragment_0007.bin). It
    is treated as evidence, not as proof, and never rewrites the source.
    """
    stem = Path(name).stem.lower()
    matches = re.findall(r"(?:fragment|part|chunk)[_-]?(\d+)", stem)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def _filename_order(fragments: list[Fragment]) -> list[int] | None:
    hints = [_filename_position_hint(fragment.name) for fragment in fragments]
    if any(value is None for value in hints):
        return None
    numeric = [int(value) for value in hints if value is not None]
    if len(set(numeric)) != len(numeric):
        return None
    expected = list(range(min(numeric), min(numeric) + len(numeric)))
    if sorted(numeric) != expected:
        return None
    return sorted(range(len(fragments)), key=lambda index: numeric[index])


def _order_fragments(fragments: list[Fragment]) -> tuple[list[int], list[dict[str, Any]]]:
    if len(fragments) <= 1:
        return list(range(len(fragments))), []

    hinted_order = _filename_order(fragments)
    if hinted_order is not None:
        edge_report = []
        for pos in range(len(hinted_order) - 1):
            i, j = hinted_order[pos], hinted_order[pos + 1]
            # Still calculate the trained model's score so the report exposes
            # both the explicit filename evidence and the ML compatibility.
            score, signals = _pair_score(fragments[i], fragments[j])
            edge_report.append({
                "from": fragments[i].name,
                "to": fragments[j].name,
                "score": round(score * 100.0, 1),
                "signals": {**{key: round(value * 100.0, 1) for key, value in signals.items()}, "filenameOrder": 100.0},
            })
        return hinted_order, edge_report

    scores: dict[tuple[int, int], tuple[float, dict[str, float]]] = {}
    for i, left in enumerate(fragments):
        for j, right in enumerate(fragments):
            if i != j:
                scores[(i, j)] = _pair_score(left, right)

    # Use a bounded beam search rather than a purely greedy matching. Greedy
    # edge selection can consume a strong edge too early and strand the rest
    # of a file. The beam keeps several globally plausible paths while staying
    # cheap for the 32-fragment API limit.
    signature_starts = [i for i, f in enumerate(fragments) if _signature_bonus(f.data) > 0]
    candidate_starts = signature_starts or list(range(len(fragments)))
    beam: list[tuple[float, tuple[int, ...]]] = [(0.0, (start,)) for start in candidate_starts]
    beam_width = 96

    for _ in range(len(fragments) - 1):
        expanded: list[tuple[float, tuple[int, ...]]] = []
        for total, path in beam:
            used = set(path)
            last = path[-1]
            choices = sorted(
                ((scores[(last, nxt)][0], nxt) for nxt in range(len(fragments)) if nxt not in used),
                reverse=True,
            )[: min(12, len(fragments))]
            for edge_score, nxt in choices:
                expanded.append((total + edge_score, path + (nxt,)))
        if not expanded:
            break
        expanded.sort(key=lambda item: item[0], reverse=True)
        # Deduplicate by the set of used fragments and current endpoint; this
        # keeps the beam diverse instead of filling it with near-identical paths.
        seen_states: set[tuple[frozenset[int], int]] = set()
        next_beam: list[tuple[float, tuple[int, ...]]] = []
        for item in expanded:
            state = (frozenset(item[1]), item[1][-1])
            if state in seen_states:
                continue
            seen_states.add(state)
            next_beam.append(item)
            if len(next_beam) >= beam_width:
                break
        beam = next_beam

    complete = [item for item in beam if len(item[1]) == len(fragments)]
    if complete:
        order = list(max(complete, key=lambda item: item[0])[1])
    else:
        order = list(max(beam, key=lambda item: item[0])[1]) if beam else list(range(len(fragments)))
        for idx in range(len(fragments)):
            if idx not in order:
                anchor = order[-1] if order else idx
                remaining = [j for j in range(len(fragments)) if j not in order]
                if remaining:
                    nxt = max(remaining, key=lambda j: scores.get((anchor, j), (0.0, {}))[0])
                    order.append(nxt)

    edge_report = []
    for pos in range(len(order) - 1):
        i, j = order[pos], order[pos + 1]
        score, signals = scores[(i, j)]
        edge_report.append({
            "from": fragments[i].name,
            "to": fragments[j].name,
            "score": round(score * 100.0, 1),
            "signals": {key: round(value * 100.0, 1) for key, value in signals.items()},
        })
    return order, edge_report


def reconstruct_fragments(items: list[tuple[str, bytes]], output_name: str = "reconstructed.bin") -> dict[str, Any]:
    if not items:
        raise ValueError("At least one fragment is required.")
    if len(items) > 32:
        raise ValueError("A maximum of 32 fragments can be reconstructed in one request.")

    # Runtime uploads normally arrive without ground-truth offsets or source
    # positions. Do not leak the upload order into the ML features because the
    # trained matcher learned position/offset relationships from labeled
    # training fragments. Unknown runtime position/offset is represented by 0;
    # the deterministic byte-continuity and signature signals remain available.
    source_size = sum(len(data) for _, data in items)
    fragments = [
        Fragment(
            name,
            data,
            fragment_features(data, position=0, total=len(items), offset=0, source_size=source_size),
        )
        for name, data in items
    ]
    order, edges = _order_fragments(fragments)
    reconstructed = b"".join(fragments[index].data for index in order)
    extension = Path(output_name).suffix.lower()
    if extension not in {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".docx", ".zip"}:
        output_name = f"{output_name}.bin" if not output_name.endswith(".bin") else output_name

    validation = analyze_file(output_name, reconstructed, "application/octet-stream")
    average_edge = sum(edge["score"] for edge in edges) / len(edges) if edges else 100.0
    report = {
        "status": "completed",
        "message": "Fragments were ordered and concatenated. Validation is reported separately and does not imply byte-exact recovery.",
        "fragmentCount": len(fragments),
        "orderedFragments": [fragments[index].name for index in order],
        "orderingMethod": "filename-sequence-hint" if _filename_order(fragments) is not None else "beam-search-ml-and-byte-signals",
        "matchConfidencePercent": round(average_edge, 1),
        "edges": edges,
        "outputSha256": hashlib.sha256(reconstructed).hexdigest(),
        "outputSize": len(reconstructed),
        "validation": validation,
    }
    return {"data": reconstructed, "report": report}
