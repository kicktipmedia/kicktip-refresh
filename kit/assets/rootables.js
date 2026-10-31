/* KickTip Rootables. For the team on the page: which games in the next 7 days move its chance the most, and which side to cheer for.
   Information only. Runs in the browser from files the site already publishes (whatif/index.json, whatif/w<week>.json, sim-bundle.json for kickoff times) for the model on screen.
   Run-gate build (Oct 24, 2026): the team page carries a compact card (title, one line, Run Rootables and the FULL terms line, all static HTML). Nothing is fetched and nothing is drawn until the person taps Run Rootables; no auto-render, no memory. Rootables never writes storage (it only reads the model pick).
   The pure function KTRootables.compute() has no DOM; tests/rootables_unit.js runs it under node against the published shards. */
(function () {
  'use strict';
  var MS7 = 7 * 864e5, THRESH = 10, MAXROWS = 8, SHOWN = 2, MINUS = '\u2212';
  var METRICS = { cfp12: { col: 'cfp12', short: 'Make the playoff field', full: 'Make the playoff field', phrase: 'chance to make the 12-team playoff field' },
                  ccg: { col: 'ccg', short: 'Make conference championship', full: 'Make conference championship', aria: 'Make conference championship', phrase: 'chance to reach the conference championship game' } };
  var SHORT = '<div class="rn rtg"><span class="rtg1">Tapping Run accepts the terms · </span><details class="rtgd"><summary>Terms<span class="w2ch" aria-hidden="true"></span></summary><p>Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></p></details></div>';   /* the SHORT under-Run line under Run Rootables again (built from src/terms_copy.py); the FULL line is static HTML in the card */
  /* Creative's strings for the blended list (Oct 31, 10:52 MT), in one place so they can be swapped */
  var STR = { tag: { cfp12: 'Playoff', ccg: '{Conf}\u00A0championship' }, race: { cfp12: 'the playoff', ccg: 'the {Conf} championship' },
              gain: '{Team} gain', also: 'Also {v}\u00A0pts for {race}', empty: 'No other games this week move {Team}\u2019s chances by much.' };
  function fill(t, o) { return t.replace(/\{(\w+)\}/g, function (_, k) { return o[k] !== undefined ? o[k] : ''; }); }
  function tagText(race, conf) { return fill(STR.tag[race], { Conf: conf || 'Conference' }); }
  function alsoText(sec, conf) { return sec ? fill(STR.also, { v: (sec.v < 0 ? MINUS : '+') + pts(Math.abs(sec.v)), race: fill(STR.race[sec.race], { Conf: conf || 'conference' }) }) : ''; }
  var MODEL_NAME = { blend: 'KickTip blend', elo: 'Elo-style', eff: 'Efficiency model' };

  /* ---------- pure part ---------- */
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function tzParts(ms, zone, opt) { var o = {}; new Intl.DateTimeFormat('en-US', Object.assign({ timeZone: zone }, opt)).formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = p.value; }); return o; }
  function mtMs(stamp) { /* '2026-10-24 17:55 MT' (Mountain Time, DST aware) -> UTC ms; null if the text is not in that form */
    var m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d) MT$/.exec(stamp || ''); if (!m) return null;
    var guess = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
    function off(t) { var p = tzParts(t, 'America/Denver', { hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }); return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute) - t; }
    var t = guess - off(guess); return guess - off(t);
  }
  var REAL = { '401864537': '2026-11-15T04:00Z' };   /* simweeks3: known-real kickoff that looks like a placeholder (Hawaii v North Dakota State, 9:00 PM MT Nov 14): id -> exact ESPN date; checked first */
  function isTba(iso, id) { if (id !== undefined && REAL[id] === iso) return false; var t = iso.slice(11); return t === '04:00Z' || t === '05:00Z'; }   /* ESPN 'time TBD' placeholders (same rule the pages use) */
  function parseKick(iso) { var t = Date.parse(iso.length === 17 ? iso.slice(0, 16) + ':00Z' : iso); return isNaN(t) ? null : t; }
  function buildGames(index, bundle) { /* index.games joined with the kickoff times of sim-bundle.json */
    var by = {}; index.games.forEach(function (g) { by[g.id] = g; }); var out = [];
    (bundle.games || []).forEach(function (b) {
      var g = by[b.id]; if (!g || !b.date) return; var k = parseKick(b.date); if (k === null) return;
      out.push({ id: g.id, week: g.week, h: g.h, a: g.a, neutral: !!g.neutral, kick: k, tba: isTba(b.date, b.id), ip: !!b.ip });
    });
    return out;
  }
  /* compute(team, metric, ctx, now): ctx = { index, games, shard(week, id) -> {h:[[team,ccg,title,cfp12,bye]..],a:[..]} | null, asOfMs }.
     Chance for a team under each result of a game = its row in the shard, or its baseline when it is not listed (it moved less than 0.3 point). Integers are per-mille; sort and threshold on the integers. */
  function compute(team, metric, ctx, now, all) {
    if (metric === 'blend') return blend(team, ctx, now);
    var index = ctx.index, col = index.metrics.indexOf(metric) + 1, rows = [], hasOwn = false;
    if (col < 1) throw new Error('metric');
    var end = ctx.asOfMs + MS7;
    ctx.games.forEach(function (g) {
      if (g.ip || g.kick > end || now > (g.tba ? g.kick + 864e5 : g.kick)) return;   /* in progress, outside the next 7 days, or already started (a TBA day counts until it is over) */
      var s = ctx.shard(g.week, g.id); if (!s) return;
      function chance(side) { var l = s[side] || []; for (var i = 0; i < l.length; i++) if (l[i][0] === team) return l[i][col]; return index.baseline[team][col - 1]; }
      if (g.h === team || g.a === team) { hasOwn = true; return; }   /* Jared Oct 31: leave off the team's own game (rooting for your own team is a given); the slots fill with the next-biggest games */
      var pH = chance('h'), pA = chance('a'), own = false;
      rows.push({ id: g.id, h: g.h, a: g.a, neutral: g.neutral, kick: g.kick, tba: g.tba, pH: pH, pA: pA, gap: Math.abs(pH - pA), root: pH >= pA ? g.h : g.a, other: pH >= pA ? g.a : g.h, pRoot: Math.max(pH, pA), pOther: Math.min(pH, pA), own: own });
    });
    var big = rows.filter(function (r) { return r.gap >= THRESH; });
    big.sort(function (x, y) { return y.gap - x.gap || x.kick - y.kick || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0); });
    return { rows: big.slice(0, MAXROWS), nBig: big.length, nWindow: rows.length, nHidden: rows.length - big.length, hasOwn: hasOwn, seasons: index.seasons, asOf: index.as_of, all: all ? rows : undefined };
  }

  /* Blended Rootables (Jared Oct 31, 10:51 MT): ONE list from the cfp12 and ccg measures ('title' is not used: unverified). Score = the larger of the two swings;
     same window, same 1.0-point threshold on the score, own games and started games left off. race = the race with the bigger swing (tie: playoff);
     sec = the other race when it also moves 1.0 point or more, signed for the side we root for (negative = that race prefers the other side). */
  function blend(team, ctx, now) {
    var P = compute(team, 'cfp12', ctx, now, true), C = compute(team, 'ccg', ctx, now, true), byC = {}, rows = [];
    C.all.forEach(function (r) { byC[r.id] = r; });
    P.all.forEach(function (p) {
      var c = byC[p.id] || null, m = p, o = c, race = 'cfp12';
      if (c && c.gap > p.gap) { m = c; o = p; race = 'ccg'; }
      var r = {}; Object.keys(m).forEach(function (k) { r[k] = m[k]; });
      r.race = race; r.gapP = p.gap; r.gapC = c ? c.gap : 0; r.sec = null;
      r.pP = [p.pH, p.pA]; r.pC = c ? [c.pH, c.pA] : null;
      if (o && o.gap >= THRESH) r.sec = { race: race === 'cfp12' ? 'ccg' : 'cfp12', v: o.root === m.root ? o.gap : -o.gap };
      rows.push(r);
    });
    var big = rows.filter(function (r) { return r.gap >= THRESH; });
    big.sort(function (x, y) { return y.gap - x.gap || x.kick - y.kick || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0); });
    return { rows: big.slice(0, MAXROWS), nBig: big.length, nWindow: rows.length, nHidden: rows.length - big.length, hasOwn: P.hasOwn, seasons: ctx.index.seasons, asOf: ctx.index.as_of, blend: true };
  }
  function pts(gap) { return (gap / 10).toFixed(1); }
  function pc(p) { return (p / 10).toFixed(1) + '%'; }
  function commas(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function whenShort(r) { /* 'Sat Oct 24 · 8:15 PM MT'; a TBA day uses the placeholder's calendar date and says time TBD, like the Remaining games table */
    if (r.tba) { var d = tzParts(r.kick, 'UTC', { weekday: 'short', month: 'short', day: 'numeric' }); return d.weekday + ' ' + d.month + ' ' + d.day + ' \u00B7 time TBD'; }
    var p = tzParts(r.kick, 'America/Denver', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return p.weekday + ' ' + p.month + ' ' + p.day + ' \u00B7 ' + p.hour + ':' + p.minute + ' ' + p.dayPeriod + ' MT';
  }
  function whenLong(r) {
    if (r.tba) { var d = tzParts(r.kick, 'UTC', { weekday: 'long', month: 'long', day: 'numeric' }); return d.weekday + ' ' + d.month + ' ' + d.day + ', time to be announced'; }
    var p = tzParts(r.kick, 'America/Denver', { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return p.weekday + ' ' + p.month + ' ' + p.day + ' at ' + p.hour + ':' + p.minute + ' ' + p.dayPeriod + ' Mountain Time';
  }
  function stampText(asOf) { var m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d) MT$/.exec(asOf || ''); if (!m) return asOf; var h = +m[4]; return MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + ((h + 11) % 12 + 1) + ':' + m[5] + ' ' + (h < 12 ? 'AM' : 'PM') + ' MT'; }

  /* Rootables v2 (Creative mock 1d26c0ff): ONE swappable template for a game card, used by the Run view below AND by tools/bake_static.js for the no-JS list.
     o = { slug: root team slug (tc- class), when, root: {name, logo}, other: {name, logo}, where: 'at'|'vs', gain: points text '3.0', label: '<Team> playoff gain', sr, extra: li attrs } */
  function rvCard(o) {
    var NB = '\u00A0', E = function (t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
    return '<li class="rb-row rv-cd' + (o.slug ? ' tc-' + o.slug : '') + '"' + (o.extra || '') + '><div aria-hidden="true">' + (o.tag ? '<p class="rv-race rv-' + o.race + '">' + E(o.tag) + '</p>' : '') + '<p class="rv-when">' + E(o.when) + '</p><div class="rv-mu"><div class="rv-sd on"><span class="rv-tag">Root' + NB + 'for</span>' + (o.root.logo || '') + '<span class="rv-nm">' + E(o.root.name) + '</span></div><span class="rv-vs">' + o.where + '</span><div class="rv-sd">' + (o.other.logo || '') + '<span class="rv-nm">' + E(o.other.name) + '</span></div></div>' +
      '<div class="rv-gn"><span>' + E(o.label) + '</span><b>+' + o.gain + NB + 'pts</b>' + (o.also ? '<span class="rv-also">' + E(o.also) + '</span>' : '') + '</div></div>' + (o.sr ? '<p class="sr">' + E(o.sr) + '</p>' : '') + '</li>';
  }
  function whenCardAt(r, tz) { var NB = '\u00A0', p;
    if (r.tba) { p = tz(r.kick, 'UTC', { weekday: 'short', month: 'short', day: 'numeric' }); return [p.weekday, p.month, p.day].join(NB) + ', time' + NB + 'TBD'; }
    p = tz(r.kick, 'America/Denver', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return [p.weekday, p.month, p.day].join(NB) + ', ' + p.hour + ':' + p.minute + NB + p.dayPeriod + NB + 'MT'; }
  var api = { compute: compute, buildGames: buildGames, mtMs: mtMs, whenShort: whenShort, whenLong: whenLong, stampText: stampText, pts: pts, pc: pc, MODEL_NAME: MODEL_NAME, rvCard: rvCard, STR: STR, fill: fill, tagText: tagText, alsoText: alsoText, whenCard: function (x) { return whenCardAt(x, tzParts); } };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  window.KTRootables = api;

  /* ---------- panel ---------- */
  var D = document, root = D.getElementById('rootables'), main = D.getElementById('main');
  if (!root || !main) return;
  /* Batch B r3 (Creative): the floating 'What if' chip never covers a Rootables row: hidden while the Rootables card is on screen. No JS: polish.css bottom padding (.has-ask #rootables) keeps the last row clear of the chip. */
  if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { D.documentElement.classList.toggle('rb-in', es[es.length - 1].isIntersecting); }).observe(root);
  var slug = main.getAttribute('data-team'), noCcg = root.getAttribute('data-noccg') === '1';
  var S = { outcome: 'cfp12', model: null, tok: 0, how: false }, cache = {}, started = false;
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fj(u) { return fetch(u, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function modelId() { /* the model on screen: the model control kt.js builds; else ?model=, else the stored model key (read only), else the blend */
    var c = main.querySelector('[data-mdl]'), id = c && c.getAttribute('data-model'); if (id && MODEL_NAME[id]) return id;
    try { var q = (new URLSearchParams(window.location.search).get('model') || '').toLowerCase(); if (q !== 'blend' && MODEL_NAME[q]) return q; } catch (e) { /* ignore */ }
    try { var v = window.localStorage.getItem('kicktip_model'); if (v !== 'blend' && MODEL_NAME[v]) return v; } catch (e) { /* ignore */ }
    return 'blend';
  }
  function load(model) { /* one fetch set per model, kept in memory: index + kickoff times, then the shard of each week the next 7 days touch */
    if (cache[model]) return cache[model];
    var base = model === 'blend' ? '/data/' : '/data/m/' + model + '/';
    var p = Promise.all([fj(base + 'whatif/index.json'), fj(base + 'sim-bundle.json')]).then(function (r) {
      var index = r[0], bundle = r[1], games = buildGames(index, bundle), asOfMs = mtMs(index.as_of), now = Date.now(), weeks = [], by = {}, shards = {};
      if (asOfMs === null) throw new Error('stamp');
      games.forEach(function (g) { if (!g.ip && g.kick <= asOfMs + MS7 && now <= (g.tba ? g.kick + 864e5 : g.kick) && weeks.indexOf(g.week) < 0) weeks.push(g.week); });
      weeks.forEach(function (w) { if (!index.shards[w]) throw new Error('shard ' + w); });
      (bundle.teams || []).forEach(function (t) { if (t.n) by[t.n] = t; }); var confs = {}; (bundle.confs || []).forEach(function (c) { confs[c.code] = c.name; });
      return Promise.all(weeks.map(function (w) { return fj(base + 'whatif/' + index.shards[w]).then(function (j) { shards[w] = j; }); })).then(function () {
        return { index: index, games: games, asOfMs: asOfMs, by: by, confs: confs, shard: function (w, id) { return (shards[w] && shards[w][id]) || null; } };
      });
    });
    p.catch(function () { if (cache[model] === p) delete cache[model]; });
    return (cache[model] = p);
  }
  function teamOf(ctx) { var i = ctx.index.team_names.indexOf(slugName(ctx)); return i; }
  function slugName(ctx) { var n = null; Object.keys(ctx.by).forEach(function (k) { if (ctx.by[k].g === slug) n = k; }); return n; }
  function nm(ctx, i) { var n = ctx.index.team_names[i], t = ctx.by[n]; return (t && (t.s || t.n)) || n; }
  function logo(ctx, i) { var t = ctx.by[ctx.index.team_names[i]]; return t && t.g && window.KTLogo ? window.KTLogo.team(t.g, 52, true) : ''; }

  function seg() {
    return '';   /* blended list (Oct 31): no playoff/conference switch */
    if (noCcg) return '';
    return '<div class="rb-seg" role="group" aria-label="Outcome">' + ['cfp12', 'ccg'].map(function (k) {
      var m = METRICS[k]; return '<button type="button" class="mb" aria-pressed="' + (S.outcome === k) + '" data-outcome="' + k + '"' + (k === 'ccg' ? ' aria-label="' + m.aria + '"' : '') + '><span class="lo">' + m.full + '</span><span class="sh">' + m.short + '</span></button>';
    }).join('') + '</div>';   /* the outcome switch is not a Run: it redraws from memory, no request */
  }
  /* MSM QA 11:26: the list is capped at MAXROWS, so 'Show all N' overstated when 12-16 qualify; the button reveals the rest of the shown list */
  function moreLabel(n) { return 'Show ' + n + ' more game' + (n === 1 ? '' : 's'); }
  function head(team, byeLine, conf) {   /* MSM QA 11:26: name the conference like the no-JS view ('Big 12\u00A0championship') once the data is in */
    var ph = noCcg ? 'playoff chances' : 'playoff and ' + (conf ? conf + '\u00A0championship' : 'conference championship') + ' chances';
    return '<div class="rb-hd"><h2 id="rbh">Rootables</h2>' + shareHtml() + '</div><p class="rb-sub">' + (byeLine ? esc(team) + ' has no game in the next 7 days. These games still move ' + esc(team) + '\u2019s ' + ph + '.' : 'Who to cheer for this week, for ' + esc(team) + '\u2019s ' + ph + '.') + '</p>';
  }
  var ICON = '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" width="18" height="18"><path d="M12 15V3M7 8l5-5 5 5M5 13v6h14v-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  function shareHtml() { var t = esc(teamLabel()); return '<a class="rb-share" href="/team/' + slug + '/#rootables" data-share data-card="/og/rootables/' + slug + '-1080x1350.png" aria-label="Share ' + t + ' Rootables">' + ICON + '<span class="rb-sl">Share</span></a><span class="rb-cp vh" aria-live="polite"></span>'; }
  /* Share (Creative SHARE-SPEC 6a68db1c): navigator.share when available (AbortError: nothing); else copy the link, label 'Link copied' for 2s (aria-live);
     clipboard failure: a read-only input with the URL, selected. No request, no AI, not gated by Run/terms. No-JS: the same plain link to #rootables (build.py rb_share). */
  /* Creative 11:21 E: one wording, set per team by build.py share_text() in og:description; fallback without a conference race. */
  function shareText(team) { var m = document.querySelector('meta[property="og:description"]'), c = m && m.getAttribute('content') || ''; return /^Games that help /.test(c) ? c : 'Games that help ' + team + '\'s playoff chances'; }
  root.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[data-share]') : null; if (!a) return;
    var team = teamLabel(), url = location.origin + '/team/' + slug + '/#rootables', lab = a.querySelector('.rb-sl'), live = root.querySelector('.rb-cp');
    if (navigator.share) { e.preventDefault(); navigator.share({ title: team + ' Rootables', text: shareText(team), url: url }).catch(function () {}); return; }
    e.preventDefault();
    var done = function () { if (lab) lab.textContent = 'Link copied'; if (live) live.textContent = 'Link copied'; clearTimeout(a._t); a._t = setTimeout(function () { if (lab) lab.textContent = 'Share'; if (live) live.textContent = ''; }, 2000); };
    var fail = function () { var f = root.querySelector('.rb-url'); if (!f) { f = document.createElement('input'); f.type = 'text'; f.readOnly = true; f.className = 'rb-url'; f.setAttribute('aria-label', 'Link to ' + team + ' Rootables'); a.parentNode.insertBefore(f, a.nextSibling); } f.value = url; f.focus(); f.select(); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, fail); else fail();
  });
  function set(html, busy) { root.setAttribute('data-rb', 'on'); if (busy) root.setAttribute('aria-busy', 'true'); else root.removeAttribute('aria-busy'); root.innerHTML = html; }
  function teamLabel() { return root.getAttribute('data-name') || 'This team'; }
  function stateLoading() { set(head(teamLabel(), false) + seg() + '<p class="rb-load" role="status">Loading Rootables\u2026</p><div class="rb-sk" aria-hidden="true"><i class="l"></i><i></i><i class="s"></i><i class="l"></i><i></i></div>', true); }
  function stateError() { set(head(teamLabel(), false) + seg() + '<div class="rb-err" role="alert"><i aria-hidden="true">!</i><div><b>Couldn\u2019t load the data</b><span>Check your connection, then try again.</span></div></div><button type="button" class="rb-run" data-try>Run Rootables again</button>' + SHORT); }
  function howHtml(team, n) {
    var t = esc(team), ns = commas(n);
    return '<button type="button" class="rb-how" aria-expanded="' + S.how + '" aria-controls="rbhw" data-how><span>How this works</span><i class="chv" aria-hidden="true"></i></button><div class="rb-hw" id="rbhw"' + (S.how ? '' : ' hidden') + '>' +
      '<p>Each number is ' + t + '\u2019s chance if that side wins the game. KickTip runs ' + ns + ' simulated seasons with that one game decided each way, using the same simulator as What If Lab by KickTip.</p>' +
      '<p>Every other game is simulated as usual. The points are the difference between the two results, so the bigger the difference, the more that game matters to ' + t + '.</p>' +
      '<p>Each game is tested on its own. Do not add the points together: results of different games overlap.</p>' +
      '<p>Games that move the chance by less than 1\u00A0pt are not shown. Small differences can come from simulation noise.</p>' +
      '<p>These numbers use ' + ns + ' seasons, so they can differ by a few tenths from the 10,000-season chances shown above.</p>' +
      '<p>Rootables uses the model selected above. Change the model and the list updates.</p>' +
      '<p><b>Information and entertainment only, not advice or a guarantee.</b></p></div>';
  }
  function whenCard(r) { /* polish: 'Sat Oct 31, 1:45 PM MT' with no break inside the date or the time */
    var NB = '\u00A0';
    if (r.tba) { var d = tzParts(r.kick, 'UTC', { weekday: 'short', month: 'short', day: 'numeric' }); return [d.weekday, d.month, d.day].join(NB) + ', time' + NB + 'TBD'; }
    var p = tzParts(r.kick, 'America/Denver', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return [p.weekday, p.month, p.day].join(NB) + ', ' + p.hour + ':' + p.minute + NB + p.dayPeriod + NB + 'MT';
  }
  function slugOf(ctx, i) { var t = ctx.by[ctx.index.team_names[i]]; return t && t.g ? String(t.g).replace(/[^a-z0-9-]/g, '') : ''; }
  function confOf(ctx, i) { var t = ctx.by[ctx.index.team_names[i]], c = t && ctx.confs && ctx.confs[t.c]; return c || ''; }
  function rowHtml(ctx, r, team, metric, k, conf) {
    if (r.race) { var sd = nm(ctx, r.root), ot = nm(ctx, r.other), rn = fill(STR.race[r.race], { Conf: conf });
      var sr2 = 'Root for ' + sd + '. ' + team + '\u2019s chance for ' + rn + ' is ' + pts(r.gap) + ' points higher if ' + sd + ' wins (' + pc(r.pRoot) + ' against ' + pc(r.pOther) + ').' + (r.sec ? ' ' + alsoText(r.sec, conf).replace(MINUS, 'minus ') + '.' : '') + ' Kickoff ' + whenLong(r) + '.';
      return rvCard({ slug: slugOf(ctx, r.root), when: whenCardAt(r, tzParts), root: { name: sd, logo: logo(ctx, r.root) }, other: { name: ot, logo: logo(ctx, r.other) }, where: r.neutral || r.root === r.h ? 'vs' : 'at', gain: pts(r.gap), label: fill(STR.gain, { Team: team }), tag: tagText(r.race, conf), race: r.race, also: alsoText(r.sec, conf), sr: sr2, extra: k >= SHOWN ? ' data-rbx hidden' : '' }); }   /* Rootables v2: the shared rvCard template; gain in percentage points ('+3.0 pts') */
    var ph = METRICS[metric].phrase, side = nm(ctx, r.root), other = nm(ctx, r.other);
    var sr = 'Root for ' + side + '. If ' + side + ' wins, ' + team + '\u2019s ' + ph + ' is ' + pc(r.pRoot) + '. If ' + other + ' wins, it is ' + pc(r.pOther) + '. That is ' + pts(r.gap) + ' points higher if ' + side + ' wins. Kickoff ' + whenLong(r) + '.';
    return rvCard({ slug: slugOf(ctx, r.root), when: whenCardAt(r, tzParts), root: { name: side, logo: logo(ctx, r.root) }, other: { name: other, logo: logo(ctx, r.other) }, where: r.neutral || r.root === r.h ? 'vs' : 'at', gain: pts(r.gap), label: team + ' ' + (metric === 'ccg' ? 'championship game' : 'playoff') + ' gain', sr: sr, extra: k >= SHOWN ? ' data-rbx hidden' : '' });
  }
  function stateReady(ctx, model) {
    var tn = ctx.index.team_names.indexOf(slugName(ctx));
    if (tn < 0) return stateError();
    var team = nm(ctx, tn), conf = confOf(ctx, tn), res = compute(tn, 'blend', ctx, Date.now());
    if (!res.nWindow) { set(head(team, false, conf) + '<p class="rb-msg" role="status">No games in the next 7 days. Check back after the next daily update.</p>'); return; }
    var after = '<div class="rb-after">';
    if (res.nBig > MAXROWS) after += '<p class="rb-hid">Showing the ' + res.rows.length + ' largest of ' + res.nBig + ' games that move these chances by 1\u00A0pt or more.</p>';
    if (res.nBig && res.nHidden) after += '<p class="rb-hid">' + (res.nHidden === 1 ? '1 game this week moves these chances by less than 1\u00A0pt and is not shown.' : res.nHidden + ' games this week move these chances by less than 1\u00A0pt and are not shown.') + '</p>';
    after += '<p class="rb-simn"><span class="bl"><b>' + commas(res.seasons) + ' simulated seasons</b>, ' + esc(MODEL_NAME[model]) + '</span><span class="bl">Simulation analysis, not advice. Data as of ' + esc(stampText(res.asOf)) + '.</span></p>' + howHtml(team, res.seasons) + '</div>';
    var list = res.rows.length ? '<ol class="rb-list" aria-label="Games ranked by how much they move ' + esc(team) + '\u2019s chance">' + res.rows.map(function (r, k) { return rowHtml(ctx, r, team, 'blend', k, conf); }).join('') + '</ol>' + (res.rows.length > SHOWN ? '<button type="button" class="rb-all" data-all data-n="' + (res.rows.length - SHOWN) + '" aria-expanded="false">' + moreLabel(res.rows.length - SHOWN) + '</button>' : '')
      : '<p class="rb-msg none" role="status">' + esc(fill(STR.empty, { Team: team })) + '</p>';
    set(head(team, !res.hasOwn, conf) + seg() + list + after);
  }
  function run() {
    var my = ++S.tok, model = S.model = modelId();
    var p = load(model); stateLoading();
    p.then(function (ctx) { if (my === S.tok) stateReady(ctx, model); }, function () { if (my === S.tok) stateError(); });
  }
  function show() { /* outcome switch or How toggle: redraw from memory, no request */
    var my = ++S.tok, model = S.model, p = cache[model]; if (!p) return run();
    p.then(function (ctx) { if (my === S.tok) stateReady(ctx, model); });
  }
  function refocus(sel) { var e = root.querySelector(sel); if (e) e.focus(); }
  root.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button') : null; if (!b || !root.contains(b)) return;
    if (b.hasAttribute('data-outcome')) { var k = b.getAttribute('data-outcome'); if (k === S.outcome) return; S.outcome = k; stateReadySync(function () { refocus('[data-outcome="' + k + '"]'); }); }
    else if (b.hasAttribute('data-how')) { S.how = !S.how; var w = root.querySelector('#rbhw'); b.setAttribute('aria-expanded', String(S.how)); if (w) w.hidden = !S.how; }
    else if (b.hasAttribute('data-run')) { start(); }
    else if (b.hasAttribute('data-try')) { run(); }
    else if (b.hasAttribute('data-all')) { var op = b.getAttribute('aria-expanded') !== 'true'; [].forEach.call(root.querySelectorAll('[data-rbx]'), function (x) { x.hidden = !op; }); b.setAttribute('aria-expanded', String(op)); b.textContent = op ? 'Show fewer games' : moreLabel(+b.getAttribute('data-n')); }
  });
  function stateReadySync(after) { var model = S.model, p = cache[model]; if (!p) { run(); return; } var my = ++S.tok; p.then(function (ctx) { if (my === S.tok) { stateReady(ctx, model); if (after) after(); } }); }
  function start() {
    if (started) return; started = true; run();
    var watch = function (card) { new MutationObserver(function () { if (started && modelId() !== S.model) run(); }).observe(card, { attributes: true, attributeFilter: ['data-model'] }); };
    var card = main.querySelector('[data-mdl]');
    if (card) watch(card); else { var mo = new MutationObserver(function () { var c = main.querySelector('[data-mdl]'); if (c) { mo.disconnect(); watch(c); if (modelId() !== S.model) run(); } }); mo.observe(main, { childList: true, subtree: true }); }
  }
})();
