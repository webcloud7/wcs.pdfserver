

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

    # Get the URL of the test server
    test_url = httpserver.url_for("/test.html")
    # Make the request to the conversion endpoint
    resp = await client.post(
        '/convert',
        json={
            'url': test_url,
            'filename': 'test.pdf'
        }
    )

    # Check the response
    assert resp.status == 200
    assert resp.content_type == 'application/pdf'

    # Read the PDF content
    pdf_content = await resp.read()

    # Basic validation that it's a PDF
    assert pdf_content.startswith(b'%PDF-')
    assert resp.headers['Content-Disposition'] == 'attachment; filename="test.pdf"'


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

    assert resp.status == 500
    data = await resp.json()
    assert data['error'] == 'Failed to fetch URL'


async def test_index_endpoint(client):
    """Test the index endpoint."""
    resp = await client.get('/')
    assert resp.status == 200
    assert await resp.text() == "WeasyPrint PDF Conversion Service"
    assert resp.content_type == 'text/plain'


async def test_health_check(client):
    """Test the health check endpoint."""
    resp = await client.get('/health')
    assert resp.status == 200
    assert await resp.text() == "OK"
    assert resp.content_type == 'text/plain'
