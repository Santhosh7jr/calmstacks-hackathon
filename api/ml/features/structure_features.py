import re


def extract_structure_features(data: bytes) -> dict:
    if not data:
        return {
            "size": 0,
            "ascii_word_count": 0,
            "null_byte_count": 0,
            "newline_count": 0,
            "pdf_marker_count": 0,
            "zip_marker_count": 0,
            "jpeg_marker_count": 0,
            "structure_density": 0.0,
        }

    size = len(data)

    null_byte_count = data.count(b"\x00")
    newline_count = data.count(b"\n")

    pdf_marker_count = (
        data.count(b"%PDF")
        + data.count(b"%%EOF")
        + data.count(b"obj")
        + data.count(b"stream")
    )

    zip_marker_count = (
        data.count(b"PK\x03\x04")
        + data.count(b"PK\x01\x02")
        + data.count(b"PK\x05\x06")
    )

    jpeg_marker_count = (
        data.count(b"\xFF\xD8")
        + data.count(b"\xFF\xD9")
    )

    # Count reasonably long ASCII words/strings.
    ascii_text = data.decode("latin-1", errors="ignore")

    ascii_words = re.findall(
        r"[A-Za-z]{3,}",
        ascii_text
    )

    ascii_word_count = len(ascii_words)

    marker_count = (
        pdf_marker_count
        + zip_marker_count
        + jpeg_marker_count
    )

    structure_density = marker_count / max(size, 1)

    return {
        "size": size,
        "ascii_word_count": ascii_word_count,
        "null_byte_count": null_byte_count,
        "newline_count": newline_count,
        "pdf_marker_count": pdf_marker_count,
        "zip_marker_count": zip_marker_count,
        "jpeg_marker_count": jpeg_marker_count,
        "structure_density": round(structure_density, 8),
    }