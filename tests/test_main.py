"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestRootEndpoint:
    """Root endpoint should serve the web site."""

    def test_root_serves_site(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert b"Air connect API" in response.content


class TestHelloEndpoint:
    """Hello endpoint should no longer exist."""

    def test_hello_removed_with_name(self):
        name = "Alice"
        response = client.get(f"/hello/{name}")
        assert response.status_code == 404

    def test_hello_removed_various(self):
        for name in ["Bob", "Charlie", "Diana", "Eve", "José", "User123"]:
            response = client.get(f"/hello/{name}")
            assert response.status_code == 404

    def test_hello_without_name(self):
        response = client.get("/hello/")
        assert response.status_code == 404


class TestInvalidEndpoints:
    """Test cases for invalid endpoints."""

    def test_invalid_endpoint(self):
        """Test that invalid endpoints return 404."""
        response = client.get("/invalid")
        assert response.status_code == 404

    def test_hello_without_name(self):
        """Test hello endpoint without name parameter."""
        response = client.get("/hello/")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_app_startup():
    """Test that the FastAPI app can be created successfully."""
    assert app is not None
    assert hasattr(app, 'routes')
    assert len(app.routes) > 0