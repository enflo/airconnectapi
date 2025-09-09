
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple, Dict

try:
    # Reuse the data combining logic from the domain module
    from app.domain.combine_data import combine  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    def combine(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("combine_data module is unavailable")

# -----------------------------
# Slug helpers (copied to avoid circular imports)
# -----------------------------

def slugify(text: Optional[str], fallback: Optional[str] = None) -> str:
    if not text or not isinstance(text, str):
        return (fallback or "").strip().lower()
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm)
    norm = re.sub(r"-+", "-", norm).strip("-")
    if not norm and fallback:
        return fallback.strip().lower()
    return norm


def airport_slug(a: Dict[str, Any]) -> str:
    name = a.get("name")
    ident = a.get("ident") or a.get("icao_code") or a.get("iata_code")
    fid = str(a.get("id")) if a.get("id") is not None else None
    slug = slugify(name, fallback=ident or fid or "")
    return slug

# -----------------------------
# SQLite helpers
# -----------------------------


def get_db_path() -> Path:
    env = os.getenv("DB_PATH")
    if env:
        return Path(env)
    return Path("data") / "openflight.db"


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Enable WAL for better concurrency (best-effort)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS airports (
            slug TEXT PRIMARY KEY,
            id INTEGER,
            ident TEXT,
            iata_code TEXT,
            icao_code TEXT,
            municipality TEXT,
            iso_country TEXT,
            iso_region TEXT,
            type TEXT,
            country_name TEXT,
            region_name TEXT,
            data TEXT NOT NULL
        );
        """
    )
    # Helpful indexes for filters
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_icao ON airports(icao_code);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_muni ON airports(municipality);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_iso_country ON airports(iso_country);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_iso_region ON airports(iso_region);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_type ON airports(type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_country_name ON airports(country_name);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_region_name ON airports(region_name);")
    conn.commit()


def db_has_data(conn: sqlite3.Connection) -> bool:
    cur = conn.execute("SELECT COUNT(1) AS c FROM airports;")
    row = cur.fetchone()
    return bool(row and int(row[0]) > 0)


def upsert_airports(conn: sqlite3.Connection, airports: Iterable[Dict[str, Any]]) -> int:
    sql = (
        "INSERT OR REPLACE INTO airports (slug, id, ident, iata_code, icao_code, municipality, iso_country, iso_region, type, country_name, region_name, data) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    count = 0
    with conn:
        for a in airports:
            # ensure slug present
            if not a.get("slug"):
                a["slug"] = airport_slug(a)
            country = a.get("country") or {}
            region = a.get("region") or {}
            params = (
                a.get("slug"),
                a.get("id"),
                a.get("ident"),
                a.get("iata_code"),
                a.get("icao_code"),
                a.get("municipality"),
                a.get("iso_country"),
                a.get("iso_region"),
                a.get("type"),
                country.get("name"),
                region.get("name"),
                json.dumps(a, ensure_ascii=False),
            )
            conn.execute(sql, params)
            count += 1
    return count


def populate_db_from_files(input_dir: Path) -> Tuple[int, int]:
    """Load data via combine() and populate the SQLite DB if needed.

    Returns a tuple (inserted, total).
    """
    conn = get_connection()
    init_db(conn)
    if db_has_data(conn):
        cur = conn.execute("SELECT COUNT(1) FROM airports;")
        total = int(cur.fetchone()[0])
        return 0, total
    # Build dataset
    try:
        data = combine(input_dir, limit=None)  # type: ignore[misc]
    except Exception:
        # Fallback: load precombined JSON if available
        combined_path = input_dir / "airports_combined.json"
        if not combined_path.exists():
            raise FileNotFoundError(f"Missing combined dataset: {combined_path}")
        with combined_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    # Ensure slugs present and insert
    inserted = upsert_airports(conn, data)
    return inserted, len(data)


def query_airports(
    conn: sqlite3.Connection,
    *,
    iata: Optional[str] = None,
    icao: Optional[str] = None,
    municipality: Optional[str] = None,
    country_name: Optional[str] = None,
    region_name: Optional[str] = None,
    iso_country: Optional[str] = None,
    iso_region: Optional[str] = None,
    airport_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Query airports as list of dicts. Returns (items, total_count_for_pagination).

    When page_size is provided, total_count is returned; otherwise it's None.
    """
    # Ensure DB schema and data are present even if lifespan didn't run
    init_db(conn)
    try:
        if not db_has_data(conn):
            populate_db_from_files(Path("impoted_data"))
    except Exception:
        # If population fails, proceed; API will 503/500 appropriately later
        pass

    conditions = []
    params: List[Any] = []

    def add_eq(field: str, value: Optional[str]) -> None:
        if value is not None:
            conditions.append(f"LOWER({field}) = LOWER(?)")
            params.append(value)

    # Exact-match filters
    add_eq("iata_code", iata)
    add_eq("icao_code", icao)
    add_eq("municipality", municipality)
    add_eq("iso_country", iso_country)
    add_eq("iso_region", iso_region)
    add_eq("country_name", country_name)
    add_eq("region_name", region_name)

    # Type filter; if unified 'other' is requested, map it to NOT IN common types
    if airport_type is not None and isinstance(airport_type, str) and airport_type.strip().lower() == "other":
        conditions.append("LOWER(type) NOT IN ('large_airport','medium_airport','small_airport')")
    else:
        add_eq("type", airport_type)

    # Unified q search across several columns (case-insensitive LIKE)
    if q is not None and isinstance(q, str) and q.strip() != "":
        like = f"%{q.strip().lower()}%"
        or_parts = [
            "LOWER(ident) LIKE ?",
            "LOWER(iata_code) LIKE ?",
            "LOWER(icao_code) LIKE ?",
            "LOWER(municipality) LIKE ?",
            "LOWER(iso_country) LIKE ?",
            "LOWER(country_name) LIKE ?",
            "LOWER(region_name) LIKE ?",
        ]
        conditions.append("(" + " OR ".join(or_parts) + ")")
        params.extend([like] * len(or_parts))

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total: Optional[int] = None
    if page_size is not None:
        cur = conn.execute(f"SELECT COUNT(1) FROM airports {where};", params)
        total = int(cur.fetchone()[0])

    # Order: prioritize large airports first, then medium, small, others; tie-breaker by ident
    order_clause = (
        " ORDER BY CASE LOWER(type) WHEN 'large_airport' THEN 0 "
        "WHEN 'medium_airport' THEN 1 WHEN 'small_airport' THEN 2 ELSE 3 END, "
        "LOWER(COALESCE(ident, ''))"
    )

    sql = f"SELECT data FROM airports {where}{order_clause}"
    if page_size is not None and page is not None:
        off = max(0, (page - 1) * page_size)
        sql += " LIMIT ? OFFSET ?"
        qparams = params + [page_size, off]
    elif limit is not None:
        sql += " LIMIT ?"
        qparams = params + [limit]
    else:
        qparams = params

    cur = conn.execute(sql, qparams)
    items = [json.loads(r[0]) for r in cur.fetchall()]
    return items, total


def get_airport_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Dict[str, Any]]:
    # Ensure DB exists and is populated for direct detail access
    init_db(conn)
    try:
        if not db_has_data(conn):
            populate_db_from_files(Path("impoted_data"))
    except Exception:
        pass
    cur = conn.execute("SELECT data FROM airports WHERE slug = ?", (slug,))
    row = cur.fetchone()
    return json.loads(row[0]) if row else None
