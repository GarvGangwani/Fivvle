#!/bin/sh
# Railway / container entrypoint — logs to stderr so deploy logs show startup.
set -eu

PORT="${PORT:-8080}"

# Materialize Firebase credentials when provided as a secret env var (Railway).
# Supports FIREBASE_SERVICE_ACCOUNT_PATH=/tmp/firebase-sa.json from older setups.
if [ -n "${FIREBASE_SERVICE_ACCOUNT_JSON:-}" ]; then
  python -c "
import os, pathlib
raw = os.environ['FIREBASE_SERVICE_ACCOUNT_JSON']
path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', '/tmp/firebase-sa.json')
dest = pathlib.Path(path)
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(raw, encoding='utf-8')
"
  echo "[fivvle] firebase credentials written to ${FIREBASE_SERVICE_ACCOUNT_PATH:-/tmp/firebase-sa.json}" >&2
fi

echo "[fivvle] starting gunicorn on 0.0.0.0:${PORT}" >&2

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT}" \
  --workers 1 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
