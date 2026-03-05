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


def make_pdf_with_widths(widths: list[int], height: int = 100) -> bytes:
    writer = PdfWriter()
    for width in widths:
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


def test_merge_respects_per_file_ranges_and_output_name():
    client = app.test_client()
    pdf_a = make_pdf_with_widths([100, 110, 120])
    pdf_b = make_pdf_with_widths([200, 210])

    data = MultiDict([
        ('file_ids[]', 'a-id'),
        ('file_ids[]', 'b-id'),
        ('order[]', 'b-id'),
        ('order[]', 'a-id'),
        ('range_ids[]', 'a-id'),
        ('ranges[]', '1-2'),
        ('range_ids[]', 'b-id'),
        ('ranges[]', '2'),
        ('output_name', 'my-report'),
        ('pdfs', (io.BytesIO(pdf_a), 'doc-a.pdf')),
        ('pdfs', (io.BytesIO(pdf_b), 'doc-b.pdf')),
    ])

    response = client.post('/merge', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert 'my-report.pdf' in response.headers['Content-Disposition']

    merged = PdfReader(io.BytesIO(response.data))
    widths = [float(page.mediabox.width) for page in merged.pages]
    assert widths == [210.0, 100.0, 110.0]


def test_merge_rejects_invalid_range_input():
    client = app.test_client()
    pdf = make_pdf_with_widths([100, 110])

    data = MultiDict([
        ('file_ids[]', 'a-id'),
        ('order[]', 'a-id'),
        ('range_ids[]', 'a-id'),
        ('ranges[]', '9-10'),
        ('pdfs', (io.BytesIO(pdf), 'doc-a.pdf')),
    ])

    response = client.post('/merge', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'out of bounds' in response.get_json()['error']
