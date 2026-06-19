# GridTrace worker image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY packages/domain-py/pyproject.toml packages/domain-py/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY apps/ml-lab/pyproject.toml apps/ml-lab/pyproject.toml

RUN uv sync --package gridtrace-worker --no-install-project --no-dev || true

COPY packages/domain-py packages/domain-py
COPY apps/api apps/api
COPY apps/worker apps/worker

RUN uv sync --package gridtrace-worker --no-dev

CMD ["uv", "run", "--package", "gridtrace-worker", "python", "-m", "gridtrace_worker.main", "scheduler"]
