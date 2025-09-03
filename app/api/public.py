from pathlib import Path
from fastapi import APIRouter, Request, Response
from starlette.responses import PlainTextResponse
from datetime import datetime

from app.models.db import get_connection, get_airport_by_slug

router = APIRouter()

# Try to configure Jinja2 templates; gracefully fall back if jinja2 is unavailable
try:  # pragma: no cover - exercised in environments without Jinja2
    from starlette.templating import Jinja2Templates

    _templates_dir = Path(__file__).resolve().parents[1] / "templates"
    templates = Jinja2Templates(directory=str(_templates_dir))
    _has_jinja = True
except Exception:  # noqa: BLE001
    templates = None  # type: ignore[assignment]
    _templates_dir = Path(__file__).resolve().parents[1] / "templates"
    _has_jinja = False


def _render_without_jinja(template_name: str) -> str:
    # Minimal include replacement for our header and head includes
    html = (_templates_dir / template_name).read_text(encoding="utf-8")
    replacements = [
        ("{% include 'partials/header.html' %}", _templates_dir / "partials" / "header.html"),
        ("{% include 'partials/head.html' %}", _templates_dir / "partials" / "head.html"),
        ("{% include 'partials/footer.html' %}", _templates_dir / "partials" / "footer.html"),
    ]
    for token, path in replacements:
        if token in html:
            try:
                frag_html = path.read_text(encoding="utf-8")
            except Exception:
                frag_html = ""
            html = html.replace(token, frag_html)
    return html


@router.get("/", include_in_schema=False)
async def website(request: Request):
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("index.html", {"request": request})
    html = _render_without_jinja("index.html")
    return Response(content=html, media_type="text/html")


@router.get("/airports", include_in_schema=False)
async def airports_page(request: Request):
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("site.html", {"request": request})
    html = _render_without_jinja("site.html")
    return Response(content=html, media_type="text/html")


@router.get("/map", include_in_schema=False)
async def map_page(request: Request):
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("map.html", {"request": request})
    html = _render_without_jinja("map.html")
    return Response(content=html, media_type="text/html")


@router.get("/about", include_in_schema=False)
async def about_page(request: Request):
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("about.html", {"request": request})
    html = _render_without_jinja("about.html")
    return Response(content=html, media_type="text/html")


@router.get("/api-info", include_in_schema=False)
async def api_info_page(request: Request):
    ctx = {"request": request, "settings": None}
    try:
        from app.core.config import get_settings  # lazy import
        ctx["settings"] = get_settings()
    except Exception:
        pass
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("api.html", ctx)
    html = _render_without_jinja("api.html")
    return Response(content=html, media_type="text/html")


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt(request: Request):
    base = str(request.base_url).rstrip("/")
    body = f"""
User-agent: *
Allow: /
Sitemap: {base}/sitemap.xml
""".lstrip()
    return PlainTextResponse(content=body, media_type="text/plain; charset=utf-8")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request):
    base = str(request.base_url).rstrip("/")
    urls = ["/", "/airports", "/map", "/about", "/api-info"]
    # Try to include airport pages
    try:
        conn = get_connection()
        cur = conn.execute("SELECT slug FROM airports ORDER BY slug LIMIT 10000;")
        urls += [f"/airports/{row[0]}" for row in cur.fetchall() if row and row[0]]
    except Exception:
        pass
    now = datetime.utcnow().strftime("%Y-%m-%d")
    # Build XML
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in urls:
        loc = f"{base}{path}"
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f"    <lastmod>{now}</lastmod>")
        parts.append("    <changefreq>daily</changefreq>")
        parts.append("    <priority>0.7</priority>")
        parts.append("  </url>")
    parts.append("</urlset>")
    xml = "\n".join(parts)
    return Response(content=xml, media_type="application/xml")


@router.get("/airports/{slug}", include_in_schema=False)
async def airport_details_page(request: Request, slug: str):
    # Try to enrich with server-side airport data for SEO (JSON-LD, meta tags)
    airport = None
    try:
        conn = get_connection()
        airport = get_airport_by_slug(conn, slug)
    except Exception:
        airport = None
    if _has_jinja and templates is not None:
        return templates.TemplateResponse("airport.html", {"request": request, "slug": slug, "airport": airport})
    html = _render_without_jinja("airport.html")
    return Response(content=html, media_type="text/html")


__all__ = ["router"]
