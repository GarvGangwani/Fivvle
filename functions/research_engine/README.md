# research_engine Cloud Function

HTTP-triggered receiver for the research pipeline. Per ADR 0020.

## Local layout

- `main.py` — the handler.
- `requirements.txt` — pip deps (mirrors `backend/pyproject.toml`).
- `app/` — **NOT in git**. Populated at deploy time by the deploy script, which rsyncs `backend/app/` here so `main.py` can import from `app.services...`.

## Deploy

See `docs/runbooks/research-engine-cloud-function.md`.

Summary of required `gcloud functions deploy` flags:

- `--gen2 --runtime=python311 --trigger-http`
- `--no-allow-unauthenticated` (IAM enforces OIDC)
- `--no-cpu-throttling` (background thread runs after 202)
- `--timeout=540s` `--memory=1Gi`
- `--source=functions/research_engine`
- `--entry-point=research_engine_handler`
- `--set-env-vars` / `--set-secrets` for DB, LLM keys, Firebase
