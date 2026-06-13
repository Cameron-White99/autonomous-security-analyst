#!/usr/bin/env bash
# Deploy the FastAPI backend to Google Cloud Run.
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - A GCP project with Cloud Run + Artifact Registry APIs enabled
#
# Usage:
#   ./scripts/deploy.sh <gcp-project-id> [region] [flags]
#
# Flags:
#   --demo          Deploy in demo mode (no API key or database required)
#   --neon <url>    Use a Neon PostgreSQL connection string for persistence
#
# Full production (requires secrets in Secret Manager):
#   gcloud secrets create anthropic-api-key --data-file=-
#   gcloud secrets create database-url --data-file=-
#   ./scripts/deploy.sh my-project europe-west1
#
# Demo deployment (no API key needed, in-memory storage):
#   ./scripts/deploy.sh my-project europe-west1 --demo
#
# Demo + Neon database (persistent incidents, no API key):
#   ./scripts/deploy.sh my-project europe-west1 --demo --neon "postgresql+asyncpg://..."

set -euo pipefail

PROJECT_ID="${1:?Usage: deploy.sh <gcp-project-id> [region] [--demo] [--neon <url>]}"
REGION="${2:-europe-west1}"
SERVICE="autonomous-security-analyst"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/asa/${SERVICE}"

DEMO=false
NEON_URL=""

# Parse optional flags (everything after positional args)
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --demo) DEMO=true ;;
    --neon) NEON_URL="${2:?--neon requires a connection string}"; shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
  shift
done

echo ">> Building and pushing image"
gcloud builds submit --project "${PROJECT_ID}" --tag "${IMAGE}" .

echo ">> Deploying to Cloud Run (demo=${DEMO})"

if [[ "$DEMO" == "true" ]]; then
  ENV_VARS="ENVIRONMENT=production,DEMO_MODE=true"
  if [[ -n "$NEON_URL" ]]; then
    ENV_VARS="${ENV_VARS},DATABASE_URL=${NEON_URL}"
  fi
  gcloud run deploy "${SERVICE}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --image "${IMAGE}" \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "${ENV_VARS}"
else
  # Production: API key and DB URL pulled from Secret Manager
  gcloud run deploy "${SERVICE}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --image "${IMAGE}" \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest,DATABASE_URL=database-url:latest"
fi

echo ">> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --format "value(status.url)"
