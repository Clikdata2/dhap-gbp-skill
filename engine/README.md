# DHAP GBP engine — the same audit, faster and cheaper

The rules still live in `SKILL.md`, and only there. This folder holds the tools that **follow** those rules. It does the slow, repeated parts of an audit the same way every time, so a run takes fewer steps, costs less, and makes fewer mistakes.

The engine never changes a rule. It reads `SKILL.md` each time it runs. If the scoring rules change, the engine **stops** and says so, until `score.py` is updated in the same pull request.

## How a run goes

1. **Collect.** Open the dealer's website and Google Maps listing in the signed-in Chrome. Paste `collectors/schema_collect.min.js` on the website and `collectors/maps_collect.min.js` on the Maps listing. Each one does in one step what used to take 8 to 15 steps, and gives back a short answer.
2. **Record.** Write what you saw in an evidence file, including the AI answer check (`ai_answers`). Copy `examples/evidence-example-vacaville.json` and change it. Every group needs a "method" (how you checked) and a "when" (the date).
3. **Write.** Write the report wording in a content file. Copy `examples/content-example-vacaville.json` and change it. It holds only words and numbers, not page code.
4. **Check and build.** Run one command:
   `python3 engine/check_all.py --evidence ev.json --content content.json --out OUT`
   It runs seven checks in order and stops at the first one that fails. If all pass, both pages are built and checked.
5. **Review and publish** as before (SKILL.md step 8).

## The seven checks (`check_all.py`)

| # | Check | What it stops |
|---|---|---|
| 1 | Rules guard | Scoring with rules that changed since the engine was checked |
| 2 | Evidence check | A missing, wrong-type or impossible fact, or a fact with no method and date |
| 3 | Facts gate | Any number or phone number in the report that is not in the evidence ("never restate a number you can't source") |
| 4 | Build | Unsafe page code, leftover placeholders, wrong counts, a changed template |
| 5 | Repository assertions | Everything in the SKILL.md assertion suite, read fresh from SKILL.md each run |
| 6 | Phone-width test | Pages that break at 360, 390 or 430 pixels wide |
| 7 | Spelling | Listed for a person to check (does not stop the run) |

## What is in here

| File | What it does |
|---|---|
| `collectors/schema_collect.js` | Reads the structured data (JSON-LD) on the 5 key pages and fills the schema evidence |
| `collectors/maps_collect.js` | Reads a Google Maps listing: rating, reviews, categories, About, posts (last 30 days), the 10 newest reviews and owner replies. It is read-only: it refuses to click Claim, Suggest an edit, Write a review, Add photos, Post, Save or Share |
| `*.min.js` | The same collectors, packed for pasting. Make them with `python3 minify.py collectors/*.js` |
| `score.py` | Turns evidence into the 8 scores, the overall score and the status, exactly as the rubrics say |
| `facts.py` | The facts gate |
| `build.py` | Builds the full report and the health alert from the templates in `templates/` |
| `check_all.py` | Runs all seven checks |
| `jev.py` | Optional second opinion on post types (see below) |
| `alert_cards.py` | Rule 7 (v15.2): picks the four Alert stat cards from the dealer's weakest areas and writes the Revenue Impact paragraph |
| `directories.py` | Rule 8 (v15.2): decides each directory's NAP match from the saved readings |
| `ai_answers.py` | AI answer check (v15.1, every run): checks the saved answers of 7 AI tools to 3 questions plus the Bing and Apple Maps cards, and writes the rep-brief table and flags. The evidence check refuses to score without it |
| `places.py` | Optional Google Places cross-check of the Maps collector (see below) |
| `probe_mobile.py`, `spellcheck.py` | Checks 6 and 7 |
| `examples/` | James Mitsubishi Greece (the locked reference) and Vacaville Mitsubishi, plus live Chrome readings for those two and Music City Mitsubishi |
| `tests/` | Stress tests (below) |

## Optional: JEV second opinion

`jev.py` asks JEV (a decision model from TypeSafe, called directly at api.typesafe.ai) whether each recent post is an offer or an event.

- **The score never comes from JEV.** The score always uses the fixed rules, so the same evidence always gives the same score.
- If JEV disagrees with the rules, or is unsure, the listing is flagged for a person to look at.
- It needs `TYPESAFE_API_KEY` set on your computer (a key from typesafe.ai). **Never put the key in this repository.** Without a key it is skipped, and the audit goes on.
- Cost: $0.042 per million word pieces it reads (input tokens), so about $0.00003 per listing. The answer is free.

## Optional: Google Places cross-check

`places.py` looks the listing up in Google's Places API (New) and compares it with what the Maps collector read in Chrome: name, rating, review count, phone, street address and website.

- **It never changes a score or the evidence.** Any difference is listed for a person to look at: a misread page, a listing that just changed, or the wrong listing.
- It also returns the weekly hours Google shows, which the collector does not read. Use them for the hours checks.
- It cannot see posts, photo dates, newest-first reviews or owner replies, so the Chrome step is still needed.
- It needs `GOOGLE_PLACES_API_KEY` set on your computer (a Google Cloud key with "Places API (New)" turned on). **Never put the key in this repository.** Without a key it is skipped, and the audit goes on.
- Cost: finding the listing is free. Reading it is one call; the first 1,000 a month are free, then $0.02 each.
- Run: `python3 engine/places.py "Dealer, street, city, state" maps.json` (maps.json = the collector's answer).

## Ways to keep a run cheap

- **Start each audit in a fresh chat session.** In a long session, every step re-reads all the earlier work, so later steps cost several times more.
- Use the collectors instead of clicking through pages one by one.
- Write a content file (about 20 KB) instead of a new build script for each dealer (about 42 KB).

## Tests

Run them all (each stress test repeats 3 rounds):

```
pip install -r engine/requirements.txt && python3 -m playwright install chromium
bash engine/run_tests.sh
```

| Test | What it tries to break |
|---|---|
| `test_score.py` | The locked James scores, the Vacaville scores, every status edge, 11 kinds of bad evidence, a changed rule, and 2,000 random evidence files |
| `test_build.py` | James, Vacaville, all four status colors, odd dealer names, 10 kinds of bad content, a changed template, the phone-width test; the same input must give the same pages every time |
| `test_schema_collector.py` | 5 test websites: `@graph` and links between blocks, broken JSON, very large pages, a menu trap, a bad `@context` |
| `test_split_posts.js`, `test_post_variety.js` | Splitting the posts page into single posts, and judging offers, events and calls to action on real post text |
| `test_paste_files.py` | The pasted `.min.js` files must match their source exactly |
| `test_jev.py` | Every way the JEV call can fail (no key, wrong key, garbage reply, missing answers, bad numbers, a server that hangs, too many or too long posts), plus live checks on real posts when a key is set |
| `test_places.py` | Every way the Places lookup can fail, address / phone / website matching rules, a wrong listing, a closed business, plus live lookups of James, Vacaville and Music City when a key is set |

The test websites are made up. One copies the structure of a real dealer site, but every name, phone number and address in it is fake.
