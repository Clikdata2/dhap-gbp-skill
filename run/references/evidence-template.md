# <Dealership Name> — DHAP GBP v<VERSION> audit evidence (internal, not client-facing)

Audited <Mon DD, YYYY> · Report ID GBP-<XXXXX>-<MMYY> · Overall **<score> / 10** · Status **<label>** (lowest category: <row> <value>)
Rules: SKILL.md v<VERSION> (v13 rubrics, v14 status rule). Methods: <how each source was read — website page source via Chrome if the site blocks plain fetches; rendered-page checks; Google Maps, Google Search panel, Facebook, Apple Maps, Bing, Yelp, mitsubishicars.com in signed-in Chrome, read-only>. Photo and review ages are Google's approximate labels.

## Scores
| # | Category | Score | Working |
|---|---|---|---|
| 1 | GBP Claimed & Verified | | what was observed for each listing; duplicates searched |
| 2 | Profile Completeness | | structure points; checklist items done/total per listing (name the missing items) |
| 3 | Photos & Visual Presence | | photos in last 30 days per listing; logo/cover seen or not; coverage categories |
| 4 | Reviews & Reputation | | rating; newest review age per listing; owner replies of 10 newest; Facebook mode; visible on site |
| 5 | GBP Posts & Engagement | | posts in last 30 days with dates; newest date; variety (offers/events/CTAs) |
| 6 | Google Maps / NAP Consistency | | Google vs website fields; five-directory results; dept phone; map pin |
| 7 | LocalBusiness Schema | | pages with JSON-LD; type; department entities; parses; own page address / phone per entity |
| 8 | Schema Field Completeness | | core fields; logo; sameAs breakdown; areaServed; hasMap/map; offers |

## Phone numbers found
List every number with its source and which department it belongs to; count distinct local numbers; note possible call-tracking numbers as "not verified".

## AI answer check (v15.1, every run)
Paste the output of `python3 engine/ai_answers.py brief evidence.json`: one row per tool and question (named, position, phone and whether it matches the site, rating and its source, sources cited), then the flags. Blocked tools are listed with the reason.

## Other checks
Departments line (Search panel) · rendered-site reviews check (pages checked) · FAQ/other structured data · locator hours vs website · directory claim status · anything else that became a finding.

## Not directly observable / judgment calls (flagged)
List each item that could not be recorded and why, and each rubric judgment call with the alternative result.

## Corrections / notes
Anything that differs from an earlier run of the same dealer, or from the locked spec/template, and why.
