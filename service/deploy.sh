#!/usr/bin/env bash
# DHAP key service — one-time setup (and safe to run again to update).
# Run it in Google Cloud Shell, inside the Google Cloud project that owns the Places key:
#   bash service/deploy.sh
# It asks you to paste each key (nothing you paste is shown or saved anywhere except Google Secret Manager),
# deploys the service, creates the first team code, and prints the two things employees need:
# the service address and the team code.
set -euo pipefail
cd "$(dirname "$0")"

REGION="${REGION:-us-central1}"
NAME="dhap-key-service"
PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$PROJECT" ]; then echo "No project selected. Run: gcloud config set project YOUR-PROJECT-ID"; exit 1; fi
echo "Project: $PROJECT   Region: $REGION"

echo "1/6 Turning on the Google services this needs (about 1 minute)..."
gcloud services enable run.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com places.googleapis.com --quiet

save_secret () {   # save_secret NAME VALUE   (creates the secret, or adds a new version)
  if gcloud secrets describe "$1" >/dev/null 2>&1; then
    printf %s "$2" | gcloud secrets versions add "$1" --data-file=- >/dev/null
  else
    printf %s "$2" | gcloud secrets create "$1" --data-file=- --replication-policy=automatic >/dev/null
  fi
}

echo "2/6 Google Places key"
read -r -s -p "   Paste the NEW Google Places key, then press Enter (or just press Enter to keep the saved one): " PK; echo
if [ -n "$PK" ]; then save_secret dhap-places-key "$PK"; echo "   Saved.";
elif ! gcloud secrets describe dhap-places-key >/dev/null 2>&1; then echo "   A Places key is required the first time."; exit 1; fi

echo "3/6 TypeSafe (JEV) key"
read -r -s -p "   Paste the TypeSafe key, then press Enter (or just press Enter to skip / keep the saved one): " TK; echo
if [ -n "$TK" ]; then save_secret dhap-typesafe-key "$TK"; echo "   Saved.";
elif ! gcloud secrets describe dhap-typesafe-key >/dev/null 2>&1; then save_secret dhap-typesafe-key "none"; echo "   Skipped (JEV stays off until you add it)."; fi

echo "4/6 Team codes"
FIRST_CODE=""
if ! gcloud secrets describe dhap-team-codes >/dev/null 2>&1; then
  FIRST_CODE="dhap_$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  save_secret dhap-team-codes "{\"team\": \"$FIRST_CODE\"}"
  echo "   Created the first team code (named \"team\")."
else
  echo "   Team codes already exist; keeping them. (Use service/team-code.sh to add or remove people.)"
fi

echo "5/6 Letting the service read the secrets"
NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
SA="${NUM}-compute@developer.gserviceaccount.com"
for s in dhap-places-key dhap-typesafe-key dhap-team-codes; do
  gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
done

echo "6/6 Deploying the service (2-4 minutes)..."
gcloud functions deploy "$NAME" --gen2 --runtime=python312 --region="$REGION" --source=. --entry-point=app \
  --trigger-http --allow-unauthenticated --memory=256Mi --timeout=60s --max-instances=3 \
  --set-secrets="GOOGLE_PLACES_API_KEY=dhap-places-key:latest,TYPESAFE_API_KEY=dhap-typesafe-key:latest,DHAP_TEAM_CODES=dhap-team-codes:latest" \
  --quiet >/dev/null

URL="$(gcloud functions describe "$NAME" --gen2 --region="$REGION" --format='value(serviceConfig.uri)')"
echo
echo "================ DONE ================"
echo "Service address:  $URL"
if [ -n "$FIRST_CODE" ]; then echo "Team code:        $FIRST_CODE"; else echo "Team code:        (unchanged — see service/team-code.sh list)"; fi
echo "Health check:     $(curl -s "$URL/health")"
echo
echo "Save the service address and the team code in your password manager now."
echo "======================================"
