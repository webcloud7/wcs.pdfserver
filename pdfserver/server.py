from aiohttp import web
from pdfserver.cache import ExpiringPDFCache
from pdfserver.fetcher import basic_auth_url_fetcher
from pdfserver.log import logger
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetchingError
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import asyncio
import io
import json


class TaskStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


routes = web.RouteTableDef()
pdf_cache = ExpiringPDFCache(expiry_minutes=30)
pdf_executor = ThreadPoolExecutor(max_workers=10)


async def create_pdf(url, css, filename, uid):
    """
    Helper function to create a PDF from a URL with optional CSS files.

    :param url: The URL to fetch HTML from.
    :param css_files: List of CSS file URLs to apply.
    :param filename: Name of the output PDF file.
    :param uid: Unique identifier for the PDF.
    :return: BytesIO object containing the PDF data.
    """
    # temp_file = io.BytesIO()
    # font_config = FontConfiguration()
    cache = pdf_cache.cache[uid]

    def _create_pdf_sync():
        temp_file = io.BytesIO()
        font_config = FontConfiguration()
        try:
            html = HTML(url, url_fetcher=basic_auth_url_fetcher)
            html.write_pdf(temp_file, stylesheets=css, font_config=font_config)
            return temp_file
        except URLFetchingError:
            logger.error(f"Failed to fetch URL: {url}")
            raise
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise

    try:
        # Run the blocking PDF generation in a thread pool
        loop = asyncio.get_event_loop()
        temp_file = await loop.run_in_executor(pdf_executor, _create_pdf_sync)
        pdf_cache.store_pdf(uid, temp_file, TaskStatus.COMPLETED.value)
    except URLFetchingError:
        cache['status'] = TaskStatus.FAILED.value
        cache['message'] = 'Failed to fetch URL'
    except Exception:
        cache['status'] = TaskStatus.FAILED.value
        cache['message'] = 'Error generating PDF'


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
    - JSON response with PDF ID and status "running".
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

    for css_file in css_files:
        css.append(CSS(filename=css_file, url_fetcher=basic_auth_url_fetcher))

    uid, cache = pdf_cache.init_store(filename, TaskStatus.RUNNING.value)

    asyncio.create_task(create_pdf(url, css, filename, uid))
    response = web.json_response(
        {"uid": uid, "filename": cache['name'], "status": cache['status']},
        status=200
    )
    return response


@routes.get('/status/{pdf_id}')
async def get_pdf_status(request):
    pdf_id = request.match_info['pdf_id']
    pdf = pdf_cache.get_pdf(pdf_id)
    if not pdf:
        return web.json_response(
            {"error": "PDF not found"},
            status=404
        )

    response_data = {
        "uid": pdf_id,
        "status": pdf['status'],
        "filename": pdf['name'],
        'timestamp': pdf['timestamp'],
        'message': pdf['message']
    }

    if pdf['status'] == TaskStatus.COMPLETED.value:
        response_data['download'] = f'/pdf/{pdf_id}'
    return web.json_response(response_data)


@routes.get('/pdf/{pdf_id}')
async def get_pdf(request):
    pdf_id = request.match_info['pdf_id']
    pdf = pdf_cache.get_pdf(pdf_id)

    file = pdf['data']
    file.seek(0)
    response = web.Response(
        body=file.getvalue(),
        content_type='application/pdf',
        headers={
            'Content-Length': str(len(file.getvalue())),
            'Content-Disposition': f'attachment; filename="{pdf['name']}"',
        }
    )
    return response


@routes.get('/')
async def index(request):
    return web.Response(text="WeasyPrint PDF Conversion Service", content_type='text/plain')


@routes.get('/health')
async def health_check(request):
    return web.Response(text="OK", content_type='text/plain')


async def init():
    app = web.Application()
    app.add_routes(routes)

    await pdf_cache.start_cleanup_task()

    # Cleanup on shutdown
    async def cleanup_on_shutdown(app):
        await pdf_cache.stop_cleanup_task()

    app.on_cleanup.append(cleanup_on_shutdown)
    return app


if __name__ == '__main__':
    app = asyncio.run(init())
    web.run_app(app, host='0.0.0.0', port=8040)
