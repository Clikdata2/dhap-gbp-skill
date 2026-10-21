#!/usr/bin/env bash
# One-time install: makes "Run DHAP GBP for ..." work in Claude Code and Codex on this Mac.
#   bash ~/dhap-gbp-skill/run/install.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS="$HOME/.claude/skills"; mkdir -p "$SKILLS"
if [ -e "$SKILLS/dhap-gbp-run" ] && [ ! -L "$SKILLS/dhap-gbp-run" ]; then
  mkdir -p "$HOME/.claude/skill-backups"   # outside the skills folder, so the old copy can't load as a second skill
  mv "$SKILLS/dhap-gbp-run" "$HOME/.claude/skill-backups/dhap-gbp-run.backup-$(date +%Y%m%d%H%M%S)"
fi
ln -sfn "$REPO/run" "$SKILLS/dhap-gbp-run"          # Claude Code: the routine updates itself with every git pull
mkdir -p "$HOME/.codex"; touch "$HOME/.codex/AGENTS.md"
python3 - "$HOME/.codex/AGENTS.md" "$REPO" <<'PY'
import re, sys
f, repo = sys.argv[1], sys.argv[2]
a, b = "<!-- >>> DHAP GBP >>> -->", "<!-- <<< DHAP GBP <<< -->"
t = re.sub(re.escape(a) + r".*?" + re.escape(b) + r"\n?", "", open(f).read(), flags=re.S)
t += f'{a}\nWhen the user says "Run DHAP GBP for ...", read {repo}/run/SKILL.md and follow it exactly (it pulls the latest rules first).\n{b}\n'
open(f, "w").write(t)
PY
echo "Done. In Claude Code or Codex, just type:  Run DHAP GBP for [Dealership] [website]"
echo "(Restart Claude Code and Codex once so they pick it up.)"
