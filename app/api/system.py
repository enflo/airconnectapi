from fastapi import APIRouter

from app.models.common import Health

router = APIRouter()


@router.get("/health", response_model=Health, include_in_schema=False)
async def health() -> Health:
    """Lightweight health check endpoint for container orchestration."""
    return {"status": "ok"}


__all__ = ["router"]
