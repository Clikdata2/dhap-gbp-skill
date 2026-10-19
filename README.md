# DHAP GBP skill — master copy (public repository)

This repository is the **only master** of the DHAP GBP skill (audit rules, report and hot-sheet specs, version history, automatic checks). Copies inside Ask AI are *copies* or loaders that read from here. If a copy and this repository disagree, the repository wins.

**This repository is public.** Never add passwords, tokens, customer data, or internal identifiers. The knowledge base id and the sub-account id are written as `{{KB_ID}}` and `{{LOCATION_ID}}`; the real values live only in the private loader skill inside Ask AI. The automatic check fails if a known internal value is committed.

## What is in here
| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself. First line shows the version. |
| `VERSION` | The version number (for example `12.1`). Must match the first line of `SKILL.md` and the newest `CHANGELOG.md` entry. |
| `CHANGELOG.md` | One entry per release. |
| `loader/ASKAI_LOADER_SKILL.md` | Public template of the thin skill that makes Ask AI read `SKILL.md` from this repository at the start of every run. |
| `templates/` | Reference pages (full report and hot sheet) — added separately; the check skips them until they exist. |
| `scripts/validate.py` + `.github/workflows/validate.yml` | Automatic check on every change: versions agree, no internal values leak, templates follow the locked rules. |
| `.github/CODEOWNERS`, `.github/pull_request_template.md` | Review owner and release checklist. |

## Rules of the road
1. **Nobody edits the skill inside Ask AI.** Change a rule here, by pull request.
2. Every change bumps `VERSION`, the first line of `SKILL.md`, the "Using DHAP GBP vN." line, and adds a `CHANGELOG.md` entry. The automatic check fails the pull request if they disagree.
3. One approver (`.github/CODEOWNERS`) merges. Prefer pull requests over pushing straight to `main`.
4. Every user's Ask AI loader reads the newest `SKILL.md`, so a merged change reaches everyone the next time they start a run.

## How Ask AI uses it
The loader skill (private, inside Ask AI) fetches `VERSION` and `SKILL.md` from this repository at the start of every run, refuses to continue if it cannot, and opens its reply with `Using DHAP GBP v<VERSION> (shared repository).` Each person who runs reports needs the loader skill in their own Ask AI.

## Check for drift (monthly, 2 minutes)
Ask each person's Ask AI: *"Run DHAP GBP check — what version did you load?"* It must match `VERSION` here.

## Roll back
On GitHub open **Pull requests → Closed**, open the merged change, press **Revert**, merge the revert pull request, add a `CHANGELOG.md` line saying why, and bump the version.
