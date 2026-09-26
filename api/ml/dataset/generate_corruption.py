from __future__ import annotations

import json
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

FRAGMENTS_DIR = BASE_DIR / "data" / "generated" / "fragments"
OUTPUT_DIR = BASE_DIR / "data" / "generated" / "corrupted"
METADATA_DIR = BASE_DIR / "data" / "generated" / "metadata"

RANDOM_SEED = 42

CORRUPTION_LEVELS = {
    "low": 0.05,
    "medium": 0.15,
    "high": 0.30,
}


def corrupt_bytes(
    data: bytes,
    corruption_ratio: float,
    method: str,
) -> tuple[bytes, int]:

    if not data:
        return data, 0

    buffer = bytearray(data)

    corruption_count = max(
        1,
        int(len(buffer) * corruption_ratio),
    )

    if method == "byte_flip":

        positions = random.sample(
            range(len(buffer)),
            min(corruption_count, len(buffer)),
        )

        for position in positions:
            buffer[position] ^= random.randint(1, 255)

        return bytes(buffer), len(positions)

    if method == "zero_bytes":

        positions = random.sample(
            range(len(buffer)),
            min(corruption_count, len(buffer)),
        )

        for position in positions:
            buffer[position] = 0

        return bytes(buffer), len(positions)

    if method == "noise":

        positions = random.sample(
            range(len(buffer)),
            min(corruption_count, len(buffer)),
        )

        for position in positions:
            buffer[position] = random.randint(0, 255)

        return bytes(buffer), len(positions)

    if method == "truncate":

        remove_count = min(
            corruption_count,
            max(1, len(buffer) - 1),
        )

        return (
            bytes(buffer[:-remove_count]),
            remove_count,
        )

    if method == "delete_middle":

        delete_count = min(
            corruption_count,
            max(1, len(buffer) - 1),
        )

        start = random.randint(
            0,
            len(buffer) - delete_count,
        )

        corrupted = (
            bytes(buffer[:start])
            + bytes(buffer[start + delete_count:])
        )

        return corrupted, delete_count

    return data, 0


def main():

    random.seed(RANDOM_SEED)

    if not FRAGMENTS_DIR.exists():

        print()
        print("=" * 60)
        print("NO GENERATED FRAGMENTS FOUND")
        print("=" * 60)
        print()
        print("Run generate_fragments.py first.")
        print()

        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    methods = [
        "byte_flip",
        "zero_bytes",
        "noise",
        "truncate",
        "delete_middle",
    ]

    metadata = []

    fragment_files = list(
        FRAGMENTS_DIR.rglob("*.bin")
    )

    if not fragment_files:

        print()
        print("=" * 60)
        print("NO FRAGMENTS FOUND")
        print("=" * 60)
        print()

        return

    print()
    print("=" * 60)
    print("RECOVERAI - CORRUPTION GENERATOR")
    print("=" * 60)
    print()

    print(
        f"Fragments found : {len(fragment_files)}"
    )

    print()

    generated = 0

    for fragment_path in fragment_files:

        try:
            original_data = fragment_path.read_bytes()
        except Exception as exc:

            print(
                f"[ERROR] {fragment_path}: {exc}"
            )

            continue

        if not original_data:

            print(
                f"[SKIP] Empty fragment: "
                f"{fragment_path.name}"
            )

            continue

        relative_parent = (
            fragment_path.parent.relative_to(
                FRAGMENTS_DIR
            )
        )

        fragment_output_dir = (
            OUTPUT_DIR / relative_parent
        )

        fragment_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Create one corrupted version for every
        # corruption level and method.
        for level, ratio in CORRUPTION_LEVELS.items():

            for method in methods:

                corrupted_data, corrupted_bytes = (
                    corrupt_bytes(
                        original_data,
                        ratio,
                        method,
                    )
                )

                output_name = (
                    f"{fragment_path.stem}"
                    f"__{method}"
                    f"__{level}.bin"
                )

                output_path = (
                    fragment_output_dir
                    / output_name
                )

                output_path.write_bytes(
                    corrupted_data
                )

                metadata.append(
                    {
                        "fragment_id": fragment_path.stem,
                        "original_fragment_path": str(
                            fragment_path.relative_to(
                                BASE_DIR
                            )
                        ),
                        "corrupted_fragment_path": str(
                            output_path.relative_to(
                                BASE_DIR
                            )
                        ),
                        "corruption_method": method,
                        "corruption_level": level,
                        "target_corruption_ratio": ratio,
                        "original_size": len(
                            original_data
                        ),
                        "corrupted_size": len(
                            corrupted_data
                        ),
                        "corrupted_bytes": corrupted_bytes,
                        "is_corrupted": True,
                    }
                )

                generated += 1

    # Also create intact examples.
    for fragment_path in fragment_files:

        try:
            original_data = fragment_path.read_bytes()
        except Exception:
            continue

        if not original_data:
            continue

        relative_parent = (
            fragment_path.parent.relative_to(
                FRAGMENTS_DIR
            )
        )

        intact_dir = (
            OUTPUT_DIR
            / relative_parent
            / "intact"
        )

        intact_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            intact_dir
            / f"{fragment_path.stem}__intact.bin"
        )

        output_path.write_bytes(
            original_data
        )

        metadata.append(
            {
                "fragment_id": fragment_path.stem,
                "original_fragment_path": str(
                    fragment_path.relative_to(
                        BASE_DIR
                    )
                ),
                "corrupted_fragment_path": str(
                    output_path.relative_to(
                        BASE_DIR
                    )
                ),
                "corruption_method": "none",
                "corruption_level": "none",
                "target_corruption_ratio": 0.0,
                "original_size": len(original_data),
                "corrupted_size": len(original_data),
                "corrupted_bytes": 0,
                "is_corrupted": False,
            }
        )

    metadata_path = (
        METADATA_DIR
        / "corruption_ground_truth.json"
    )

    metadata_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "random_seed": RANDOM_SEED,
                "total_samples": len(metadata),
                "samples": metadata,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("CORRUPTION GENERATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Original fragments : {len(fragment_files)}")
    print(f"Generated samples  : {generated}")
    print(
        f"Total dataset rows : {len(metadata)}"
    )
    print()
    print("Corrupted data:")
    print(f"  {OUTPUT_DIR}")
    print()
    print("Ground truth:")
    print(f"  {metadata_path}")
    print()


if __name__ == "__main__":
    main()