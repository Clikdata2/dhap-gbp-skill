#!/usr/bin/env bash
# One-time (idempotent) setup for the phone-width probe and spell check.
# Creates ~/.dhap-gbp-venv with Playwright (+ headless Chromium) and pyspellchecker.
set -euo pipefail
VENV="${DHAP_VENV:-$HOME/.dhap-gbp-venv}"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade playwright pyspellchecker
"$VENV/bin/python" -m playwright install chromium
echo "ready: $VENV/bin/python"
