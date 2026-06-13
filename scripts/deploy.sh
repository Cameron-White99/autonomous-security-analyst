#!/usr/bin/env bash
# Deploy the FastAPI backend to Google Cloud Run.
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - A GCP project with Cloud Run + Artifact Registry APIs enabled
#   - Secrets created:  gcloud secrets create anthropic-api-key --data-file=-
#                       gcloud secrets create database-url --data-file=-
#
# Usage: ./scripts/deploy.sh <gcp-project-id> [region]

set -euo pipefail

PROJECT_ID="${1:?Usage: deploy.sh <gcp-project-id> [region]}"
REGION="${2:-europe-west1}"
SERVICE="autonomous-security-analyst"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/asa/${SERVICE}"

echo ">> Building and pushing image"
gcloud builds submit --project "${PROJECT_ID}" --tag "${IMAGE}" .

echo ">> Deploying to Cloud Run"
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

echo ">> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --format "value(status.url)"
