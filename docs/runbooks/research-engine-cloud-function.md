# Runbook — research_engine Cloud Function

**Purpose:** Deploy and operate the research-engine Cloud Function that receives HTTP dispatches from the FastAPI backend per ADR 0020.

**Related:** ADR 0009 (pluggable dispatcher), ADR 0020 (Cloud Function HTTP dispatcher wiring).

---

## 1. Prerequisites

- gcloud CLI authenticated and pointed at the Fivvle GCP project: `gcloud config get-value project`.
- APIs enabled:
  ```
  gcloud services enable cloudfunctions.googleapis.com cloudbuild.googleapis.com run.googleapis.com secretmanager.googleapis.com
  ```
- Cloud SQL Postgres instance reachable from Cloud Functions (same VPC or via Cloud SQL Auth Proxy / Unix socket).
- Secrets created in Secret Manager (one per value, see §3).

---

## 2. Service accounts and IAM

Two service accounts are involved.

### 2.1 — Cloud Function SA

Create once, never delete:

```powershell
gcloud iam service-accounts create research-engine-cf `
  --display-name="research_engine Cloud Function"
```

Grant minimum required roles (least privilege per AGENTS.md):

```powershell
$PROJECT = gcloud config get-value project
$CF_SA = "research-engine-cf@$PROJECT.iam.gserviceaccount.com"

# Cloud SQL Client (to connect to Postgres)
gcloud projects add-iam-policy-binding $PROJECT `
  --member="serviceAccount:$CF_SA" `
  --role="roles/cloudsql.client"

# Secret Manager — read the secrets enumerated in §3
gcloud projects add-iam-policy-binding $PROJECT `
  --member="serviceAccount:$CF_SA" `
  --role="roles/secretmanager.secretAccessor"

# Logging (auto-attached to most SAs but explicit here)
gcloud projects add-iam-policy-binding $PROJECT `
  --member="serviceAccount:$CF_SA" `
  --role="roles/logging.logWriter"
```

### 2.2 — FastAPI (Cloud Run) SA → invoker

The Cloud Run service account that runs FastAPI must hold `roles/cloudfunctions.invoker` on the deployed function (set AFTER deploy in §5):

```powershell
$FASTAPI_SA = "fivvle-api@$PROJECT.iam.gserviceaccount.com"  # replace with actual SA

gcloud functions add-invoker-policy-binding research_engine `
  --region=us-central1 `
  --member="serviceAccount:$FASTAPI_SA"
```

---

## 3. Secrets

Create in Secret Manager. Values are not in git.

| Secret name | Source |
|---|---|
| `database-url` | Cloud SQL Postgres connection string (use Unix socket form: `postgresql+asyncpg://user:pass@/db?host=/cloudsql/<instance>`) |
| `anthropic-api-key` | Anthropic dashboard |
| `moonshot-api-key` | Moonshot dashboard |
| `tavily-api-key` | Tavily dashboard |
| `firebase-project-id` | Firebase console (project ID — plaintext, but treated as secret for parity) |
| `sentry-dsn` | Sentry project DSN |

Create example:

```powershell
echo "postgresql+asyncpg://..." | gcloud secrets create database-url --data-file=-
```

Grant Function SA access to each:

```powershell
gcloud secrets add-iam-policy-binding database-url `
  --member="serviceAccount:$CF_SA" `
  --role="roles/secretmanager.secretAccessor"
```

(Repeat per secret. Loop in PowerShell if preferred.)

---

## 4. Deploy

### 4.1 — Pre-deploy: copy backend code into the function source tree

The function's `main.py` imports from `app.*`. The deploy script copies `backend/app/` into `functions/research_engine/app/` before invoking gcloud, then cleans up after.

Save the deploy script (next file in this commit): `scripts/deploy_research_engine_function.ps1`.

### 4.2 — Deploy command

The deploy script runs this:

```powershell
gcloud functions deploy research_engine `
  --gen2 `
  --runtime=python311 `
  --region=us-central1 `
  --source=functions/research_engine `
  --entry-point=research_engine_handler `
  --trigger-http `
  --no-allow-unauthenticated `
  --no-cpu-throttling `
  --timeout=540s `
  --memory=1Gi `
  --cpu=1 `
  --max-instances=10 `
  --min-instances=0 `
  --service-account=$CF_SA `
  --set-secrets="DATABASE_URL=database-url:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,MOONSHOT_API_KEY=moonshot-api-key:latest,TAVILY_API_KEY=tavily-api-key:latest,FIREBASE_PROJECT_ID=firebase-project-id:latest,SENTRY_DSN=sentry-dsn:latest" `
  --set-env-vars="DISPATCHER_MODE=in_process,LOG_LEVEL=INFO"
```

Notes:
- `--no-cpu-throttling` keeps CPU allocated to the container so the background thread can finish the pipeline after the 202 response. Without this, the thread is throttled and the pipeline stalls.
- `--timeout=540s` is the 2nd-gen HTTP max (9 minutes). Pipeline target: ≤6 minutes.
- `DISPATCHER_MODE=in_process` inside the function: the function itself uses in-process pipeline execution (it IS the pipeline). The HTTP dispatcher is the caller, not the function.

### 4.3 — Capture the function URL

After deploy:

```powershell
$FUNCTION_URL = gcloud functions describe research_engine --region=us-central1 --format="value(serviceConfig.uri)"
Write-Host "RESEARCH_ENGINE_URL=$FUNCTION_URL"
```

---

## 5. Wire FastAPI to the function

Set on the FastAPI Cloud Run service (or your secret-config tool):

| Env var | Value |
|---|---|
| `DISPATCHER_MODE` | `http` |
| `RESEARCH_ENGINE_URL` | the URL captured in §4.3 |
| `OIDC_AUDIENCE` | leave unset (defaults to `RESEARCH_ENGINE_URL`) |

Then redeploy the FastAPI service so the new env is picked up.

Bind `roles/cloudfunctions.invoker` to the FastAPI SA (§2.2) if not done.

---

## 6. Verify

### 6.1 — Direct curl (sanity check, optional)

Mint an OIDC token for the function's audience and POST:

```powershell
$TOKEN = gcloud auth print-identity-token --audiences=$FUNCTION_URL
$EXP_ID = [guid]::NewGuid().ToString()

curl.exe -X POST $FUNCTION_URL `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d "{\"experiment_id\": \"$EXP_ID\"}" `
  -i
```

Expected: `HTTP/2 202`. (The experiment doesn't exist in the DB, so the pipeline will log an error and exit gracefully — that's fine for the sanity check; we just verify the dispatch path works.)

### 6.2 — End-to-end via FastAPI

Trigger a real `/confirm` or `/chat/turn` finalize. Watch Cloud Run logs:

```powershell
gcloud functions logs read research_engine --region=us-central1 --limit=50
```

Expect: `dispatch accepted` log entry with `experiment_id`, followed eventually by pipeline-phase logs (planner, searcher, reader, synthesizer).

---

## 7. Rollback

If something is wrong with the function, flip FastAPI back to in-process:

```powershell
# Update Cloud Run env var
gcloud run services update fivvle-api `
  --region=us-central1 `
  --update-env-vars="DISPATCHER_MODE=in_process"
```

This restores the dev-mode behavior in production. Performance is lower (pipeline competes for FastAPI worker CPU) but the system works. Investigate the CF issue without blocking users.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| HTTP 401 from CF | FastAPI SA missing `roles/cloudfunctions.invoker` | Re-bind §2.2 |
| HTTP 403 from CF | OIDC token audience mismatch | Confirm `RESEARCH_ENGINE_URL` and `OIDC_AUDIENCE` (if set) exactly match the function URL |
| HTTP 500 from CF | `init_engine` failed; likely DB connectivity | Check function logs for `init_engine failed`; verify Cloud SQL connector + DATABASE_URL secret |
| 202 returned but no pipeline logs | Container killed before background thread ran | Confirm `--no-cpu-throttling` is set; check Cloud Run revision config |
| Experiment stuck in RESEARCHING forever | Container killed mid-pipeline OR pipeline crashed silently | Check function logs around the experiment ID's window; manually flip status to RESEARCH_FAILED via admin; user retries via `/confirm` |
| Cold start latency >5s | CF default cold start | Set `--min-instances=1` if latency unacceptable (cost trade-off) |

---

## 9. Costs

- Cloud Function: ~$0.40/million invocations + CPU/memory/networking. With `--no-cpu-throttling`, CPU bills during background work. Per-pipeline estimate: ~$0.005–$0.010 in CF compute (LLM + Tavily are the dominant costs, billed separately).
- `--min-instances=0` means no idle cost; cold start on first dispatch after idle.

---

## 10. Operational notes

- Don't manually edit `functions/research_engine/app/` — it's a generated artifact, gitignored.
- The deploy script must run from the repo root.
- Re-deploys are cheap. Always re-deploy after `backend/app/` changes; the function's `app/` copy is stale otherwise.
- For CI/CD: integrate the deploy script into a workflow that runs after backend tests pass.
