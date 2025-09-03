OpenFlight – Project Development Guidelines

Audience: Advanced developers contributing to this repository.

This document outlines project-specific practices for building, configuring, testing, and extending the codebase.

1. Build and Configuration

1.1. Python and OS
- Python: 3.8+ (tested on 3.12). The project targets py38 as baseline for tooling.
- OS: macOS/Linux. SQLite DB is file-based in data/.

1.2. Environment Setup
- Recommended: Use a virtual environment.
  - python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

1.3. Installing Dependencies
There are two equivalent paths; pick one depending on your workflow:
- Using PEP 621/pyproject and dev extras (recommended for contributors):
  - pip install -e .[dev]
- Using requirements.txt (runtime-only):
  - pip install -r requirements.txt

Notes:
- Runtime deps are declared in pyproject.toml [project.dependencies]. Dev tooling and test deps are in [project.optional-dependencies].
- No database server is required. A SQLite file is populated at startup from impoted_data/.

1.4. Configuration via Environment Variables
Settings are maintained in app/core/config.py and loaded at runtime via get_settings(). Relevant env vars:
- APP_NAME: default "AriConnect". Used as FastAPI title.
- ENVIRONMENT: default "production".
- ALLOWED_ORIGINS: CSV or * for CORS. Default *.
- RATE_LIMIT_ENABLED: 1/true/yes/on to enable rate-limiting middleware. Default 1.
- RATE_LIMIT_REQUESTS: integer; default 120.
- RATE_LIMIT_WINDOW_SECONDS: integer; default 60.
- RATE_LIMIT_SCOPE: path prefix to apply rate limiting; default /api.
- RATE_LIMIT_CLIENT_IP_HEADER: optional header to trust for client IP (e.g., X-Forwarded-For).

1.5. Running the Application
- Local dev (auto-reload):
  - uvicorn main:app --reload
- The main module app/main.py builds the app with:
  - CORS middleware based on ALLOWED_ORIGINS
  - Static files mounted at /static from app/static
  - RateLimiterMiddleware (scoped to /api by default)
  - Routers: app.api.system, app.api.public, app.api.api
- On startup, populate_db_from_files(Path("impoted_data")) initializes the SQLite dataset. This is idempotent and logs inserted/total counts. The SQLite database is stored under data/openflight.db.

1.6. Static and Templates
- Jinja2 templates reside under app/templates. Public routes render HTML; API routes return JSON.
- A custom 404 handler returns HTML for non-/api paths and JSON for /api paths.

2. Testing

2.1. Framework and Configuration
- Tests use pytest with pytest-asyncio and FastAPI's TestClient.
- Pytest configuration (pyproject.toml [tool.pytest.ini_options]):
  - testpaths = ["tests"]
  - python_files = ["test_*.py", "*_test.py"]
  - python_classes = ["Test*"]
  - python_functions = ["test_*"]
  - addopts = -v --tb=short
  - asyncio_mode = auto

2.2. How to Run Tests
- Install dev dependencies first (see 1.3), then run:
  - pytest
- Common invocations:
  - Run a single file: pytest tests/test_filters.py -q
  - Run a specific test: pytest tests/test_pagination.py::test_pagination_pages_disjoint -q
  - Stop on first failure: pytest --maxfail=1 -q

2.3. Test Data and Determinism
- The app lazily populates the SQLite DB at startup from impoted_data/ (CSV/DAT/JSON). This ensures tests have a consistent dataset without network calls.
- Tests import from main import app to obtain the preconfigured FastAPI instance. The app lifespan handler automatically prepares the database when TestClient spins up the app for requests.

2.4. Example: Creating and Running a Simple Test
To add a minimal smoke test that validates the app object exposes routes:
- Create tests/test_smoke_example.py with:
  from main import app

  def test_smoke_app_routes_exist():
      assert app is not None
      assert hasattr(app, "routes")
      assert len(app.routes) > 0

- Run: pytest tests/test_smoke_example.py -q
- After verifying locally, remove the file if it was only for demonstration purposes.

2.5. Async Tests
- asyncio_mode is auto; you can mark async tests with @pytest.mark.asyncio when needed.
- Prefer TestClient for HTTP-level tests; for direct coroutine testing, ensure event loop handling aligns with pytest-asyncio best practices.

2.6. Troubleshooting Tests
- If you see rate limiting causing unexpected 429 responses during high-concurrency tests, temporarily disable via RATE_LIMIT_ENABLED=0.
- If templates produce DeprecationWarning from Starlette templating during tests, it's benign. The current code uses TemplateResponse(name, {"request": request}). Starlette recommends TemplateResponse(request, name). This does not affect behavior.
- If the DB file is locked on some systems, ensure no parallel processes are accessing data/openflight.db. The test suite runs serially by default; avoid -n auto without validating SQLite concurrency.

3. Development Conventions

3.1. Code Style and Linters
- Black (line length 88), isort (profile black), ruff (rules: E, F, W, I, UP, B, C4, SIM, RUF with some ignores), mypy (py38 baseline, tests/ excluded).
- Typical checks:
  - ruff check .
  - black --check .
  - isort --check-only .
  - mypy .

3.2. Project Structure
- Entry points:
  - main.py: compatibility wrapper exporting app and create_app from app.main.
  - app/main.py: app factory, middleware, routers, and lifespan setup.
- API and views:
  - app/api/system.py: health/system endpoints.
  - app/api/public.py: public site routes and templates.
  - app/api/api.py: data API endpoints (e.g., /api/airports) with filtering and pagination.
- Core:
  - app/core/config.py: env-driven settings.
  - app/core/rate_limit.py: lightweight rate limiting middleware.
  - app/core/logging.py: logging configuration for app startup.
- Data model and persistence:
  - app/models/db.py: SQLite integration and populate_db_from_files reading from impoted_data/.

3.3. API Testing Tips
- Use TestClient against main.app to leverage the full stack (lifespan, middleware, routers).
- For pagination, tests assert X-Total-Count, X-Page, X-Page-Size, X-Total-Pages headers. If you add new endpoints with pagination, maintain this header contract.
- Filters are case-insensitive in tests; normalize to lowercase when comparing.

3.4. Running the Server for Manual QA
- Example command with env overrides:
  - RATE_LIMIT_ENABLED=0 ALLOWED_ORIGINS=http://localhost:5173 uvicorn main:app --reload
- Browse http://127.0.0.1:8000/ for the HTML site; API docs route may be disabled (docs_url=None). Consider enabling docs locally if needed by adjusting app factory in a feature branch.

3.5. Data Lifecycle
- Dataset is populated from impoted_data/* files on each startup, idempotently. If you change the extractor/transformer, ensure it remains idempotent and compatible with existing tests. Keep data/openflight.db out of version control if you plan to regenerate it locally.

3.6. Common Pitfalls
- Import path: tests import from main, not app.main. Keep main.py exporting app and create_app.
- Static mounting: app/static must exist; fallbacks are handled, but missing assets can cause 404s in browser, not in tests.
- CORS: If integrating with a frontend during local dev, configure ALLOWED_ORIGINS accordingly.

4. Adding New Tests
- Place tests under tests/ and follow pytest discovery rules.
- Prefer black-box testing via HTTP requests to ensure middleware and headers are validated.
- If adding new API endpoints with filters or pagination, mirror the style used in tests/test_filters.py and tests/test_pagination.py.
- Keep tests deterministic; avoid network I/O. If you need fixtures, place them in tests/__init__.py or create tests/conftest.py.

5. Commands Quick Reference
- Setup: python -m venv .venv && source .venv/bin/activate; pip install -e .[dev]
- Run app: uvicorn main:app --reload
- Run tests: pytest
- Run a specific test: pytest tests/test_pagination.py::test_pagination_pages_disjoint -q
- Linters/formatters: ruff check .; black .; isort .; mypy .

Appendix: Verified Example Commands
The following were executed successfully during guideline preparation:
- pytest  # 20 tests passed on Python 3.12
- pytest tests/test_smoke_example.py -q  # simple demonstration test passed, then removed as it was only illustrative
