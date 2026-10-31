// fbsfilter unit test: compute() over a site's data drops games with a non-FBS side. usage: node fbsfilter_unit.js <site> <rootables.js> [old rootables.js]
const fs = require('fs'), path = require('path'); const [SITE, NEW, OLD] = process.argv.slice(2).map((p) => p && path.resolve(p));
const J = (r) => JSON.parse(fs.readFileSync(path.join(SITE, r), 'utf8'));
const idx = J('data/whatif/index.json'), bun = J('data/sim-bundle.json'), by = {}, sh = {}; (bun.teams || []).forEach((t) => { if (t.n) by[t.n] = t; });
const fcs = idx.team_names.indexOf('FCS opponent'), nonFBS = new Set(idx.team_names.map((n, i) => (by[n] && by[n].g ? -1 : i)).filter((i) => i >= 0));
function run(file) { delete require.cache[file]; const RB = require(file); const games = RB.buildGames(idx, bun);
  const ctx = { index: idx, games, asOfMs: RB.mtMs(idx.as_of), by, shard: (w, id) => { if (!(w in sh)) { const f = idx.shards[w]; sh[w] = f ? J('data/whatif/' + f) : null; } return (sh[w] && sh[w][id]) || null; } };
  const out = {}; idx.team_names.forEach((n, t) => { if (!by[n] || !by[n].g) return; const r = RB.compute(t, 'blend', ctx, ctx.asOfMs); out[by[n].g] = r.rows; }); return out; }
const bad = (rows) => rows.filter((r) => nonFBS.has(r.h) || nonFBS.has(r.a));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const N = run(NEW); const tot = Object.values(N).reduce((a, r) => a + bad(r).length, 0);
ok(tot === 0, 'patched: rows with a non-FBS side across all ' + Object.keys(N).length + ' FBS teams = ' + tot);
for (const s of ['duke', 'ole-miss']) ok(N[s] && !N[s].some((r) => r.h === fcs || r.a === fcs), s + ' rows exclude the FCS game (' + (N[s] || []).length + ' rows)');
if (OLD) { const O = run(OLD); const ot = Object.values(O).reduce((a, r) => a + bad(r).length, 0); console.log('info old rootables.js: non-FBS rows = ' + ot + ' (duke ' + bad(O.duke).length + ', ole-miss ' + bad(O['ole-miss']).length + ')');
  let same = 0, diff = []; for (const s in O) { const a = O[s].filter((r) => !(nonFBS.has(r.h) || nonFBS.has(r.a))).map((r) => r.id).join(), b = N[s].map((r) => r.id).join(); if (a === b || (O[s].length === 8 && a === b.slice(0, a.length))) same++; else diff.push(s); }
  ok(diff.length === 0, 'only change vs old = the dropped rows (slots refill from the next-biggest): teams checked ' + same + (diff.length ? ' diff ' + diff : '')); }
console.log(fail ? 'FBSFILTER_UNIT FAIL ' + fail : 'FBSFILTER_UNIT PASS'); process.exit(fail ? 1 : 0);
