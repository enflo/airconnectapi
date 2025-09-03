
import os
from functools import lru_cache
from typing import List


class Settings:
    """Simple settings loader using environment variables.

    Avoids extra dependencies (pydantic-settings) and keeps configuration centralized.
    """

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AriConnect")
        self.environment: str = os.getenv("ENVIRONMENT", "production")
        # Comma-separated list or '*' to allow all
        self.allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
        # Rate limiting settings
        self.rate_limit_enabled: bool = str(os.getenv("RATE_LIMIT_ENABLED", "1")).strip().lower() in {"1", "true", "yes", "on"}
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
        self.rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.rate_limit_scope: str = os.getenv("RATE_LIMIT_SCOPE", "/api")
        # Optional header name to extract client IP (e.g., X-Forwarded-For)
        self.rate_limit_client_ip_header: str = os.getenv("RATE_LIMIT_CLIENT_IP_HEADER", "")

    @property
    def allowed_origins_list(self) -> List[str]:
        val = (self.allowed_origins or "").strip()
        if val in {"", "*"}:
            return ["*"]
        return [o.strip() for o in val.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
