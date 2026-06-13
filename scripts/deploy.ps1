# Deploy the FastAPI backend to Google Cloud Run.
#
# Usage:
#   .\scripts\deploy.ps1 -ProjectId <id> [-Region <region>] [-Demo] [-NeonUrl <url>]
#
# Examples:
#   .\scripts\deploy.ps1 -ProjectId asa-sec-analyst -Demo
#   .\scripts\deploy.ps1 -ProjectId asa-sec-analyst -Demo -NeonUrl "postgresql+asyncpg://..."

param(
    [Parameter(Mandatory=$true)]  [string]$ProjectId,
    [string]$Region   = "europe-west1",
    [switch]$Demo,
    [string]$NeonUrl  = ""
)

$Service = "autonomous-security-analyst"
$Image   = "$Region-docker.pkg.dev/$ProjectId/asa/$Service"

Write-Host ">> Building and pushing image" -ForegroundColor Cyan
gcloud builds submit --project $ProjectId --tag $Image .
if (-not $?) { exit 1 }

Write-Host ">> Deploying to Cloud Run (demo=$Demo)" -ForegroundColor Cyan

if ($Demo) {
    $EnvVars = "ENVIRONMENT=production,DEMO_MODE=true"
    if ($NeonUrl -ne "") {
        $EnvVars = "$EnvVars,DATABASE_URL=$NeonUrl"
    }
    gcloud run deploy $Service `
        --project $ProjectId `
        --region $Region `
        --image $Image `
        --platform managed `
        --allow-unauthenticated `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 3 `
        --set-env-vars $EnvVars
} else {
    gcloud run deploy $Service `
        --project $ProjectId `
        --region $Region `
        --image $Image `
        --platform managed `
        --allow-unauthenticated `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 3 `
        --set-env-vars "ENVIRONMENT=production" `
        --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest,DATABASE_URL=database-url:latest"
}

if (-not $?) { exit 1 }

Write-Host "`n>> Done. Service URL:" -ForegroundColor Green
gcloud run services describe $Service --project $ProjectId --region $Region --format "value(status.url)"
