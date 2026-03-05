# PDF Merger - Flask App

A drag-and-drop web app to merge multiple PDF files in a custom order.

## Local Run

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Features

- Multi-file PDF upload (drag-and-drop or file browser)
- Drag to reorder before merge
- Duplicate filenames supported safely
- Server-side merge via `pypdf`
- Max upload cap configurable with `MAX_UPLOAD_MB` (default `100`)
- App branding configurable with `APP_NAME` (default `PDF Merger`)
- Health endpoint at `/health`

## Project Structure

```text
PdfMerger/
|- app.py
|- requirements.txt
|- templates/
|  |- index.html
|- tests/
|  |- test_app.py
|- render.yaml
|- Procfile
```

## Deploy To Render

1. Push this repo to GitHub.
2. In Render, create a new Web Service from the repo.
3. Keep these values:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Health Check Path: `/health`
4. Set the Render service name to your desired app name.
5. Set `APP_NAME` in Render environment variables to the exact display name you want.

Notes:
- The service name controls the default Render URL (`https://<service-name>.onrender.com`).
- You can later connect a custom domain for branding.
