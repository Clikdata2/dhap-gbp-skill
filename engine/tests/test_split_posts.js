// Unit test for dhapSplitPosts: the posts page text must become one piece per post, each with its own date.
// Layout copied from the live Vacaville "See local posts" page (Oct 20 2026). Run: node tests/test_split_posts.js [rounds]
const fs = require('fs');
let ok = true;
const T = (name, cond, extra) => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : ' ' + JSON.stringify(extra))); ok = ok && cond; };
for (const file of ['maps_collect.js', 'maps_collect.min.js']) {  // test the source AND the paste file, so the packing step cannot break it
  const src = fs.readFileSync(__dirname + '/../collectors/' + file, 'utf8');
  const split = new Function(src.slice(0, src.indexOf('async function dhapMaps')) + '; return dhapSplitPosts;')();
  const page = 'Vacaville Mitsubishi\n\nVacaville Mitsubishi\n16 hours ago\n\n\nScary Good Oil Change Deals\nValid Oct 19 - Oct 31\nView Offer\n6 days ago\n\n\nPRESENTING SPONSOR of Boo Bash. Tickets: $25\nLearn more\nOct 8, 2026\n\n1.99% APR for 72 Months\nView Offer\nAug 1, 2026\n\nSummer update';
  const p = split(page);
  T(file + ': 4 posts found', p.length === 4, p.map(x => x.date));
  T(file + ': dates are the date lines only', JSON.stringify(p.map(x => x.date)) === JSON.stringify(['16 hours ago', '6 days ago', 'Oct 8, 2026', 'Aug 1, 2026']), p.map(x => x.date));
  T(file + ': each piece holds its own words', /Oil Change/.test(p[0].text) && !/Boo Bash/.test(p[0].text) && /Boo Bash/.test(p[1].text) && /APR/.test(p[2].text), p.map(x => x.text.slice(0, 30)));
  T(file + ': no bare-date pieces (the capture-group bug)', p.every(x => x.text.length > x.date.length), p);
  T(file + ': no posts -> empty list', split('Vacaville Mitsubishi\n\nNo updates').length === 0);
  T(file + ': a date inside the words does not start a new post', split('X\n6 days ago\n\nEvent on Oct 30, 2026 downtown\nLearn more').length === 1);
  T(file + ': last post with no line after its date', split('X\n2 days ago').length === 1 && split('X\n2 days ago')[0].date === '2 days ago');
}
process.exit(ok ? 0 : 1);
