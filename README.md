# Airconnect API

A simple, open project exploring airport data. We combine public datasets into a fast, searchable experience with a small, focused FastAPI app and a clean JSON API.

- Simplicity: a small codebase that’s easy to read, run, and extend.
- Openness: open source, open data, transparent architecture.
- Practicality: rational defaults, fast responses, useful endpoints with filters and pagination.

## What it is
Airconnect API ingests public CSV and JSON sources (OurAirports, OpenFlights samples) and exposes:

- A lightweight website to browse airports and view them on a map.
- A JSON API with filtering and pagination headers for easy client consumption.
- A file-based SQLite database prepared at startup from impoted_data/ (idempotent).

Data sources:
- OurAirports CSV datasets (airports, countries, regions, comments): https://ourairports.com/data/
- OpenFlights sample airline/route information: https://openflights.org/data.html
- airline-route-data project (compiled route samples): https://github.com/Jonty/airline-route-data

## Quick start

Prerequisites: Python 3.8+ (tested on 3.12). macOS/Linux recommended.

1) Create and activate a virtualenv
- python -m venv .venv && source .venv/bin/activate

2) Install dependencies
- Recommended for contributors (dev extras): pip install -e .[dev]
- Runtime-only alternative: pip install -r requirements.txt

3) Run the app
- uvicorn main:app --reload

Open https://airconnectapi.com/.

Notes
- Static files are under app/static and mounted at /static.
- CORS and rate-limiting are configured via environment variables (see Settings below).
- The SQLite DB is stored at data/airconnectapi.db and is populated at startup from impoted_data/.

## API overview

Routers
- Public site: HTML pages under /
- System: health/system endpoints
- Data API: under /api (airports, etc.)

Pagination headers on list endpoints
- X-Total-Count, X-Page, X-Page-Size, X-Total-Pages

Filtering
- Case-insensitive filters as used in tests (see tests/test_filters.py).

Run example
- curl 'https://airconnectapi.com/api/airports?page=1&page_size=20&country=us'

## Settings (env variables)

- APP_NAME: default "AriConnect" — FastAPI title.
- ENVIRONMENT: default "production".
- ALLOWED_ORIGINS: CSV or * for CORS. Default *.
- RATE_LIMIT_ENABLED: 1/true/yes/on to enable rate limiting. Default 1.
- RATE_LIMIT_REQUESTS: integer; default 120.
- RATE_LIMIT_WINDOW_SECONDS: integer; default 60.
- RATE_LIMIT_SCOPE: path prefix to apply rate limiting; default /api.
- RATE_LIMIT_CLIENT_IP_HEADER: optional header to trust for client IP (e.g., X-Forwarded-For).

Example
- RATE_LIMIT_ENABLED=0 ALLOWED_ORIGINS=http://localhost:5173 uvicorn main:app --reload

## Tests

- Install dev deps: pip install -e .[dev]
- Run all tests: pytest
- Useful: pytest tests/test_pagination.py::test_pagination_pages_disjoint -q

Troubleshooting
- If rate limiting causes 429s during tests, set RATE_LIMIT_ENABLED=0.
- If SQLite file is locked, ensure no parallel processes use data/airconnectapi.db.

## Project structure

- main.py: compatibility wrapper exporting app and create_app from app.main
- app/main.py: app factory, middleware, routers, lifespan setup
- app/api/system.py: health/system endpoints
- app/api/public.py: public routes and templates
- app/api/api.py: data API endpoints (filters/pagination)
- app/core/config.py: env-driven settings
- app/core/rate_limit.py: lightweight rate limiting middleware
- app/core/logging.py: logging configuration
- app/models/db.py: SQLite + populate_db_from_files reading from impoted_data/
- app/templates: Jinja2 templates for site and API pages

## Contributing

- Fork the repo, create a feature branch, run tests, and open a PR.
- Code style: Black, isort, Ruff, mypy. See pyproject.toml for settings.

Quick checks
- ruff check .
- black --check .
- isort --check-only .
- mypy .

## License
MIT — see LICENSE.

## Acknowledgments
- FastAPI — framework
- Uvicorn — ASGI server
- Pydantic — data validation
- OurAirports/OpenFlights — datasets

## Docker

Build the image:
- docker build -t airconnectapi .

Run the container:
- docker run -p 8000:8000 \
  -e ALLOWED_ORIGINS=* \
  -e RATE_LIMIT_ENABLED=1 \
  -v $(pwd)/data:/app/data \
  --name airconnectapi \
  airconnectapi

Compose (recommended for local dev):
- docker compose up --build

After start, browse:
- http://127.0.0.1:8000/

Notes:
- The container initializes a SQLite database at /app/data/airconnectapi.db from /app/impoted_data at startup.
- Environment variables control CORS and rate limiting; see Settings above.
- To inject your own dataset files, bind-mount ./impoted_data read-only to /app/impoted_data.

## Ubuntu deployment (systemd + Nginx)

The repository includes production-ready deployment assets under deploy/:
- deploy/ubuntu-deploy.sh: idempotent installer that sets up Python venv, systemd service, and Nginx reverse proxy.
- deploy/openflight.service: example systemd unit (for Airconnect API).
- deploy/openflight.nginx.conf: example Nginx site configuration (for Airconnect API).

Quick start on a fresh Ubuntu host (run as root):
- apt update && apt install -y git
- git clone <this-repo> /opt/airconnectapi-src && cd /opt/airconnectapi-src
- bash deploy/ubuntu-deploy.sh

What the script does:
- Creates a system user airconnectapi and installs the app under /opt/airconnectapi
- Creates a Python venv at /opt/airconnectapi/.venv and installs dependencies
- Installs a systemd unit airconnectapi.service that runs uvicorn main:app on 127.0.0.1:8000
- Installs Nginx reverse proxy serving / and static files from /opt/airconnectapi/app/static at /static
- Creates /etc/default/airconnectapi for environment variables (e.g., RATE_LIMIT_ENABLED=0)

Managing the service:
- systemctl status airconnectapi
- systemctl restart airconnectapi
- journalctl -u airconnectapi -f

TLS/HTTPS:
- For HTTPS, install certbot and adjust Nginx server block or use a reverse proxy/Load Balancer.
- Example: apt install -y certbot python3-certbot-nginx && certbot --nginx
