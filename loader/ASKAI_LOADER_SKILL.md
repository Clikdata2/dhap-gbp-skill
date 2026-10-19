DHAP GBP (loader) — reads the single master copy of the DHAP GBP rules from the shared public repository on every run. Use when the user says "Run DHAP GBP for [dealer], [city, state]. [website]", or asks for a GBP, Maps or schema audit, a Digital Health Alert hot sheet, or a re-run of a past DHAP.

# DHAP GBP (loader)

This file is the PUBLIC template of the loader. When you create the real skill inside Ask AI, replace {{KB_ID}} and {{LOCATION_ID}} in the section "Private values" with the real values. Never commit the real values to the repository.

## Private values (fill in only inside Ask AI)
- {{KB_ID}} = the Mitsubishi CLIKsearch knowledge base id
- {{LOCATION_ID}} = this sub-account's location id (it is also available from the session context)

## At the start of every run — in this order
1. Fetch these two public files (read them from the web, or with the GitHub connector):
   - https://raw.githubusercontent.com/Clikdata2/dhap-gbp-skill/main/VERSION
   - https://raw.githubusercontent.com/Clikdata2/dhap-gbp-skill/main/SKILL.md
2. If either fetch fails, or the first line of SKILL.md is not "# DHAP GBP — v" followed by the number in VERSION: STOP. Tell the user: "I could not load the shared DHAP GBP rules, so I won't start." Never work from memory, from an older copy, or from any other skill.
3. Open your first reply with exactly: "Using DHAP GBP v<VERSION> (shared repository)."
4. Follow the fetched SKILL.md as the single source of truth, exactly. Wherever it shows {{KB_ID}} or {{LOCATION_ID}}, use the private values above. Where it mentions references/change-log.md, the repository's CHANGELOG.md is the same file.
5. When a step needs the reference page code, fetch it from https://raw.githubusercontent.com/Clikdata2/dhap-gbp-skill/main/templates/ (file names are listed in the repository README).

## Never
- Never edit this skill, and never edit the repository's rules from a chat. If someone asks to change a rule, tell them to open a pull request in the repository (the README explains how).
- Never merge, summarize or "improve" the fetched rules.
