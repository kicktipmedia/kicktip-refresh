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
const py = J(HUB + '/data.json'), NAME = { 'Utah Utes': 0 };
ok(R.mtMs('2026-10-24 17:55 MT') === Date.UTC(2026, 9, 24, 23, 55), 'mtMs MDT'); ok(R.mtMs('2026-11-02 17:55 MT') === Date.UTC(2026, 10, 3, 0, 55), 'mtMs MST');
ok(R.stampText('2026-10-24 17:55 MT') === 'Oct 24, 2026, 5:55 PM MT', 'stamp text');
['blend', 'elo', 'eff'].forEach(model => {
  const c = ctxFor(model), p = py[model], nm = c.index.team_names;
  ok(c.index.as_of === p.as_of && c.index.seasons === p.seasons, model + ' stamp/seasons');
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
let u = show(U, 'cfp12'); ok(u[0] === 'Utah Utes 52.0% 18.9% +33.1' && u[1] === 'Utah Utes 48.5% 19.4% +29.1', 'Utah make12 ' + u.slice(0, 2));
u = show(U, 'ccg'); ok(u[0] === 'Utah Utes 61.3% 23.2% +38.1' && u[1] === 'Utah Utes 56.2% 26.3% +29.9', 'Utah ccg ' + u.slice(0, 2));
u = show(B, 'cfp12'); ok(u[0] === 'BYU Cougars 70.8% 28.1% +42.7', 'BYU make12 ' + u[0]);
const ru = R.compute(U, 'cfp12', c, c.asOfMs); ok(ru.nWindow === 54 && ru.nBig === 10 && ru.nHidden === 44 && ru.rows.length === 5 && ru.hasOwn, 'Utah 54 window/10 big/44 hidden');
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
ok(sr.rows.map(r => r.id).join(',') === 'f,g,e,d,c', 'order largest first, ties by earlier kickoff, max 5: ' + sr.rows.map(r => r.id)); 
ok(sr.nBig === 7 && sr.nWindow === 8 && sr.nHidden === 1, 'gap 10 shown, gap 9 hidden: ' + [sr.nBig, sr.nWindow, sr.nHidden]);
ok(sr.rows[3].root === 2 && sr.rows[3].pRoot === 600, 'root for the side with the higher chance (away)');
const none = { index: idx, asOfMs: 0, games: [defs[0].g], shard: () => ({ h: [], a: [] }) }; const rn = R.compute(0, 'cfp12', none, 0); ok(rn.nWindow === 1 && rn.nBig === 0, 'unlisted team = baseline = 0 gap');
const ipg = { index: idx, asOfMs: 0, games: [Object.assign({}, defs[2].g, { ip: true })], shard: () => defs[2].s }; ok(R.compute(0, 'cfp12', ipg, 0).nWindow === 0, 'in progress dropped');
const tba = Object.assign({}, defs[2].g, { tba: true, kick: 1e6 }); ok(R.compute(0, 'cfp12', { index: idx, asOfMs: 0, games: [tba], shard: () => defs[2].s }, 1e6 + 5e7).nWindow === 1 && R.compute(0, 'cfp12', { index: idx, asOfMs: 0, games: [tba], shard: () => defs[2].s }, 1e6 + 9e7).nWindow === 0, 'TBA day lasts to the end of the day');
console.log(`rootables_unit: ${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
