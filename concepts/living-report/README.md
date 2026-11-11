# Living Report — design concept (not a rule)

A test of the DHAP and the Digital Health Alert as interactive infographics: one continuous, guided scroll instead of
tabs and separate screens. Sample: James Mitsubishi Greece (Oct 20 2026 audit).

- `james-mitsubishi-greece_dhap_living.html` — the DHAP
- `james-mitsubishi-greece_health-alert_living.html` — the Digital Health Alert

Open either file in a browser. Nothing in `SKILL.md`, the engine or the templates changes; live reports are built
exactly as before.

## What it does

**No new facts and no new product wording.** `build.py` first builds the normal pages with `engine/build.py`, reads
the text out of them, and lays the same text out again. The only text not taken from the built pages is the
"Next steps" stepper, which quotes `knowledge-base/jessica-kb-qa.json`; the build checks each sentence against the
knowledge base and leaves the stepper out if one is no longer there.

**DHAP**

| Idea (from the interactive-infographic examples) | Where it is used |
|---|---|
| A story on a spine that the scroll moves along | The eight tabs become eight chapters joined by a progress line that runs from red (the findings) to green (the fix); the tab bar stays as the chapter rail |
| The idea and the mechanic are the same thing | A health check: the score is a gauge, a pulse line opens and closes the report |
| Stats behind hotspots | The RULE K proof panel (v16.8) on the eight top stats |
| The legend is the control | The scorecard is a bar chart; its four status bands filter it, each row opens to show how its 10 points add up |
| Overview first, detail on demand | Findings, AI signals and long cards open on click; findings filter by group |
| A map of what is there and what is missing | "Both views": website schema next to Google listings, per department |
| The page helps the reader decide | Opportunities read as finding → CLIKsearch action |
| The infographic is the storefront | The 3-Pack as three profile cards, omni-social as one GBP post going to six platforms |
| Step-by-step toggle | Next steps, from the knowledge base |

**Alert** — the same three screens, same order, same words, as one monitored scroll: the breadcrumb follows the reader
(later steps stay locked until reached), the step buttons are replaced by the line that sat above each one, at the button's type
size (a click on it scrolls to the next screen), alerts fire and numbers count as
they come into view.

## Rebuild

```bash
python3 concepts/living-report/build.py \
  --evidence reference/james-2026-10-20/evidence.json --content reference/james-2026-10-20/content.json \
  --proof-spec reference/james-2026-10-20/proof-spec.json --proof-images reference/james-2026-10-20/proof \
  --out concepts/living-report
```

Any dealer's evidence and content files work the same way. The concept pages carry no Clarity tracking.
