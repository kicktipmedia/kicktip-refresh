/* KickTip "Choose your team" (home), What if tiles, My teams search, team-page What if button. No frameworks, no cookies, no requests of its own except the race1 fallback below (team list again after 6 s without data, or on Try again), no inline styles (strict CSP).
   TEAM-ONLY picker (change 5). "Your team" and "Following" are two separate things (change 8). Your team = the team set with the Your team button (kept in the device key kicktip_you, written only when you tap Your team, Remove or Clear your team), else the first team saved in My teams (the old rule, kept for visitors who never used the button). Following = the My teams list (KTMyTeams, unchanged).
   Team names come from the page's own data (assets/kt.js fires kt:render with T). Rows and chips stay real links, so Open in new tab and no-script both work. */
(function () {
  'use strict';
  var D = document, W = window, main = D.getElementById('main');
  if (!main) return;
  var page = main.getAttribute('data-page'), T = null;
  var AR = '<svg class="pk-go" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 5l7 7-7 7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';

  var SEARCH = '<svg class="pk-ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5" stroke="#4C5560" stroke-width="2.4" fill="none"/><path d="M15.5 15.5L21 21" stroke="#4C5560" stroke-width="2.4" stroke-linecap="round"/></svg>';
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return [].slice.call((r || D).querySelectorAll(s)); }
  function norm(s) { return String(s).toLowerCase().replace(/[\u2018\u2019']/g, '').replace(/[^a-z0-9]+/g, ' ').replace(/^ | $/g, ''); }
  function poss(n) { return n + '\u2019s'; }

  /* ---------- team page: the What if panel's button opens the existing What if panel (the fixed pill) ---------- */
  D.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-pk-open]'); if (!b) return;
    var p = D.getElementById('kpill'); if (p) { e.preventDefault(); var nm = b.getAttribute('data-pk-name'); if (nm) { main.setAttribute('data-exa', nm); main.setAttribute('data-exb', nm); } if (W.KTLab) W.KTLab.opener = b; p.click(); }
  });
  if (page !== 'home' && page !== 'team') return;

  /* ---------- search data ---------- */
  var IDX = null;
  function build() {
    if (!T) return null;
    var teams = [];
    Object.keys(T).forEach(function (s) { var t = T[s]; if (!t || !t.n) return; teams.push({ s: s, n: t.n, cs: t.cs, cn: t.cn, k: norm(t.n) }); });
    return { teams: teams, confs: confsOf(teams) };
  }
  function score(k, q) { if (k.indexOf(q) === 0) return 0; if ((' ' + k).indexOf(' ' + q) >= 0) return 1; return k.indexOf(q) >= 0 ? 2 : -1; }
  function find(raw) {
    var q = norm(raw), ix = IDX; if (!q || !ix) return { teams: [] };
    var ts = [];
    ix.teams.forEach(function (t) { var sc = score(t.k, q); if (sc < 0) sc = score(norm(t.s.replace(/-/g, ' ')), q) >= 0 ? 3 : -1; if (sc >= 0) ts.push([sc, t]); });
    ts.sort(function (a, b) { return a[0] - b[0] || (a[1].n < b[1].n ? -1 : 1); });
    return { teams: ts.slice(0, 8).map(function (x) { return x[1]; }), all: ts.map(function (x) { return x[1]; }) };
  }
  /* search1: conferences in the home search. A conference row (header) links to its page and never sets Your team or Follow;
     every member team follows as a normal row. Aliases are exact (or a prefix of 3+ letters), so "b1g", "big12", "sec" all work. */
  var CAL = {
    'big-12': ['big 12', 'big12', 'b12', 'big twelve', 'big xii'], 'big-ten': ['big ten', 'big10', 'big 10', 'b1g'], 'sec': ['sec', 'southeastern'],
    'acc': ['acc', 'atlantic coast'], 'pac-12': ['pac 12', 'pac12', 'pac-12', 'pacific 12'], 'mountain-west': ['mountain west', 'mwc', 'mw'],
    'sun-belt': ['sun belt', 'sunbelt'], 'mac': ['mac', 'mid american', 'midamerican'], 'american': ['american', 'aac', 'american conference', 'american athletic'],
    'conference-usa': ['conference usa', 'c usa', 'cusa', 'c-usa'], 'independents': ['independents', 'independent', 'ind']
  };
  /* Short forms people type for a team whose name does not contain them (ASU, FSU ...). Exact match, or a prefix of 3+ letters; shown first, then the name matches. */
  var TAL = { 'asu': ['arizona-state'], 'fsu': ['florida-state'], 'msu': ['michigan-state', 'mississippi-state'], 'osu': ['ohio-state', 'oklahoma-state', 'oregon-state'], 'psu': ['penn-state'],
    'wsu': ['washington-state'], 'wazzu': ['washington-state'], 'ksu': ['kansas-state', 'kennesaw-state'], 'isu': ['iowa-state'], 'bsu': ['boise-state'], 'fau': ['florida-atlantic'], 'fiu': ['florida-international'],
    'ecu': ['east-carolina'], 'usf': ['south-florida'], 'unc': ['north-carolina'], 'uga': ['georgia'], 'wvu': ['west-virginia'], 'vt': ['virginia-tech'], 'tamu': ['texas-a-m'], 'a m': ['texas-a-m'], 'umass': ['massachusetts'],
    'nd': ['notre-dame'], 'ou': ['oklahoma'], 'cuse': ['syracuse'], 'zona': ['arizona'], 'pitt': ['pittsburgh'], 'usu': ['utah-state'], 'nmsu': ['new-mexico-state'], 'sdsu': ['san-diego-state'], 'sjsu': ['san-jose-state'],
    'csu': ['colorado-state'], 'jsu': ['jacksonville-state'], 'mtsu': ['middle-tennessee'], 'wku': ['western-kentucky'], 'jmu': ['james-madison'], 'usm': ['southern-miss'], 'bgsu': ['bowling-green'],
    'appalachian state': ['app-state'], 'miami ohio': ['miami-oh'], 'miami of ohio': ['miami-oh'], 'texas a and m': ['texas-a-m'] };
  function aliasTeams(q, ix) {
    var out = [];
    Object.keys(TAL).forEach(function (a) { if (a === q || (q.length >= 3 && a.indexOf(q) === 0)) TAL[a].forEach(function (s) { out.push(s); }); });
    return ix.teams.filter(function (t) { return out.indexOf(t.s) >= 0; }).sort(function (a, b) { return a.n < b.n ? -1 : a.n > b.n ? 1 : 0; });
  }
  function confsOf(teams) {
    var by = {}, out = [];
    teams.forEach(function (t) {
      if (!t.cs) return; var c = by[t.cs];
      if (!c) { c = by[t.cs] = { cs: t.cs, cn: t.cn, label: t.cs === 'american' ? 'American Conference' : t.cn, mem: [], al: [] }; out.push(c); }
      c.mem.push(t);
    });
    out.forEach(function (c) {
      var al = [norm(c.label), norm(c.cn), norm(c.cs.replace(/-/g, ' ')), c.cs.replace(/-/g, '')].concat((CAL[c.cs] || []).map(norm));
      c.al = al.filter(function (a, i) { return a && al.indexOf(a) === i; });
      c.mem.sort(function (a, b) { return a.n < b.n ? -1 : a.n > b.n ? 1 : 0; });
    });
    return out;
  }
  function confScore(c, q) {   /* 0 exact alias | 1 prefix of an alias (q has 3+ letters) | -1 none */
    var best = -1;
    for (var i = 0; i < c.al.length; i++) { var a = c.al[i]; if (a === q) return 0; if (q.length >= 3 && a.indexOf(q) === 0) best = 1; }
    return best;
  }
  function findPick(raw) {
    var q = norm(raw), ix = IDX; if (!q || !ix) return { n: 0, groups: [], rest: [] };
    var f = find(raw), cs = [], seen = {};
    (ix.confs || []).forEach(function (c) { var sc = confScore(c, q); if (sc >= 0) cs.push([sc, c]); });
    cs.sort(function (a, b) { return a[0] - b[0] || (a[1].label < b[1].label ? -1 : 1); });
    var groups = cs.map(function (x) { x[1].mem.forEach(function (t) { seen[t.s] = 1; }); return { conf: x[1], teams: x[1].mem }; });
    var al = aliasTeams(q, ix), ak = {}; al.forEach(function (t) { ak[t.s] = 1; });
    var rest = al.concat(f.all.filter(function (t) { return !ak[t.s]; })).filter(function (t) { return !seen[t.s]; }).slice(0, 8);
    return { n: Object.keys(seen).length + rest.length, groups: groups, rest: rest };
  }
  function confRowHtml(c, raw) {
    var lg = W.KTLogo && W.KTLogo.conf ? W.KTLogo.conf(c.cs, 24, true) : '';
    return '<li class="pk-cr"><a class="pk-cn" href="/conference/' + esc(c.cs) + '/">' + lg + '<span class="pk-t"><span class="pk-n">' + hi(c.label, raw) + '<span class="vh">, </span></span><span class="pk-c">' + c.mem.length + ' teams<span class="vh">. Conference page</span></span></span>' + AR + '</a></li>';
  }
  function hi(name, raw) { var r = raw.replace(/^\s+|\s+$/g, ''), i = r ? name.toLowerCase().indexOf(r.toLowerCase()) : -1; return i < 0 ? esc(name) : esc(name.slice(0, i)) + '<b>' + esc(name.slice(i, i + r.length)) + '</b>' + esc(name.slice(i + r.length)); }
  function logo(s) { return W.KTLogo ? W.KTLogo.team(s, 24, true) : ''; }

  /* ================= HOME ================= */
  var inp = $('#team-search'), res = $('#pk-list'), stat = $('#pk-st'), clr = $('.pk-x'), how = $('.pk-how'), pill = D.getElementById('kpill'), box = $('.pk-box');
  var cur = -1, opts = [], open = false, NONE = null;

  function syncPill() { if (!pill || !inp) return; pill.classList.toggle('pk-hide', open || D.activeElement === inp); }
  D.addEventListener('focusin', function (e) { if (pill && e.target && e.target.id === 'mt-pk-in') pill.classList.add('pk-hide'); });
  D.addEventListener('focusout', function (e) { if (pill && e.target && e.target.id === 'mt-pk-in') setTimeout(function () { pill.classList.toggle('pk-hide', !!(inp && (open || D.activeElement === inp)) || (D.activeElement && D.activeElement.id === 'mt-pk-in')); }, 0); });
  function setOpen(o) { open = o; if (res) res.hidden = !o; syncPill(); }
  function say(m) { if (stat) stat.textContent = m; }
  function render(quiet) {
    var raw = inp.value; clr.hidden = !raw; cur = -1;
    if (!norm(raw)) { res.innerHTML = ''; setOpen(false); say(''); return; }
    if (!IDX) { res.className = 'pk-res pk-nm'; res.removeAttribute('aria-label'); res.innerHTML = '<p>Teams are still loading. Try again in a moment.</p>'; setOpen(true); say('Teams are still loading.'); return; }
    var f = findPick(raw);
    if (!f.n && !f.groups.length) {
      res.className = 'pk-res pk-nm'; res.removeAttribute('aria-label');
      res.innerHTML = '<p><b>No team or conference matches \u201C' + esc(raw.replace(/^\s+|\s+$/g, '')) + '\u201D.</b></p><p>Check the spelling.</p>';
      setOpen(true); say('No results for ' + raw); return;
    }
    res.className = 'pk-res'; res.removeAttribute('aria-label');
    var h = '<ul class="pk-trs" aria-label="' + (f.groups.length ? 'Matching conferences and teams' : 'Matching teams') + '">';
    f.groups.forEach(function (g) { h += confRowHtml(g.conf, raw) + g.teams.map(function (t) { return rowHtml(t.s, { raw: raw }); }).join(''); });
    if (f.groups.length && f.rest.length) h += '<li class="pk-sep">Teams</li>';
    h += f.rest.map(function (t) { return rowHtml(t.s, { raw: raw }); }).join('') + '</ul>';
    res.innerHTML = h; setOpen(true);
    if (!quiet) {
      var g1 = f.groups.length, tm = f.n + (f.n === 1 ? ' team' : ' teams');
      say(g1 ? (g1 === 1 ? f.groups[0].conf.label + ' and ' + tm + '. ' : g1 + ' conferences and ' + tm + '. ') + 'Tap a team to choose it, or use the buttons on a row.'
             : f.n + (f.n === 1 ? ' result. ' : ' results. ') + 'Tap a name to choose that team, or use the buttons on a row.');
    }
  }
  function close(clear) { setOpen(false); cur = -1; if (clear) { inp.value = ''; clr.hidden = true; res.innerHTML = ''; say(''); } }

  /* ---------- your team (change 8): the Your team button, else the first saved in My teams ---------- */
  var YK = 'kicktip_you', YV;   /* YV: undefined = the button was never used (old rule: first saved team) | '' = you cleared it (no team) | a team slug */
  (function () { try { var o = JSON.parse(W.localStorage.getItem(YK) || 'null'); if (o && o.v === 1 && typeof o.s === 'string' && /^[a-z0-9-]*$/.test(o.s)) YV = o.s; } catch (e) { /* none */ } })();
  function youWrite(s) { YV = s; try { W.localStorage.setItem(YK, JSON.stringify({ v: 1, s: s })); } catch (e) { /* storage refused: held in memory for this page view */ } }
  function saved() { try { var g = W.KTMyTeams && W.KTMyTeams.get(); var a = g && g.teams || []; for (var i = 0; i < a.length; i++) if (!T || T[a[i]]) return a[i]; } catch (e) { /* none */ } return null; }
  function yourTeam() { if (!YV && holding()) return null; var s = YV === '' ? null : (YV || saved()); return s && T && T[s] ? s : null; }
  /* tiles1:begin  (home tiles with inline content; written by kicktip-tiles1/apply.py from src/pk-tiles-block.js; re-running apply.py replaces everything between these markers)
     Strip + three tiles for "your team" = the team just chosen here, else the first saved in My teams (KTMyTeams), else BYU shown as a labeled example. STORES NOTHING (no cookies, no storage).
     Tile 1 paints at once from pred-teams (T). Tiles 2 and 3 use ONE fetch of /data/tile-data.json (credentials omitted; built by tools/build_tile_data.py at every data refresh), with same-height placeholder bars meanwhile.
     Numbers are hidden (never mismatched) when tile-data.json's as_of differs from the page's model stamp, or when a non-default model is on screen. A game whose kickoff has passed in the visitor's clock is skipped. */
  var TD = null, TDS = 'idle', tdP = null, MM = false, EXAMPLE = 'byu', DAYMS = 864e5;
  function pctT(p) { if (p === null || p === undefined) return 'n/a'; var v = Math.round(p * 100); if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%'; }   /* same rule as kt.js pct() */
  function pctM(raw) { var v = Math.floor((raw + 5) / 10); if (raw > 0 && v < 1) return '<1%'; if (raw < 1000 && v >= 100) return '>99%'; return v + '%'; }   /* whole percent from per-mille integers */
  function ptsM(g) { return (g / 10).toFixed(1); }
  function metricOf(t) { return (t.p >= 0.01 || t.c === null || t.c === undefined) ? 'cfp12' : 'ccg'; }   /* same rule as tools/build_tile_data.py: teams under 1% to make the playoff use conference championship game chances */
  function isInd(t) { return !t.cs || t.cs === 'independents'; }
  function started(k, tba) { return Date.now() > (tba ? k + DAYMS : k); }
  var MON3 = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06', Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12' };
  function pageStamp() {   /* 'YYYY-MM-DD HH:MM' (MT) from the Sources box, the same stamp the freshness line shows; null if it cannot be read */
    var sa = D.querySelectorAll('.src .kt-asof[data-asof]'); if (sa.length) return sa[sa.length - 1].getAttribute('data-asof');
    var src = $('.src'), m = src && /(?:Model numbers|Chances) recalculated from them: (?:[A-Za-z]{3}, )?([A-Za-z]{3}) (\d{1,2}), (\d{4}), (\d{1,2}):(\d{2}) ([AP]M) MT/.exec(src.textContent); if (!m) return null;
    var h = +m[4] % 12 + (m[6] === 'PM' ? 12 : 0), dd = ('0' + m[2]).slice(-2);
    return m[3] + '-' + MON3[m[1]] + '-' + dd + ' ' + ('0' + h).slice(-2) + ':' + m[5];
  }
  function tdState() {   /* idle | loading | err | stale | ok */
    if (TDS !== 'ok') return TDS;
    var ps = pageStamp(); if (MM || !ps || String(TD.as_of).replace(/ MT$/, '') !== ps) return 'stale';
    return 'ok';
  }
  function loadTD() {
    if (tdP) return tdP; TDS = 'loading';
    tdP = fetch('/data/tile-data.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('tile-data'); return r.json(); }).then(function (j) { if (!j || j.v !== 1 || !j.teams) throw new Error('tile-data'); TD = j; TDS = 'ok'; }).catch(function () { TDS = 'err'; });
    var gpP = 0 && fetch('/data/sim-bundle.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (B) { if (B && B.games && B.games.length) { NGAMES = B.games.length; [].forEach.call(D.querySelectorAll('.tt-n'), function (x) { x.textContent = NGAMES.toLocaleString('en-US') + ' remaining games'; }); } GP = KTWhy.pairs(B); }).catch(function () { GP = null; });
    tdP.then(function () { lastKey = null; paint(); });
    return tdP;
  }
  var RD = {};
  if (W.KTRvHome) W.KTRvHome.bindRows(D);
  function loadRD(s) { if (RD[s] !== undefined || RD['_' + s]) return; RD['_' + s] = 1;
    fetch('/data/rootables/' + s + '.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) { if (!j || j.v !== 1 || !j.rows) throw 0; RD[s] = j; }).catch(function () { RD[s] = 'err'; }).then(function () { delete RD['_' + s]; lastKey = null; paint(); }); }
  var PH = function (c) { return '<span class="pt-ph ' + c + '" aria-hidden="true"></span>'; };
  function updHtml() { return '<p class="pt-err" role="status">Updating the numbers.</p>'; }
  function errHtml() { return '<p class="pt-err" role="status">Couldn\u2019t load the numbers. <button type="button" class="pt-retry" data-pt-retry>Try again</button></p>'; }
  /* conftile1: row logos. Row names come from tile-data.json as team names; map them to slugs through pred-teams (all 76 names in the current data resolve). A name that does not resolve renders with no logo. */
  var NSM = null;
  function slugOfName(nm) { if (!NSM) { NSM = {}; for (var k in T) NSM[T[k].n] = k; } return NSM[nm]; }
  function rn(nm, bold) { var sl = slugOfName(nm), lg = sl && W.KTLogo ? W.KTLogo.team(sl, 24, true) : '', x = bold ? '<b>' + esc(nm) + '</b>' : esc(nm); return lg ? '<span class="pt-tn">' + lg + x + '</span>' : x; }
  function confLab(c) { return c[0] === 'american' ? 'American Conference' : c[1]; }
  function confList() { if (!T) return []; var seen = {}, o = []; for (var k in T) { var c = T[k]; if (c.cs && c.cs !== 'independents' && !seen[c.cs]) { seen[c.cs] = 1; o.push([c.cs, c.cn]); } } return o.sort(function (x, y) { return confLab(x).localeCompare(confLab(y)); }); }
  var LWGO = false, LWON = false;   /* home5b: the ask bar stays visible at first load; the Lab-in-view hide starts after the first scroll or focus inside the Lab */
  function labWatch() { if (!W.KTLab) return; if (LWGO || (W.scrollY || W.pageYOffset || 0) > 0) { LWGO = true; W.KTLab.watch(D.getElementById('wl-home')); return; }
    if (LWON) return; LWON = true; var go = function () { if (LWGO) return; LWGO = true; W.removeEventListener('scroll', go); D.removeEventListener('focusin', fi); if (W.KTLab) W.KTLab.watch(D.getElementById('wl-home')); };
    var fi = function (e) { if (e.target && e.target.closest && e.target.closest('#wl-home')) go(); }; W.addEventListener('scroll', go, { passive: true }); D.addEventListener('focusin', fi); }
  var NGAMES = null, TTOPEN = false;
  function ttAge(ps) {   /* nojs1: exact 'Oct 30, 9:41 PM MT' stamp from the data's own time (assets/stamp.js, the one format helper); '' = unknown */
    if (ps === undefined) ps = pageStamp(); if (!ps || !W.KTStamp) return '';
    return W.KTStamp.fmt(ps);
  }
  function ktAsof() { if (!W.KTStamp) return; [].forEach.call(D.querySelectorAll('.kt-asof[data-asof]'), function (x) { var r = ttAge(x.getAttribute('data-asof')), u = x.closest('.kt-upd') || x.closest('.pk-fresh'); if (r) { if (x.textContent !== r) x.textContent = r; } else { x.hidden = true; if (u) u.hidden = true; } }); }   /* same text the page was baked with; unparseable = hidden, never 'recently' */
  function ttPanel() {
    var n = NGAMES ? NGAMES.toLocaleString('en-US') + ' remaining games' : 'remaining games', a = ttAge();
    return '<div class="tt-dp" id="tt-dp" role="region" aria-label="How we got this"' + (TTOPEN ? '' : ' hidden') + '><b>How we got this</b><ul>' +
      '<li>10,000 simulated seasons of the <span class="tt-n">' + n + '</span></li>' +
      '<li>Rules: the conference\u2019s own tiebreakers, then the 12-team playoff field</li>' +
      '<li>Data: ESPN public scores and schedules' + (a ? ', updated ' + a : '') + '</li></ul>' +
      '<p class="tt-fm"><a href="/method/">Full method</a></p></div>';
  }
  if (!W.__ttw) { W.__ttw = 1; D.addEventListener('click', function (e) { var b = e.target && e.target.closest && e.target.closest('.tt-d'); if (!b) return;
    var p = D.getElementById(b.getAttribute('aria-controls')); if (!p) return; TTOPEN = p.hidden; p.hidden = !TTOPEN; b.setAttribute('aria-expanded', TTOPEN ? 'true' : 'false'); }); }
  function tilesHtml(s, ex, st) {
    var nd = !T, t = nd ? FB : T[s], n = esc(t.n), pn = esc(poss(t.n)), ind = isInd(t), m = metricOf(t), ccgm = m === 'ccg', td = st === 'ok' && TD.teams[s], i, h;
    if (td && td.m !== m) { st = 'stale'; td = null; }
    var strip = ex ? '<div class="pt-strip" data-state="example"><span class="pt-who">' + logo32(s) + '<span>Example: <b>' + n + '</b>. Choose your team above to see yours.</span></span></div>'
                   : '';
    /* tile 1: from pred-teams only */
    var cells = [['Playoff chances', pctT(t.p), 'pt-hero', 'cfp'], ['First-round bye', pctT(t.b), '', 'cfpd']];
    if (!ind) cells.push(['Make conference championship', pctT(t.c), '', 'conf'], ['Win the conference', pctT(t.w), '', 'conf']);
    h = ''; var NDH = ''; cells.forEach(function (c) { h += '<div' + (c[2] ? ' class="' + c[2] + '"' : '') + '><dt>' + lslot(c[3], t, ind) + '<span class="pt-lt">' + esc(c[0]) + '' + '</span></dt><dd' + (c[1] === 'n/a' ? ' class="pt-na"' : '') + '>' + esc(c[1]) + '</dd></div>'; NDH += '<div' + (c[2] ? ' class="' + c[2] + '"' : '') + '><dt>' + lslot(c[3], t, ind) + '<span class="pt-lt">' + esc(c[0]) + '</span></dt><dd>' + PH('') + '</dd></div>'; });
    var t1 = '<li class="pk-tile pt-t pt-t1"><div class="pt-hd"><h3>Your team\u2019s chances</h3><a href="/team/' + s + '/">Team page<span class="vh"> for ' + n + '</span>' + AR + '</a></div>' + (nd && st === 'err' ? errHtml() : '<dl class="pt-g">' + (nd ? NDH : h) + '</dl>' + (nd ? '' : '<button type="button" class="tt-d tt-mr" aria-expanded="' + (TTOPEN ? 'true' : 'false') + '" aria-controls="tt-dp"><span>Show the math</span><span class="tt-ch" aria-hidden="true"></span></button>' + ttPanel())) + (ind ? '<p class="pt-note">Independents have no conference championship game.</p>' : '') + '</li>';
    /* tile 2: the Lab (built after gm/body below) */
    var nowP = nd ? PH('pt-ph-n') : pctT(ccgm ? t.c : t.p), g = null, gm = '', body = '';
    if (td) { for (i = 0; i < td.n.length; i++) if (!started(td.n[i].k, td.n[i].t)) { g = td.n[i]; break; } }
    var cap = (ccgm ? 'Conference championship game chances' : 'Playoff chances') + ', next game';
    if (st === 'loading' || st === 'idle') {
      gm = '<p class="pt-gm">' + PH('pt-ph-g') + '</p>';
      body = '<p class="pt-cap">' + cap + '</p><dl class="pt-g3"><div><dt>Now</dt><dd>' + nowP + '</dd></div><div><dt>If ' + n + ' wins</dt><dd>' + PH('pt-ph-n') + '</dd></div><div><dt>If ' + n + ' loses</dt><dd>' + PH('pt-ph-n') + '</dd></div></dl>';
    } else if (st === 'err') body = errHtml();
    else if (st === 'stale') body = updHtml();
    else if (st === 'ok') {
      if (g) {
        gm = '<p class="pt-gm"><b>' + (g.h === 0 ? 'at ' : 'vs ') + esc(g.o) + '</b>' + esc(g.d) + '</p>';
        body = '<p class="pt-cap">' + cap + '</p><dl class="pt-g3"><div><dt>Now</dt><dd>' + nowP + '</dd></div><div><dt>If ' + n + ' wins</dt><dd>' + pctM(g.w) + '</dd></div><div><dt>If ' + n + ' loses</dt><dd>' + pctM(g.l) + '</dd></div></dl>';
      } else body = '<p class="pt-empty">No game left to run.</p>';
    }
    /* lab1: ONE the Lab tile replaces the What if tile and the Big 12 title race tile. Team run | Conference run share one box; the shared builders (seg, confPanel, confCard, markA) live in chat.js (W.KTLab) so the home tile and the bottom sheet draw the same thing. */
    if (W.KTLab) W.KTLab.confs = confList;
    var RT20 = '<svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M7 3.5 13.5 10 7 16.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var K = W.KTLab || { name: ((document.getElementById('pk-wh') || {}).textContent || ''), sub: '', seg: function () { return ''; }, confPanel: function () { return ''; }, markA: function () { return ''; } };
    if (LABS !== s) { LABS = s; K.cs = (ind || ex) ? '' : t.cs; K.cn = (ind || ex) ? '' : t.cn; }   /* the Conference run starts on the team's own conference (none for Independents or the example); a choice in the select is kept until the team changes */
    K.team = { s: s, n: t.n, ex: !!ex };
    var lm = 'team';   /* labtile1: no tabs on the home tile; the Conference run panel is gone, the link row below is the single path to the conference page */
    var lcs = (ind || ex || !t.cs || !/^[a-z0-9-]+$/.test(t.cs)) ? '' : t.cs, lcn = lcs ? String(t.cn || '') : '';
    var lk = '';   /* jared5: no 'See all conference races' link on the home tile */
    var who = '<div class="wl-who">' + logo(s) + '<p class="wl-nm">' + n + '</p><a class="wl-ch" href="/#choose" data-pk-choose' + (ex ? '' : ' aria-label="Change team. Now ' + n + '"') + '>' + (ex ? 'Choose your team' : 'Change team') + '</a></div>';
    var wl = '<li class="pk-tile pt-t pt-t2 pk-wi wl ktsp" id="wl-home" data-state="' + (ind ? 'ind' : 'team') + '" data-mode="team"><div class="wl-hd"><img class="wl-mk ktsp-sh" src="/assets/brand/lab/what-if-lab-A3-spot-400.png" width="72" height="96" alt="" aria-hidden="true" decoding="async" fetchpriority="low"><div class="wl-ht"><h3 id="pk-wh" tabindex="-1">' + esc(K.name) + '</h3>' + (K.sub ? '<p class="wl-sub">' + esc(K.sub) + '</p><p class="wl-tag">Real data. Real simulations. No guessing.</p>' : '') + '</div></div>' +
      '<div class="wl-pn" id="wl-p-team" data-wl-m="team">' + who + gm + body +
      '<button type="button" class="btn-wi on-light" data-pk-open data-pk-name="' + n + '" aria-label="Run a what if for ' + n + '">Run a what if\u2026</button>' + lk + '</div></li>';
    var t2 = wl;
    /* tile 3: Who to root for */
    var ph = ccgm ? 'chances to reach the conference championship game' : 'playoff chances', rows = [], more = [];
    /* rootables-shared (Nov 1): tile 3 reads the SAME per-team file as the team page and the share card (data/rootables/<slug>.json), rows drawn by KTRvHome.row (one swappable template) */
    var rd = RD[s], cf = rd && rd.v ? rd.conf : '';
    ph = ccgm && !(rd && rd.v) ? ph : (isInd(t) || !cf ? 'playoff chances' : 'playoff and ' + esc(cf) + '\u00A0championship chances');
    if (st === 'ok') { if (rd === undefined) { loadRD(s); st = 'loading'; } else if (rd === 'err') st = 'err'; else if (String(rd.as_of).replace(/ MT$/, '') !== pageStamp()) st = 'stale'; }
    if (st === 'ok') rd.rows.forEach(function (r) { if (!started(r.k, r.t)) { if (rows.length < 4) rows.push(r); else if (more.length < 4) more.push(r); } });   /* rows 1-4 are the collapsed list; rows 5-6 (when the data has them) sit behind the See the full list toggle */
    if (RXS !== s) { RXS = s; RX = false; }
    body = '';
    if (st === 'loading' || st === 'idle') {
      body = '<p class="pt-cap">Points added to ' + pn + ' ' + ph + '</p><ol class="pt-rl" aria-hidden="true">'; for (i = 0; i < 4; i++) body += '<li class="pt-r"><p class="pt-ro">' + PH('pt-ph-l') + '</p><p class="pt-rw">' + PH('pt-ph-s') + '</p></li>'; body += '</ol>';
    } else if (st === 'err') body = errHtml();
    else if (st === 'stale') body = updHtml();
    else if (st === 'ok') {
      if (rows.length) {
        body = '<p class="pt-cap">Points added to ' + pn + ' ' + ph + '</p><ol class="pt-rl rv-rl" id="pt-rl" aria-label="Results that help ' + n + ' most">';
        rows.concat(more).forEach(function (r, ri) { var x = ri >= rows.length, L = function (g) { return g && W.KTLogo ? W.KTLogo.team(g, 20, true) : ''; };
          body += W.KTRvHome.row({ id: s + '-' + ri, slug: r.root.g, root: { name: r.root.n, logo: L(r.root.g) }, other: { name: r.other.n, logo: L(r.other.g) }, gain: r.pts, when: r.d, tag: r.tag, race: r.race, why: r.why, extra: x ? ' data-x' + (RX ? '' : ' hidden') : '' }); });
        body += '</ol>';
        if (more.length) body += '<button type="button" class="pt-more more" id="pt-more" aria-expanded="' + (RX ? 'true' : 'false') + '" aria-controls="pt-rl"><span class="pt-ml">' + (RX ? 'Show less' : 'See the full list') + '</span> <span class="cv" aria-hidden="true">\u2304</span></button>';
      } else body = '<p class="pt-empty">No game this week moves ' + pn + ' ' + ph + ' by 1.0 point or more.</p>';
    }
    var t3 = '<li class="pk-tile pt-t pt-t3" id="rootables"><div class="pt-hd"><h3>KickTip Rootables <span class="pt-sub">Who to root for</span></h3></div>' + body +
      '</li>';
    return strip + '<ul class="pk-tiles pt-tiles">' + t1 + t2 + t3 + '</ul>';
  }
  function lslot(k, t, ind) {   /* fixed-width mark slot (the label names the row, so the mark is decorative); a row without a mark keeps an empty slot */
    var cs = k === 'conf' && !ind && t && typeof t.cs === 'string' && /^[a-z0-9-]+$/.test(t.cs) && t.cs !== 'independents' ? t.cs : '';
    var B = k === 'cfp' ? '/assets/logos/conf/kt/cfp-mark-paper' : k === 'cfpd' ? '/assets/logos/conf/kt/cfp-mark-ink' : cs ? '/assets/logos/conf/kt/' + cs : '';
    if (!B) return '<span class="pt-lg" aria-hidden="true"></span>';
    return '<span class="pt-lg" aria-hidden="true"><img src="' + B + '@1x.png" srcset="' + B + '@1x.png 1x, ' + B + '@2x.png 2x, ' + B + '@3x.png 3x" alt="" loading="lazy" decoding="async"></span>';
  }
  function tlogos(t, ind) {   /* home6: CFP mark left of the title */
    return '<span class="pt-cfp"><img src="/assets/logos/conf/kt/cfp.svg" alt="College Football Playoff" width="32" height="32" loading="lazy" decoding="async"></span>';
  }
  function tconf(t, ind) {   /* home6: the team's conference mark + name (paper tile: full color, 44x24 box); independents get no mark, name indented to the same column */
    var cs = !ind && t && typeof t.cs === 'string' && /^[a-z0-9-]+$/.test(t.cs) && t.cs !== 'independents' ? t.cs : '', B = '/assets/logos/conf/kt/' + cs, nm = esc(t && t.cn || '');
    if (!nm) return '';
    if (!cs) return '<p class="pt-cf pt-cf-i"><span>' + nm + '</span></p>';
    return '<p class="pt-cf"><img src="' + B + '@1x.png" srcset="' + B + '@1x.png 1x, ' + B + '@2x.png 2x, ' + B + '@3x.png 3x" alt="' + nm + '" width="44" height="24" loading="lazy" decoding="async"><span aria-hidden="true">' + nm + '</span></p>';
  }
  function tlogoWire() { [].forEach.call(D.querySelectorAll('.pt-lgs img'), function (i) { var off = function () { i.classList.add('pt-lgx'); }; if (i.complete && !i.naturalWidth && i.src) off(); else i.addEventListener('error', off); }); }
  /* why2: the reason under each Who to root for row, from data the page already has: pred-teams (conference, playoff chance), the projected 12-team field (pred-teams field) and the season's played games (sim-bundle). One or two short sentences; no number is invented. */
  var KTWhy = (function () {
    function an(nm) { nm = String(nm || ''); var v = /^[A-Z]{2,}\b/.test(nm) ? /^[AEFHILMNORSX]/.test(nm) : /^[AEIO]/.test(nm); return (v ? 'an ' : 'a ') + nm; }   /* initialisms by letter sound (an LSU, a UCLA); words by first letter, U as 'a' (a Utah) */
    function poss(nm) { return /s$/.test(nm) ? nm + '\u2019' : nm + '\u2019s'; }
    function why(o) {   /* o: {s, a, x (slugs or null), an, xn (names), own, T, F (field [[slug, auto]]), G (played pairs {slug: [slugs]}), ccgm} */
      var T = o.T || {}, F = o.F || [], S = T[o.s] || {}, A = o.a && T[o.a], X = o.x && T[o.x], sn = S.n || '', xn = o.xn, out = [];
      function pos(sl) { for (var i = 0; i < F.length; i++) if (F[i][0] === sl) return i + 1; return 0; }
      function rankP(sl) { var p = T[sl] && T[sl].p, r = 1; if (p === null || p === undefined) return 0; for (var k in T) if (T[k].p > p) r++; return r; }
      var rival = X && S.cs && S.cs !== 'independents' && X.cs === S.cs, ps = pos(o.s), px = o.x ? pos(o.x) : 0;
      var met = function (u, v) { var g = o.G && o.G[u]; return !!(g && v && g.indexOf(v) >= 0); };
      if (o.own) {
        out.push('This is ' + poss(sn) + ' own game.');
        if (rival) out.push(xn + ' is ' + an(S.cn) + ' rival, so a win also counts in the conference standings.');
        else if (px) out.push(xn + ' is No. ' + px + ' in KickTip\u2019s projected 12-team field, so a win is over a field team.');
        else if (ps) out.push('A win keeps ' + sn + ' on track in the projected 12-team field, where it sits at No. ' + ps + '.');
        return out.join(' ');
      }
      if (rival) out.push(xn + ' is ' + an(S.cn) + ' rival, so ' + an(xn) + ' loss helps ' + sn + ' toward the conference championship game.');
      if (!o.ccgm && px && rival) out.push('It is also No. ' + px + ' in KickTip\u2019s projected 12-team field.');
      else if (!o.ccgm && px) out.push(xn + ' is No. ' + px + ' in KickTip\u2019s projected 12-team field' + (ps ? ' (' + sn + ' is No. ' + ps + ')' : '') + ', so ' + an(xn) + ' loss can open a spot or a seed.');
      else if (!o.ccgm && o.x && !px) { var rk = rankP(o.x); if (rk && rk <= 16) out.push((rival ? 'It is also No. ' : xn + ' is No. ') + rk + ' by playoff chances, just outside the projected 12-team field' + (rival ? '.' : ', so a loss keeps it from moving into a spot.')); }
      if (out.length < 2 && o.a && met(o.s, o.a)) out.push(sn + ' played ' + o.an + ' this season, so ' + an(o.an) + ' win helps ' + poss(sn) + ' strength of schedule.');
      if (!out.length) out.push('Small ripple effect: ' + an(xn) + ' loss slightly opens the at-large pool.');
      return out.slice(0, 2).join(' ');
    }
    function pairs(B) {   /* sim-bundle played games -> {slug: [opponent slugs]} */
      var o = {}; if (!B || !B.teams || !B.played) return o;
      B.played.forEach(function (g) { var h = B.teams[g[0]], a = B.teams[g[1]]; if (!h || !a || !h.g || !a.g) return; (o[h.g] = o[h.g] || []).push(a.g); (o[a.g] = o[a.g] || []).push(h.g); });
      return o;
    }
    return { why: why, pairs: pairs };
  })();
  /* why2 end */
  function whyHtml(r, td, t, ccgm, pn, ph, p, s) {
    var wa = { s: s, a: slugOfName(r.a) || null, x: slugOfName(r.x) || null, an: r.a, xn: r.x, own: r.o === 1, T: T, F: FLD, G: GP, ccgm: ccgm }, why = KTWhy.why(wa);
    WYN++; WARGS['pt-wy' + WYN] = wa; return '<p class="pt-wy" id="pt-wy' + WYN + '" hidden>' + esc(why) + '</p>';
  }
  var WYN = 0, WARGS = {}, gbP = null;
  function loadGP() {   /* sim-bundle loads only when a Why? or Show the math opens */
    if (gbP) return gbP;
    gbP = fetch('/data/sim-bundle.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (B) {
      if (B && B.games && B.games.length) { NGAMES = B.games.length; [].forEach.call(D.querySelectorAll('.tt-n'), function (x) { x.textContent = NGAMES.toLocaleString('en-US') + ' remaining games'; }); }
      GP = KTWhy.pairs(B); for (var k in WARGS) { var el = D.getElementById(k); if (el) { WARGS[k].G = GP; el.textContent = KTWhy.why(WARGS[k]); } }
    }).catch(function () { gbP = null; });
    return gbP;
  }
  D.addEventListener('click', function (e) { var b = e.target && e.target.closest && e.target.closest('.pt-wb, .tt-d'); if (b) loadGP(); }, true);
  function whyBtn() {   /* why3: the Why? toggle sits at the right end of the points line; its text opens below the row */
    return '<button type="button" class="pt-wb" aria-expanded="false" aria-controls="pt-wy' + (WYN + 1) + '">Why?<span class="vh"> Root for this team</span></button>';
  }
  function logo32(s) { return W.KTLogo ? W.KTLogo.team(s, 32, true) : ''; }
  var lastKey = null, wasRetry = false, RX = false, RXS = null, LABS = null;   /* LABS: the team the Lab's conference choice belongs to */   /* RX: the Who to root for tile is expanded (kept across repaints, reset when the team changes) */
  function paint() {
    if (!how) return; syncUI();
    if (!T) {   /* race1: no team data yet. 'loading' = the static skeleton, 'err' = the existing error line + Try again; nothing is painted before the 6 s wait ends */
      if (!ND) return; var nk = 'nd|' + ND; if (nk === lastKey) return; lastKey = nk;
      how.setAttribute('aria-label', 'Your team at a glance'); how.innerHTML = '<div class="w">' + tilesHtml(EXAMPLE, true, ND) + '</div>'; labWatch(); tlogoWire();
      if (wasRetry && ND === 'err') { wasRetry = false; var nh = $('#pk-wh'); if (nh) nh.focus({ preventScroll: true }); }
      return;
    }
    var s = yourTeam(), ex = !s; if (ex && holding()) return; if (ex) s = T[EXAMPLE] ? EXAMPLE : null; if (!s) return;
    var st = tdState(), k = s + '|' + (ex ? 'x' : 'c') + '|' + st + '|' + (RD[s] === undefined ? 'n' : RD[s] === 'err' ? 'e' : 'r') + '|' + (T[s].p + ',' + T[s].c + ',' + T[s].b + ',' + T[s].w);
    if (k === lastKey) return; lastKey = k;
    how.setAttribute('aria-label', 'Your team at a glance');
    how.innerHTML = '<div class="w">' + tilesHtml(s, ex, st) + '</div>'; if (location.hash === '#rootables' && !W.__rtj) { W.__rtj = 1; var rj = D.getElementById('rootables'); if (rj) W.requestAnimationFrame(function () { rj.scrollIntoView(); }); } H.classList.add('pc-rdy'); markCards(); labWatch(); tlogoWire();
    if (wasRetry && st !== 'loading' && st !== 'idle') { wasRetry = false; var h = $('#pk-wh'); if (h) h.focus({ preventScroll: true }); }
  }
  D.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-pt-retry]'); if (!b) return;
    e.preventDefault(); wasRetry = true; for (var q in RD) if (RD[q] === 'err') delete RD[q]; tdP = null; TDS = 'idle'; lastKey = null; if (!T) { ND = 'loading'; loadT(); } loadTD(); paint();
  });
  D.addEventListener('click', function (e) {   /* change 1: the toggle at the bottom of the Who to root for tile */
    var wb = e.target.closest && e.target.closest('.pt-wb'); if (wb) { var wx = D.getElementById(wb.getAttribute('aria-controls')), op = wb.getAttribute('aria-expanded') !== 'true'; wb.setAttribute('aria-expanded', op ? 'true' : 'false'); if (wx) wx.hidden = !op; return; }
    var b = e.target.closest && e.target.closest('#pt-more'); if (!b) return;
    RX = !RX; var t = b.closest('.pt-t3');
    $$('.pt-rx,[data-x]', t).forEach(function (li) { li.hidden = !RX; });
    b.setAttribute('aria-expanded', RX ? 'true' : 'false'); b.querySelector('.pt-ml').textContent = RX ? 'Show less' : 'See the full list';
    if (b.scrollIntoView) b.scrollIntoView({ block: 'nearest' });
  });
  D.addEventListener('kt:render', function (e) { var d = e.detail || {}; MM = !!(d.model && d.def && d.model !== d.def); });
  if (page === 'home') loadTD();
  /* tiles1:end */
  /* ---------- picker1: the Your team bar, the Change panel, one live region ---------- */
  var H = D.documentElement, bar = $('#pk-bar'), pan = $('#pk-pan'), chg = $('#pk-chg'), svb = $('#pk-sv'), live = $('#pk-live'), tmn = $('#pk-tm'), pkh = $('#pk-h'), cls = $('#pk-close'), swr = $('#pk-sw'), sll = $('#pk-sl');
  var STAR = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 16.9 6.8 19.7l1-5.9-4.3-4.1 5.9-.8z" stroke="currentColor" stroke-width="2" stroke-linejoin="round" fill="none"/></svg>';
  var STARON = STAR.replace('fill="none"', 'fill="currentColor"');
  var TICK = '<svg class="pk-ck" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 12.5l4.5 4.5L19 7.5" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
  var uiMode = H.classList.contains('pc-col') ? 'bar' : 'full';   /* full | bar | open */
  /* picker1b: signed-in device hint (kicktip_acct) and no team on this device yet: pk-pre collapsed the page, so keep the bar skeleton until the account list lands
     (account.js calls useAccount -> change event -> paint -> syncUI) or the hint goes away (signed out), for at most 6 s; then fall back to the full picker. */
  function hintOn() { try { return !!W.localStorage.getItem('kicktip_acct'); } catch (e) { return false; } }
  var acctHold = uiMode === 'bar' && hintOn();
  function holding() { return acctHold && hintOn() && !(W.KTMyTeams && W.KTMyTeams.signedIn && W.KTMyTeams.signedIn()); }
  function announce(m) { if (live) live.textContent = m; }
  function hasSaved(s) { try { return !!(W.KTMyTeams && W.KTMyTeams.has && W.KTMyTeams.has(s)); } catch (e) { return false; } }
  function savedList() { try { var g = W.KTMyTeams && W.KTMyTeams.get(); return (g && g.teams || []).filter(function (s) { return T && T[s]; }); } catch (e) { return []; } }
  function fitName() {   /* one line if it fits at 22..16 px; else two lines at 16 px (keeps the bar the same height for 126 of 138 teams at 390) */
    var n = $('#pk-bn'); if (!n || !n.textContent || !n.clientWidth) return;
    n.style.whiteSpace = 'nowrap'; n.style.overflowWrap = '';
    var sz = [22, 20, 19, 18, 17, 16], i = 0;
    for (; i < sz.length; i++) { n.style.fontSize = sz[i] + 'px'; if (n.scrollWidth <= n.clientWidth + 0.5) break; }
    if (i === sz.length) { n.style.whiteSpace = ''; var k = [17, 16, 15, 14]; n.style.overflowWrap = 'normal'; for (i = 0; i < k.length; i++) { n.style.fontSize = k[i] + 'px'; if (n.scrollWidth <= n.clientWidth + 0.5) break; } if (i === k.length) n.style.overflowWrap = ''; }   /* two lines: longest word must fit */
  }
  function setMode(m) {
    if (!bar || !pan) return; uiMode = m;
    H.classList.toggle('pc-col', m !== 'full'); H.classList.toggle('pc-opn', m === 'open');
    pan.hidden = (m === 'bar'); if (m === 'bar') pan.setAttribute('inert', ''); else pan.removeAttribute('inert');
    chg.setAttribute('aria-expanded', m === 'open' ? 'true' : 'false'); if (cls) cls.hidden = (m !== 'open' && !sheet);
    if (pkh) pkh.classList.toggle('vh', m !== 'open' && !sheet); syncPill(); if (m !== 'full') fitName();
  }
  function expand() { if (uiMode === 'bar') { setMode('open'); inp.focus({ preventScroll: true }); } }
  function collapse(toBtn) { if (uiMode === 'open') { close(true); setMode('bar'); if (toBtn !== false && chg) chg.focus({ preventScroll: true }); } }
  function fillBar(s) {
    var t = T[s], n = esc(t.n), on = hasSaved(s), bl = $('#pk-bl'), bn = $('#pk-bn');
    if (bl && bl.getAttribute('data-s') !== s) { bl.innerHTML = logo32(s); bl.setAttribute('data-s', s); }
    if (bn) bn.textContent = t.n;
    svb.hidden = false; svb.setAttribute('aria-pressed', on ? 'true' : 'false'); svb.setAttribute('aria-label', 'Save ' + t.n + ' to My teams');   /* constant name + aria-pressed: no double signal */
    svb.innerHTML = on ? STARON : STAR; if (tmn) tmn.hidden = on; fitName();
  }
  function renderLists() {
    var you = yourTeam(), ids = you ? [you] : [], pn = $('#pk-none'), cb = $('#pk-clr');
    savedList().forEach(function (x) { if (ids.indexOf(x) < 0) ids.push(x); });
    if (sll) sll.innerHTML = ids.map(function (x) { return rowHtml(x, { rem: true }); }).join('');
    if (swr) swr.hidden = !ids.length; if (pn) pn.hidden = !!you; if (cb) cb.hidden = !you;
  }
  function syncUI() {
    if (page !== 'home' || !bar) return;
    if (!T) { if (ND === 'err' && uiMode !== 'full') setMode('full'); if (ND === 'err') H.classList.add('pc-rdy'); return; }
    var s = yourTeam();
    if (!s) { if (holding()) return; if (uiMode !== 'full') setMode('full'); renderLists(null); H.classList.add('pc-rdy'); return; }
    fillBar(s); renderLists(s);
    if (uiMode === 'full') setMode('bar');
  }
  function markCards() {   /* My teams section: the card of the team on screen says Your team */
    var s = page === 'home' ? yourTeam() : null;
    $$('.mt-c').forEach(function (c) { var on = c.getAttribute('data-t') === s, tg = $('.mt-yt', c); if (on) c.setAttribute('aria-current', 'true'); else c.removeAttribute('aria-current'); if (on && !tg) { var hd = $('.mt-ch', c); if (hd) hd.insertAdjacentHTML('beforeend', '<span class="mt-yt">Your team</span>'); } else if (!on && tg) tg.parentNode.removeChild(tg); });
  }
  function pickSave(s) {   /* choosing a team also saves it to My teams (through KTMyTeams); Undo puts My teams back as it was */
    var M = W.KTMyTeams, m = D.getElementById('pk-msg'); if (!M || !M.pick || !m) return;
    var r = M.pick(s); if (r.r === 'already' || r.r === 'page') return;
    if (r.r === 'full') { m.innerHTML = 'My teams is full (' + M.cap() + '). <a href="/#my-teams">Open My teams</a> to remove one.'; return; }
    m.innerHTML = 'Saved to My teams \u00b7 <button type="button" class="pb-undo">Undo<span class="vh"> saving ' + esc(T[s].n) + '</span></button>';
    var u = m.querySelector('.pb-undo'); if (u) u.addEventListener('click', function () { M.unpick(r.snap); m.textContent = 'Removed ' + T[s].n + ' from My teams.'; paint(); syncUI(); if (chg) chg.focus({ preventScroll: true }); });
  }
  function choose(s) {   /* tap a team name: set as your team and show it (the same one-tap flow as before) */
    if (!T || !T[s]) return; var was = yourTeam() === s; if (!was) youWrite(s);
    lastKey = null; sheetOff(); close(true); paint(); setMode('bar'); syncUI(); pickSave(s);
    announce((was ? 'Showing ' + T[s].n + '.' : T[s].n + ' set as your team.') + ' Its chances and the What if are just below.');
    inp.blur(); syncPill(); W.scrollTo(0, 0); if (chg) chg.focus({ preventScroll: true });
  }
  /* ---------- rows: one team = its name (a real link) + two 44px toggles: Your team and Follow (or Remove inside Your teams) ---------- */
  var RING = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="7.5" stroke="currentColor" stroke-width="2.2" fill="none"/></svg>';
  var CHK = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 12.5l4.5 4.5L19 7.5" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
  var XIC = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" fill="none"/></svg>';
  function rowHtml(s, o) {
    var t = T[s], n = esc(t.n), yt = yourTeam() === s, fw = hasSaved(s);
    return '<li class="pk-tr"><a class="pk-tn" href="/team/' + s + '/" data-slug="' + s + '">' + logo(s) + '<span class="pk-t"><span class="pk-n">' + (o.raw ? hi(t.n, o.raw) : n) + '</span><span class="pk-c">' + esc(t.cn) + '</span></span></a><span class="pk-ctl">' +
      '<button type="button" class="pk-yb" data-yt="' + s + '" aria-pressed="' + (yt ? 'true' : 'false') + '">' + (yt ? CHK : RING) + '<span class="pk-bl">Your team</span><span class="vh"> ' + n + '</span></button>' +
      (o.rem ? '<button type="button" class="pk-rm" data-rm="' + s + '" aria-label="Remove ' + n + '">' + XIC + '<span class="pk-bl" aria-hidden="true">Remove</span></button>'
             : '<button type="button" class="pk-fb" data-fw="' + s + '" aria-pressed="' + (fw ? 'true' : 'false') + '">' + (fw ? STARON : STAR) + '<span class="pk-bl">' + (fw ? 'Following' : 'Follow') + '</span><span class="vh"> ' + n + '</span></button>') + '</span></li>';
  }
  function toggles(e) {
    var b = e.target.closest && e.target.closest('button[data-yt],button[data-fw],button[data-rm],#pk-clr'); if (!b || !pan.contains(b) || !T) return;
    var s = b.getAttribute('data-yt') || b.getAttribute('data-fw') || b.getAttribute('data-rm') || '', n = s && T[s] ? T[s].n : '', msg = '';
    var kind = b.hasAttribute('data-yt') ? 'yt' : b.hasAttribute('data-fw') ? 'fw' : b.hasAttribute('data-rm') ? 'rm' : 'clr', host = b.closest('#pk-list') ? 'res' : b.closest('#pk-sl') ? 'sl' : '';
    if (YV === undefined) { var y0 = yourTeam(); if (y0) youWrite(y0); }   /* pin the team that was "your team" by the old first-saved rule, so un-following it does not hand the title to the next team */
    if (kind === 'yt') { if (yourTeam() === s) { youWrite(''); msg = 'Your team cleared. No team chosen.'; } else { youWrite(s); msg = n + ' set as your team.'; } }
    else if (kind === 'clr') { youWrite(''); msg = 'Your team cleared. No team chosen.'; }
    else if (kind === 'fw') { if (!(W.KTMyTeams && W.KTMyTeams.toggle)) return; var was = hasSaved(s), ok = W.KTMyTeams.toggle(s), pm = $('#pk-pm'); msg = was ? n + ' removed.' : ok ? 'Following ' + n + '.' : ((pm && pm.textContent) || 'You have reached the limit. Remove a team to follow another.'); }
    else { if (yourTeam() === s) youWrite(''); if (hasSaved(s) && W.KTMyTeams) W.KTMyTeams.toggle(s); msg = n + ' removed.'; }
    announce(msg); lastKey = null;
    if (uiMode === 'full' && yourTeam()) setMode('open');   /* first team chosen from the full picker: stay in the panel so more teams can be followed */
    syncUI(); paint(); markCards(); if (open) render(true);
    var sel = kind === 'yt' ? 'button[data-yt="' + s + '"]' : kind === 'fw' ? 'button[data-fw="' + s + '"]' : '', root = host === 'res' ? res : host === 'sl' ? sll : pan;
    var nb = (sel && $(sel, root)) || (kind === 'rm' && ($('button[data-rm]', sll))) || (kind === 'rm' || kind === 'clr' ? $('#pk-sl-lab') || pkh : null);
    if (nb) { nb.focus({ preventScroll: true }); if (nb.scrollIntoView) nb.scrollIntoView({ block: 'nearest' }); }
  }
  /* ---------- change 4: phone keyboard. While the search box is in use on a phone the panel becomes a sheet exactly as tall as the visible area (visualViewport) ---------- */
  var VV = W.visualViewport, MQ = W.matchMedia ? W.matchMedia('(max-width:759px)') : null, sheet = false;
  function vvSync() {   /* --vvh visible height, --vvt how far the visible area sits below the top of the layout viewport (iOS moves it when the keyboard opens), --kb keyboard height */
    var ih = W.innerHeight, h = VV ? VV.height : ih, t = VV ? VV.offsetTop : 0, st = H.style;
    st.setProperty('--vvh', Math.round(h) + 'px'); st.setProperty('--vvt', Math.round(t) + 'px'); st.setProperty('--kb', Math.max(0, Math.round(ih - h - t)) + 'px');
  }
  if (VV) { VV.addEventListener('resize', vvSync); VV.addEventListener('scroll', vvSync); } W.addEventListener('resize', vvSync);
  var sheetOp = null;
  D.addEventListener('pointerdown', function (e) { var a = e.target && e.target.closest && e.target.closest('a,button'); if (a && pan && !pan.contains(a)) sheetOp = a; }, true);
  function sheetOn() { if (sheet || !MQ || !MQ.matches || !pan || !inp) return; sheet = true; pan.setAttribute('role', 'dialog'); pan.setAttribute('aria-modal', 'true'); pan.setAttribute('aria-labelledby', 'pk-h'); vvSync(); H.classList.add('pk-sheet'); if (pkh) pkh.classList.remove('vh'); if (cls) cls.hidden = false; }
  function sheetOff() { if (!sheet) return; sheet = false; H.classList.remove('pk-sheet'); pan.removeAttribute('role'); pan.removeAttribute('aria-modal'); pan.removeAttribute('aria-labelledby'); var op = sheetOp, ae = D.activeElement; if (op && op.isConnected && (!ae || ae === D.body || pan.contains(ae))) W.setTimeout(function () { if (op.offsetParent) op.focus({ preventScroll: true }); }, 0); var pm = $('#pk-pm'); if (pm) pm.textContent = ''; setMode(uiMode); }
  if (MQ && MQ.addEventListener) MQ.addEventListener('change', function () { if (!MQ.matches) sheetOff(); });
  function closePanel() { var was = sheet; sheetOff(); if (uiMode === 'open') collapse(true); else { close(true); if (was && D.activeElement && D.activeElement.blur) D.activeElement.blur(); } }
  function focusSearch() { if (!inp) return; if (uiMode === 'bar') { setMode('open'); } else { var c = $('#choose'); if (c && c.scrollIntoView) c.scrollIntoView({ block: 'start' }); } inp.focus({ preventScroll: true }); try { inp.select(); } catch (e) { /* none */ } syncPill(); }
  if (page === 'home' && bar) {
    if (acctHold) { var hn = 0, hiv = W.setInterval(function () { hn++; if (!holding() || hn >= 24) { W.clearInterval(hiv); acctHold = false; lastKey = null; syncUI(); paint(); } }, 250); }
    W.addEventListener('resize', fitName); if (D.fonts && D.fonts.ready) D.fonts.ready.then(fitName);
    pan.hidden = uiMode === 'bar'; if (uiMode === 'bar') pan.setAttribute('inert', '');
    chg.addEventListener('click', function () { if (uiMode === 'open') collapse(true); else expand(); });
    D.addEventListener('click', function (e) {   /* lab1: Change team / Choose your team inside the Lab (and the sheet) open the same picker as the Change team button */
      var a = e.target.closest && e.target.closest('[data-pk-choose]'); if (!a) return; e.preventDefault();
      if (W.KTLab && W.KTLab.close) W.KTLab.close(true);
      var c = D.getElementById('choose'); if (c && c.scrollIntoView) c.scrollIntoView({ block: 'start' });
      if (uiMode === 'bar') expand(); else if (inp) inp.focus({ preventScroll: true });
    });
    if (cls) cls.addEventListener('click', closePanel);
    pan.addEventListener('keydown', function (e) { if ((e.key === 'Escape' || e.key === 'Esc') && !e.defaultPrevented && (uiMode === 'open' || sheet)) { e.preventDefault(); closePanel(); } });
    svb.addEventListener('click', function () { var s = yourTeam(); if (s && W.KTMyTeams && W.KTMyTeams.toggle) { if (YV === undefined) youWrite(s); W.KTMyTeams.toggle(s); fillBar(s); renderLists(s); markCards(); svb.focus({ preventScroll: true }); } });
  }

  if (page === 'home' && inp && res) {
    inp.addEventListener('input', function () { render(); });
    inp.addEventListener('focus', function () { sheetOn(); syncPill(); if (inp.value && !open) render(); });
    inp.addEventListener('keydown', function (e) {
      var k = e.key, first = $('a.pk-tn, a.pk-cn', res);
      if (k === 'ArrowDown') { if (!open && inp.value) render(); first = $('a.pk-tn, a.pk-cn', res); if (open && first) { e.preventDefault(); first.focus(); } }
      else if (k === 'Escape' || k === 'Esc') { if (open) { e.preventDefault(); close(false); } else if (inp.value) { e.preventDefault(); close(true); } }
      else if (k === 'Enter') { if (!open || !first) return; e.preventDefault(); if (first.classList.contains('pk-cn')) W.location.assign(first.getAttribute('href')); else chooseRow(first, null); }
    });
    function chooseRow(el, ev) { var s = el.getAttribute('data-slug'); if (s) { if (ev) ev.preventDefault(); choose(s); } }
    res.addEventListener('keydown', function (e) {   /* arrows move between the name links; Tab reaches the two buttons on each row */
      var a = e.target.closest && e.target.closest('a.pk-tn, a.pk-cn'); if (!a) return;
      var all = $$('a.pk-tn, a.pk-cn', res), i = all.indexOf(a);
      if (e.key === 'ArrowDown') { e.preventDefault(); if (all[i + 1]) all[i + 1].focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); if (i > 0) all[i - 1].focus(); else inp.focus(); }
    });
    res.addEventListener('mousedown', function (e) { if (e.target.closest('button, a')) e.preventDefault(); });   /* keep focus (and the keyboard) in the box while something in the results is tapped */
    clr.addEventListener('click', function () { close(true); inp.focus(); });
    inp.addEventListener('blur', function () { setTimeout(function () { if (D.activeElement !== inp && !(res.contains(D.activeElement))) { setOpen(false); } syncPill(); }, 0); });
    D.addEventListener('mousedown', function (e) { if (open && !e.target.closest('.pk-box, .pk-res')) { setOpen(false); } });
    D.addEventListener('focusin', function (e) { if (open && !e.target.closest('.pk-box, .pk-res')) setOpen(false); });
    pan.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('#pk-pm a')) { sheetOff(); return; }   /* the cap message links to My teams, which the sheet would cover */
      var a = e.target.closest && e.target.closest('a.pk-tn');
      if (a) { if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return; var s = a.getAttribute('data-slug'); if (s && T && T[s]) { e.preventDefault(); choose(s); } return; }
      toggles(e);
    });


    D.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href="#choose"], a[href="/#choose"]'); if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey) return;
      e.preventDefault(); focusSearch();
    });
    if (W.location.hash === '#choose') focusSearch();
    /* freshness line: the same stamp the Sources box shows, so it is right after every data refresh */
    ktAsof();
    var fr = $('.pk-fresh'), src = $('.src'); if (fr && src && !fr.querySelector('.kt-asof')) { var m = /(?:Model numbers|Chances) recalculated from them: (?:[A-Za-z]{3}, )?([A-Za-z]{3} \d{1,2}), \d{4}, (\d{1,2}:\d{2} [AP]M) MT/.exec(src.textContent); if (m) fr.textContent = 'Updated ' + m[1] + ', ' + m[2] + ' MT'; }
  }

  /* ================= MY TEAMS (editor search; hooks called from assets/myteams.js) ================= */
  W.KTPick = {
    mark: function () { markCards(); },
    mtHtml: function () {
      return '<div class="pk pk--card"><div class="pk-box">' + SEARCH + '<input id="mt-pk-in" class="pk-in" type="text" value="" placeholder="Team" name="mt-team-search" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" aria-labelledby="mteh" aria-controls="mt-pk-list"></div><div class="pk-res" id="mt-pk-list" hidden></div><p class="vh" id="mt-pk-st" role="status" aria-live="polite"></p></div>';
    },
    mtBind: function (root, TT, add, getDraft) {
      var i = $('#mt-pk-in', root), l = $('#mt-pk-list', root), st = $('#mt-pk-st', root); if (!i || !l) return;
      if (TT) { T = T || TT; IDX = IDX || build(); }
      function draw() {
        var raw = i.value, q = norm(raw); if (!q) { l.hidden = true; l.innerHTML = ''; st.textContent = ''; return; }
        var f = find(raw), list = f.teams.slice();

        l.hidden = false;
        if (!list.length) { l.className = 'pk-res pk-nm'; l.innerHTML = '<p><b>No team matches \u201C' + esc(raw.replace(/^\s+|\s+$/g, '')) + '\u201D.</b></p><p>Check the spelling.</p>'; st.textContent = 'No results for ' + raw; return; }
        var d = getDraft(); l.className = 'pk-res';
        l.innerHTML = '<ul class="pk-ul">' + list.map(function (t) { var on = d.indexOf(t.s) >= 0; return '<li class="pk-rw">' + logo(t.s) + '<span class="pk-t"><span class="pk-n">' + hi(t.n, raw) + '</span><span class="pk-c">' + esc(t.cn) + '</span></span><button type="button" class="pk-add" data-add="' + t.s + '"' + (on ? ' aria-disabled="true" aria-label="' + esc(t.n) + ' is already chosen">Added' : ' aria-label="Add ' + esc(t.n) + '">Add') + '</button></li>'; }).join('') + '</ul>';
        st.textContent = list.length + (list.length === 1 ? ' result.' : ' results.');
      }
      i.addEventListener('input', draw);
      i.addEventListener('keydown', function (e) { if (e.key === 'Escape' || e.key === 'Esc') { if (i.value) { e.preventDefault(); i.value = ''; draw(); } } });
      l.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-add]'); if (!b || b.getAttribute('aria-disabled') === 'true') return;
        var r = add(b.getAttribute('data-add'));
        if (r === 'ok') { var n = $('#mt-pk-in', root); if (n) n.focus(); }
      });
    }
  };

  /* ---------- data in ---------- */
  /* race1: this script is the last deferred one, so on a slow connection kt.js can fire kt:render before it runs. kt.js keeps the last payload in window.KTLAST; read it here (same code path as the event). */
  var FLD = null, GP = null;   /* why2: projected field (from kt:render) and played-game pairs (sim-bundle) */
  var ND = null, ndT = 0, TP = null, NDWAIT = 6000, FB = { n: 'BYU', cs: 'big-12', cn: 'Big 12', p: null, b: null, c: null, w: null };
  function gotData(d) {
    MM = !!(d.model && d.def && d.model !== d.def);
    if (d.T) { T = d.T; IDX = build(); ND = null; clearTimeout(ndT); }
    if (d.F) FLD = d.F;
    if (page === 'home') { lastKey = null; paint(); if (inp && D.activeElement === inp && inp.value) render(); }
  }
  function ndFail() { TP = null; if (T) return; clearTimeout(ndT); ND = 'err'; lastKey = null; paint(); }   /* no data in 6 s, or the fetch failed: the existing error line + Try again */
  function loadT() {   /* Try again with no team data: fetch the team list ourselves (the default model, same file kt.js reads) */
    if (TP || T) return; ND = 'loading'; clearTimeout(ndT); ndT = setTimeout(ndFail, NDWAIT);
    TP = fetch('/data/pred-teams.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('pred-teams'); return r.json(); }).then(function (j) {
      if (!j || !j.teams) throw new Error('pred-teams'); TP = null; if (!T) gotData({ T: j.teams, F: j.field || null, model: null, def: null });
    }).catch(ndFail);
  }
  D.addEventListener('kt:render', function (e) { gotData(e.detail || {}); });
  if (W.KTLAST) gotData(W.KTLAST); else if (page === 'home') { ND = null; clearTimeout(ndT); ndT = setTimeout(ndFail, NDWAIT); }
  if (page === 'home') {
    var ready = function () { if (W.KTMyTeams && W.KTMyTeams.on) W.KTMyTeams.on(function () { paint(); }); };
    if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', ready); else ready();
  }
})();
