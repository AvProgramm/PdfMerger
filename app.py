import io
import os
import re

from flask import Flask, jsonify, render_template, request, send_file
from pypdf import PdfReader, PdfWriter

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
APP_NAME = os.getenv("APP_NAME", "PDF Merger")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def parse_page_selection(selection: str, total_pages: int) -> list[int]:
    if total_pages <= 0:
        raise ValueError("PDF has no pages")

    if not selection or selection.strip().lower() in {"all", "*"}:
        return list(range(total_pages))

    indexes = []
    seen = set()
    chunks = [chunk.strip() for chunk in selection.split(",") if chunk.strip()]
    if not chunks:
        raise ValueError("Page range is empty")

    for chunk in chunks:
        if "-" in chunk:
            parts = chunk.split("-", 1)
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError(f"Invalid range segment '{chunk}'")
            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                raise ValueError(f"Range start must be <= end in '{chunk}'")
            for page_num in range(start, end + 1):
                if page_num < 1 or page_num > total_pages:
                    raise ValueError(f"Page {page_num} is out of bounds (1-{total_pages})")
                page_index = page_num - 1
                if page_index not in seen:
                    indexes.append(page_index)
                    seen.add(page_index)
        else:
            if not chunk.isdigit():
                raise ValueError(f"Invalid page '{chunk}'")
            page_num = int(chunk)
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"Page {page_num} is out of bounds (1-{total_pages})")
            page_index = page_num - 1
            if page_index not in seen:
                indexes.append(page_index)
                seen.add(page_index)

    if not indexes:
        raise ValueError("No pages selected")
    return indexes


def sanitize_output_filename(raw_name: str) -> str:
    if not raw_name:
        base = APP_NAME.lower().replace(" ", "-")
        return f"{base}-merged.pdf"

    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw_name).strip(" .-_")
    if not normalized:
        base = APP_NAME.lower().replace(" ", "-")
        normalized = f"{base}-merged"

    if not normalized.lower().endswith(".pdf"):
        normalized += ".pdf"
    return normalized


@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/merge", methods=["POST"])
def merge_pdfs():
    files = request.files.getlist("pdfs")
    file_ids = request.form.getlist("file_ids[]")
    order = request.form.getlist("order[]")
    range_ids = request.form.getlist("range_ids[]")
    ranges = request.form.getlist("ranges[]")
    output_name = request.form.get("output_name", "")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No PDF files provided"}), 400

    if len(file_ids) != len(files):
        return jsonify({"error": "Malformed payload: file IDs did not match uploaded files"}), 400

    if range_ids and len(range_ids) != len(ranges):
        return jsonify({"error": "Malformed payload: page ranges are invalid"}), 400

    range_map = {range_id: selection for range_id, selection in zip(range_ids, ranges)}

    file_map = {}
    for file_id, upload in zip(file_ids, files):
        if upload and upload.filename and upload.filename.lower().endswith(".pdf"):
            file_map[file_id] = upload

    ordered_file_ids = [file_id for file_id in order if file_id in file_map] if order else list(file_map.keys())

    if not ordered_file_ids:
        return jsonify({"error": "No valid PDF files found"}), 400

    writer = PdfWriter()
    try:
        for file_id in ordered_file_ids:
            upload = file_map[file_id]
            upload.seek(0)
            reader = PdfReader(io.BytesIO(upload.read()))
            selected_indexes = parse_page_selection(range_map.get(file_id, ""), len(reader.pages))
            for page_index in selected_indexes:
                writer.add_page(reader.pages[page_index])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to process PDF: {exc}"}), 500

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    download_name = sanitize_output_filename(output_name)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=download_name)


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": f"Upload is too large. Max total size is {MAX_UPLOAD_MB} MB."}), 413


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
