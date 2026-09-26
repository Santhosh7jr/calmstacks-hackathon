MAGIC_SIGNATURES = {
    "pdf": [
        b"%PDF"
    ],
    "jpg": [
        b"\xFF\xD8\xFF"
    ],
    "png": [
        b"\x89PNG\r\n\x1a\n"
    ],
    "gif": [
        b"GIF87a",
        b"GIF89a"
    ],
    "zip": [
        b"PK\x03\x04",
        b"PK\x05\x06",
        b"PK\x07\x08"
    ],
    "doc": [
        b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    ],
    "docx": [
        b"PK\x03\x04"
    ],
    "exe": [
        b"MZ"
    ],
    "sqlite": [
        b"SQLite format 3\x00"
    ],
}


def detect_file_type(data: bytes) -> str:
    for file_type, signatures in MAGIC_SIGNATURES.items():
        for signature in signatures:
            if data.startswith(signature):
                return file_type

    return "unknown"


def extract_header_features(data: bytes) -> dict:
    first_bytes = data[:16]

    features = {
        "has_pdf_header": int(data.startswith(b"%PDF")),
        "has_jpeg_header": int(data.startswith(b"\xFF\xD8\xFF")),
        "has_png_header": int(data.startswith(b"\x89PNG\r\n\x1a\n")),
        "has_gif_header": int(
            data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
        ),
        "has_zip_header": int(
            data.startswith(b"PK\x03\x04")
            or data.startswith(b"PK\x05\x06")
            or data.startswith(b"PK\x07\x08")
        ),
        "has_doc_header": int(
            data.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
        ),
        "has_exe_header": int(data.startswith(b"MZ")),
        "has_sqlite_header": int(
            data.startswith(b"SQLite format 3\x00")
        ),
    }

    features["detected_file_type"] = detect_file_type(data)

    # Useful for ML models that need numerical input.
    features["header_byte_0"] = first_bytes[0] if len(first_bytes) > 0 else 0
    features["header_byte_1"] = first_bytes[1] if len(first_bytes) > 1 else 0
    features["header_byte_2"] = first_bytes[2] if len(first_bytes) > 2 else 0
    features["header_byte_3"] = first_bytes[3] if len(first_bytes) > 3 else 0

    return features