# DHAP GBP skill — master copy (public repository)

This repository is the **only copy** of the DHAP GBP rules (audit rules, report and hot-sheet specs, version history, automatic checks). **Nothing has to be installed or saved in anyone's Ask AI.** Every report run reads the newest rules from here, so everyone, whether two people or twenty, is always on the same version.

**This repository is public.** Never add passwords, tokens, customer data, or internal identifiers. The knowledge base id and the sub-account id are written as `{{KB_ID}}` and `{{LOCATION_ID}}`; Ask AI finds the real values at run time (see "How it works"). The automatic check fails if a known internal value is committed.

## Run a report (no setup — anyone)
Open Ask AI, copy the block below, change the dealer details on the first line, and send it:

```
Run DHAP GBP for [Business Name], [City, State], a [type of business]. [website URL]

Before you start, read these two files from the shared repository and follow SKILL.md exactly as the only source of truth:
https://raw.githubusercontent.com/Clikdata2/dhap-gbp-skill/main/VERSION
https://raw.githubusercontent.com/Clikdata2/dhap-gbp-skill/main/SKILL.md
Open your reply with "Using DHAP GBP v<VERSION>." If you cannot read both files, stop and tell me. Do not work from memory or from any saved skill.
```

That is all. A change merged here reaches everyone on their next run. (A web copy can lag a few minutes right after a merge.)

## How it works
- The prompt only tells Ask AI where the rules are. The rules themselves live in `SKILL.md` and nowhere else.
- The location id comes from the Ask AI session. The knowledge base is found by its name, "Mitsubishi CLIKsearch". If Ask AI cannot find exactly one, it stops and says so.
- If anyone still has an older saved copy of this skill in their Ask AI, they should archive it so that only this repository is used.

## What is in here
| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself. First line shows the version. |
| `VERSION` | The version number (for example `14.2`). Must match the first line of `SKILL.md` and the newest `CHANGELOG.md` entry. |
| `CHANGELOG.md` | One entry per release. |
| `knowledge-base/` | The question-and-answer set behind the voice assistant, with its own change log. |
| `templates/` | Reference pages (full report and hot sheet) that the automatic check holds to the locked rules. |
| `loader/ASKAI_LOADER_SKILL.md` | Optional shortcut only: a thin skill that lets someone type "Run DHAP GBP" without pasting the block above. Not needed. |
| `scripts/validate.py` + `.github/workflows/validate.yml` | Automatic check on every change: versions agree, no internal values leak, templates follow the locked rules. |
| `.github/CODEOWNERS`, `.github/pull_request_template.md` | Review owner and release checklist. |

## Rules of the road
1. **Rules change here, by pull request, never inside Ask AI.**
2. Every change bumps `VERSION`, the first line of `SKILL.md`, the "Using DHAP GBP vN." line, and adds a `CHANGELOG.md` entry. The automatic check fails the pull request if they disagree.
3. One approver (`.github/CODEOWNERS`) merges. Prefer pull requests over pushing straight to `main`.
4. Every run reads the newest `SKILL.md`, so a merged change reaches everyone at once. There is nothing to sync.

## Check that everyone is current
The first line of every report reply shows the version it used. It must match `VERSION` here. If a reply shows a different version, that person used a saved copy; ask them to archive it and use the block above.

## Roll back
On GitHub open **Pull requests, then Closed**, open the merged change, press **Revert**, merge the revert pull request, add a `CHANGELOG.md` line saying why, and bump the version.
