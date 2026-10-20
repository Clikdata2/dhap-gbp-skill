// Unit test for dhapPostVariety with real post texts seen in the audits (Oct 2026). Run: node tests/test_post_variety.js
const src = require('fs').readFileSync(__dirname + '/../collectors/maps_collect.js', 'utf8');
const f = new Function(src.slice(0, src.indexOf('async function dhapMaps')) + '; return dhapPostVariety;')();
const T = (name, texts, want) => { const g = f(texts); const ok = JSON.stringify(g) === JSON.stringify(want); console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok ? '' : ' got ' + JSON.stringify(g))); return ok; };
let ok = true;
ok &= T('Music City Oct 15 (sales event = offer)', ['4 days ago\n\n0% APR for 72 Months on the 2026 Outlander\nValid Oct 15 - Nov 2\nYear End Sales Event at Music City Mitsubishi: 0% APR for 72 months on in-stock new 2026 Outlander models.\nView Offer'], { offers: true, events: false, cta: true });
ok &= T('Vacaville Boo Bash (real event)', ['6 days ago\n\nVacaville Mitsubishi is proud to be the PRESENTING SPONSOR of Downtown Vacaville Boo Bash! Grab your friends, bring your best costume. Tickets: $25 per person\nLearn more'], { offers: false, events: true, cta: true });
ok &= T('plain update, no button', ['Oct 2, 2026\n\nWondering what your car is worth near Vacaville, CA? Get a free, no-obligation trade-in appraisal.'], { offers: false, events: false, cta: false });
ok &= T('no posts at all', [], { offers: false, events: false, cta: false });
ok &= T('clearance sales event + call now', ['Oct 9, 2026\n\nClearance Sales Event this weekend only!\nCall now'], { offers: false, events: false, cta: true });
ok &= T('raffle with Call now', ['Sep 19, 2026\n\nSupport breast cancer awareness and enter for your chance to win. Barbara Pink Ribbon Raffle. 1 ticket: $20\nCall now'], { offers: false, events: true, cta: true });
ok &= T('service specials (deal words + prices)', ['Oct 6, 2026\n\nSCARY GOOD SERVICE DEALS! $39.95 FULL-SYNTHETIC OIL CHANGE. $50 OFF BRAKE PAD & ROTOR REPLACEMENT\nCall now'], { offers: true, events: false, cta: true });
ok &= T('whole Vacaville Sales month (5 posts together)', ['16 hours ago\nScary Good Oil Change Deals\nValid Oct 19 - Oct 31\nView Offer', '6 days ago\nPRESENTING SPONSOR of Boo Bash\nLearn more', 'Oct 8, 2026\n1.99% APR for 72 Months\nView Offer', 'Oct 7, 2026\nTAKE A RIDE PICK YOUR PUMPKIN free pumpkin with a test drive\nLearn more', 'Oct 2, 2026\nfree trade-in appraisal\nCall now'], { offers: true, events: true, cta: true });
process.exit(ok ? 0 : 1);
