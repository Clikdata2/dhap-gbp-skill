---
name: dhap-gbp-run
description: Run the full DHAP GBP audit for a franchise auto dealership end to end and deliver the named files (full DHAP report, Digital Health Alert, audit-evidence record, rep brief). Use whenever the user says "Run DHAP GBP for [Dealership] [website]" or asks for a GBP / Maps / schema audit, a Digital Health Alert, or a re-run for a dealer. Pulls the latest rules from the Clikdata2/dhap-gbp-skill repository first, every time. Do NOT use for the older "Create Digital Health Analysis & Proposal (DHAP)" skill.
---

# DHAP GBP — run routine (shared, installed once per computer by run/install.sh or run/install.ps1)

The user's whole request is one line: **"Run DHAP GBP for [Dealership] [website]"**. Do everything below without asking them for anything else, except a missing website.

**Where things are.** REPO = the folder this file lives in, one level up (the user's local copy of `Clikdata2/dhap-gbp-skill`; usually `~/dhap-gbp-skill`, or `%USERPROFILE%\dhap-gbp-skill` on Windows). The **rules** live only in `REPO/SKILL.md`; this file is the **process**. Never work from memory or from an older copy.

## Procedure (every step, every run)
**0. Plan.** Keep a task list.

**1. Get the latest rules.** Make sure REPO is on `main` (`git -C REPO checkout main` if a branch is checked out), then run `git -C REPO pull --ff-only`. If it fails (no internet, local edits), say so and stop. Read ALL of `REPO/SKILL.md` and the top of `REPO/CHANGELOG.md`. Open your first reply with exactly `Using DHAP GBP v<REPO/VERSION>.`

**2. One-time tools check (silent when already done).** If `~/.dhap-gbp-venv` (Windows: `%USERPROFILE%\.dhap-gbp-venv`) is missing, create it: `bash REPO/run/scripts/setup_env.sh` on Mac; on Windows `python -m venv %USERPROFILE%\.dhap-gbp-venv` then `pip install -r REPO/engine/requirements.txt` and `python -m playwright install chromium` with that venv. Never repeat this once it exists.

**3. Business info.** The user gives only the dealership name and website. Read the city, state, street address and brand from the website and the Google listing (the website settles same-name dealers in different towns). Mitsubishi → MiDS, Jessica, RULE I. Any other brand → the NON-MITSUBISHI ADAPTATION section of SKILL.md. Ask only if the website is missing.

**4. Knowledge base — always read it.** Use the GHL integration's knowledge-base operations: list the sub-account's knowledge bases (the location comes from the connection), pick the one named "Mitsubishi CLIKsearch" (match the name with surrounding spaces trimmed) — if not exactly one match, stop and tell the user — then list all of its FAQs and check every program fact the report states against them (pricing, posts and photos per month, go-live, results figures and labels, start-up order, schema build). Do not skip this step or report it as unavailable while the GHL integration is connected; look for its tools first. Only when no GHL integration exists in the session, use the facts stated in SKILL.md and say so in the delivery message. Never write the knowledge base id or the location id into any page or file.

**5. Audit and record evidence** exactly as `REPO/run/references/evidence-capture.md`. Use **Claude in Chrome** (the user's signed-in Chrome), read-only, by default and without asking. Save a screenshot for every number, tile and stat card that will carry a popup (RULE K scope: top hero numbers on the DHAP Summary and AI Visibility, Alert tiles and stat cards), crop it to the claim, blur reviewer names, and crop out any account name, avatar or notification. Anything you cannot observe is "not recorded" — never guessed — and no overall score is published while evidence is incomplete. Optional checks run on their own when available: `engine/places.py` and `engine/jev.py` use the team key service (`DHAP_SERVICE_URL` + `DHAP_TEAM_CODE`) and skip quietly otherwise.

**6. Score.** Write the evidence JSON (fields as `REPO/engine/examples/evidence-example-james.json` or `REPO/reference/james-2026-10-20/evidence.json`) and run `python3 REPO/engine/score.py score evidence.json --repo REPO`. Report edge warnings.

**7. Findings and wording** from evidence only (no review-markup finding, "Both views" for departments, evidence tags, competitor notes). Write the content JSON (as `REPO/reference/james-2026-10-20/content.json`) with `"dhap_url": "REPLACE_WITH_DHAP_FUNNEL_LINK"` — the funnel link is always added by hand; never guess it.

**8. Build and check.**
- Mitsubishi dealers: `python3 REPO/engine/check_all.py --repo REPO --evidence evidence.json --content content.json --out OUT` (all seven gates must pass).
- Other brands: build from the templates per `REPO/run/references/build-guide.md` and the NON-MITSUBISHI ADAPTATION (pattern: `REPO/run/scripts/example_build_vacaville.py`), then run `REPO/run/scripts/run_assertions.py`, `probe_mobile.py` and `spellcheck.py` with the venv's Python; skip only the Mitsubishi-only suite lines and list each skip.
- **RULE K popups:** write the popup spec for the in-scope numbers, tiles and stat cards only, then run `REPO/scripts/proof_popup.py spec.json proof_dir --insert DHAP.html ALERT.html` (adds the block and the hint lines), then `REPO/scripts/check_proof_popups.py DHAP.html ALERT.html` with the venv's Python — it checks scope and taps every popup on 390 px and 360 px phones, and must say PASSED.

**9. Rep brief.** Write an internal `<dealership-name>_rep-brief_<MM-DD-YY>.md` (never sent to the dealer): the score in one breath with a one-line reason per category; what to lead with (proven findings) and what to credit; every judgment call explained in plain words with how to say it to the dealer; what changed since the last report (re-runs); a note on any listing-site phone number that differs from the website (SKILL.md DIRECTOR'S CHECKS 5: may be a tracking number, inferred effect on AI visibility and local search, how to ask); honest answers to likely questions; what not to say; what was not verified.

**10. Deliver.** File names (dealership name as given, lowercase, hyphens; audit date): `<name>_dhap_<MM-DD-YY>.html`, `<name>_health-alert_<MM-DD-YY>.html`, `audit_evidence_<name>_<MM-DD-YY>.md`, `<name>_rep-brief_<MM-DD-YY>.md`. Send all four to the user. Finish with: score, status and what sets it; judgment calls; anything not observable; every departure from the locked spec (and why); anything unverified. Do not list the funnel link: it is always the placeholder `REPLACE_WITH_DHAP_FUNNEL_LINK` and is added by hand. Close the Chrome tabs you opened. Publish nothing unless asked.

**11. Rule changes** happen only by pull request to the repository. If you notice a rule problem, tell the user as a suggested repository change.
