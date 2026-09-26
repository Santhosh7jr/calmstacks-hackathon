from io import BytesIO
import json

from flask import Blueprint, jsonify, request, send_file

from recoverai_core.recovery.fragments import reconstruct_fragments

fragments_bp = Blueprint("fragments", __name__)


@fragments_bp.post("")
@fragments_bp.post("/reconstruct")
def reconstruct():
    uploaded = request.files.getlist("files")
    if not uploaded:
        return jsonify({"message": "Upload at least one fragment using the 'files' field."}), 400
    items = [(item.filename or f"fragment_{index}.bin", item.read()) for index, item in enumerate(uploaded)]
    if any(not data for _, data in items):
        return jsonify({"message": "Empty fragments are not allowed."}), 400
    output_name = request.form.get("outputName", "reconstructed.bin")
    try:
        result = reconstruct_fragments(items, output_name)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"message": f"Fragment reconstruction failed: {exc}"}), 500

    response = send_file(
        BytesIO(result["data"]),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=f"reconstructed_{output_name}",
    )
    response.headers["X-Reconstruction-Report"] = json.dumps(result["report"], separators=(",", ":"))
    response.headers["Access-Control-Expose-Headers"] = "X-Reconstruction-Report, Content-Disposition"
    return response
