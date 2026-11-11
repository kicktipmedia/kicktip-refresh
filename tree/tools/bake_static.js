#!/usr/bin/env node
/* KickTip no-JS v1 baker. usage: node bake_static.js <siteDir> [--unbake] [--check]
   Bakes the default-model numbers into static HTML at publish time so pages show real numbers without JavaScript; kt.js/top25.js still
   draw on top with the SAME markup (ported 1:1 below; the suite compares baked vs JS-drawn DOM), so there is no flash and no layout shift.
   Inputs (site's own files only, no network, deterministic): data/pred-teams.json, data/pred-top25.json, data/pred-paths.json, data/polls.json,
   data/sim-bundle.json (as_of), assets/lg.js (logo map), assets/stamp.js (the one stamp-format helper).
   Every edit sits between <!--bk:N--> ... <!--/bk--> where N indexes DEF (the exact bytes it replaced), so --unbake restores the pre-bake HTML byte
   for byte. apply_data unbakes the base before its 3-way merge (pipeline sites are never baked) and bakes again after the data is regenerated.
   Bake = unbake + bake, so it is idempotent. Exit 3 on any problem (missing anchor, missing team, unparseable as-of). */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const SITE = process.argv[2], UNBAKE = process.argv.includes('--unbake'), CHECK = process.argv.includes('--check'), VERIFY = process.argv.includes('--verify');
function die(m) { console.error('BAKE FAIL: ' + m); process.exit(3); }
if (!SITE || !fs.existsSync(SITE + '/index.html')) die('usage: bake_static.js <siteDir> [--unbake]');
const DEF = ['', '&ndash;', '<span class="lk">Loading</span>', 'recently',
  '<noscript><p class="h25-js0">Turn on JavaScript to see the KickTip Top 25.</p></noscript>',
  'Turn on JavaScript to see the chances. Without it this page shows no simulation numbers.',
  '<tr><td colspan="3"><span class="lk">Loading</span></td></tr>',
  'Spreads: ESPN, numbers only, shown when one has been posted.',
  '<span class="lk">Loading</span>',   /* 8: audit2 game cells (wp/kl/mk/ln) on /games/, conference and team pages */
  '<noscript><p class="rb-msg">Turn on JavaScript to run Rootables.</p></noscript>',   /* 9: audit2 Rootables phase 2 (no-JS list) */
  '',   /* 10: audit2 polish2 next-game What If card (baked; unbake removes it) */
  '<li><span class="lk">Loading</span></li>',   /* 11: audit2 conference 'Who controls their destiny' */
  'What if BYU loses?',   /* 12 */
  '<div class="rn rtg rb-terms">Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></div><noscript><p class="rb-msg">Turn on JavaScript to see Rootables.</p></noscript>',   /* 13: rootables-shared (Nov 1): no Run tap; the visible terms line + the live Rootables list, baked from data/rootables/<slug>.json */
  'Compared with the AP and Coaches polls.',   /* 14: home Top 25 intro. Unbake restores this sentence. */
  'NR means not ranked by that poll.'];   /* 15: home Top 25 note. Unbake restores this sentence. */
const NOJS_TXT = 'Turn on JavaScript to switch rating systems and sort.';   /* audit2: the numbers are in the HTML now */
const MK = /<!--bk:(\d+)-->[\s\S]*?<!--\/bk-->/g;
const mk = (n, s) => '<!--bk:' + n + '-->' + String(s).replace(/\u00A0/g, '&nbsp;') + '<!--/bk-->';   /* HTML entities only: no literal NBSP in baked HTML (shared RB.* strings use \u00A0 for the DOM) */
function unbake(t) { return t.replace(MK, (m, n) => { if (DEF[+n] === undefined) die('unknown marker ' + n); return DEF[+n]; }); }
function walk(d, out = []) { for (const f of fs.readdirSync(d).sort()) { const p = path.join(d, f), s = fs.statSync(p); if (s.isDirectory()) walk(p, out); else if (f.endsWith('.html')) out.push(p); } return out; }
const files = walk(SITE);
if (UNBAKE) { let n = 0; for (const f of files) { const t = fs.readFileSync(f, 'utf8'), u = unbake(t); if (u !== t) { fs.writeFileSync(f, u); n++; } } console.log('unbaked', n, 'files'); process.exit(0); }

/* ---- helpers loaded from the site itself ---- */
const J = (r) => JSON.parse(fs.readFileSync(path.join(SITE, r), 'utf8'));
const K = require(path.resolve(SITE, 'assets/stamp.js'));
const sb = { window: {}, document: { addEventListener() {}, readyState: 'complete', querySelectorAll: () => [] }, console };
sb.window.addEventListener = () => {}; vm.createContext(sb); vm.runInContext(fs.readFileSync(path.join(SITE, 'assets/lg.js'), 'utf8'), sb);
const LG = sb.window.KTLogo; if (!LG || !LG.team) die('lg.js did not expose KTLogo');
const PT = J('data/pred-teams.json'), T = PT.teams, FIELD = PT.field || [], R = J('data/pred-top25.json'), PP = J('data/pred-paths.json'), POLLS = J('data/polls.json');
const ASOF = J('data/sim-bundle.json').as_of, ASOF_ATTR = String(ASOF || '').replace(/ MT$/, '');
const NBSP = (s) => s.replace(/\u00a0/g, '&nbsp;');
const STAMP = K.fmt(ASOF);   /* '' = unparseable: the new stamps are left out (rule 6) */
const upd = (cls) => STAMP ? mk(0, '<p class="kt-upd' + (cls ? ' ' + cls : '') + '">' + K.label + '<span class="kt-asof" data-asof="' + ASOF_ATTR + '">' + NBSP(STAMP) + '</span></p>') : '';
for (const k of Object.keys(T)) T[k].k = k;
/* Sources block: 'Spreads: ESPN · Updated <stamp>' from the spreads file's own pull time = the newest read time in /data/pred-lines.json (l[k] = [spread, read epoch s, kickoff]); missing/unparseable = no stamp (rule 6) */
let SP_STAMP = '', SP_ISO = '';
try { const L = J('data/pred-lines.json').l || {}; let m = 0; for (const v of Object.values(L)) if (Array.isArray(v) && typeof v[1] === 'number' && v[1] > m) m = v[1]; if (m) { SP_ISO = new Date(m * 1000).toISOString().replace(/\.\d+Z$/, 'Z'); SP_STAMP = K.fmt(SP_ISO); } } catch (e) { SP_STAMP = ''; }


/* ---- ported 1:1 from assets/kt.js (formatting, rowTop, fieldTable, teamTiles, chipHTML) ---- */
const MINUS = '\u2212', UP = '\u25B2', DN = '\u25BC';
function pct(p) { if (p === null || p === undefined) return 'n/a'; const v = Math.round(p * 100); if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%'; }
function bar(p) { return '<span class="bar" data-w="' + Math.round(Math.max(p > 0 ? 2 : 0, p * 48)) + '"></span>'; }
function cellPct(p) { return p === null || p === undefined ? '<span class="lk">n/a</span>' : bar(p) + pct(p); }
function esc(t) { return String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function chipHTML(k, t) {
  if (!t || !t.m) return ''; const up = t.m[0] > 0, n = Math.abs(t.m[0]);
  return '<button type="button" class="mv ' + (up ? 'up' : 'dn') + '" data-mv="' + esc(k) + '" aria-expanded="false" aria-haspopup="dialog" aria-label="' + esc(t.n) + ': ' + (up ? 'up ' : 'down ') + n + ' points since the last daily update. Show why."><span class="pl"><s aria-hidden="true">' + (up ? UP : DN) + '</s>' + (up ? '+' : MINUS) + n + '</span></button>';
}
function rowTop(t, i, logo, chip) {
  let nm = '<a class="tl" href="/team/' + t.k + '/">' + esc(t.n) + '</a>'; const cp = chip ? chipHTML(t.k, t) : ''; if (cp) nm = '<span class="tcn">' + nm + cp + '</span>';
  return '<tr><td class="n">' + (i + 1) + '</td><td>' + (logo ? '<span class="tnm">' + LG.team(t.k, 24, i >= 6) + nm + '</span>' : nm) + '</td><td>' + esc(t.cn) + '</td><td class="n">' + cellPct(t.p) + '</td><td class="n">' + cellPct(t.b) + '</td><td class="n">' + cellPct(t.c) + '</td><td class="n">' + cellPct(t.w) + '</td></tr>';
}
const topRows = () => Object.values(T).sort((x, y) => y.p - x.p || x.n.localeCompare(y.n)).slice(0, 12).map((t, i) => rowTop(t, i, true, true)).join('');
const fieldRows = () => FIELD.map((e, i) => { const t = T[e[0]], s = i + 1; if (!t) die('field team missing ' + e[0]); return '<tr><td class="n">' + s + '</td><td><span class="tnm">' + LG.team(e[0], 24, true) + '<a class="tl" href="/team/' + e[0] + '/">' + esc(t.n) + '</a></span></td><td><span class="tnm">' + LG.conf(t.cs, 20, true) + '<span>' + esc(t.cn) + '</span></span></td><td>' + (s <= 4 ? 'First-round bye' : s <= 8 ? 'Hosts a first-round game' : 'Plays on the road') + (e[1] ? ' (conference leader)' : '') + '</td></tr>'; }).join('');
function pathRows(k) { const pp = PP.t && PP.t[k]; if (!pp || !pp.rows.length) return null; return pp.rows.map((r) => '<tr><td class="n">' + r[0] + '</td><td class="n">' + pct(r[1]) + '</td><td class="n">' + (r[2] === null ? '<span class="lk">too few simulated seasons</span>' : cellPct(r[2])) + '</td></tr>').join(''); }

/* ---- ported 1:1 from assets/top25.js ---- */
const PN = { ap: 'AP', coaches: 'Coaches' };
const pctSay = (s) => s === '<1%' ? 'less than 1%' : s === '>99%' ? 'more than 99%' : s;
function pollState(k) { const p = POLLS && POLLS.polls && POLLS.polls[k]; if (!p || !p.released || !Array.isArray(p.ranks)) return { on: false, rank: {}, asof: '' }; const m = {}; p.ranks.forEach((x) => { m[x[1]] = x[0]; }); return { on: true, rank: m, asof: p.asof }; }
const ps = { ap: pollState('ap'), coaches: pollState('coaches'), cfp: pollState('cfp') };
const pv = (s, slug) => !s.on ? '\u2014' : s.rank[slug] === undefined ? 'NR' : String(s.rank[slug]);
const say = (s, k, slug) => !s.on ? PN[k] + ' not released yet' : s.rank[slug] === undefined ? 'not ranked by ' + PN[k] : PN[k] + ' ' + s.rank[slug];
function cfpBit(slug) { const s = ps.cfp; if (!s.on) return ''; return ' \u00b7 CFP ' + (s.rank[slug] === undefined ? '\u2014' : String(s.rank[slug])); }
function cfpSay(slug) { const s = ps.cfp; if (!s.on) return ''; return s.rank[slug] === undefined ? ', outside the CFP 25' : ', CFP ' + s.rank[slug]; }
const label = (nm, kt, rec, slug, p) => nm + ', KickTip rank ' + kt + '. Record ' + rec + '. ' + say(ps.ap, 'ap', slug) + ', ' + say(ps.coaches, 'coaches', slug) + cfpSay(slug) + '. Chance to make the 12-team playoff field ' + pctSay(p) + '.';
function t25row(e, kt, lazy) {
  const slug = e[0], t = T[slug], nm = t.n, rec = e[1] + '-' + e[2], p = pct(t.p);
  return '<li><a class="h25-r" href="/team/' + slug + '/" aria-label="' + esc(label(nm, kt, rec, slug, p)) + '"><span class="h25-rk" aria-hidden="true">' + kt + '</span>' + LG.team(slug, 44, lazy) +
    '<span class="h25-tx" aria-hidden="true"><span class="h25-nm">' + esc(nm) + '</span><span class="h25-sb">' + rec + ' \u00b7 AP ' + pv(ps.ap, slug) + ' \u00b7 Coaches ' + pv(ps.coaches, slug) + cfpBit(slug) + '</span></span>' +
    '<span class="h25-pc" aria-hidden="true"><b>' + p + '</b><small>playoff field</small></span></a></li>';
}
const mtS = (s) => { s = String(s); return /\d:\d\d|[ap]\.?m\b/i.test(s) && !/\bMT$/.test(s) ? s + ' MT' : s; };
const t25asof = () => { const one = (k) => ps[k].on ? PN[k] + ' poll as of ' + esc(mtS(ps[k].asof)) + '.' : PN[k] + ' poll: not released yet.'; const cfp = ps.cfp.on && ps.cfp.asof ? ' CFP, ' + esc(mtS(ps.cfp.asof)) + '.' : ''; return '<span>' + one('ap') + ' ' + one('coaches') + cfp + '</span>'; };


/* ---- audit2: game cells, ported 1:1 from assets/kt.js fillGame/lineInfo/mkCell/lnBlock (default model = data/pred-games.json).
   'now' is the data as-of time (deterministic): a spread is 'no longer current' when the game had started or the read was over 24 h old at the as-of. ---- */
const RB = require(path.resolve(SITE, 'assets/rootables.js'));
const ASOF_MS = RB.mtMs(ASOF), NOW = ASOF_MS / 1000; if (!ASOF_MS) die('as_of not parseable for games: ' + ASOF);
const PG = J('data/pred-games.json').g || {}; let LN = {}; try { LN = J('data/pred-lines.json').l || {}; } catch (e) { LN = {}; }
const lineS = (s, h, a) => s === null || s === undefined ? null : s === 0 ? 'Even' : (s < 0 ? h : a) + ' ' + MINUS + Math.abs(s).toFixed(1);
const margS = (s, h, a) => s === null || s === undefined ? null : s === 0 ? 'Even' : (s < 0 ? h : a) + ' by ' + Math.abs(s).toFixed(1);
const sayS = (s, h, a) => s === 0 ? 'Even' : (s < 0 ? h : a) + ' minus ' + Math.abs(s).toFixed(1);
const tmS = (sec) => NBSP(K.fmt(new Date(sec * 1000).toISOString().replace(/\.\d+Z$/, 'Z')) || '');
const lval = (s, h, a) => '<span aria-hidden="true">' + esc(lineS(s, h, a)) + '</span><span class="vh">' + esc(sayS(s, h, a)) + '</span>';
function gInfo(at, g) {
  const L = LN[at.gk] || null, k = +at.k || 0, ks = g && g[0] !== null && g[0] !== undefined ? g[1] : null;
  const r = { h: at.h, a: at.a, ks: ks, L: L, closed: false, started: k > 0 && NOW >= k };
  if (L) r.closed = (L[2] > 0 && NOW >= L[2]) || (NOW - L[1] > 86400);
  return r;
}
const CLT = '<span class="cl" title="ESPN&#39;s spread is no longer current, because the game has started or the number is over 24 hours old.">Spread no longer current</span>';
function mkCellS(i, tbl) {
  if (i.L && !i.closed) return [lval(i.L[0], i.h, i.a) + (tbl ? '<small>' + tmS(i.L[1]) + '</small>' : ''), 'Spread (ESPN): ' + lineS(i.L[0], i.h, i.a)];
  if (i.L) return [CLT + '<small>Last spread: ' + esc(lineS(i.L[0], i.h, i.a)) + ', ' + tmS(i.L[1]) + '</small>', 'Spread no longer current'];
  if (i.started) return ['<span class="nm">No spread was listed before kickoff.</span>', 'No spread was listed before kickoff'];
  return ['<span class="nm">No spread listed yet.</span>' + (tbl ? '' : '<span class="nm2">Spreads usually appear within about a day of kickoff.</span>'), 'No spread listed yet'];
}
function lnBlockS(id, i) {   /* closed (mobile default); the summary in the button carries the numbers, so nothing is hidden behind JS */
  const m = mkCellS(i, false), sum = [m[1]]; let rows = '<div class="r"><dt>Spread (ESPN)' + (i.L && !i.closed ? '<small>' + tmS(i.L[1]) + '</small>' : i.L ? '<small>Last spread: ' + esc(lineS(i.L[0], i.h, i.a)) + ', ' + tmS(i.L[1]) + '</small>' : '') + '</dt><dd' + (i.L && !i.closed ? '' : ' class="nm"') + '>' + (i.L && i.closed ? CLT : m[0]) + '</dd></div>';
  if (i.ks !== null) { rows += '<div class="r"><dt>KickTip&#39;s expected margin</dt><dd>' + esc(margS(i.ks, i.h, i.a)) + '</dd></div>'; sum.push('KickTip\'s expected margin: ' + margS(i.ks, i.h, i.a)); }
  return '<button type="button" class="gbt" aria-expanded="false" aria-controls="ln-' + id + '"><span>ESPN spread and expected margin</span><span class="gsm">' + esc(sum.join(' \u00B7 ')) + '</span><i class="gcv" aria-hidden="true"></i></button><div class="gnb" id="ln-' + id + '" hidden><dl>' + rows + '</dl></div>';
}
function gameCell(at, kind, tag) {
  const g = PG[at.gk], i = gInfo(at, g), h = at.h, a = at.a;
  if (kind === 'wp') { if (g && g[0] !== null && g[0] !== undefined) { const hp = g[0] >= 0.5; return tag === 'td' ? esc(hp ? h : a) + ' ' + pct(hp ? g[0] : 1 - g[0]) : '<span class="gwl">KickTip win chance</span><span class="gwr"><span>' + esc(a) + ' <b>' + pct(1 - g[0]) + '</b></span><span>' + esc(h) + ' <b>' + pct(g[0]) + '</b></span></span><span class="gpb" aria-hidden="true"><i data-pw="' + Math.round(g[0] * 1000) / 10 + '"></i></span>'; }
    return g === undefined ? '<span class="lk">n/a</span>' : '<span class="lk">No estimate (FCS opponent)</span>'; }
  if (kind === 'kl') return i.ks !== null ? esc(margS(i.ks, h, a)) : '<span class="lk">n/a</span>';
  if (kind === 'mk') return mkCellS(i, true)[0];
  if (kind === 'ln') return g === undefined && !i.L ? '' : lnBlockS(at.id, i);
  die('cell kind ' + kind);
}
const attr = (s, n) => { const m = new RegExp(' data-' + n + '="([^"]*)"').exec(s); return m ? m[1].replace(/&amp;/g, '&').replace(/&#x27;|&#39;/g, "'") : null; };
function bakeGames(t, rel) {
  return t.replace(/<(article|tr)\b([^>]*\bdata-gk="[^"]+"[^>]*)>([\s\S]*?)<\/\1>/g, (all, tg, as, body) => {
    const at = { gk: attr(as, 'gk'), id: attr(as, 'id'), h: attr(as, 'h'), a: attr(as, 'a'), k: attr(as, 'k') };
    if (!body.includes('data-c="')) return all; if (!at.h || !at.a || !at.id) die('game attrs missing ' + at.gk + ' in ' + rel);
    const nb = body.replace(/(<(td|div)\b[^>]*\bdata-c="(wp|kl|mk|ln)"[^>]*>)<span class="lk">Loading<\/span>(<\/\2>)/g, (x, o, tag, kind, c) => { stats.gcells++; return o + mk(8, gameCell(at, kind, tag)) + c; });
    return '<' + tg + as + '>' + nb + '</' + tg + '>';
  });
}
/* ---- audit2: Rootables phase 2 (no-JS): the default-model list for the page's team, computed by assets/rootables.js's own compute() at the data as-of ---- */
let RBX = null, LGMX = null;
function rbLogoMap() { if (LGMX) return LGMX; const m = /MAP = (\{.*?\}\}), PAD/s.exec(fs.readFileSync(path.join(SITE, 'assets/lg.js'), 'utf8')); if (!m) die('lg.js MAP not found'); return (LGMX = JSON.parse(m[1]).t); }
function rbCtx() {
  if (RBX) return RBX; const idx = J('data/whatif/index.json'), bun = J('data/sim-bundle.json'), games = RB.buildGames(idx, bun), sh = {}, by = {};
  (bun.teams || []).forEach((t) => { if (t.n) by[t.n] = t; }); const confs = {}; (bun.confs || []).forEach((x) => { confs[x.code] = x.name; });
  return (RBX = { index: idx, games: games, asOfMs: RB.mtMs(idx.as_of), by: by, confs: confs, shard: (w, id) => { if (!(w in sh)) { const f = idx.shards[w]; sh[w] = f ? J('data/whatif/' + f) : null; } return (sh[w] && sh[w][id]) || null; } });
}
/* ---- audit2 polish2: next-game What If (team page). The team's own next game in the Rootables window, playoff chance if it wins / loses, from the same What If shards ---- */
function nwHtml(slug) {
  const c = rbCtx(); let nmK = null; Object.keys(c.by).forEach((k) => { if (c.by[k].g === slug) nmK = k; });
  const tn = c.index.team_names.indexOf(nmK); if (tn < 0) return null;
  const col = c.index.metrics.indexOf('cfp12') + 1; if (col < 1) return null;
  const end = c.asOfMs + 7 * 864e5; let g0 = null;
  c.games.forEach((g) => { if (g.ip || g.kick > end || c.asOfMs > (g.tba ? g.kick + 864e5 : g.kick)) return; if (g.h !== tn && g.a !== tn) return; if (!g0 || g.kick < g0.kick) g0 = g; });
  if (!g0) return null; const sh = c.shard(g0.week, g0.id); if (!sh) return null;
  const base = c.index.baseline[tn][col - 1];
  const ch = (side) => { const l = sh[side] || []; for (let i = 0; i < l.length; i++) if (l[i][0] === tn) return l[i][col]; return base; };
  const nm = (i) => { const n = c.index.team_names[i], t = c.by[n]; return (t && (t.s || t.n)) || n; };
  const home = g0.h === tn, win = home ? ch('h') : ch('a'), loss = home ? ch('a') : ch('h'), opp = nm(home ? g0.a : g0.h), team = nm(tn);
  const P = (x) => Math.round(x / 10), b = P(base);
  const pill = (v) => { const d = P(v) - b; return d === 0 ? '<span class="w2d">no change</span>' : '<span class="w2d ' + (d > 0 ? 'up' : 'dn') + '">' + (d > 0 ? '+' : '&minus;') + Math.abs(d) + '&nbsp;pts</span>'; };
  const row = (lab, v) => '<div class="nw-r"><span class="nw-l">If ' + esc(team) + ' ' + lab + '</span><span class="nw-v"><b>' + P(v) + '%</b> ' + pill(v) + '</span></div><p class="nw-was">playoff &middot; was&nbsp;' + b + '%</p>';
  return '<div class="card nw"><h3 class="nw-h">Next game What If</h3><p class="nw-m">' + NBSP(esc(RB.whenShort(g0))) + ' &middot; ' + (g0.neutral ? 'vs' : home ? 'vs' : 'at') + ' ' + esc(opp) + '</p>' + row('wins', win) + row('loses', loss) + '<p class="nw-st">Chance to make the 12&#8209;team playoff (KickTip blend), data as of ' + NBSP(esc(K.fmt(c.index.as_of.replace(/ MT$/, '')) || RB.stampText(c.index.as_of))) + '.</p></div>';
}
function rbHtml(slug) {
  const c = rbCtx(); let nmK = null; Object.keys(c.by).forEach((k) => { if (c.by[k].g === slug) nmK = k; });
  const tn = c.index.team_names.indexOf(nmK); if (tn < 0) return null;
  const nm = (i) => { const n = c.index.team_names[i], t = c.by[n]; return (t && (t.s || t.n)) || n; };
  const team = nm(tn), res = RB.compute(tn, 'blend', c, c.asOfMs), conf = c.confs[(c.by[nmK] || {}).c] || '', S = RB.STR;   /* blended list (Oct 31): cfp12 + ccg, tagged by race */
  const st = '<p class="rb-simn"><span class="bl">Simulation analysis, not advice. Data as of ' + NBSP(esc(K.fmt(c.index.as_of.replace(/ MT$/, '')) || RB.stampText(c.index.as_of))) + '.</span></p>';
  if (!res.nWindow) return '<p class="rb-msg">No games in the next 7 days.</p>' + st;
  if (!res.rows.length) return '<p class="rb-msg none">' + esc(RB.fill(S.empty, { Team: team })) + '</p>' + st;
  const LGM = rbLogoMap(), lgo = (i) => { const t = c.by[c.index.team_names[i]], m = t && t.g && LGM[t.g]; return m ? '<span class="lg s52" aria-hidden="true"><img src="/assets/logos/64/' + m[0] + '.png" alt="" width="52" height="52" decoding="async" loading="lazy"></span>' : ''; };
  const sl = (i) => String((c.by[c.index.team_names[i]] || {}).g || '').replace(/[^a-z0-9-]/g, '');
  const li = res.rows.map((r) => RB.rvCard({ slug: sl(r.root), when: RB.whenCard(r), root: { name: nm(r.root), logo: lgo(r.root) }, other: { name: nm(r.other), logo: lgo(r.other) }, where: r.neutral || r.root === r.h ? 'vs' : 'at', gain: RB.pts(r.gap), label: RB.fill(S.gain, { Team: team }), tag: RB.tagText(r.race, conf), race: r.race, also: RB.alsoText(r.sec, conf),
    sr: 'Root for ' + nm(r.root) + '. ' + team + '\u2019s chance for ' + RB.fill(S.race[r.race], { Conf: conf }) + ' is ' + RB.pts(r.gap) + ' points higher if ' + nm(r.root) + ' wins.' + (r.sec ? ' ' + RB.alsoText(r.sec, conf).replace('\u2212', 'minus ') + '.' : '') + ' Kickoff ' + RB.whenLong(r) + '.' })).join('');
  const L = li.split('</li>').filter(Boolean).map((x) => x + '</li>'), top = L.slice(0, 2).join(''), more = L.slice(2).join('');
  return '<p class="rb-sub">For ' + esc(team) + '&#8217;s ' + (conf ? 'playoff and ' + esc(conf) + '&nbsp;championship' : 'playoff') + ' chances (KickTip blend):</p><ol class="rb-list">' + top + '</ol>' + (more ? '<details class="rb-more"><summary>Show ' + (L.length - 2) + ' more game' + (L.length === 3 ? '' : 's') + '</summary><ol class="rb-list" start="3">' + more + '</ol></details>' : '') + st;
}

/* rootables-shared (Nov 1): the team page list = RB.readyHtml(), the SAME live markup the browser draws, fed by the shared per-team file (tools/gen_rootables.js) */
const ENT = (s) => s.replace(/\u00A0/g, '&nbsp;').replace(/[^\x00-\x7f]/g, (c) => '&#' + c.codePointAt(0) + ';');   /* entities only: no literal NBSP / U+2011 */
function rbReady(slug) {
  const f = path.join(SITE, 'data/rootables', slug + '.json'); if (!fs.existsSync(f)) die('data/rootables/' + slug + '.json missing (run tools/gen_rootables.js first)');
  const d = JSON.parse(fs.readFileSync(f, 'utf8')); if (d.v !== 1 || d.slug !== slug) die('bad rootables file ' + slug);
  const now = RB.mtMs(d.as_of); if (now === null) die('as_of unparseable in ' + slug);
  if (!RB.readyHtml) die('assets/rootables.js has no readyHtml (rootables-shared site required)');
  return ENT(RB.readyHtml(d, { logo: (s) => (s ? LG.team(s, 52, true) : ''), how: false, now: now, noHead: true }));
}
/* ---- page edits ---- */
let stats = { files: 0, asof: 0, home: 0, team: 0, conf: 0, cells: 0, spreads: 0, gcells: 0, slate: 0, rb: 0 };
function rep1(t, re, fn, what, f) { let n = 0; const o = t.replace(re, (...a) => { n++; return fn(...a); }); if (n !== 1) die(what + ' anchor found ' + n + 'x in ' + f); return o; }
const SCRIPT = (t) => { const m = /\/assets\/stamp\.js\?v=([0-9a-f]{10})/.exec(t); return m ? m[1] : null; };
const stampTok = require('crypto').createHash('sha256').update(fs.readFileSync(path.join(SITE, 'assets/stamp.js'))).digest('hex').slice(0, 10);
const cssTok = fs.existsSync(path.join(SITE, 'assets/nojs.css')) ? require('crypto').createHash('sha256').update(fs.readFileSync(path.join(SITE, 'assets/nojs.css'))).digest('hex').slice(0, 10) : null;
/* merge: ONE stamp per view switcher, placed after the closing </div> of <div data-vroot> so it shows in every view (bracket/list/cards) with JS on and off */
function afterVroot(t, rel) {
  const o = '<div data-vroot>', i = t.indexOf(o); if (i < 0 || t.indexOf(o, i + 1) >= 0) die('data-vroot count != 1 in ' + rel);
  const re = /<div\b[^>]*>|<\/div>/g; re.lastIndex = i; let d = 0, m;
  while ((m = re.exec(t))) { d += m[0][1] === '/' ? -1 : 1; if (!d) return t.slice(0, re.lastIndex) + upd() + t.slice(re.lastIndex); }
  die('unbalanced data-vroot in ' + rel);
}
for (const f of files) {
  const rel = path.relative(SITE, f).replace(/\\/g, '/'); const t0 = fs.readFileSync(f, 'utf8'); let t = unbake(t0);
  if (SP_STAMP && t.includes(DEF[7])) { t = t.split(DEF[7]).join(mk(7, 'Spreads: ESPN \u00b7 updated <span class="kt-spu" data-pulled="' + SP_ISO + '">' + NBSP(SP_STAMP) + '</span>. Numbers only, shown when one has been posted.')); stats.spreads++; }
  /* as-of stamps everywhere: exact time, never 'recently' */
  if (t.includes('class="kt-asof"')) {
    t = t.replace(/(<span class="kt-asof" data-asof="([^"]*)">)recently(<\/span>)/g, (m, a, v, b) => { const s = K.fmt(v); if (!s) die('unparseable data-asof "' + v + '" in ' + rel); stats.asof++; return a + mk(3, NBSP(s)) + b; });
    if (/class="kt-asof"[^>]*>recently</.test(t)) die('kt-asof "recently" left in ' + rel);
    if (!t.includes('/assets/stamp.js')) {
      const at = t.search(/<script src="\/assets\/(lg|asof|pk)\.js/); if (at < 0) die('no script anchor for stamp.js in ' + rel);
      t = t.slice(0, at) + mk(0, '<script src="/assets/stamp.js?v=' + stampTok + '" defer></script>') + t.slice(at);
    }
  }
  const page = (/<main[^>]*data-page="([^"]+)"/.exec(t) || [])[1];
  let baked = false;
  if (t.includes('data-c="')) t = bakeGames(t, rel);
  if (/data-c="(wp|kl|mk|ln)"[^>]*><span class="lk">Loading/.test(t)) die('game Loading cell left in ' + rel);
  if (rel === 'index.html') {
    t = rep1(t, /(<p class="h25-eb" data-t25eb>)(<\/p>)/, (m, a, b) => a + mk(0, esc('Rating: ' + (PT.model && (PT.model.btn || PT.model.name)))) + b, 't25eb', rel);
    t = rep1(t, /<noscript><p class="h25-js0">Turn on JavaScript to see the KickTip Top 25\.<\/p><\/noscript>/, () => mk(4, ''), 't25 noscript', rel);
    const top = R.teams.slice(0, 25).filter((e) => T[e[0]]); if (top.length !== 25) die('top25 has ' + top.length + ' teams');
    t = rep1(t, /(<ol class="h25-l h25-ph" data-t25l[^>]*>)(<\/ol>)/, (m, a, b) => a + mk(0, top.slice(0, 5).map((e, i) => t25row(e, i + 1, false)).join('')) + b, 't25l', rel);
    t = rep1(t, /(<ol class="h25-l" start="6"[^>]*data-t25r>)(<\/ol>)/, (m, a, b) => a + mk(0, top.slice(5).map((e, i) => t25row(e, i + 6, true)).join('')) + b, 't25r', rel);
    t = rep1(t, /(<p class="h25-asof" data-t25asof>)(<\/p>)/, (m, a, b) => upd('h25-upd') + a + mk(0, t25asof()) + b, 't25asof', rel);
    if (ps.cfp.on) {
      t = t.replace(DEF[14], mk(14, 'Compared with the AP and Coaches polls and the CFP rankings.'));
      t = t.replace(DEF[15], mk(15, 'NR means not ranked by that poll. A dash means not in the CFP 25.'));
    }
    t = rep1(t, /(<table id="top12">[\s\S]*?<tbody>)(<\/tbody>)/, (m, a, b) => a + mk(0, topRows()) + b, 'top12', rel);
    t = rep1(t, /(<table id="fieldseeds" class="fld">[\s\S]*?<tbody>)(<\/tbody>)(<\/table><\/div>)/, (m, a, b, c) => a + mk(0, fieldRows()) + b + c, 'fieldseeds', rel);
    t = afterVroot(t, rel);
    stats.home++; baked = true;
  } else if (page === 'team') {
    const k = (/<main[^>]*data-team="([^"]+)"/.exec(t) || [])[1], tm = T[k]; if (!tm) die('team ' + k + ' not in pred-teams (' + rel + ')');
    const m = { c: tm.c, w: tm.w, p: tm.p, b: tm.b };
    let n = 0; t = t.replace(/(<b data-tile="([cwpb])">)&ndash;(<\/b>)/g, (x, a, key, b) => { n++; const v = m[key]; return a + mk(1, v === null || v === undefined ? 'n/a' : pct(v)) + b; });
    if (n < 2 || !t.includes('data-tile="p"')) die('tiles found ' + n + ' in ' + rel);
    t = rep1(t, /(<b data-tile="b">[\s\S]*?<\/div><\/div>)(<p class="note(?: pc-nt)?">Chances come from)/, (x, a, b) => a + upd() + b, 'tiles stamp', rel);
    const pp = PP.t && PP.t[k];
    if (pp && t.includes('<b data-wo>&ndash;</b>')) t = t.replace('<b data-wo>&ndash;</b>', '<b data-wo>' + mk(1, pp.wo === null || pp.wo === undefined ? 'n/a' : pct(pp.wo)) + '</b>');
    const pr = pathRows(k); if (pr) t = t.replace(/(<table id="paths" class="fld">[\s\S]*?<tbody>)<tr><td colspan="3"><span class="lk">Loading<\/span><\/td><\/tr>(<\/tbody>)/, (x, a, b) => a + mk(6, pr) + b);
    if (t.includes(DEF[13])) { t = t.split(DEF[13]).join(mk(13, rbReady(k))); stats.rb++; }
    else if (t.includes(DEF[9])) { const rh = rbHtml(k); if (rh) { t = rep1(t, /<noscript><p class="rb-msg">Turn on JavaScript to run Rootables\.<\/p><\/noscript>/, () => mk(9, '<noscript>' + rh + '</noscript>'), 'rootables', rel); stats.rb++; } }
    if (t.includes('<section id="what-if" aria-label="What if"><ul class="pk-tiles pk-one">')) { const nh = nwHtml(k); if (nh) { t = t.replace('<section id="what-if" aria-label="What if"><ul class="pk-tiles pk-one">', '<section id="what-if" aria-label="What if">' + mk(10, nh) + '<ul class="pk-tiles pk-one">'); stats.nw = (stats.nw || 0) + 1; } }
    /* Creative 11:21 A: the floating Lab chip carried a hardcoded sample ("What if BYU loses?") pasted on every page by the Lab rollout; on team pages it must name the page's own team. Marked bake (DEF[12]): unbake restores the shared sample, every bake/refresh writes the page's team. */
    { const nm = (/<section class="card rb" id="rootables"[^>]*data-name="([^"]+)"/.exec(t) || [])[1] || (tm.n ? esc(tm.n) : null);
      if (nm) t = t.replace(/(<span class="kph">)What if BYU loses\?(<\/span>)/, (x, a, b) => a + mk(12, 'What if ' + nm + ' loses?') + b); }
    stats.team++; baked = true;
  } else if (page === 'slate') {
    t = rep1(t, /(<\/tbody><\/table><\/div><\/div>)(<p class="note"><b>How to read)/, (x, a, b) => a + upd() + b, 'slate stamp', rel);
    stats.slate++; baked = true;
  } else if (page === 'conference' && t.includes(' data-f="')) {
    t = t.replace(/(<td class="n" data-f="([cwpb])" data-t="([^"]+)">)<span class="lk">Loading<\/span>(<\/td>)/g, (x, a, fk, k, b) => { const tm = T[k]; if (!tm) die('conf team ' + k + ' missing (' + rel + ')'); stats.cells++; return a + mk(2, cellPct(tm[fk])) + b; });
    if (/data-f="[cwpb]"[^>]*><span class="lk">Loading/.test(t)) die('conf Loading cell left in ' + rel);
    const cs = (/<main[^>]*data-conf="([^"]+)"/.exec(t) || [])[1];
    if (cs && t.includes('<ul class="dest" id="dest">' + DEF[11])) {   /* ported 1:1 from kt.js destiny() */
      const rows = Object.values(T).filter((x) => x.cs === cs && x.x !== null && x.x !== undefined).sort((a, b) => b.x - a.x).filter((x) => x.x >= 0.02);
      const h = rows.length ? rows.map((x) => { const c = x.x >= 0.9 ? ['p1', 'IN WITH WINS'] : ['p2', 'NEEDS HELP']; return '<li><span class="pill ' + c[0] + '">' + c[1] + '</span>' + esc(x.n) + ': if it wins out, ' + pct(x.x) + ' to reach the conference championship game.</li>'; }).join('') : '<li>No team has a better than 2% chance to reach the conference championship game by winning out.</li>';
      t = t.replace('<ul class="dest" id="dest">' + DEF[11], '<ul class="dest" id="dest">' + mk(11, h));
    }
    t = afterVroot(t, rel);
    stats.conf++; baked = true;
  }
  if (baked) {
    t = t.replace(/(<noscript><div class="ldm"><p>)Turn on JavaScript to see the chances\. Without it this page shows no simulation numbers\.(<\/p>)/g, (x, a, b) => a + mk(5, NOJS_TXT) + b);
    if (cssTok && (rel === 'index.html' || page === 'conference')) t = rep1(t, /<\/head>/, () => mk(0, '<noscript><link rel="stylesheet" href="/assets/nojs.css?v=' + cssTok + '"></noscript>') + '</head>', 'head', rel);
  }
  if (CHECK && unbake(t) !== unbake(t0)) die('unbake not exact for ' + rel);
  if (t !== t0) { if (VERIFY) die('stale bake (numbers or stamp differ from data) in ' + rel); fs.writeFileSync(f, t); stats.files++; }
}
const stale = files.filter((f) => new RegExp('data-asof="(?!' + ASOF_ATTR + '")').test(fs.readFileSync(f, 'utf8')));
if (stale.length) die('data-asof differs from data as_of ' + ASOF_ATTR + ' in ' + stale.slice(0, 5).map((f) => path.relative(SITE, f)).join(', '));
console.log(VERIFY ? 'verified' : 'baked', JSON.stringify(stats), 'asof', ASOF, 'stamp', JSON.stringify(STAMP));
