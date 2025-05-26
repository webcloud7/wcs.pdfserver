from copy import deepcopy
from urllib.request import Request, urlopen
from weasyprint.urls import HTTP_HEADERS
from weasyprint.urls import StreamingGzipFile
from weasyprint.urls import UNICODE_SCHEME_RE
from urllib3.util import make_headers
import zlib
import os


def basic_auth_url_fetcher(url, timeout=120, ssl_context=None, auth=None):
    """This is a copy of weasyprint's default fetcher, but adds
    basic auth header and removes file:// support.
    Expect auth being a username, password tuple
    """
    if UNICODE_SCHEME_RE.match(url):
        # See https://bugs.python.org/issue34702
        if url.startswith('file://'):
            url = url.split('?')[0]

        headers = deepcopy(HTTP_HEADERS)
        username = os.environ.get('REMOTE_USERNAME', None)
        password = os.environ.get('REMOTE_PASSWORD', None)
        if username and password:
            headers.update(make_headers(basic_auth=f'{username}:{password}'))

        response = urlopen(Request(url, headers=headers), timeout=timeout, context=ssl_context)
        response_info = response.info()
        result = {
            'redirected_url': response.geturl(),
            'mime_type': response_info.get_content_type(),
            'encoding': response_info.get_param('charset'),
            'filename': response_info.get_filename(),
        }
        content_encoding = response_info.get('Content-Encoding')
        if content_encoding == 'gzip':
            result['file_obj'] = StreamingGzipFile(fileobj=response)
        elif content_encoding == 'deflate':
            data = response.read()
            try:
                result['string'] = zlib.decompress(data)
            except zlib.error:
                # Try without zlib header or checksum
                result['string'] = zlib.decompress(data, -15)
        else:
            result['file_obj'] = response
        return result
    else:  # pragma: no cover
        raise ValueError('Not an absolute URI: %r' % url)
