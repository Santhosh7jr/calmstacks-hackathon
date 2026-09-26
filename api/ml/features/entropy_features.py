import math
from collections import Counter


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    length = len(data)

    entropy = 0.0

    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def extract_entropy_features(data: bytes) -> dict:
    entropy = calculate_entropy(data)

    return {
        "entropy": round(entropy, 6),
        "entropy_normalized": round(entropy / 8.0, 6),
    }