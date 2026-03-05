import io
import os

from flask import Flask, jsonify, render_template, request, send_file
from pypdf import PdfReader, PdfWriter

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
APP_NAME = os.getenv("APP_NAME", "PDF Merger")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


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

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No PDF files provided"}), 400

    if len(file_ids) != len(files):
        return jsonify({"error": "Malformed payload: file IDs did not match uploaded files"}), 400

    file_map = {}
    for file_id, upload in zip(file_ids, files):
        if upload and upload.filename and upload.filename.lower().endswith(".pdf"):
            file_map[file_id] = upload

    ordered_files = [file_map[file_id] for file_id in order if file_id in file_map] if order else list(file_map.values())

    if not ordered_files:
        return jsonify({"error": "No valid PDF files found"}), 400

    writer = PdfWriter()
    try:
        for upload in ordered_files:
            upload.seek(0)
            reader = PdfReader(io.BytesIO(upload.read()))
            for page in reader.pages:
                writer.add_page(page)
    except Exception as exc:
        return jsonify({"error": f"Failed to process PDF: {exc}"}), 500

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    download_name = f"{APP_NAME.lower().replace(' ', '-')}-merged.pdf"
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
