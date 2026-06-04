# scripts/deploy_research_engine_function.ps1
# Per ADR 0020 + docs/runbooks/research-engine-cloud-function.md.
# Run from the repo root: .\scripts\deploy_research_engine_function.ps1

$ErrorActionPreference = "Stop"

# --- Config (edit these for your project) ---
$REGION = "us-central1"
$FUNCTION_NAME = "research_engine"
$RUNTIME = "python311"
$MEMORY = "1Gi"
$CPU = "1"
$TIMEOUT = "540s"
$MAX_INSTANCES = "10"
$MIN_INSTANCES = "0"

$PROJECT = gcloud config get-value project 2>$null
if (-not $PROJECT) {
    Write-Error "gcloud project not set. Run: gcloud config set project <id>"
    exit 1
}
$CF_SA = "research-engine-cf@$PROJECT.iam.gserviceaccount.com"

# Comma-separated secrets list (must match Secret Manager names — see runbook §3)
$SECRETS = "DATABASE_URL=database-url:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,MOONSHOT_API_KEY=moonshot-api-key:latest,TAVILY_API_KEY=tavily-api-key:latest,FIREBASE_PROJECT_ID=firebase-project-id:latest,SENTRY_DSN=sentry-dsn:latest"

# Env vars (non-secret)
$ENV_VARS = "DISPATCHER_MODE=in_process,LOG_LEVEL=INFO"

# --- 1. Pre-deploy: copy backend/app into the function source ---
$FUNC_DIR = "functions/research_engine"
$FUNC_APP = "$FUNC_DIR/app"

if (-not (Test-Path "backend/app")) {
    Write-Error "backend/app not found. Run this script from the repo root."
    exit 1
}

if (Test-Path $FUNC_APP) {
    Write-Host "Removing stale $FUNC_APP..."
    Remove-Item $FUNC_APP -Recurse -Force
}

Write-Host "Copying backend/app -> $FUNC_APP..."
Copy-Item "backend/app" $FUNC_APP -Recurse

# Strip __pycache__ from the copy (slim deploy archive)
Get-ChildItem $FUNC_APP -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $FUNC_APP -Recurse -File -Filter "*.pyc" | Remove-Item -Force

# --- 2. Deploy ---
Write-Host "Deploying $FUNCTION_NAME to $REGION..."

gcloud functions deploy $FUNCTION_NAME `
    --gen2 `
    --runtime=$RUNTIME `
    --region=$REGION `
    --source=$FUNC_DIR `
    --entry-point=research_engine_handler `
    --trigger-http `
    --no-allow-unauthenticated `
    --no-cpu-throttling `
    --timeout=$TIMEOUT `
    --memory=$MEMORY `
    --cpu=$CPU `
    --max-instances=$MAX_INSTANCES `
    --min-instances=$MIN_INSTANCES `
    --service-account=$CF_SA `
    --set-secrets=$SECRETS `
    --set-env-vars=$ENV_VARS

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deploy failed (exit $LASTEXITCODE). Leaving $FUNC_APP in place for inspection."
    exit $LASTEXITCODE
}

# --- 3. Cleanup ---
Write-Host "Cleaning up $FUNC_APP..."
Remove-Item $FUNC_APP -Recurse -Force

# --- 4. Print the function URL ---
$FUNCTION_URL = gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(serviceConfig.uri)"
Write-Host ""
Write-Host "==================================================="
Write-Host "Deploy complete."
Write-Host "RESEARCH_ENGINE_URL=$FUNCTION_URL"
Write-Host ""
Write-Host "Next: set this URL on the FastAPI Cloud Run service (DISPATCHER_MODE=http)."
Write-Host "See docs/runbooks/research-engine-cloud-function.md §5."
Write-Host "==================================================="
