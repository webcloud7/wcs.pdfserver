import pytest
from aiohttp import web
from pdfserver.server import routes


pytest_plugins = ["pytest_httpserver"]


@pytest.fixture
async def client(aiohttp_client):
    """Create a test client for the app."""
    app = web.Application()
    app.add_routes(routes)
    return await aiohttp_client(app)
