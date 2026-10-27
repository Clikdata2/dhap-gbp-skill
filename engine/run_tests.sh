#!/usr/bin/env bash
# Runs every engine test. The stress tests repeat 3 rounds each. Live JEV and Places cases run only when TYPESAFE_API_KEY / GOOGLE_PLACES_API_KEY are set.
# Needs: Python with engine/requirements.txt installed, Playwright's Chromium (python -m playwright install chromium), Node.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
node tests/test_post_variety.js
node tests/test_split_posts.js
"$PY" tests/test_paste_files.py
"$PY" tests/test_score.py
"$PY" tests/test_decide.py
"$PY" tests/test_areas.py
"$PY" tests/test_ai_answers.py 3
"$PY" tests/test_ai_visibility.py 3
"$PY" tests/test_rules_7_8.py 3
"$PY" tests/test_jev.py 3
"$PY" tests/test_places.py 3
"$PY" tests/test_schema_collector.py 3
"$PY" tests/test_build.py 3
echo "ENGINE: ALL TESTS PASSED"
