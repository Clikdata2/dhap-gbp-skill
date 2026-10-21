#!/usr/bin/env bash
# DHAP key service — set up one employee's Mac for Claude Code and Codex. Run once per Mac:
#   bash service/setup-employee.sh
# It asks for the service address and the person's team code (both from your password manager),
# saves them where Claude Code and Codex read them, and tests the connection.
set -euo pipefail

read -r -p "Paste the service address (starts with https://): " URL
read -r -s -p "Paste your team code (starts with dhap_), then press Enter: " CODE; echo
URL="${URL%/}"
case "$URL" in https://*) ;; *) echo "That address should start with https://"; exit 1;; esac
case "$CODE" in dhap_*) ;; *) echo "That team code should start with dhap_"; exit 1;; esac

echo "Testing the connection..."
STATUS="$(curl -s -o /dev/null -w '%{http_code}' -H "X-DHAP-Code: $CODE" "$URL/lookup?q=Google%20Mountain%20View")"
if [ "$STATUS" = "401" ]; then echo "The service says the team code is wrong. Check it and run this again."; exit 1; fi
if [ "$STATUS" != "200" ]; then echo "Could not reach the service (got $STATUS). Check the address and your internet, then run this again."; exit 1; fi
echo "Connection works."

BLOCK_START="# >>> DHAP key service >>>"
BLOCK_END="# <<< DHAP key service <<<"
for F in "$HOME/.zshenv" "$HOME/.bash_profile"; do
  touch "$F"
  # remove an older copy of the block, then add the new one
  python3 - "$F" "$BLOCK_START" "$BLOCK_END" <<'PY'
import re, sys
f, a, b = sys.argv[1:4]
t = open(f).read()
t = re.sub(re.escape(a) + r".*?" + re.escape(b) + r"\n?", "", t, flags=re.S)
open(f, "w").write(t)
PY
  {
    echo "$BLOCK_START"
    echo "export DHAP_SERVICE_URL=\"$URL\""
    echo "export DHAP_TEAM_CODE=\"$CODE\""
    echo "$BLOCK_END"
  } >> "$F"
done

echo
echo "Done. Close every Terminal, Claude Code and Codex window and open them again so they pick this up."
echo "To check later, run:  echo \$DHAP_SERVICE_URL"
