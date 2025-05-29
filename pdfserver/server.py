from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from pdfserver.cache import ExpiringPDFCache
from pdfserver.fetcher import basic_auth_url_fetcher
from pdfserver.log import logger
from pdfserver.utils import extrat_data_from_request
from pdfserver.utils import pdf_response
from pdfserver.utils import TaskStatus
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetchingError
import markdown
import asyncio
import io


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
    cache = pdf_cache.storage[uid]
    try:
        # Run the blocking PDF generation in a thread pool
        loop = asyncio.get_event_loop()
        temp_file = await loop.run_in_executor(pdf_executor, _create_pdf_sync, url, css)
        pdf_cache.save_pdf(uid, filename, temp_file)
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

    uid, cache = pdf_cache.add()
    asyncio.create_task(create_pdf(data['url'], data['css'], data['filename'], uid))
    response = web.json_response(
        {"uid": uid, "filename": data['filename'], "status": cache['status']},
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
        "filename": pdf['filename'],
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
    return pdf_response(pdf['data'], pdf['filename'])


@routes.get('/')
async def index(request):
    with open('Readme.md', 'r') as f:
        readme_content = f.read()
    markdown_html = markdown.markdown(readme_content)
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WeasyPrint PDF Conversion Service</title>
    <link rel="icon" href="static/favicon.ico" type="image/x-icon">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <style>
        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
        }}

        @media (max-width: 767px) {{
            .markdown-body {{
                padding: 15px;
            }}
        }}
    </style>
</head>
<body>
    <article class="markdown-body">
        {markdown_html}
    </article>
</body>
</html>
"""
    return web.Response(text=html_content, content_type='text/html')


@routes.get('/health')
async def health_check(request):
    return web.Response(text="OK", content_type='text/plain')


async def init():
    app = web.Application()
    app.router.add_static('/static/', path='pdfserver/static', name='static')
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
