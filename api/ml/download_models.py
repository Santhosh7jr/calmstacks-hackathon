"""Download optional open-source deep-learning weights used by RecoverAI.

The LaMa ONNX file is not committed because it is ~88 MB and would make a
normal GitHub repository unnecessarily large. The model is downloaded only
when the user explicitly runs this script.
"""
from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

MODEL_URL = "https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "lama"
MODEL_PATH = MODEL_DIR / "inpainting_lama_2025jan.onnx"


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 10_000_000:
        print(f"LaMa model already exists: {MODEL_PATH}")
        return
    print("Downloading OpenCV LaMa ONNX model (~88 MB)...")
    request = Request(MODEL_URL, headers={"User-Agent": "RecoverAI/1.0"})
    with urlopen(request, timeout=120) as response, MODEL_PATH.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r{downloaded / total * 100:5.1f}%", end="", flush=True)
    print(f"\nSaved: {MODEL_PATH}")


if __name__ == "__main__":
    main()
