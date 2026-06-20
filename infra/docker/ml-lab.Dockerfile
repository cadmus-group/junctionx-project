# GridTrace ML lab image (training, evaluation, explainability CLI)
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/domain-py/pyproject.toml packages/domain-py/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY apps/ml-lab/pyproject.toml apps/ml-lab/pyproject.toml

RUN uv sync --package gridtrace-ml-lab --no-install-project --no-dev

COPY packages/domain-py packages/domain-py
COPY apps/api apps/api
COPY apps/worker apps/worker
COPY apps/ml-lab apps/ml-lab
COPY data/fixtures data/fixtures

RUN uv sync --package gridtrace-ml-lab --no-dev

ENTRYPOINT ["uv", "run", "--package", "gridtrace-ml-lab", "gridtrace-ml"]
CMD ["--help"]
