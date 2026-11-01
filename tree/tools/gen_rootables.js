#!/usr/bin/env node
/* rootables-shared (Nov 1, 2026): the ONE Rootables data source. For every team page, the blended list (assets/rootables.js compute(tn,'blend') at the
   data as-of: max of playoff and reach-conference-championship-game swing, own and non-FBS games left off, 7-day window, 1.0-pt threshold, cap 8) plus the
   why sentence (assets/ktwhy.js), written to data/rootables/<slug>.json. Home (pk.js), the team page bake (bake_static.js) and the share cards
   (og/og_rows.js) all read these files, so every surface shows the same games, order and numbers. Replaces the Python ranking port in build_tile_data.py.
   Deterministic (no clock, no network). usage: node gen_rootables.js <site> [--check]  (--check: exit 3 if any file would change) */
'use strict';
const fs = require('fs'), path = require('path');
const SITE = path.resolve(process.argv[2] || '.'), CHECK = process.argv.includes('--check');
function die(m) { console.error('ROOTABLES FAIL: ' + m); process.exit(3); }
const J = (r) => JSON.parse(fs.readFileSync(path.join(SITE, r), 'utf8'));
const RB = require(path.join(SITE, 'assets/rootables.js')), WCP = path.join(SITE, 'assets/ktwhy.js'), WC = fs.existsSync(WCP) ? require(WCP) : null;   /* why text only when the site ships ktwhy.js (home/team why: held) */
const idx = J('data/whatif/index.json'), bun = J('data/sim-bundle.json'), PT = J('data/pred-teams.json');
const games = RB.buildGames(idx, bun), sh = {}, by = {};
(bun.teams || []).forEach((t) => { if (t.n) by[t.n] = t; });
const asOfMs = RB.mtMs(idx.as_of); if (asOfMs === null) die('as_of not parseable: ' + idx.as_of);
const ctx = { index: idx, games, asOfMs, by, shard: (w, id) => { if (!(w in sh)) { const f = idx.shards[w]; sh[w] = f ? J('data/whatif/' + f) : null; } return (sh[w] && sh[w][id]) || null; } };
const confName = {}; (bun.confs || []).forEach((c) => { confName[c.code] = c.name; });
const RC = WC ? WC.records(bun) : null;
const slugOf = (i) => (by[idx.team_names[i]] || {}).g || '', nm = (i) => { const n = idx.team_names[i], t = by[n]; return (t && (t.s || t.n)) || n; };
const asc = (s) => s.replace(/[\u007f-\uffff]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));   /* ASCII-only JSON: no literal NBSP anywhere */
const outDir = path.join(SITE, 'data/rootables'); if (!CHECK) fs.mkdirSync(outDir, { recursive: true });
let n = 0, changed = 0, rowsN = 0; const seen = new Set();
for (const slug of fs.readdirSync(path.join(SITE, 'team')).sort()) {
  if (!fs.existsSync(path.join(SITE, 'team', slug, 'index.html'))) continue;
  const key = Object.keys(by).find((k) => by[k].g === slug); const tn = key ? idx.team_names.indexOf(key) : -1; if (tn < 0) continue;
  const conf = confName[(by[key] || {}).c] || '', team = nm(tn), res = RB.compute(tn, 'blend', ctx, asOfMs);
  const rows = res.rows.filter((r) => slugOf(r.h) && slugOf(r.a)).map((r) => ({
    id: r.id, k: r.kick, t: r.tba ? 1 : 0, race: r.race, tag: RB.tagText(r.race, conf), g: r.gap, pts: RB.pts(r.gap), also: RB.alsoText(r.sec, conf),
    when: RB.whenCard(r), d: RB.whenShort ? RB.whenShort(r) : '', wl: RB.whenLong(r),
    root: { n: nm(r.root), g: slugOf(r.root) }, other: { n: nm(r.other), g: slugOf(r.other) }, h: slugOf(r.h), a: slugOf(r.a), neutral: r.neutral ? 1 : 0,
    where: r.neutral || r.root === r.h ? 'vs' : 'at', pP: r.pP, pC: r.pC, sec: r.sec || null,
    why: !WC ? '' : WC.why({ s: slug, sn: team, row: r, rootSlug: slugOf(r.root), otherSlug: slugOf(r.other), rootName: nm(r.root), otherName: nm(r.other), T: PT.teams, F: PT.field, B: bun, R: RC }).text }));
  const doc = { v: 1, as_of: idx.as_of, seasons: idx.seasons, slug, team, conf, n_big: res.nBig, n_window: res.nWindow, n_hidden: res.nHidden, has_own: !!res.hasOwn, rows };
  const body = asc(JSON.stringify(doc)) + '\n', p = path.join(outDir, slug + '.json'); seen.add(slug + '.json');
  const old = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
  if (old !== body) { changed++; if (!CHECK) fs.writeFileSync(p, body); }
  n++; rowsN += rows.length;
}
if (n < 130) die('only ' + n + ' teams');
if (CHECK && changed) die(changed + ' rootables files stale');
console.log('rootables: ' + n + ' teams, ' + rowsN + ' rows, ' + changed + ' changed, as_of ' + idx.as_of);
