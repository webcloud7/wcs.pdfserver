from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pdfserver.cache import ExpiringPDFCache
from pdfserver.fetcher import basic_auth_url_fetcher
from pdfserver.log import logger
from pdfserver.utils import pdf_response
from pdfserver.utils import extrat_data_from_request
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetchingError
import asyncio
import io


class TaskStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


routes = web.RouteTableDef()
pdf_cache = ExpiringPDFCache(expiry_minutes=30)
pdf_executor = ThreadPoolExecutor(max_workers=10)


def _create_pdf_sync(url, css):
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


async def create_pdf(url, css, filename, uid):
    """
    Helper function to create a PDF from a URL with optional CSS files.

    :param url: The URL to fetch HTML from.
    :param css_files: List of CSS file URLs to apply.
    :param filename: Name of the output PDF file.
    :param uid: Unique identifier for the PDF.
    :return: BytesIO object containing the PDF data.
    """
    cache = pdf_cache.cache[uid]
    try:
        # Run the blocking PDF generation in a thread pool
        loop = asyncio.get_event_loop()
        temp_file = await loop.run_in_executor(pdf_executor, _create_pdf_sync, url, css)
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
        "filename": 'a_file.pdf',
    }

    Returns:
    - JSON response with PDF ID and status "running".
    """
    data = await extrat_data_from_request(request)

    if data['error']:
        return web.json_response(
            {"error": data['error']},
            status=400
        )

    uid, cache = pdf_cache.init_store(data['filename'], TaskStatus.RUNNING.value)

    asyncio.create_task(create_pdf(data['url'], data['css'], data['filename'], uid))
    response = web.json_response(
        {"uid": uid, "filename": cache['name'], "status": cache['status']},
        status=200
    )
    return response


@routes.post('/convert_sync')
async def convert_to_pdf_sync(request):
    """
    Synchronous endpoint to convert HTML from a URL to PDF.

    Expected JSON payload:
    {
        "url": "http://localhost/path/to/endpoint",
        "css_files": ["http://localhost/path/to/file.css", ...],
        "filename": 'a_file.pdf',
    }
    Returns:
    - A PDF file as a response.
    """
    data = await extrat_data_from_request(request)

    if data['error']:
        return web.json_response(
            {"error": data['error']},
            status=400
        )
    try:
        temp_file = _create_pdf_sync(data['url'], data['css'])
    except URLFetchingError:
        return web.json_response(
            {"error": "Failed to fetch URL"},
            status=400
        )
    except Exception:
        return web.json_response(
            {"error": "Error generating PDF"},
            status=400
        )
    return pdf_response(temp_file, data['filename'])


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
    return pdf_response(pdf['data'], pdf['name'])


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
