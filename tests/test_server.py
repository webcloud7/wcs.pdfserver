from pdfserver.server import TaskStatus
import time
import asyncio

TEST_HTML_RESPONSE = """
<!DOCTYPE html>
<html>
<head>
    <title>Test HTML</title>
</head>
<body>
    <h1>Hello, WeasyPrint!</h1>
</body>
</html>
"""


async def test_convert_to_pdf_success(client, httpserver):
    """Test successful PDF conversion with a real HTTP server."""
    httpserver.expect_request("/test.html").respond_with_data(
        TEST_HTML_RESPONSE,
        content_type="text/html"
    )
    test_url = httpserver.url_for("/test.html")
    resp = await client.post(
        '/convert',
        json={
            'url': test_url,
            'filename': 'test.pdf'
        }
    )

    # Check the response
    assert resp.status == 200
    assert resp.content_type == 'application/json'

    data = await resp.json()
    assert data['status'] == TaskStatus.RUNNING.value
    uid = data['uid']

    max_wait = 1  # seconds
    for _ in range(max_wait * 20):
        status_response = await client.get(f'/status/{uid}')
        assert status_response.status == 200
        status_data = await status_response.json()
        if status_data['status'] == TaskStatus.COMPLETED.value:
            break
        await asyncio.sleep(0.5)

    download_url = status_data['download']

    resp_pdf = await client.get(download_url)
    pdf_content = await resp_pdf.read()

    # Basic validation that it's a PDF
    assert pdf_content.startswith(b'%PDF-')
    assert resp_pdf.headers['Content-Disposition'] == 'attachment; filename="test.pdf"'


async def test_sync_conversion_to_pdf_success(client, httpserver):
    httpserver.expect_request("/test.html").respond_with_data(
        TEST_HTML_RESPONSE,
        content_type="text/html"
    )
    test_url = httpserver.url_for("/test.html")
    resp = await client.post(
        '/convert_sync',
        json={
            'url': test_url,
            'filename': 'test.pdf'
        }
    )
    pdf_content = await resp.read()
    assert pdf_content.startswith(b'%PDF-')
    assert resp.headers['Content-Disposition'] == 'attachment; filename="test.pdf"'


async def test_sync_convert_to_pdf_missing_url(client):
    """Test PDF conversion with missing URL."""
    resp = await client.post(
        '/convert_sync',
        json={'filename': 'test.pdf'}
    )
    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'URL is required'


async def test_convert_to_pdf_missing_url(client):
    """Test PDF conversion with missing URL."""
    resp = await client.post(
        '/convert',
        json={'filename': 'test.pdf'}
    )

    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'URL is required'


async def test_convert_to_pdf_invalid_json(client):
    """Test PDF conversion with invalid JSON."""
    resp = await client.post(
        '/convert',
        data='invalid json'
    )

    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'Invalid JSON in request body'


async def test_sync_convert_to_pdf_invalid_json(client):
    """Test PDF conversion with invalid JSON."""
    resp = await client.post(
        '/convert_sync',
        data='invalid json'
    )
    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'Invalid JSON in request body'


async def test_convert_to_pdf_generation_error(client, httpserver):
    """Test PDF conversion with generation error."""
    # Use a non-existent path to cause an error
    httpserver.expect_request("/nonexistent.html").respond_with_data(
        "Not Found",
        status=404,
        content_type="text/plain"
    )

    test_url = httpserver.url_for("/nonexistent.html")
    resp = await client.post(
        '/convert',
        json={
            'url': test_url,
            'filename': 'test.pdf'
        }
    )

    assert resp.status == 200
    data = await resp.json()
    assert data['status'] == TaskStatus.RUNNING.value
    uid = data['uid']

    max_wait = 1
    for _ in range(max_wait * 20):
        status_response = await client.get(f'/status/{uid}')
        status_data = await status_response.json()
        if status_data['status'] == TaskStatus.FAILED.value:
            break
        await asyncio.sleep(0.5)

    assert status_data['message'] == 'Failed to fetch URL'


async def test_sync_convert_to_pdf_generation_error(client, httpserver):
    """Test PDF conversion with generation error."""
    # Use a non-existent path to cause an error
    httpserver.expect_request("/nonexistent.html").respond_with_data(
        "Not Found",
        status=404,
        content_type="text/plain"
    )

    test_url = httpserver.url_for("/nonexistent.html")
    resp = await client.post(
        '/convert_sync',
        json={
            'url': test_url,
            'filename': 'test.pdf'
        }
    )

    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'Failed to fetch URL'


async def test_index_endpoint(client):
    """Test the index endpoint."""
    resp = await client.get('/')
    assert resp.status == 200
    assert '<h1>WeasyPrint PDF Conversion Service</h1>' in (await resp.text())
    assert resp.content_type == 'text/html'


async def test_health_check(client):
    """Test the health check endpoint."""
    resp = await client.get('/health')
    assert resp.status == 200
    assert await resp.text() == "OK"
    assert resp.content_type == 'text/plain'
