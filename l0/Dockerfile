# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.10.9 AS uv

FROM python:3.14-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential clang && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /project
ENV UV_LINK_MODE=copy

# Deps layer (only rebuilds when lock/pyproject changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group dev --group docs

# Source layer
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group dev --group docs

CMD ["make", "help"]
