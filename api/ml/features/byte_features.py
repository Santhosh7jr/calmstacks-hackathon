from collections import Counter


def extract_byte_features(data: bytes) -> dict:
    if not data:
        return {
            "byte_mean": 0.0,
            "byte_std": 0.0,
            "zero_ratio": 0.0,
            "printable_ratio": 0.0,
            "unique_byte_ratio": 0.0,
            "high_byte_ratio": 0.0,
        }

    values = list(data)

    mean = sum(values) / len(values)

    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = variance ** 0.5

    zero_count = sum(1 for x in values if x == 0)

    printable_count = sum(
        1 for x in values
        if 32 <= x <= 126 or x in (9, 10, 13)
    )

    high_byte_count = sum(1 for x in values if x >= 128)

    unique_count = len(set(values))

    return {
        "byte_mean": round(mean, 6),
        "byte_std": round(std, 6),
        "zero_ratio": round(zero_count / len(values), 6),
        "printable_ratio": round(printable_count / len(values), 6),
        "unique_byte_ratio": round(unique_count / 256, 6),
        "high_byte_ratio": round(high_byte_count / len(values), 6),
    }