# docker/Dockerfile
# Base stage with common dependencies
FROM python:3.11-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Development stage
FROM base AS dev
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production builder stage
FROM base AS builder
RUN uv sync --frozen --no-dev

# Production stage with distroless-like slim base
FROM python:3.11-slim AS prod

# Security labels for image scanning and metadata
LABEL org.opencontainers.image.title="agent-service" \
      org.opencontainers.image.description="Production-ready AI Agent Service API" \
      org.opencontainers.image.vendor="Your Organization" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/yourorg/agent-service" \
      org.opencontainers.image.licenses="MIT" \
      security.scan.enabled="true" \
      security.scan.level="production"

WORKDIR /app

# Install only runtime dependencies (curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY src/ src/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user with specific UID/GID
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /bin/false -d /app appuser && \
    chown -R appuser:appuser /app

USER appuser

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
