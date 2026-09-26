from flask import Blueprint, jsonify, request
from app.services.integrity import analyze_file, SUPPORTED_EXTENSIONS

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.post("")
@analyze_bp.post("/analyze")
def analyze():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"message": "No file was uploaded."}), 400

    name = uploaded.filename
    extension = "." + name.rsplit(".", 1)[1].lower() if "." in name else ""
    if extension not in SUPPORTED_EXTENSIONS:
        return jsonify({
            "message": "Unsupported file type. Supported files: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP, ICO, PPM, PGM, PBM, PNM, JP2, PDF, DOCX, and ZIP."
        }), 400

    data = uploaded.read()
    if not data:
        return jsonify({"message": "The uploaded file is empty."}), 400

    return jsonify(analyze_file(name, data, uploaded.mimetype or "application/octet-stream"))
