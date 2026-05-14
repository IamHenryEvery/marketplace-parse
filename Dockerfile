# Image used by parser workers and the scheduler.
# Heavy because it bundles Chromium (Playwright) + PyTorch + transformers.
# Source code is mounted as a volume in docker-compose, so most edits don't
# require rebuilding.

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    HF_HOME=/hf-cache

# uv (statically linked binary)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System libs Chromium needs at runtime. Installed manually instead of via
# `playwright install --with-deps` because the latter targets Ubuntu and breaks
# dpkg on Debian Bookworm (it ends up removing core packages like dash, after
# which /bin/sh disappears and any subsequent RUN fails).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates fonts-liberation \
        libnss3 libnspr4 libdbus-1-3 \
        libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
        libcups2 libdrm2 libxkbcommon0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libxcb1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: dependencies only — cached separately from source.
# README.md is referenced by pyproject.toml (readme = "README.md"); hatchling
# validates its presence whenever the project itself is installed, so it has
# to be in the build context before any layer that does that.
# --extra worker pulls playwright-stealth + torch + transformers; api extra is
# included so this image can also run uvicorn if needed.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --extra worker --extra api

# Layer 2: Playwright Chromium browser binary (system libs already installed).
# --no-sync prevents `uv run` from re-syncing/installing the project here:
# deps are already present from layer 1, and the project itself goes in layer 3.
RUN uv run --no-sync playwright install chromium

# Layer 3: project source — overlaid by a bind-mount in dev.
COPY marketplace_parse ./marketplace_parse
COPY alembic.ini ./
RUN uv sync --frozen --extra worker --extra api

# Default: yandex worker. Each compose service overrides this.
CMD ["python", "-m", "marketplace_parse.workers.parser", "--marketplace", "yandex_market"]
