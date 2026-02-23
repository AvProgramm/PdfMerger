# PDF Merger — Flask App

A clean, drag-and-drop web app to merge multiple PDF files in any order.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

## Features

- Upload multiple PDFs via drag-and-drop or file browser
- Drag rows to reorder before merging
- Remove individual files
- Merged PDF downloads instantly via the browser
- Handles up to 100 MB total payload

## Project Structure

```
pdf_merger/
├── app.py              # Flask backend
├── requirements.txt
└── templates/
    └── index.html      # Single-page UI
```
