// Unit test of KTRootables.compute() against Creative's published-shard numbers (crosscheck.txt, data.json from compute.py).
// usage: node tests/rootables_unit.js [dataDir]   (default: the live copies Creative saved)
const fs = require('fs'), R = require('../src/assets/rootables.js');
const HUB = '/workspace/hub/kicktip-rootables', DIR = process.argv[2] || HUB + '/live/data';
let pass = 0, fail = 0; const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const J = f => JSON.parse(fs.readFileSync(f));
function ctxFor(model) {
  const b = DIR + (model === 'blend' ? '' : '/m/' + model), index = J(b + '/whatif/index.json'), bundle = J(fs.existsSync(b + '/sim-bundle.json') ? b + '/sim-bundle.json' : DIR + '/sim-bundle.json'), sh = {};
  Object.keys(index.shards).forEach(w => sh[w] = J(b + '/whatif/' + index.shards[w]));
  return { index, games: R.buildGames(index, bundle), asOfMs: R.mtMs(index.as_of), shard: (w, id) => (sh[w] && sh[w][id]) || null };
}
const py = J(__dirname + '/rootables_ref_noown.json')   /* Oct 31: reference = tests/rootables_ref_compute.py (Creative compute.py + own-game exclusion), run on the same saved live data */, NAME = { 'Utah Utes': 0 };
ok(R.mtMs('2026-10-24 17:55 MT') === Date.UTC(2026, 9, 24, 23, 55), 'mtMs MDT'); ok(R.mtMs('2026-11-02 17:55 MT') === Date.UTC(2026, 10, 3, 0, 55), 'mtMs MST');
ok(R.stampText('2026-10-24 17:55 MT') === 'Oct 24, 2026, 5:55 PM MT', 'stamp text');
['blend', 'elo', 'eff'].forEach(model => {
  const c = ctxFor(model), p = py[model], nm = c.index.team_names;
  ok(c.index.as_of === p.as_of && c.index.seasons === p.seasons, model + ' stamp/seasons');
  Object.keys(p.teams).forEach(tm => { const t = nm.indexOf(tm), r = R.compute(t, 'blend', c, c.asOfMs), x = p.teams[tm].blend;
    ok(r.nWindow === x.n_window && r.nBig === x.n_big && r.nHidden === x.n_hidden && r.rows.length === x.top.length, `${model} ${tm} blend counts`);
    r.rows.forEach((row, i) => { const y = x.top[i]; ok(row.id === y.id && row.gap === y.score && row.race === y.race && row.root === y.root && JSON.stringify(row.sec) === JSON.stringify(y.sec), `${model} ${tm} blend row ${i}`); }); });
  Object.keys(p.teams).forEach(tm => ['cfp12', 'ccg'].forEach(m => {
    const t = nm.indexOf(tm), r = R.compute(t, m, c, c.asOfMs), x = p.teams[tm][m];
    ok(r.nWindow === x.n_window && r.nBig === x.n_big && r.nHidden === x.n_hidden, `${model} ${tm} ${m} counts js ${r.nWindow}/${r.nBig}/${r.nHidden} py ${x.n_window}/${x.n_big}/${x.n_hidden}`);
    ok(r.rows.length === x.top.length, `${model} ${tm} ${m} rows`);
    r.rows.forEach((row, i) => { const y = x.top[i];
      ok(row.gap === y.gap && row.id === y.id && (row.root === (y.home_wins >= y.away_wins ? y.hid : y.aid)) && Math.max(row.pH, row.pA) === Math.max(y.home_wins, y.away_wins), `${model} ${tm} ${m} row ${i}`); });
  }));
});
// the named numbers
const c = ctxFor('blend'), nm = c.index.team_names, U = nm.indexOf('Utah Utes'), B = nm.indexOf('BYU Cougars');
const show = (t, m) => R.compute(t, m, c, c.asOfMs).rows.map(r => [nm[r.root], R.pc(r.pRoot), R.pc(r.pOther), '+' + R.pts(r.gap)].join(' '));
const ru = R.compute(U, 'cfp12', c, c.asOfMs), rb = R.compute(B, 'cfp12', c, c.asOfMs);
ok(ru.hasOwn && rb.hasOwn, 'Utah/BYU play this week (hasOwn kept for the bye line)');
ok(![U, B].some(t => ['cfp12', 'ccg'].some(m => R.compute(t, m, c, c.asOfMs).rows.some(r => r.h === t || r.a === t))), 'own game never listed (Utah, BYU)');
ok(nm.every((x, t) => !c.index.baseline[t] || !R.compute(t, 'cfp12', c, c.asOfMs).rows.some(r => r.h === t || r.a === t)), 'own game never listed (all teams)');
const lsu = R.compute(nm.indexOf('LSU Tigers'), 'cfp12', c, c.asOfMs); ok(!lsu.hasOwn && lsu.rows.length > 0, 'LSU bye');
const tn = R.compute(nm.indexOf('Tennessee Volunteers'), 'cfp12', c, c.asOfMs); ok(tn.nBig === 0 && tn.nHidden === 54, 'Tennessee none >=1.0');
// window: the clock moves the window; started games drop; in-progress flag drops
const later = R.compute(U, 'cfp12', c, c.asOfMs + 3 * 864e5); ok(later.nWindow < 54, 'window shrinks as the clock moves');
// synthetic: threshold 10 shown / 9 hidden, ties by earlier kickoff then id, max 5, unlisted team = baseline
const idx = { metrics: ['ccg', 'title', 'cfp12', 'bye'], seasons: 6000, as_of: 'x', baseline: [[0, 0, 500, 0], [0, 0, 500, 0], [0, 0, 500, 0], [0, 0, 500, 0]] };
const mk = (id, kick, pH, pA, extra) => ({ g: { id, week: 1, h: 1, a: 2, neutral: false, kick, tba: false, ip: false }, s: { h: [[0, 0, 0, pH, 0]], a: [[0, 0, 0, pA, 0]] } });
const defs = [mk('a', 5e5, 510, 500), mk('b', 4e5, 509, 500), mk('c', 3e5, 600, 500), mk('d', 2e5, 500, 600), mk('e', 1e5, 600, 500), mk('f', 6e5, 700, 500), mk('g', 7e5, 650, 500), mk('h', 8e5, 400, 500)];
const sc = { index: idx, asOfMs: 0, games: defs.map(d => d.g), shard: (w, id) => defs.find(d => d.g.id === id).s };
const sr = R.compute(0, 'cfp12', sc, 0);
ok(sr.rows.map(r => r.id).join(',') === 'f,g,e,d,c,h,a', 'order largest first, ties by earlier kickoff, all 7 under the cap of 8: ' + sr.rows.map(r => r.id)); 
ok(sr.nBig === 7 && sr.nWindow === 8 && sr.nHidden === 1, 'gap 10 shown, gap 9 hidden: ' + [sr.nBig, sr.nWindow, sr.nHidden]);
ok(sr.rows[3].root === 2 && sr.rows[3].pRoot === 600, 'root for the side with the higher chance (away)');
const none = { index: idx, asOfMs: 0, games: [defs[0].g], shard: () => ({ h: [], a: [] }) }; const rn = R.compute(0, 'cfp12', none, 0); ok(rn.nWindow === 1 && rn.nBig === 0, 'unlisted team = baseline = 0 gap');
const ipg = { index: idx, asOfMs: 0, games: [Object.assign({}, defs[2].g, { ip: true })], shard: () => defs[2].s }; ok(R.compute(0, 'cfp12', ipg, 0).nWindow === 0, 'in progress dropped');
const tba = Object.assign({}, defs[2].g, { tba: true, kick: 1e6 }); ok(R.compute(0, 'cfp12', { index: idx, asOfMs: 0, games: [tba], shard: () => defs[2].s }, 1e6 + 5e7).nWindow === 1 && R.compute(0, 'cfp12', { index: idx, asOfMs: 0, games: [tba], shard: () => defs[2].s }, 1e6 + 9e7).nWindow === 0, 'TBA day lasts to the end of the day');
// cap 8 (Oct 31 12:17): 10 qualifying games -> 8 rows, nBig 10
{ const d10 = [...Array(10).keys()].map(i => mk('z' + i, 1e5 * (i + 1), 520 + 10 * i, 500)); const s10 = R.compute(0, 'cfp12', { index: idx, asOfMs: 0, games: d10.map(d => d.g), shard: (w, id) => d10.find(d => d.g.id === id).s }, 0);
  ok(s10.rows.length === 8 && s10.nBig === 10 && s10.rows[0].id === 'z9' && s10.rows[7].id === 'z2', 'cap 8 of 10: ' + s10.rows.map(r => r.id)); }
{ const sb = R.compute(0, 'blend', sc, 0); ok(sb.rows.length <= 8, 'blend cap 8'); }
// blended list: own game never listed for any team; 'title' measure never read
ok(nm.every((x, t) => !c.index.baseline[t] || !R.compute(t, 'blend', c, c.asOfMs).rows.some(r => r.h === t || r.a === t)), 'blend: own game never listed (all teams)');
{ const ti = c.index.metrics.indexOf('title') + 1, cx = Object.assign({}, c, { index: Object.assign({}, c.index, { baseline: c.index.baseline.map(b => b.map((v, i) => i === ti - 1 ? NaN : v)) }), shard: (w, id) => { const s = c.shard(w, id); return s && { h: s.h.map(r => r.map((v, i) => i === ti ? NaN : v)), a: s.a.map(r => r.map((v, i) => i === ti ? NaN : v)) }; } });
  ok(nm.every((x, t) => !c.index.baseline[t] || JSON.stringify(R.compute(t, 'blend', cx, c.asOfMs)) === JSON.stringify(R.compute(t, 'blend', c, c.asOfMs))), "blend: poisoning the 'title' column changes nothing (title never read)"); }
console.log(`rootables_unit: ${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
