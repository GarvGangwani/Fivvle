#!/bin/sh
# Railway / container entrypoint — logs to stderr so deploy logs show startup.
set -eu

PORT="${PORT:-8080}"
echo "[fivvle] starting gunicorn on 0.0.0.0:${PORT}" >&2

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT}" \
  --workers 1 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
