# GridTrace API image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy workspace manifests first for better layer caching.
COPY pyproject.toml uv.lock* ./
COPY packages/domain-py/pyproject.toml packages/domain-py/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY apps/ml-lab/pyproject.toml apps/ml-lab/pyproject.toml

RUN uv sync --package gridtrace-api --no-install-project --no-dev || true

COPY packages/domain-py packages/domain-py
COPY apps/api apps/api

RUN uv sync --package gridtrace-api --no-dev

EXPOSE 8000
CMD ["uv", "run", "--package", "gridtrace-api", "uvicorn", "gridtrace_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
