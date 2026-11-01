#!/usr/bin/env node
/* Batch B share cards, data half (SHARE-SPEC rev 3, 1b18d56c). For every team page: the FULL blended Rootables list, computed by the site's own
   assets/rootables.js compute(tn,'blend') at the data as-of (cfp12 + ccg from /data/whatif, max swing, own + started games left off, 7-day window,
   1.0-pt threshold, ties to Playoff, 'title' never read): the exact rows the page lists (cap 8). Read-only; prints JSON in card3.py's format.
   Built from batchB/og/og_data.js (audit2 parked top-3 version). usage: node og_rows.js <site> */
const fs = require('fs'), path = require('path'); const SITE = path.resolve(process.argv[2] || '.');
const J = (r) => JSON.parse(fs.readFileSync(path.join(SITE, r), 'utf8'));
const RB = require(path.join(SITE, 'assets/rootables.js'));   /* rootables-shared: rows come from data/rootables/<slug>.json (tools/gen_rootables.js), the ONE source home and the team page also read */
const idx = J('data/whatif/index.json'), bun = J('data/sim-bundle.json'), games = RB.buildGames(idx, bun), sh = {}, by = {};
(bun.teams || []).forEach((t) => { if (t.n) by[t.n] = t; });
const ctx = { index: idx, games, asOfMs: RB.mtMs(idx.as_of), by, shard: (w, id) => { if (!(w in sh)) { const f = idx.shards[w]; sh[w] = f ? J('data/whatif/' + f) : null; } return (sh[w] && sh[w][id]) || null; } };
const LG = JSON.parse(/MAP = (\{.*?\}\}), PAD/s.exec(fs.readFileSync(path.join(SITE, 'assets/lg.js'), 'utf8'))[1]).t;
const TC = {}; { const css = fs.existsSync(path.join(SITE, 'assets/tc.css')) ? fs.readFileSync(path.join(SITE, 'assets/tc.css'), 'utf8') : ''; let m; const re = /\.tc-([a-z0-9-]+)\{--tc:(#[0-9A-Fa-f]{6})\}/g; while ((m = re.exec(css))) TC[m[1]] = m[2].toUpperCase(); }
let CFP = {}; try { const c = J('data/tb/cfp-rankings.json'); if (c.released) (c.teams || []).forEach((x) => { CFP[x.slug] = x.rank; }); } catch (e) {}   /* spec: cfp_rank or null (no rank before the first CFP release) */
const confName = {}; (bun.confs || []).forEach((c) => { confName[c.code] = c.name; });
const slugOf = (i) => (by[idx.team_names[i]] || {}).g || '', nm = (i) => { const n = idx.team_names[i], t = by[n]; return (t && (t.s || t.n)) || n; };
const side = (i) => { const g = slugOf(i), l = (LG[g] || [])[0]; return { name: nm(i), id: l ? +l : null, slug: g, rank: CFP[g] || null }; };
const DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
function when(r) {   /* real kickoff from the data: {day:'Sat Oct 31', time:'1:45 PM' | null (TBD)}; zone America/Denver (TBD kickoffs carry a UTC date only) */
  const f = new Intl.DateTimeFormat('en-US', { timeZone: r.tba ? 'UTC' : 'America/Denver', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }).formatToParts(new Date(r.kick));
  const p = {}; f.forEach((x) => { p[x.type] = x.value; }); return { day: p.weekday + ' ' + p.month + ' ' + p.day, time: r.tba ? null : p.hour + ':' + p.minute + ' ' + p.dayPeriod }; }
const iso = (ms) => new Date(ms).toISOString().slice(0, 16);
const out = { as_of: idx.as_of, stamp: RB.stampText(idx.as_of), teams: {} };
fs.readdirSync(path.join(SITE, 'team')).sort().forEach((slug) => {
  if (!fs.existsSync(path.join(SITE, 'team', slug, 'index.html'))) return;
  const f = path.join(SITE, 'data/rootables', slug + '.json'); if (!fs.existsSync(f)) return;
  const d = JSON.parse(fs.readFileSync(f, 'utf8')); if (d.as_of !== idx.as_of) { console.error('og_rows: stale data/rootables/' + slug + '.json'); process.exit(3); }
  const S = (g, n) => { const l = (LG[g] || [])[0]; return { name: n, id: l ? +l : null, slug: g, rank: CFP[g] || null }; };
  const rows = d.rows.map((r) => { const rootH = r.root.g === r.h, home = rootH ? S(r.root.g, r.root.n) : S(r.other.g, r.other.n), away = rootH ? S(r.other.g, r.other.n) : S(r.root.g, r.root.n), w = when({ kick: r.k, tba: !!r.t });
    return { ko: iso(r.k), day: w.day, time: w.time, when: w.day + ' \u00b7 ' + (w.time ? w.time + ' MT' : 'time TBD'), away, home, root: rootH ? 'home' : 'away', neutral: !!r.neutral,
      race: r.tag.replace(/\u00a0/g, ' '), gain: Math.round(r.g) / 10, gain_txt: r.pts, color: TC[r.root.g] || '#121519', why: r.why }; });
  out.teams[slug] = { team: d.team, n_big: d.n_big, n_window: d.n_window, games: rows };
});
process.stdout.write(JSON.stringify(out));
