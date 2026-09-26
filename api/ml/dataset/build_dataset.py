import json
from pathlib import Path

import pandas as pd

from features.feature_extractor import extract_features


BASE_DIR = Path(__file__).resolve().parents[1]

CORRUPTED_DIR = (
    BASE_DIR
    / "data"
    / "generated"
    / "corrupted"
)

METADATA_DIR = (
    BASE_DIR
    / "data"
    / "generated"
    / "metadata"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

OUTPUT_FILE = OUTPUT_DIR / "fragment_dataset.csv"

CORRUPTION_METADATA = (
    METADATA_DIR
    / "corruption_ground_truth.json"
)

FRAGMENT_METADATA = (
    METADATA_DIR
    / "fragment_ground_truth.json"
)


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required metadata file not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def build_fragment_lookup(fragment_data):
    """
    Build a lookup from fragment_id to its original
    file and fragment information.

    The actual ground-truth schema uses:
        original_filename
        original_file_id
        file_size
    """

    lookup = {}

    files = fragment_data.get("files", [])

    for source_entry in files:

        # IMPORTANT:
        # The JSON uses original_filename, NOT source_file.
        source_file = source_entry.get(
            "original_filename",
            ""
        )

        source_file_id = source_entry.get(
            "original_file_id",
            ""
        )

        source_file_size = source_entry.get(
            "file_size",
            0
        )

        file_type = source_entry.get(
            "file_type",
            "unknown"
        )

        fragments = source_entry.get(
            "fragments",
            []
        )

        for fragment in fragments:

            fragment_id = fragment.get(
                "fragment_id"
            )

            if not fragment_id:
                continue

            lookup[fragment_id] = {
                "source_file": source_file,

                "source_file_id": source_file_id,

                "source_file_size": source_file_size,

                "file_type": file_type,

                "fragment_position": fragment.get(
                    "fragment_position",
                    -1
                ),

                "total_fragments": fragment.get(
                    "total_fragments",
                    0
                ),

                "offset": fragment.get(
                    "offset",
                    -1
                ),

                "original_size": fragment.get(
                    "size",
                    0
                ),

                "original_sha256": fragment.get(
                    "sha256",
                    ""
                ),

                "previous_fragment": fragment.get(
                    "previous_fragment"
                ),

                "next_fragment": fragment.get(
                    "next_fragment"
                ),
            }

    return lookup

def resolve_sample_path(sample_path):
    """
    Resolve paths stored inside corruption metadata.

    Handles both absolute paths and paths that were
    generated relative to the project.
    """

    path = Path(sample_path)

    if path.exists():
        return path

    candidates = [
        BASE_DIR.parent.parent / path,
        BASE_DIR.parent / path,
        BASE_DIR / path,
        CORRUPTED_DIR / path.name,
    ]

    for candidate in candidates:

        if candidate.exists():
            return candidate

    return None


def build_dataset():

    print("\n" + "=" * 60)
    print("RECOVERAI - DATASET BUILDER")
    print("=" * 60)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    corruption_data = load_json(
        CORRUPTION_METADATA
    )

    fragment_data = load_json(
        FRAGMENT_METADATA
    )

    # ---------------------------------------------------------
    # BUILD FRAGMENT LOOKUP
    # ---------------------------------------------------------

    fragment_lookup = build_fragment_lookup(
        fragment_data
    )

    print(
        f"\nOriginal fragments indexed : "
        f"{len(fragment_lookup)}"
    )

    # ---------------------------------------------------------
    # PROCESS CORRUPTION SAMPLES
    # ---------------------------------------------------------

    samples = corruption_data.get(
        "samples",
        []
    )

    print(
        f"Corruption metadata : "
        f"{len(samples)} samples"
    )

    rows = []

    missing_metadata = 0
    missing_files = 0
    failed_features = 0

    for index, sample in enumerate(
        samples,
        start=1
    ):

        fragment_id = sample.get(
            "fragment_id"
        )

        if not fragment_id:
            missing_metadata += 1
            continue

        original_info = fragment_lookup.get(
            fragment_id
        )

        if original_info is None:

            missing_metadata += 1

            print(
                f"[WARNING] Fragment ID not found: "
                f"{fragment_id}"
            )

            continue

        sample_path = resolve_sample_path(
            sample.get(
                "corrupted_fragment_path",
                ""
            )
        )

        if sample_path is None:

            missing_files += 1

            continue

        try:

            with open(
                sample_path,
                "rb"
            ) as file:

                data = file.read()

            features = extract_features(
                data
            )

            row = {
                # ---------------------------------------------
                # Fragment identity
                # ---------------------------------------------

                "fragment_id": fragment_id,

                "source_file": original_info[
                    "source_file"
                ],

                "source_file_size": original_info[
    "source_file_size"
],

"source_file_id": original_info[
    "source_file_id"
],

"file_type": original_info[
    "file_type"
],

"total_fragments": original_info[
    "total_fragments"
],

                "fragment_position": original_info[
                    "fragment_position"
                ],

                "offset": original_info[
                    "offset"
                ],

                "original_size": original_info[
                    "original_size"
                ],

                # ---------------------------------------------
                # Fragment relationships
                # ---------------------------------------------

                "previous_fragment": (
                    original_info[
                        "previous_fragment"
                    ]
                    or ""
                ),

                "next_fragment": (
                    original_info[
                        "next_fragment"
                    ]
                    or ""
                ),

                # ---------------------------------------------
                # Corruption information
                # ---------------------------------------------

                "corruption_method": sample.get(
                    "corruption_method",
                    "none"
                ),

                "corruption_level": sample.get(
                    "corruption_level",
                    "intact"
                ),

                "target_corruption_ratio": float(
                    sample.get(
                        "target_corruption_ratio",
                        0.0
                    )
                ),

                "actual_corrupted_bytes": int(
                    sample.get(
                        "corrupted_bytes",
                        0
                    )
                ),

                "is_corrupted": int(
                    sample.get(
                        "is_corrupted",
                        False
                    )
                ),
            }

            # Add extracted byte/entropy/header/
            # structure features.
            row.update(features)

            rows.append(row)

        except Exception as error:

            failed_features += 1

            print(
                f"[WARNING] Failed sample "
                f"{index}: {error}"
            )

    if not rows:

        raise RuntimeError(
            "No dataset rows were created."
        )

    # ---------------------------------------------------------
    # DATAFRAME
    # ---------------------------------------------------------

    dataframe = pd.DataFrame(
        rows
    )

    dataframe = dataframe.sort_values(
        by=[
            "source_file",
            "fragment_position",
            "corruption_method",
            "corruption_level",
        ],
        na_position="last"
    )

    dataframe = dataframe.reset_index(
        drop=True
    )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    unique_sources = (
        dataframe["source_file"]
        .dropna()
        .astype(str)
        .unique()
    )

    unique_fragments = (
        dataframe["fragment_id"]
        .nunique()
    )

    corrupted_count = int(
        dataframe[
            "is_corrupted"
        ].sum()
    )

    intact_count = int(
        (
            dataframe[
                "is_corrupted"
            ] == 0
        ).sum()
    )

    print("\n" + "=" * 60)
    print("DATASET BUILD COMPLETE")
    print("=" * 60)

    print(
        f"Dataset rows       : "
        f"{len(dataframe)}"
    )

    print(
        f"Feature columns     : "
        f"{len(dataframe.columns)}"
    )

    print(
        f"Unique fragments    : "
        f"{unique_fragments}"
    )

    print(
        f"Unique source files : "
        f"{len(unique_sources)}"
    )

    print(
        f"Corrupted samples   : "
        f"{corrupted_count}"
    )

    print(
        f"Intact samples      : "
        f"{intact_count}"
    )

    print(
        f"Missing metadata    : "
        f"{missing_metadata}"
    )

    print(
        f"Missing files       : "
        f"{missing_files}"
    )

    print(
        f"Feature failures    : "
        f"{failed_features}"
    )

    print("\nSource files:")

    for source in sorted(
        unique_sources
    ):
        count = int(
            (
                dataframe[
                    "source_file"
                ].astype(str)
                == source
            ).sum()
        )

        print(
            f"  - {source}: "
            f"{count} samples"
        )

    print(
        f"\nOutput:\n{OUTPUT_FILE}"
    )

    return dataframe


if __name__ == "__main__":
    build_dataset()