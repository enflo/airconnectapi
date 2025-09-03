
from contextlib import asynccontextmanager
from typing import AsyncIterator
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.rate_limit import RateLimiterMiddleware

from app.api.system import router as system_router
from app.api.public import router as public_router
from app.api.api import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.models.db import populate_db_from_files


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    # Initialize and populate SQLite database from local data files (idempotent)
    try:
        inserted, total = populate_db_from_files(Path("impoted_data"))
        logging.getLogger(__name__).info(
            "SQLite dataset ready: %s inserted, %s total", inserted, total
        )
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Failed to prepare SQLite DB: %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None)

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    try:
        from fastapi.staticfiles import StaticFiles
        app_dir = Path(__file__).resolve().parent
        # Prefer app/static; fallback to repo_root/static if present
        candidates = [app_dir / "static", app_dir.parent / "static"]
        static_dir = next((p for p in candidates if p.exists()), candidates[0])
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception:
        # If StaticFiles is unavailable, skip mounting; templates can still work with external assets
        pass

    # Rate limiting middleware (applies to /api by default)
    application.add_middleware(
        RateLimiterMiddleware,
        enabled=settings.rate_limit_enabled,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        scope_prefix=settings.rate_limit_scope,
        header_client_ip=settings.rate_limit_client_ip_header or None,
    )

    # Routers
    application.include_router(system_router)
    application.include_router(public_router)
    application.include_router(api_router)

    # 404 handler: HTML page for non-API paths, JSON for API paths
    async def not_found_handler(request: Request, exc: StarletteHTTPException):  # type: ignore[override]
        if exc.status_code != 404:
            # Fallback: default JSON for non-404 if registered here inadvertently
            return JSONResponse({"detail": exc.detail or "Error"}, status_code=exc.status_code)
        path = request.url.path or ""
        if path.startswith("/api"):
            return JSONResponse({"detail": exc.detail or "Not Found"}, status_code=404)
        try:
            # Prefer Jinja2Templates from public module when available
            from app.api.public import templates as _templates, _has_jinja, _render_without_jinja  # type: ignore
            if _has_jinja and _templates is not None:
                return _templates.TemplateResponse("404.html", {"request": request}, status_code=404)
            html = _render_without_jinja("404.html")
            return Response(content=html, media_type="text/html", status_code=404)
        except Exception:
            # Very minimal fallback HTML
            html = """<!doctype html><html><head><title>404 Not Found</title></head><body><h1>404 - Page not found</h1><p>The requested page could not be found.</p><p><a href='/'>Go back home</a></p></body></html>"""
            return Response(content=html, media_type="text/html", status_code=404)

    # Register only for 404 status code
    application.add_exception_handler(404, not_found_handler)

    return application


app = create_app()

__all__ = ["app", "create_app"]
