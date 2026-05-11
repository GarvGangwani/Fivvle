# syntax=docker/dockerfile:1
# After `uv lock` is committed, switch the RUN line to always use:
#   uv sync --frozen --no-dev
# and keep `COPY uv.lock ./` (remove the conditional).
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.13 /uv /usr/local/bin/uv

COPY pyproject.toml ./

# `uv.lock` is committed per project policy; until it exists locally, build without --frozen.
COPY uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

COPY app/ ./app/

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} --workers 2 --timeout 120 --access-logfile - --error-logfile -"]
