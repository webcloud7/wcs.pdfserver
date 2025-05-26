from pdfserver.fetcher import basic_auth_url_fetcher
from pytest_httpserver import RequestMatcher
from unittest.mock import patch
import os
import pytest
import gzip


def test_basic_auth_url_fetcher_with_auth(httpserver):
    auth_header = {'Authorization': 'Basic dXNlcjpwYXNz'}
    httpserver.expect_request("/test.html", headers=auth_header).respond_with_data(
        '<html><body>Test</body></html>',
        content_type="text/html"
    )
    test_url = httpserver.url_for("/test.html")

    with patch.dict(os.environ, {'REMOTE_USERNAME': 'user', 'REMOTE_PASSWORD': 'pass'}):
        result = basic_auth_url_fetcher(test_url)
        assert result['redirected_url'] == test_url
        assert result['mime_type'] == 'text/html'
        httpserver.assert_request_made(RequestMatcher("/test.html"))


def test_basic_auth_url_fetcher_without_auth(httpserver):
    httpserver.expect_request("/test.html").respond_with_data(
        '<html><body>Test</body></html>',
        content_type="text/html"
    )
    test_url = httpserver.url_for("/test.html")

    with patch.dict(os.environ, {}, clear=True):
        result = basic_auth_url_fetcher(test_url)
        assert result['redirected_url'] == test_url
        assert result['mime_type'] == 'text/html'
        httpserver.assert_request_made(RequestMatcher("/test.html"))


def test_basic_auth_url_fetcher_invalid_url():
    with pytest.raises(ValueError, match="Not an absolute URI"):
        basic_auth_url_fetcher('invalid-url')


def test_basic_auth_url_fetcher_gzip_encoding(httpserver):
    httpserver.expect_request("/test.gz").respond_with_data(
        gzip.compress(b'<html><body>Test</body></html>'),
        headers={'Content-Type': 'text/html', 'Content-Encoding': 'gzip'},
        content_type="text/html"
    )
    test_url = httpserver.url_for("/test.gz")

    result = basic_auth_url_fetcher(test_url)

    assert result['redirected_url'] == test_url
    assert result['mime_type'] == 'text/html'
    assert 'file_obj' in result
    httpserver.assert_request_made(RequestMatcher("/test.gz"))
