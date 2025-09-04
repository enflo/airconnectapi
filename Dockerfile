# Multi-stage Dockerfile for Airconnect API

# 1) Base image with Python
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (curl for healthchecks, build-essential for any wheels if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Builder stage to install dependencies separately to leverage cache
FROM base AS builder
# Copy only dependency manifests for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# 3) Final runtime image
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_NAME="AriConnect" \
    ENVIRONMENT="production" \
    ALLOWED_ORIGINS="*" \
    RATE_LIMIT_ENABLED="1" \
    RATE_LIMIT_REQUESTS="120" \
    RATE_LIMIT_WINDOW_SECONDS="60" \
    RATE_LIMIT_SCOPE="/api"

WORKDIR /app

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application source
COPY app ./app
COPY main.py ./
COPY pyproject.toml ./
COPY README.md ./
# Data and imported dataset directories
COPY impoted_data ./impoted_data
# Ensure data dir exists and is writeable
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Healthcheck: hit the system health endpoint if available
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Default command: run uvicorn pointing to main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
