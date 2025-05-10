from aiohttp import web
from weasyprint import HTML, CSS
import io
import json
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pdf server')

routes = web.RouteTableDef()


@routes.post('/convert')
async def convert_to_pdf(request):
    """
    Endpoint to convert HTML from a URL to PDF

    Expected JSON payload:
    {
        "url": "http://localhost/path/to/endpoint",
        "css_files": ["http://localhost/path/to/file.css", ...]
        "filename": 'a_file.pdf'
    }

    Returns:
    - PDF file as attachment or
    - JSON with error message
    """

    try:
        # Parse request body
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body"},
            status=400
        )

    if 'url' not in data:
        return web.json_response(
            {"error": "URL is required"},
            status=400
        )

    url = data['url']
    css_files = data.get('css', [])
    css = []
    filename = data.get('filename', 'output.pdf')

    html = HTML(url)
    for css_file in css_files:
        css.append(CSS(filename=css_file))

    temp_file = io.BytesIO()
    try:
        html.write_pdf(temp_file, stylesheets=css)
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return web.json_response(
            {"error": "Failed to generate PDF"},
            status=500
        )
    else:
        temp_file.seek(0)
        response = web.Response(
            body=temp_file.getvalue(),
            content_type='application/pdf',
            headers={
                'Content-Length': str(len(temp_file.getvalue())),
                'Content-Disposition': f'attachment; filename="{filename}"',
            }
        )
        return response


@routes.get('/')
async def index(request):
    return web.Response(text="WeasyPrint PDF Conversion Service", content_type='text/plain')


@routes.get('/health')
async def health_check(request):
    return web.Response(text="OK", content_type='text/plain')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, host='0.0.0.0', port=8040)
