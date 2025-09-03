import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def assert_all(items, pred):
    assert all(pred(item) for item in items), "One or more items did not satisfy the filter predicate"


class TestAirportsFilters:
    def test_filter_by_iata(self):
        resp = client.get("/api/airports", params={"iata": "JFK"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert_all(data, lambda a: (a.get("iata_code") or "").lower() == "jfk")

    def test_filter_by_icao(self):
        resp = client.get("/api/airports", params={"icao": "KJFK"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert_all(data, lambda a: (a.get("icao_code") or "").lower() == "kjfk")

    def test_filter_by_municipality_with_limit(self):
        resp = client.get("/api/airports", params={"municipality": "New York", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= len(data) <= 3
        assert_all(data, lambda a: (a.get("municipality") or "").lower() == "new york")

    def test_filter_by_country_name_choice(self):
        resp = client.get("/api/airports", params={"country_name": "United States", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= len(data) <= 2
        assert_all(data, lambda a: (a.get("country") or {}).get("name", "").lower() == "united states")

    def test_filter_by_region_name_choice(self):
        # New York is a US region (US-NY)
        resp = client.get("/api/airports", params={"region_name": "New York", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= len(data) <= 2
        assert_all(data, lambda a: (a.get("region") or {}).get("name", "").lower() == "new york")

    def test_filter_by_iso_country_choice_with_limit(self):
        resp = client.get("/api/airports", params={"iso_country": "US", "limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= len(data) <= 5
        assert_all(data, lambda a: (a.get("iso_country") or "").lower() == "us")

    def test_filter_by_type_choice(self):
        resp = client.get("/api/airports", params={"type": "large_airport", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= len(data) <= 3
        assert_all(data, lambda a: (a.get("type") or "").lower() == "large_airport")

    def test_limit_without_filters(self):
        resp = client.get("/api/airports", params={"limit": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 4



def test_filter_by_iso_region_choice_with_limit():
    resp = client.get("/api/airports", params={"iso_region": "US-NY", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert 1 <= len(data) <= 3
    assert_all(data, lambda a: (a.get("iso_region") or "").lower() == "us-ny")
