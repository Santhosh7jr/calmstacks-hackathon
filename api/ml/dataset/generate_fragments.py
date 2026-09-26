from __future__ import annotations

import json
import math
import random
import hashlib
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "generated"
FRAGMENTS_DIR = OUTPUT_DIR / "fragments"
METADATA_DIR = OUTPUT_DIR / "metadata"

MIN_FRAGMENT_SIZE = 4096
MAX_FRAGMENT_SIZE = 65536

RANDOM_SEED = 42

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".doc",
    ".docx",
    ".txt",
    ".csv",
    ".json",
    ".xml",
    ".zip",
    ".sqlite",
    ".db",
    ".log",
    ".bin",
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_file_type(path: Path) -> str:
    extension = path.suffix.lower()

    mapping = {
        ".pdf": "pdf",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".bmp": "bmp",
        ".webp": "webp",
        ".doc": "doc",
        ".docx": "docx",
        ".txt": "text",
        ".csv": "csv",
        ".json": "json",
        ".xml": "xml",
        ".zip": "zip",
        ".sqlite": "sqlite",
        ".db": "database",
        ".log": "log",
        ".bin": "binary",
    }

    return mapping.get(extension, "unknown")


def calculate_fragment_sizes(file_size: int) -> list[int]:
    """
    Create variable-sized fragments.

    Variable fragment sizes are intentional. Real fragmented data
    does not necessarily have identical chunk sizes.
    """

    if file_size <= 0:
        return []

    if file_size <= MIN_FRAGMENT_SIZE:
        return [file_size]

    sizes = []
    remaining = file_size

    while remaining > 0:
        if remaining <= MAX_FRAGMENT_SIZE:
            size = remaining
        else:
            size = random.randint(
                MIN_FRAGMENT_SIZE,
                min(MAX_FRAGMENT_SIZE, remaining),
            )

        sizes.append(size)
        remaining -= size

    return sizes


def split_file(file_path: Path) -> list[dict]:
    data = file_path.read_bytes()

    file_size = len(data)

    if file_size == 0:
        return []

    fragment_sizes = calculate_fragment_sizes(file_size)

    fragments = []

    offset = 0

    for position, size in enumerate(fragment_sizes):

        fragment_data = data[offset:offset + size]

        fragments.append(
            {
                "position": position,
                "offset": offset,
                "size": len(fragment_data),
                "data": fragment_data,
            }
        )

        offset += size

    return fragments


def save_fragment(
    fragment_data: bytes,
    output_path: Path,
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(fragment_data)


# ---------------------------------------------------------
# Main processing
# ---------------------------------------------------------

def process_file(file_path: Path) -> dict | None:

    try:
        original_data = file_path.read_bytes()
    except Exception as exc:
        print(f"[ERROR] Cannot read {file_path}: {exc}")
        return None

    if not original_data:
        print(f"[SKIP] Empty file: {file_path}")
        return None

    file_id = hashlib.sha256(original_data).hexdigest()[:16]

    file_type = detect_file_type(file_path)

    fragments = split_file(file_path)

    if not fragments:
        return None

    file_output_dir = FRAGMENTS_DIR / file_id

    file_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    fragment_metadata = []

    for fragment in fragments:

        position = fragment["position"]

        fragment_id = (
            f"{file_id}_fragment_{position:04d}"
        )

        fragment_filename = (
            f"{fragment_id}.bin"
        )

        fragment_path = (
            file_output_dir / fragment_filename
        )

        save_fragment(
            fragment["data"],
            fragment_path,
        )

        fragment_metadata.append(
            {
                "fragment_id": fragment_id,
                "filename": fragment_filename,
                "path": str(
                    fragment_path.relative_to(BASE_DIR)
                ),
                "original_file_id": file_id,
                "original_filename": file_path.name,
                "file_type": file_type,
                "fragment_position": position,
                "total_fragments": len(fragments),
                "offset": fragment["offset"],
                "size": fragment["size"],
                "sha256": sha256_bytes(fragment["data"]),
                "is_original": True,
            }
        )

    # Ground-truth relationships.
    for index, fragment in enumerate(fragment_metadata):

        fragment["previous_fragment"] = (
            fragment_metadata[index - 1]["fragment_id"]
            if index > 0
            else None
        )

        fragment["next_fragment"] = (
            fragment_metadata[index + 1]["fragment_id"]
            if index < len(fragment_metadata) - 1
            else None
        )

    return {
        "original_file_id": file_id,
        "original_filename": file_path.name,
        "original_path": str(file_path.relative_to(BASE_DIR)),
        "file_type": file_type,
        "file_size": len(original_data),
        "sha256": sha256_bytes(original_data),
        "fragment_count": len(fragment_metadata),
        "fragments": fragment_metadata,
    }


def find_raw_files() -> list[Path]:

    if not RAW_DIR.exists():
        return []

    files = []

    for path in RAW_DIR.rglob("*"):

        if not path.is_file():
            continue

        # Ignore hidden/system files.
        if path.name.startswith("."):
            continue

        # Only process supported file types.
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files.append(path)

    return sorted(files)


def main():

    random.seed(RANDOM_SEED)

    FRAGMENTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_files = find_raw_files()

    if not raw_files:
        print()
        print("=" * 60)
        print("NO RAW FILES FOUND")
        print("=" * 60)
        print()
        print(f"Put sample files inside:")
        print(f"  {RAW_DIR}")
        print()
        return

    print()
    print("=" * 60)
    print("RECOVERAI - FRAGMENT GENERATOR")
    print("=" * 60)
    print()

    print(f"Raw directory : {RAW_DIR}")
    print(f"Output        : {FRAGMENTS_DIR}")
    print(f"Files found   : {len(raw_files)}")
    print()

    all_metadata = []

    successful = 0
    failed = 0

    for index, file_path in enumerate(raw_files, start=1):

        print(
            f"[{index}/{len(raw_files)}] "
            f"Processing: {file_path.name}"
        )

        result = process_file(file_path)

        if result is None:
            failed += 1
            continue

        successful += 1

        all_metadata.append(result)

        print(
            f"    Type      : {result['file_type']}"
        )

        print(
            f"    Size      : {result['file_size']:,} bytes"
        )

        print(
            f"    Fragments : {result['fragment_count']}"
        )

        print()

    metadata_file = (
        METADATA_DIR / "fragment_ground_truth.json"
    )

    metadata_file.write_text(
        json.dumps(
            {
                "version": "1.0",
                "random_seed": RANDOM_SEED,
                "total_files": len(all_metadata),
                "successful_files": successful,
                "failed_files": failed,
                "files": all_metadata,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    total_fragments = sum(
        item["fragment_count"]
        for item in all_metadata
    )

    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Files processed     : {successful}")
    print(f"Files failed        : {failed}")
    print(f"Total fragments     : {total_fragments}")
    print()
    print(f"Fragments saved to:")
    print(f"  {FRAGMENTS_DIR}")
    print()
    print("Ground truth saved to:")
    print(f"  {metadata_file}")
    print()


if __name__ == "__main__":
    main()