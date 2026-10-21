#!/usr/bin/env bash
# DHAP key service — add, remove or list team members. Run in Google Cloud Shell, in the same project.
#   bash service/team-code.sh add maria maria@yourcompany.com   -> makes maria's code and lets ONLY maria read it
#   bash service/team-code.sh remove maria                      -> maria's code stops working within about a minute
#   bash service/team-code.sh list                              -> shows the names (not the codes)
# Each person's service address + code is kept in Google Secret Manager as "dhap-code-NAME".
# Only that person (and project owners) can read it. No password manager is needed.
set -euo pipefail
REGION="${REGION:-us-central1}"
NAME="dhap-key-service"
ACTION="${1:-}"; WHO="$(echo "${2:-}" | tr 'A-Z' 'a-z')"; EMAIL="${3:-}"
PROJECT="$(gcloud config get-value project 2>/dev/null)"

CURRENT="$(gcloud secrets versions access latest --secret=dhap-team-codes)"
case "$ACTION" in
  list)
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("\n".join(sorted(d)) or "(none)")' "$CURRENT"; exit 0 ;;
  add)
    [[ "$WHO" =~ ^[a-z0-9-]{2,30}$ ]] || { echo "Give a short name with letters, numbers or dashes, for example: maria"; exit 1; }
    [[ "$EMAIL" == *@*.* ]] || { echo "Give the person's Google email, for example: bash service/team-code.sh add $WHO $WHO@yourcompany.com"; exit 1; } ;;
  remove)
    [ -n "$WHO" ] || { echo "Give a name, for example: bash service/team-code.sh remove maria"; exit 1; } ;;
  *) echo "Use: add NAME EMAIL | remove NAME | list"; exit 1 ;;
esac

NEW_CODE="dhap_$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
UPDATED="$(python3 - "$CURRENT" "$ACTION" "$WHO" "$NEW_CODE" <<'PY'
import json, sys
d = json.loads(sys.argv[1]); action, who, code = sys.argv[2], sys.argv[3], sys.argv[4]
if action == "add": d[who] = code
else:
    if who not in d: sys.exit(f"No one named {who!r}. Run: bash service/team-code.sh list")
    d.pop(who)
print(json.dumps(d))
PY
)"
printf %s "$UPDATED" | gcloud secrets versions add dhap-team-codes --data-file=- >/dev/null

# start a fresh copy of the service so it reads the new list right away
gcloud run services update "$NAME" --region="$REGION" --update-env-vars="CODES_UPDATED=$(date +%s)" --quiet >/dev/null

if [ "$ACTION" = "add" ]; then
  URL="$(gcloud functions describe "$NAME" --gen2 --region="$REGION" --format='value(serviceConfig.uri)')"
  CARD="Service address: $URL
Team code: $NEW_CODE"
  if gcloud secrets describe "dhap-code-$WHO" >/dev/null 2>&1; then
    printf %s "$CARD" | gcloud secrets versions add "dhap-code-$WHO" --data-file=- >/dev/null
  else
    printf %s "$CARD" | gcloud secrets create "dhap-code-$WHO" --data-file=- --replication-policy=automatic >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "dhap-code-$WHO" --member="user:$EMAIL" \
    --role=roles/secretmanager.secretAccessor --quiet >/dev/null
  echo "Done. $WHO's code is saved in Secret Manager as dhap-code-$WHO, and only $EMAIL can read it."
  echo
  echo "Send $WHO this message (it has no secrets in it):"
  echo "----------------------------------------------------------------"
  echo "Your DHAP team code is ready. Go to https://shell.cloud.google.com"
  echo "(sign in as $EMAIL), paste this line, and press Enter:"
  echo "  gcloud secrets versions access latest --secret=dhap-code-$WHO --project=$PROJECT"
  echo "It shows your service address and team code. Then follow Part B of the setup guide."
  echo "----------------------------------------------------------------"
else
  gcloud secrets delete "dhap-code-$WHO" --quiet >/dev/null 2>&1 || true
  echo "$WHO removed. Their code no longer works, and their saved copy is deleted."
fi
