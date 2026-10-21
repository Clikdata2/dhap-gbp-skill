#!/usr/bin/env bash
# DHAP proof service — deploy (or update) the screenshot / schema / popup helper used by Ask AI.
# Run in Google Cloud Shell, in the same project, AFTER service/deploy.sh (it reuses the team codes):
#   bash shot/deploy-shot.sh
set -euo pipefail
cd "$(dirname "$0")"
REGION="${REGION:-us-central1}"
NAME="dhap-proof-service"
PROJECT="$(gcloud config get-value project 2>/dev/null)"
[ -n "$PROJECT" ] || { echo "No project selected. Run: gcloud config set project YOUR-PROJECT-ID"; exit 1; }
gcloud secrets describe dhap-team-codes >/dev/null 2>&1 || { echo "Run service/deploy.sh first (it creates the team codes)."; exit 1; }
echo "Deploying the proof service (5-8 minutes the first time; it builds a browser image)..."
gcloud run deploy "$NAME" --source=. --region="$REGION" --allow-unauthenticated \
  --memory=2Gi --cpu=2 --timeout=120 --concurrency=2 --max-instances=2 \
  --set-secrets="DHAP_TEAM_CODES=dhap-team-codes:latest" --quiet >/dev/null
URL="$(gcloud run services describe "$NAME" --region="$REGION" --format='value(status.url)')"
echo
echo "================ DONE ================"
echo "Proof service address:  $URL"
echo "Health check:           $(curl -s "$URL/health")"
echo "Next: in GHL, add a Custom Value named \"DHAP Proof URL\" with that address."
echo "======================================"
