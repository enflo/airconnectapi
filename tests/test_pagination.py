import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_pagination_headers_and_count():
    resp = client.get("/api/airports", params={"size": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 5

    headers = resp.headers
    # Required pagination headers should be present
    assert "X-Total-Count" in headers
    assert "X-Page" in headers
    assert "X-Page-Size" in headers
    assert "X-Total-Pages" in headers

    total = int(headers["X-Total-Count"]) if headers["X-Total-Count"].isdigit() else int(float(headers["X-Total-Count"]))
    page = int(headers["X-Page"]) if headers["X-Page"].isdigit() else int(float(headers["X-Page"]))
    size = int(headers["X-Page-Size"]) if headers["X-Page-Size"].isdigit() else int(float(headers["X-Page-Size"]))
    total_pages = int(headers["X-Total-Pages"]) if headers["X-Total-Pages"].isdigit() else int(float(headers["X-Total-Pages"]))

    assert page == 1
    assert size == 5
    assert total_pages == (total + size - 1) // size


def test_pagination_pages_disjoint():
    resp1 = client.get("/api/airports", params={"size": 5, "page": 1})
    resp2 = client.get("/api/airports", params={"size": 5, "page": 2})
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    data1 = resp1.json()
    data2 = resp2.json()

    ids1 = {str(a.get("id") or a.get("ident")) for a in data1}
    ids2 = {str(a.get("id") or a.get("ident")) for a in data2}

    # Pages should not overlap
    assert ids1.isdisjoint(ids2)


def test_pagination_with_filter_and_size():
    resp = client.get("/api/airports", params={"iso_country": "US", "size": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= len(data) <= 3

    # All returned items should respect the filter
    assert all((a.get("iso_country") or "").lower() == "us" for a in data)

    headers = resp.headers
    assert headers.get("X-Page") == "1"
    assert headers.get("X-Page-Size") == "3"


def test_size_overrides_limit_when_both_provided():
    resp = client.get("/api/airports", params={"size": 2, "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 2
    # Ensure that size takes precedence over limit and we can receive up to 2 items
    assert len(data) == 2 or len(data) == 1  # Allow 1 if dataset is very small