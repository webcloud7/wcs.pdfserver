from aiohttp import web
from enum import Enum
from pdfserver.fetcher import basic_auth_url_fetcher
from weasyprint import CSS
import json


class TaskStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def pdf_response(file, filename):
    """Utility function to create a PDF response."""
    file.seek(0)
    return web.Response(
            body=file.getvalue(),
            content_type='application/pdf',
            headers={
                'Content-Length': str(len(file.getvalue())),
                'Content-Disposition': f'attachment; filename="{filename}"',
            }
        )


async def extrat_data_from_request(request):

    result = {
        'error': None,
        'url': None,
        'css': [],
        'filename': None,
    }

    data = {}
    try:
        # Parse request body
        data = await request.json()
    except json.JSONDecodeError:
        result["error"] = "Invalid JSON in request body"
        return result

    if 'url' not in data:
        result["error"] = "URL is required"
        return result

    result['url'] = data['url']
    result['filename'] = data.get('filename', 'output.pdf')
    for css_file in data.get('css', []):
        result['css'].append(CSS(filename=css_file, url_fetcher=basic_auth_url_fetcher))

    return result
