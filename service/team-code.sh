#!/usr/bin/env bash
# DHAP key service — add, remove or list team codes. Run in Google Cloud Shell, in the same project.
#   bash service/team-code.sh add  maria      -> prints a new code for maria
#   bash service/team-code.sh remove maria    -> maria's code stops working within about a minute
#   bash service/team-code.sh list            -> shows the names (not the codes)
set -euo pipefail
REGION="${REGION:-us-central1}"
NAME="dhap-key-service"
ACTION="${1:-}"; WHO="${2:-}"

CURRENT="$(gcloud secrets versions access latest --secret=dhap-team-codes)"
case "$ACTION" in
  list)
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("\n".join(sorted(d)) or "(none)")' "$CURRENT"; exit 0 ;;
  add|remove)
    [ -n "$WHO" ] || { echo "Give a name, for example: bash service/team-code.sh $ACTION maria"; exit 1; } ;;
  *) echo "Use: add NAME | remove NAME | list"; exit 1 ;;
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

if [ "$ACTION" = "add" ]; then echo "New code for $WHO:  $NEW_CODE"; echo "Give it to $WHO through your password manager."
else echo "$WHO removed. Their code no longer works."; fi
