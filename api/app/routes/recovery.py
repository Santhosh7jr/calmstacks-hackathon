import json
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from recoverai_core.recovery.engine import RecoveryFailure, recover_file
from recoverai_core.analyzer import SUPPORTED_EXTENSIONS

recovery_bp = Blueprint("recovery", __name__)


@recovery_bp.post("")
@recovery_bp.post("/recover")
def recover():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"message": "No file was uploaded."}), 400

    data = uploaded.read()
    if not data:
        return jsonify({"message": "The uploaded file is empty."}), 400

    name = uploaded.filename
    extension = "." + name.rsplit(".", 1)[1].lower() if "." in name else ""
    if extension not in SUPPORTED_EXTENSIONS:
        return jsonify({"message": "Unsupported file type."}), 400

    try:
        result = recover_file(name, data, uploaded.mimetype or "application/octet-stream")
    except RecoveryFailure as exc:
        return jsonify(exc.report), 422
    except Exception as exc:
        return jsonify({"message": f"Recovery failed: {exc}"}), 500

    response = send_file(
        BytesIO(result.data),
        mimetype=uploaded.mimetype or "application/octet-stream",
        as_attachment=True,
        download_name=f"recovered_{name}",
    )
    full = result.report
    purification = full.get("purification") or {}
    response_report = {
        "status": full.get("status"),
        "message": full.get("message"),
        "recoveryPercent": full.get("recoveryPercent", 0),
        "changed": full.get("changed", False),
        "methods": full.get("methods", []),
        "warnings": full.get("warnings", []),
        "quality": full.get("quality", {}),
        "originalSha256": full.get("originalSha256"),
        "repairedSha256": full.get("repairedSha256"),
        "purification": {
            key: purification.get(key)
            for key in ("backend", "model", "pixelsInpainted", "pixelsPurified", "patchSize", "passes", "trainingSamples", "note", "fallback")
            if purification.get(key) is not None
        },
    }
    response.headers["X-Recovery-Report"] = json.dumps(response_report, separators=(",", ":"))
    response.headers["Access-Control-Expose-Headers"] = "X-Recovery-Report, Content-Disposition"
    return response
