import io

from pypdf import PdfReader, PdfWriter
from werkzeug.datastructures import MultiDict

from app import app


def make_pdf(width: int, height: int) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_healthcheck():
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}


def test_merge_supports_duplicate_filenames_and_respects_order():
    client = app.test_client()

    pdf_small = make_pdf(100, 100)
    pdf_large = make_pdf(200, 200)

    data = MultiDict([
        ('file_ids[]', 'first-id'),
        ('file_ids[]', 'second-id'),
        ('order[]', 'second-id'),
        ('order[]', 'first-id'),
        ('pdfs', (io.BytesIO(pdf_small), 'same-name.pdf')),
        ('pdfs', (io.BytesIO(pdf_large), 'same-name.pdf')),
    ])

    response = client.post('/merge', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    merged = PdfReader(io.BytesIO(response.data))
    assert len(merged.pages) == 2

    first_width = float(merged.pages[0].mediabox.width)
    second_width = float(merged.pages[1].mediabox.width)
    assert first_width == 200
    assert second_width == 100


def test_merge_rejects_malformed_payload():
    client = app.test_client()
    pdf = make_pdf(100, 100)

    data = MultiDict([
        ('file_ids[]', 'only-id'),
        ('pdfs', (io.BytesIO(pdf), 'doc-a.pdf')),
        ('pdfs', (io.BytesIO(pdf), 'doc-b.pdf')),
    ])

    response = client.post('/merge', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'Malformed payload' in response.get_json()['error']
