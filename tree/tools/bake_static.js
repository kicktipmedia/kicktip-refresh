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
  'Spreads: ESPN, numbers only, shown when one has been posted.'];
const NOJS_TXT = 'Turn on JavaScript to see game numbers and switch models.';
const MK = /<!--bk:(\d+)-->[\s\S]*?<!--\/bk-->/g;
const mk = (n, s) => '<!--bk:' + n + '-->' + s + '<!--/bk-->';
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
function pollState(k) { const p = POLLS && POLLS.polls && POLLS.polls[k]; if (!p || !p.released) return { on: false, rank: {}, asof: '' }; const m = {}; p.ranks.forEach((x) => { m[x[1]] = x[0]; }); return { on: true, rank: m, asof: p.asof }; }
const ps = { ap: pollState('ap'), coaches: pollState('coaches') };
const pv = (s, slug) => !s.on ? '\u2014' : s.rank[slug] === undefined ? 'NR' : String(s.rank[slug]);
const say = (s, k, slug) => !s.on ? PN[k] + ' not released yet' : s.rank[slug] === undefined ? 'not ranked by ' + PN[k] : PN[k] + ' ' + s.rank[slug];
const label = (nm, kt, rec, slug, p) => nm + ', KickTip rank ' + kt + '. Record ' + rec + '. ' + say(ps.ap, 'ap', slug) + ', ' + say(ps.coaches, 'coaches', slug) + '. Chance to make the 12-team playoff field ' + pctSay(p) + '.';
function t25row(e, kt, lazy) {
  const slug = e[0], t = T[slug], nm = t.n, rec = e[1] + '-' + e[2], p = pct(t.p);
  return '<li><a class="h25-r" href="/team/' + slug + '/" aria-label="' + esc(label(nm, kt, rec, slug, p)) + '"><span class="h25-rk" aria-hidden="true">' + kt + '</span>' + LG.team(slug, 44, lazy) +
    '<span class="h25-tx" aria-hidden="true"><span class="h25-nm">' + esc(nm) + '</span><span class="h25-sb">' + rec + ' \u00b7 AP ' + pv(ps.ap, slug) + ' \u00b7 Coaches ' + pv(ps.coaches, slug) + '</span></span>' +
    '<span class="h25-pc" aria-hidden="true"><b>' + p + '</b><small>playoff field</small></span></a></li>';
}
const mtS = (s) => { s = String(s); return /\d:\d\d|[ap]\.?m\b/i.test(s) && !/\bMT$/.test(s) ? s + ' MT' : s; };
const t25asof = () => { const one = (k) => ps[k].on ? PN[k] + ' poll as of ' + esc(mtS(ps[k].asof)) + '.' : PN[k] + ' poll: not released yet.'; return '<span>' + one('ap') + ' ' + one('coaches') + '</span>'; };

/* ---- page edits ---- */
let stats = { files: 0, asof: 0, home: 0, team: 0, conf: 0, cells: 0, spreads: 0 };
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
  if (rel === 'index.html') {
    t = rep1(t, /(<p class="h25-eb" data-t25eb>)(<\/p>)/, (m, a, b) => a + mk(0, esc('Rating: ' + (PT.model && (PT.model.btn || PT.model.name)))) + b, 't25eb', rel);
    t = rep1(t, /<noscript><p class="h25-js0">Turn on JavaScript to see the KickTip Top 25\.<\/p><\/noscript>/, () => mk(4, ''), 't25 noscript', rel);
    const top = R.teams.slice(0, 25).filter((e) => T[e[0]]); if (top.length !== 25) die('top25 has ' + top.length + ' teams');
    t = rep1(t, /(<ol class="h25-l h25-ph" data-t25l[^>]*>)(<\/ol>)/, (m, a, b) => a + mk(0, top.slice(0, 5).map((e, i) => t25row(e, i + 1, false)).join('')) + b, 't25l', rel);
    t = rep1(t, /(<ol class="h25-l" start="6"[^>]*data-t25r>)(<\/ol>)/, (m, a, b) => a + mk(0, top.slice(5).map((e, i) => t25row(e, i + 6, true)).join('')) + b, 't25r', rel);
    t = rep1(t, /(<p class="h25-asof" data-t25asof>)(<\/p>)/, (m, a, b) => upd('h25-upd') + a + mk(0, t25asof()) + b, 't25asof', rel);
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
    stats.team++; baked = true;
  } else if (page === 'conference' && t.includes(' data-f="')) {
    t = t.replace(/(<td class="n" data-f="([cwpb])" data-t="([^"]+)">)<span class="lk">Loading<\/span>(<\/td>)/g, (x, a, fk, k, b) => { const tm = T[k]; if (!tm) die('conf team ' + k + ' missing (' + rel + ')'); stats.cells++; return a + mk(2, cellPct(tm[fk])) + b; });
    if (/data-f="[cwpb]"[^>]*><span class="lk">Loading/.test(t)) die('conf Loading cell left in ' + rel);
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
