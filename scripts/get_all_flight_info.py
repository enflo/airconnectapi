#!/usr/bin/env python3
"""
All-in-one helper to obtain flight-related data for this project:
  1) Download OurAirports/OpenFlights datasets into a local directory
  2) Scrape airport routes from flightsfrom.com into airline_routes.json
  3) Combine OurAirports CSVs into a single JSON (airports_combined.json)

Notes:
- The scraping step writes airline_routes.json into the chosen output directory.
- The combining step is implemented inline in this script and writes
  airports_combined.json next to the downloaded CSV files.
"""
import argparse
import csv
import json
import logging
import subprocess
import sys
from pathlib import Path

from typing import Iterable, List, Optional, Dict, Any
from urllib.parse import urlparse

import httpx

# Embedded downloader logic (moved from scripts/download_data.py)
# List of URLs to download
URLS: List[str] = [
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/runways.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airport-comments.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airport-frequencies.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/regions.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/navaids.csv",
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/countries.csv",
    "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat",
    "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
]


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or "downloaded_file"


def download_file(
    client: httpx.Client,
    url: str,
    dest: Path,
    force: bool = False,
    retries: int = 3,
) -> None:
    if dest.exists() and not force:
        logging.info("Skipping existing file: %s", dest)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_dest = dest.with_suffix(dest.suffix + ".part")

    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with open(temp_dest, "wb") as f:
                    for chunk in response.iter_bytes():
                        if chunk:
                            f.write(chunk)
            temp_dest.replace(dest)
            logging.info("Downloaded: %s -> %s", url, dest)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logging.warning(
                "Attempt %d/%d failed for %s: %s", attempt, retries, url, exc
            )
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass

    assert last_error is not None
    raise last_error


def download_all(urls: Iterable[str], output_dir: Path, force: bool = False) -> None:
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    headers = {"User-Agent": "openflight-downloader/1.0"}

    with httpx.Client(timeout=timeout, limits=limits, headers=headers) as client:
        for url in urls:
            filename = filename_from_url(url)
            dest = output_dir / filename
            download_file(client, url, dest, force=force)


def configure_logging() -> None:
    # Ensure logging is configured once
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    # Keep INFO as default
    logging.getLogger(__name__).setLevel(logging.INFO)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_scraper(output_dir: Path) -> None:
    """Run the flightsfrom.com scraper so it writes to output_dir.

    The scraper script writes airline_routes.json to the current working directory,
    so we set cwd=output_dir.
    """
    script = project_root() / "scripts" / "scrape_airport_routes.py"
    if not script.exists():
        logging.warning("Scraper script not found: %s", script)
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info("Scraping airline routes into: %s/airline_routes.json", output_dir)
    try:
        subprocess.run([sys.executable, str(script)], check=True, cwd=str(output_dir))
        logging.info("Scraping completed.")
    except subprocess.CalledProcessError as exc:
        logging.warning("Scraper failed (non-zero exit code): %s", exc)
    except FileNotFoundError as exc:
        logging.warning("Python executable or script not found: %s", exc)


def run_combine(input_dir: Path, output_file: Path | None = None, indent: int | None = 2) -> None:
    """Combine OurAirports CSVs into a single JSON file (inline implementation).

    Input directory is expected to contain at least airports.csv. If countries.csv,
    regions.csv, and airport-comments.csv are present, they are used to enrich
    each airport with nested country/region objects and a comments list.
    """

    def _safe_int(v: Any) -> Optional[int]:
        try:
            if v is None:
                return None
            s = str(v).strip()
            if s == "":
                return None
            return int(float(s))  # handle values like '123.0'
        except Exception:
            return None

    def _safe_float(v: Any) -> Optional[float]:
        try:
            if v is None:
                return None
            s = str(v).strip()
            if s == "":
                return None
            return float(s)
        except Exception:
            return None

    def _read_csv(path: Path) -> Iterable[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize whitespace
                yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    if output_file is None:
        output_file = input_dir / "airports_combined.json"

    airports_path = input_dir / "airports.csv"
    countries_path = input_dir / "countries.csv"
    regions_path = input_dir / "regions.csv"
    comments_path = input_dir / "airport-comments.csv"

    if not airports_path.exists():
        logging.warning("airports.csv not found in %s; skipping combine.", input_dir)
        return

    # Load reference data (optional)
    countries_by_code: Dict[str, Dict[str, Any]] = {}
    if countries_path.exists():
        try:
            for c in _read_csv(countries_path):
                code = (c.get("code") or "").strip()
                if code:
                    countries_by_code[code] = {"code": code, "name": c.get("name")}
        except Exception as exc:
            logging.warning("Failed to read countries.csv: %s", exc)

    regions_by_code: Dict[str, Dict[str, Any]] = {}
    if regions_path.exists():
        try:
            for r in _read_csv(regions_path):
                code = (r.get("code") or "").strip()
                if code:
                    regions_by_code[code] = {"code": code, "name": r.get("name")}
        except Exception as exc:
            logging.warning("Failed to read regions.csv: %s", exc)

    comments_by_ident: Dict[str, List[Dict[str, Any]]] = {}
    comments_by_ref: Dict[str, List[Dict[str, Any]]] = {}
    if comments_path.exists():
        try:
            for cm in _read_csv(comments_path):
                ident = (cm.get("airport_ident") or "").strip()
                ref = (cm.get("airport_ref") or "").strip()
                if ident:
                    comments_by_ident.setdefault(ident, []).append(cm)
                if ref:
                    comments_by_ref.setdefault(ref, []).append(cm)
        except Exception as exc:
            logging.warning("Failed to read airport-comments.csv: %s", exc)

    # Build combined list
    combined: List[Dict[str, Any]] = []
    total = 0
    with open(airports_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            try:
                aid = _safe_int(row.get("id"))
                ident = (row.get("ident") or "").strip()
                iso_country = (row.get("iso_country") or "").strip()
                iso_region = (row.get("iso_region") or "").strip()

                a: Dict[str, Any] = {
                    "id": aid,
                    "ident": ident or None,
                    "type": (row.get("type") or "").strip() or None,
                    "name": (row.get("name") or "").strip() or None,
                    "latitude_deg": _safe_float(row.get("latitude_deg")),
                    "longitude_deg": _safe_float(row.get("longitude_deg")),
                    "elevation_ft": _safe_int(row.get("elevation_ft")),
                    "continent": (row.get("continent") or "").strip() or None,
                    "iso_country": iso_country or None,
                    "iso_region": iso_region or None,
                    "municipality": (row.get("municipality") or "").strip() or None,
                    "gps_code": (row.get("gps_code") or "").strip() or None,
                    "iata_code": (row.get("iata_code") or "").strip() or None,
                    "icao_code": (row.get("icao_code") or "").strip() or None,
                    "local_code": (row.get("local_code") or "").strip() or None,
                    "home_link": (row.get("home_link") or "").strip() or None,
                    "wikipedia_link": (row.get("wikipedia_link") or "").strip() or None,
                    "keywords": (row.get("keywords") or "").strip() or None,
                }

                # Attach country/region metadata if available
                if iso_country and iso_country in countries_by_code:
                    a["country"] = countries_by_code[iso_country]
                if iso_region and iso_region in regions_by_code:
                    a["region"] = regions_by_code[iso_region]

                # Attach comments (by ident and by ref)
                comments: List[Dict[str, Any]] = []
                if ident:
                    comments.extend(comments_by_ident.get(ident, []))
                if aid is not None:
                    comments.extend(comments_by_ref.get(str(aid), []))
                if comments:
                    a["comments"] = comments
                else:
                    a["comments"] = []

                combined.append(a)
            except Exception as exc:  # best-effort; skip bad rows
                logging.warning("Skipping airport row due to error: %s", exc)
                continue

    # Write output
    try:
        indent_val = None if indent in (None, 0) else indent
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=indent_val)
        logging.info(
            "Combined %d airports into %s (countries=%d, regions=%d, comments_by_ident=%d, comments_by_ref=%d)",
            len(combined),
            output_file,
            len(countries_by_code),
            len(regions_by_code),
            len(comments_by_ident),
            len(comments_by_ref),
        )
    except Exception as exc:
        logging.warning("Failed to write combined JSON: %s", exc)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Obtain all flight information (download + scrape + combine)")
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=project_root() / "impoted_data",
        help="Output directory for downloaded/scraped files (default: impoted_data at project root)",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Re-download files even if they already exist",
    )
    p.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping airline routes",
    )
    p.add_argument(
        "--skip-combine",
        action="store_true",
        help="Skip combining CSVs into airports_combined.json",
    )
    return p.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    out_dir: Path = args.output
    force: bool = args.force

    logging.info("Starting dataset download to: %s", out_dir)
    download_all(URLS, output_dir=out_dir, force=force)
    logging.info("Downloads completed.")

    if not args.skip_scrape:
        run_scraper(out_dir)
    else:
        logging.info("Skipping scrape step as requested.")

    if not args.skip_combine:
        run_combine(out_dir)
    else:
        logging.info("Skipping combine step as requested.")

    logging.info("All steps finished.")


if __name__ == "__main__":
    main()
