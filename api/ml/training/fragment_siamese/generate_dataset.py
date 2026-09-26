from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Iterable

DEFAULT_SEED = 42
DEFAULT_FRAGMENT_SIZE = 8192
DEFAULT_MIN_FRAGMENT_SIZE = 4096
DEFAULT_MAX_FRAGMENT_SIZE = 16384
DEFAULT_BOUNDARY_BYTES = 512


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".pdf": "pdf", ".jpg": "image", ".jpeg": "image", ".png": "image",
        ".gif": "image", ".bmp": "image", ".webp": "image",
        ".doc": "document", ".docx": "document", ".txt": "text",
        ".csv": "text", ".json": "text", ".xml": "text",
        ".zip": "archive", ".sqlite": "database", ".db": "database",
        ".log": "text", ".bin": "binary",
    }.get(ext, "binary")


EXCLUDED_NAME_MARKERS = (
    "corrupted", "corrupt", "shuffled", "missing_fragment",
    "unrelated", "recovered", "recovery_test",
)


def is_training_source(path: Path) -> tuple[bool, str]:
    name = path.name.lower()
    stem = path.stem.lower()
    if path.name.startswith("."):
        return False, "hidden file"
    if any(marker in name or marker in stem for marker in EXCLUDED_NAME_MARKERS):
        return False, "test/corrupted fixture name"
    if stem.startswith("fragment_") or "_fragment_" in stem:
        return False, "fragment fixture"
    return True, "accepted"


def source_files(raw_dir: Path, min_size: int) -> tuple[list[Path], list[dict]]:
    accepted: list[Path] = []
    report: list[dict] = []
    for p in sorted(raw_dir.rglob("*")):
        if not p.is_file():
            continue
        size = p.stat().st_size
        ok, reason = is_training_source(p)
        if ok and size < min_size:
            ok, reason = False, f"too small ({size} bytes < {min_size})"
        if ok:
            accepted.append(p)
        report.append({"filename": p.name, "size": size, "status": "accepted" if ok else "excluded", "reason": reason})
    return accepted, report


def split_bytes(data: bytes, rng: random.Random, min_size: int,
                max_size: int) -> list[bytes]:
    parts = []
    offset = 0
    while offset < len(data):
        remaining = len(data) - offset
        if remaining <= max_size:
            size = remaining
        else:
            size = rng.randint(min_size, max_size)
        parts.append(data[offset:offset + size])
        offset += size
    return parts


def save_fragments(path: Path, data: bytes, out_dir: Path, rng: random.Random,
                   min_size: int, max_size: int) -> list[dict]:
    file_id = sha256(data)[:16]
    file_dir = out_dir / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_bytes(data, rng, min_size, max_size)
    records = []

    offset = 0
    for pos, chunk in enumerate(chunks):
        fid = f"{file_id}_fragment_{pos:04d}"
        fp = file_dir / f"{fid}.bin"
        fp.write_bytes(chunk)
        records.append({
            "fragment_id": fid,
            "path": str(fp),
            "position": pos,
            "size": len(chunk),
            "offset": offset,
            "source_file_id": file_id,
            "source_filename": path.name,
            "file_type": detect_type(path),
        })
        offset += len(chunk)

    return records


def pair_record(a: dict, b: dict, label: int, kind: str,
                boundary_bytes: int) -> dict:
    return {
        "fragment_a": a["path"],
        "fragment_b": b["path"],
        "label": int(label),
        "negative_type": None if label else kind,
        "source_file_a": a["source_file_id"],
        "source_file_b": b["source_file_id"],
        "position_a": a["position"],
        "position_b": b["position"],
        "file_type_a": a["file_type"],
        "file_type_b": b["file_type"],
        "a_tail_bytes": boundary_bytes,
        "b_head_bytes": boundary_bytes,
    }


def make_pairs(groups: list[list[dict]], rng: random.Random,
               boundary_bytes: int, negatives_per_positive: int) -> list[dict]:
    pairs = []
    all_frags = [f for g in groups for f in g]

    for group in groups:
        # Positive: exact adjacent ground-truth relationships.
        for a, b in zip(group, group[1:]):
            pairs.append(pair_record(a, b, 1, "positive", boundary_bytes))

            candidates: list[tuple[dict, dict, str]] = []

            # Same file, non-adjacent.
            for other in group:
                if other["position"] in {a["position"], b["position"]}:
                    continue
                if abs(other["position"] - a["position"]) > 1:
                    candidates.append((a, other, "same_file_non_adjacent"))

            # Reverse direction of a true adjacent pair.
            candidates.append((b, a, "reversed_adjacent"))

            # Cross-file candidates.
            cross = [f for f in all_frags if f["source_file_id"] != a["source_file_id"]]
            same_type = [f for f in cross if f["file_type"] == a["file_type"]]
            if same_type:
                candidates.append((a, rng.choice(same_type), "same_type_cross_file"))
            elif cross:
                candidates.append((a, rng.choice(cross), "cross_file"))

            rng.shuffle(candidates)
            seen = set()
            selected = 0
            for na, nb, kind in candidates:
                key = (na["fragment_id"], nb["fragment_id"])
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(pair_record(na, nb, 0, kind, boundary_bytes))
                selected += 1
                if selected >= negatives_per_positive:
                    break

    return pairs


def split_by_source(pairs: list[dict], source_ids: list[str], rng: random.Random,
                    train_ratio: float, val_ratio: float) -> dict[str, list[dict]]:
    ids = source_ids[:]
    rng.shuffle(ids)

    n = len(ids)
    if n < 3:
        # Pipeline can still be tested, but training quality cannot be validated
        # with fewer than three independent source files.
        train_ids = set(ids[:-2] if n > 2 else ids[:1])
        val_ids = set(ids[-2:-1]) if n >= 2 else set()
        test_ids = set(ids[-1:]) if n >= 2 else set()
    else:
        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1, int(round(n * val_ratio)))
        if n_train + n_val >= n:
            n_train = max(1, n - 2)
            n_val = 1
        train_ids = set(ids[:n_train])
        val_ids = set(ids[n_train:n_train + n_val])
        test_ids = set(ids[n_train + n_val:])

    result = {"train": [], "validation": [], "test": []}
    for p in pairs:
        if p["source_file_a"] in train_ids and p["source_file_b"] in train_ids:
            result["train"].append(p)
        elif p["source_file_a"] in val_ids and p["source_file_b"] in val_ids:
            result["validation"].append(p)
        elif p["source_file_a"] in test_ids and p["source_file_b"] in test_ids:
            result["test"].append(p)

    return result


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Siamese fragment adjacency dataset.")
    parser.add_argument("--raw-dir", type=Path, default=Path(__file__).resolve().parents[2] / "data" / "fragment_siamese" / "raw")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "data" / "fragment_siamese")
    parser.add_argument("--fragment-size", type=int, default=DEFAULT_FRAGMENT_SIZE)
    parser.add_argument("--min-fragment-size", type=int, default=DEFAULT_MIN_FRAGMENT_SIZE)
    parser.add_argument("--max-fragment-size", type=int, default=DEFAULT_MAX_FRAGMENT_SIZE)
    parser.add_argument("--boundary-bytes", type=int, default=DEFAULT_BOUNDARY_BYTES)
    parser.add_argument("--negatives-per-positive", type=int, default=3)
    parser.add_argument("--min-source-size", type=int, default=DEFAULT_MIN_FRAGMENT_SIZE * 2)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    files, source_report = source_files(args.raw_dir, args.min_source_size)
    if not files:
        print(json.dumps({"source_report": source_report}, indent=2))
        raise SystemExit(f"No usable source files >= {args.min_source_size} bytes found in {args.raw_dir}")

    fragment_root = args.output_dir / "fragments"
    fragment_root.mkdir(parents=True, exist_ok=True)

    groups = []
    source_meta = []
    for path in files:
        data = path.read_bytes()
        group = save_fragments(
            path, data, fragment_root, rng,
            args.min_fragment_size, args.max_fragment_size
        )
        if len(group) < 2:
            continue
        groups.append(group)
        source_meta.append({
            "source_file_id": group[0]["source_file_id"],
            "filename": path.name,
            "file_type": group[0]["file_type"],
            "size": len(data),
            "fragment_count": len(group),
        })

    if len(groups) < 3:
        print(
            f"WARNING: only {len(groups)} source files produced >=2 fragments. "
            "Use at least 3 independent files for a meaningful train/validation/test split."
        )

    pairs = make_pairs(groups, rng, args.boundary_bytes, args.negatives_per_positive)
    source_ids = [g[0]["source_file_id"] for g in groups]
    splits = split_by_source(pairs, source_ids, rng, 0.70, 0.15)

    out_pairs = args.output_dir / "pairs"
    counts = {}
    for name, rows in splits.items():
        counts[name] = write_jsonl(out_pairs / f"{name}.jsonl", rows)

    metadata = {
        "version": "1.0",
        "seed": args.seed,
        "boundary_bytes": args.boundary_bytes,
        "min_fragment_size": args.min_fragment_size,
        "max_fragment_size": args.max_fragment_size,
        "negatives_per_positive": args.negatives_per_positive,
        "source_report": source_report,
        "source_files": source_meta,
        "source_file_count": len(source_meta),
        "total_pairs": len(pairs),
        "split_counts": counts,
        "warning": (
            "Dataset is too small for meaningful ML evaluation."
            if len(source_meta) < 10 else None
        ),
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
