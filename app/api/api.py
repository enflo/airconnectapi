import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from app.models.db import get_connection, query_airports, get_airport_by_slug


router = APIRouter(prefix="/api")


def slugify(text: Optional[str], fallback: Optional[str] = None) -> str:
    """Create a URL-friendly slug from a string.

    - Normalize unicode and strip accents
    - Lowercase
    - Replace non-alphanumeric with hyphens
    - Collapse multiple hyphens and trim
    """
    if not text or not isinstance(text, str):
        return (fallback or "").strip().lower()
    # Normalize and strip accents
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    # Lowercase and replace non-alphanum with hyphen
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm)
    # Collapse and trim hyphens
    norm = re.sub(r"-+", "-", norm).strip("-")
    if not norm and fallback:
        return fallback.strip().lower()
    return norm


def airport_slug(a: dict[str, Any]) -> str:
    name = a.get("name")
    ident = a.get("ident") or a.get("icao_code") or a.get("iata_code")
    fid = str(a.get("id")) if a.get("id") is not None else None
    slug = slugify(name, fallback=ident or fid or "")
    return slug


def attach_slugs(items: List[dict[str, Any]]) -> None:
    for a in items:
        if "slug" not in a or not a.get("slug"):
            a["slug"] = airport_slug(a)


@router.get("/airports", summary="Combined OurAirports data as JSON", responses={
    200: {
        "description": "A list of airports",
        "content": {
            "application/json": {
                "examples": {
                    "sample": {
                        "summary": "Example airports",
                        "value": [
                            {
                                "id": 3797,
                                "ident": "KJFK",
                                "name": "John F Kennedy International Airport",
                                "iata_code": "JFK",
                                "icao_code": "KJFK",
                                "municipality": "New York",
                                "iso_country": "US",
                                "iso_region": "US-NY",
                                "type": "large_airport",
                                "latitude_deg": 40.6413,
                                "longitude_deg": -73.7781,
                                "elevation_ft": 13,
                                "slug": "john-f-kennedy-international-airport",
                                "country": {"code": "US", "name": "United States"},
                                "region": {"code": "US-NY", "name": "New York"}
                            },
                            {
                                "id": 507,
                                "ident": "KTEB",
                                "name": "Teterboro Airport",
                                "iata_code": "TEB",
                                "icao_code": "KTEB",
                                "municipality": "Teterboro",
                                "iso_country": "US",
                                "iso_region": "US-NJ",
                                "type": "medium_airport",
                                "latitude_deg": 40.8501,
                                "longitude_deg": -74.0608,
                                "slug": "teterboro-airport",
                                "country": {"code": "US", "name": "United States"},
                                "region": {"code": "US-NJ", "name": "New Jersey"}
                            }
                        ]
                    }
                }
            }
        },
    },
    500: {
        "description": "Server error",
        "content": {"application/json": {"example": {"detail": "Failed to generate combined data"}}},
    },
    503: {
        "description": "Service unavailable: dataset not ready",
        "content": {"application/json": {"example": {"detail": "Dataset not ready: <reason>"}}},
    },
})
async def get_airporsts_informations(
    response: Response,
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        description="Limit number of airports returned to reduce payload size",
    ),
    page: int = Query(1, ge=1, description="Page number for pagination (1-based)"),
    page_size: Optional[int] = Query(default=None, ge=1, alias="size", description="Page size for pagination; when provided, 'limit' is ignored and pagination headers are set"),
    iata: Optional[str] = Query(default=None, description="Filter by IATA code (e.g., JFK)"),
    icao: Optional[str] = Query(default=None, description="Filter by ICAO code (e.g., KJFK)"),
    municipality: Optional[str] = Query(default=None, description="Filter by municipality (city/town)"),
    country_name: Optional[str] = Query(default=None, description="Filter by country name (e.g., United States)"),
    region_name: Optional[str] = Query(default=None, description="Filter by region name (e.g., New York)"),
    iso_country: Optional[str] = Query(default=None, description="Filter by ISO country code (e.g., US)"),
    iso_region: Optional[str] = Query(default=None, description="Filter by ISO region code (e.g., US-NY)"),
    airport_type: Optional[str] = Query(default=None, alias="type", description="Filter by airport type (e.g., large_airport, small_airport, heliport)"),
    q: Optional[str] = Query(default=None, description="Unified search across name, codes, municipality, and country/region"),
) -> List[dict[str, Any]]:
    """Run the combine_data script logic and return the JSON array.

    Reads CSVs from impoted_data/ and returns the combined airports with nested
    country, region, and comments.

    Filters:
    - iata: IATA code
    - icao: ICAO code
    - municipality: case-insensitive exact match
    - country_name: nested country.name, case-insensitive exact match
    - region_name: nested region.name, case-insensitive exact match
    - iso_country: ISO country code
    - iso_region: ISO region code
    - type: airport type

    Limit is applied after filtering.
    """
    try:
        # Query from SQLite with filters and pagination
        has_pagination = page_size is not None
        # Default to 50 results when not paginating and no explicit limit provided
        effective_limit = None if has_pagination else (limit if limit is not None else 50)
        conn = get_connection()
        items, total = query_airports(
            conn,
            iata=iata,
            icao=icao,
            municipality=municipality,
            country_name=country_name,
            region_name=region_name,
            iso_country=iso_country,
            iso_region=iso_region,
            airport_type=airport_type,
            q=q,
            limit=effective_limit,
            page=page if has_pagination else None,
            page_size=page_size,
        )
        if has_pagination:
            total_val = total or 0
            size = page_size or 1
            total_pages = (total_val + size - 1) // size if size > 0 else 0
            response.headers["X-Total-Count"] = str(total_val)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(size)
            response.headers["X-Total-Pages"] = str(total_pages)
            return items  # type: ignore[return-value]
        else:
            return items  # type: ignore[return-value]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Dataset not ready: {exc}")
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception(
            "Failed to generate combined data: %s", exc
        )
        raise HTTPException(status_code=500, detail="Failed to generate combined data")


@router.get("/airports/{slug}", summary="Airport details by slug", responses={
    200: {
        "description": "Airport details",
        "content": {
            "application/json": {
                "examples": {
                    "sample": {
                        "summary": "Example airport",
                        "value": {
                            "id": 3797,
                            "ident": "KJFK",
                            "name": "John F Kennedy International Airport",
                            "iata_code": "JFK",
                            "icao_code": "KJFK",
                            "municipality": "New York",
                            "iso_country": "US",
                            "iso_region": "US-NY",
                            "type": "large_airport",
                            "latitude_deg": 40.6413,
                            "longitude_deg": -73.7781,
                            "elevation_ft": 13,
                            "slug": "john-f-kennedy-international-airport",
                            "country": {"code": "US", "name": "United States"},
                            "region": {"code": "US-NY", "name": "New York"}
                        }
                    }
                }
            }
        },
    },
    404: {
        "description": "Not found",
        "content": {"application/json": {"example": {"detail": "Airport not found"}}},
    },
    500: {
        "description": "Server error",
        "content": {"application/json": {"example": {"detail": "Failed to get airport details"}}},
    },
    503: {
        "description": "Service unavailable: dataset not ready",
        "content": {"application/json": {"example": {"detail": "Dataset not ready: <reason>"}}},
    },
})
async def get_airport_details(slug: str) -> dict[str, Any]:
    try:
        conn = get_connection()
        target = get_airport_by_slug(conn, slug)
        if target is None:
            raise HTTPException(status_code=404, detail="Airport not found")
        return target  # type: ignore[return-value]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Dataset not ready: {exc}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception(
            "Failed to get airport details: %s", exc
        )
        raise HTTPException(status_code=500, detail="Failed to get airport details")


__all__ = ["router", "get_airporsts_informations", "get_airport_details"]
