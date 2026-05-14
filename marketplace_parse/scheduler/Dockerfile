# Slim image for the APScheduler service. It only enqueues parse tasks via
# RabbitMQ on a cron, so it has no need for Chromium, Playwright, torch, or
# transformers. Pulls in only `--extra scheduler` (apscheduler) on top of the
# core deps (sqlalchemy, asyncpg, aio-pika, pydantic, alembic).

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Layer 1: dependencies only — cached separately from source.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra scheduler

# Layer 2: project source — overlaid by a bind-mount in dev.
COPY marketplace_parse ./marketplace_parse
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --extra scheduler

CMD ["python", "-m", "marketplace_parse.scheduler.runner"]
