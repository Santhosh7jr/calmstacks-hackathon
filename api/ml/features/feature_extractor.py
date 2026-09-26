from pathlib import Path

from .byte_features import extract_byte_features
from .entropy_features import extract_entropy_features
from .header_features import extract_header_features
from .structure_features import extract_structure_features


def extract_features(data: bytes) -> dict:
    """
    Extract all numerical and descriptive features from a byte fragment.
    """

    features = {}

    features.update(
        extract_byte_features(data)
    )

    features.update(
        extract_entropy_features(data)
    )

    features.update(
        extract_header_features(data)
    )

    features.update(
        extract_structure_features(data)
    )

    return features


def extract_features_from_file(file_path: str | Path) -> dict:
    path = Path(file_path)

    with open(path, "rb") as file:
        data = file.read()

    features = extract_features(data)

    features["file_name"] = path.name
    features["file_size"] = len(data)

    return features


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage:")
        print("python feature_extractor.py <file>")
        sys.exit(1)

    file_path = sys.argv[1]

    features = extract_features_from_file(file_path)

    print("\n" + "=" * 60)
    print("RECOVERAI - FEATURE EXTRACTION")
    print("=" * 60)

    for key, value in features.items():
        print(f"{key:25}: {value}")

    print("=" * 60)