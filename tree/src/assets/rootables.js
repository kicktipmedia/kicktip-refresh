/* KickTip Rootables. For the team on the page: which games in the next 7 days move its chance the most, and which side to cheer for.
   Information only. Runs in the browser from files the site already publishes (whatif/index.json, whatif/w<week>.json, sim-bundle.json for kickoff times) for the model on screen.
   Run-gate build (Oct 24, 2026): the team page carries a compact card (title, one line, Run Rootables and the FULL terms line, all static HTML). Nothing is fetched and nothing is drawn until the person taps Run Rootables; no auto-render, no memory. Rootables never writes storage (it only reads the model pick).
   The pure function KTRootables.compute() has no DOM; tests/rootables_unit.js runs it under node against the published shards. */
(function () {
  'use strict';
  var MS7 = 7 * 864e5, THRESH = 10, MAXROWS = 5, MINUS = '\u2212';
  var METRICS = { cfp12: { col: 'cfp12', short: 'Make the 12', full: 'Make the 12', phrase: 'make-the-12 chance' },
                  ccg: { col: 'ccg', short: 'Reach CCG', full: 'Reach CCG', aria: 'Reach the conference championship game', phrase: 'chance to reach the conference championship game' } };
  var SHORT = '__RUN_SHORT_HTML__';   /* the SHORT under-Run line under Run Rootables again (built from src/terms_copy.py); the FULL line is static HTML in the card */
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
  function isTba(iso) { var t = iso.slice(11); return t === '04:00Z' || t === '05:00Z'; }   /* ESPN 'time TBA' placeholders (same rule the pages use) */
  function parseKick(iso) { var t = Date.parse(iso.length === 17 ? iso.slice(0, 16) + ':00Z' : iso); return isNaN(t) ? null : t; }
  function buildGames(index, bundle) { /* index.games joined with the kickoff times of sim-bundle.json */
    var by = {}; index.games.forEach(function (g) { by[g.id] = g; }); var out = [];
    (bundle.games || []).forEach(function (b) {
      var g = by[b.id]; if (!g || !b.date) return; var k = parseKick(b.date); if (k === null) return;
      out.push({ id: g.id, week: g.week, h: g.h, a: g.a, neutral: !!g.neutral, kick: k, tba: isTba(b.date), ip: !!b.ip });
    });
    return out;
  }
  /* compute(team, metric, ctx, now): ctx = { index, games, shard(week, id) -> {h:[[team,ccg,title,cfp12,bye]..],a:[..]} | null, asOfMs }.
     Chance for a team under each result of a game = its row in the shard, or its baseline when it is not listed (it moved less than 0.3 point). Integers are per-mille; sort and threshold on the integers. */
  function compute(team, metric, ctx, now) {
    var index = ctx.index, col = index.metrics.indexOf(metric) + 1, rows = [], hasOwn = false;
    if (col < 1) throw new Error('metric');
    var end = ctx.asOfMs + MS7;
    ctx.games.forEach(function (g) {
      if (g.ip || g.kick > end || now > (g.tba ? g.kick + 864e5 : g.kick)) return;   /* in progress, outside the next 7 days, or already started (a TBA day counts until it is over) */
      var s = ctx.shard(g.week, g.id); if (!s) return;
      function chance(side) { var l = s[side] || []; for (var i = 0; i < l.length; i++) if (l[i][0] === team) return l[i][col]; return index.baseline[team][col - 1]; }
      var pH = chance('h'), pA = chance('a'), own = g.h === team || g.a === team; if (own) hasOwn = true;
      rows.push({ id: g.id, h: g.h, a: g.a, neutral: g.neutral, kick: g.kick, tba: g.tba, pH: pH, pA: pA, gap: Math.abs(pH - pA), root: pH >= pA ? g.h : g.a, other: pH >= pA ? g.a : g.h, pRoot: Math.max(pH, pA), pOther: Math.min(pH, pA), own: own });
    });
    var big = rows.filter(function (r) { return r.gap >= THRESH; });
    big.sort(function (x, y) { return y.gap - x.gap || x.kick - y.kick || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0); });
    return { rows: big.slice(0, MAXROWS), nBig: big.length, nWindow: rows.length, nHidden: rows.length - big.length, hasOwn: hasOwn, seasons: index.seasons, asOf: index.as_of };
  }
  function pts(gap) { return (gap / 10).toFixed(1); }
  function pc(p) { return (p / 10).toFixed(1) + '%'; }
  function commas(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function whenShort(r) { /* 'Sat Oct 24 · 8:15 PM MT'; a TBA day uses the placeholder's calendar date and says time TBA, like the Remaining games table */
    if (r.tba) { var d = tzParts(r.kick, 'UTC', { weekday: 'short', month: 'short', day: 'numeric' }); return d.weekday + ' ' + d.month + ' ' + d.day + ' \u00B7 time TBA'; }
    var p = tzParts(r.kick, 'America/Denver', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return p.weekday + ' ' + p.month + ' ' + p.day + ' \u00B7 ' + p.hour + ':' + p.minute + ' ' + p.dayPeriod + ' MT';
  }
  function whenLong(r) {
    if (r.tba) { var d = tzParts(r.kick, 'UTC', { weekday: 'long', month: 'long', day: 'numeric' }); return d.weekday + ' ' + d.month + ' ' + d.day + ', time to be announced'; }
    var p = tzParts(r.kick, 'America/Denver', { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return p.weekday + ' ' + p.month + ' ' + p.day + ' at ' + p.hour + ':' + p.minute + ' ' + p.dayPeriod + ' Mountain Time';
  }
  function stampText(asOf) { var m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d) MT$/.exec(asOf || ''); if (!m) return asOf; var h = +m[4]; return MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + m[1] + ', ' + ((h + 11) % 12 + 1) + ':' + m[5] + ' ' + (h < 12 ? 'AM' : 'PM') + ' MT'; }
  var api = { compute: compute, buildGames: buildGames, mtMs: mtMs, whenShort: whenShort, whenLong: whenLong, stampText: stampText, pts: pts, pc: pc, MODEL_NAME: MODEL_NAME };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  window.KTRootables = api;

  /* ---------- panel ---------- */
  var D = document, root = D.getElementById('rootables'), main = D.getElementById('main');
  if (!root || !main) return;
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
      (bundle.teams || []).forEach(function (t) { if (t.n) by[t.n] = t; });
      return Promise.all(weeks.map(function (w) { return fj(base + 'whatif/' + index.shards[w]).then(function (j) { shards[w] = j; }); })).then(function () {
        return { index: index, games: games, asOfMs: asOfMs, by: by, shard: function (w, id) { return (shards[w] && shards[w][id]) || null; } };
      });
    });
    p.catch(function () { if (cache[model] === p) delete cache[model]; });
    return (cache[model] = p);
  }
  function teamOf(ctx) { var i = ctx.index.team_names.indexOf(slugName(ctx)); return i; }
  function slugName(ctx) { var n = null; Object.keys(ctx.by).forEach(function (k) { if (ctx.by[k].g === slug) n = k; }); return n; }
  function nm(ctx, i) { var n = ctx.index.team_names[i], t = ctx.by[n]; return (t && (t.s || t.n)) || n; }
  function logo(ctx, i) { var t = ctx.by[ctx.index.team_names[i]]; return t && t.g && window.KTLogo ? window.KTLogo.team(t.g, 28, true) : ''; }

  function seg() {
    if (noCcg) return '';
    return '<div class="rb-seg" role="group" aria-label="Outcome">' + ['cfp12', 'ccg'].map(function (k) {
      var m = METRICS[k]; return '<button type="button" class="mb" aria-pressed="' + (S.outcome === k) + '" data-outcome="' + k + '"' + (k === 'ccg' ? ' aria-label="' + m.aria + '"' : '') + '><span class="lo">' + m.full + '</span><span class="sh">' + m.short + '</span></button>';
    }).join('') + '</div><p class="ccgdef">CCG = conference championship game</p>';   /* the outcome switch is not a Run: it redraws from memory, no request */
  }
  function head(team, byeLine) {
    var ph = METRICS[S.outcome].phrase;
    return '<div class="rb-hd"><h2 id="rbh">Rootables</h2></div><p class="rb-sub">' + (byeLine ? esc(team) + ' has no game in the next 7 days. These games still move ' + esc(team) + '\u2019s ' + ph + '.' : 'Who to cheer for this week, for ' + esc(team) + '\u2019s ' + ph + '.') + '</p>';
  }
  function set(html, busy) { root.setAttribute('data-rb', 'on'); if (busy) root.setAttribute('aria-busy', 'true'); else root.removeAttribute('aria-busy'); root.innerHTML = html; }
  function teamLabel() { return root.getAttribute('data-name') || 'This team'; }
  function stateLoading() { set(head(teamLabel(), false) + seg() + '<p class="rb-load" role="status">Loading Rootables\u2026</p><div class="rb-sk" aria-hidden="true"><i class="l"></i><i></i><i class="s"></i><i class="l"></i><i></i></div>', true); }
  function stateError() { set(head(teamLabel(), false) + seg() + '<div class="rb-err" role="alert"><i aria-hidden="true">!</i><div><b>Couldn\u2019t load the data</b><span>Check your connection, then try again.</span></div></div><button type="button" class="rb-run" data-try>Run Rootables again</button>' + SHORT); }
  function howHtml(team, n) {
    var t = esc(team), ns = commas(n);
    return '<button type="button" class="rb-how" aria-expanded="' + S.how + '" aria-controls="rbhw" data-how><span>How this works</span><i class="chv" aria-hidden="true"></i></button><div class="rb-hw" id="rbhw"' + (S.how ? '' : ' hidden') + '>' +
      '<p>Each number is ' + t + '\u2019s chance if that side wins the game. KickTip runs ' + ns + ' simulated seasons with that one game decided each way, using the same simulator as Ask KickTip.</p>' +
      '<p>Every other game is simulated as usual. The points are the gap between the two results, so the bigger the gap, the more that game matters to ' + t + '.</p>' +
      '<p>Each game is tested on its own. Do not add the points together: results of different games overlap.</p>' +
      '<p>Games that move the chance by less than 1.0 point are not shown. Small differences can come from simulation noise.</p>' +
      '<p>These numbers use ' + ns + ' seasons, so they can differ by a few tenths from the 10,000-season chances shown above.</p>' +
      '<p>Rootables uses the model selected above. Change the model and the list updates.</p>' +
      '<p><b>Information and entertainment only, not advice or a guarantee.</b></p></div>';
  }
  function rowHtml(ctx, r, team, metric) {
    var ph = METRICS[metric].phrase;
    var side = nm(ctx, r.root), other = nm(ctx, r.other), t = esc(team), s = esc(side), o = esc(other);
    function tm(i) { return '<span class="t' + (i === r.root ? ' r' : '') + '">' + logo(ctx, i) + esc(nm(ctx, i)) + '</span>'; }
    var sr = 'Root for ' + side + '. If ' + side + ' wins, ' + team + '\u2019s ' + ph + ' is ' + pc(r.pRoot) + '. If ' + other + ' wins, it is ' + pc(r.pOther) + '. That is ' + pts(r.gap) + ' points higher if ' + side + ' wins. Kickoff ' + whenLong(r) + '.';
    return '<li class="rb-row"><div class="rb-when">' + whenShort(r) + (r.own ? '<span class="rb-own">' + t + '\u2019s game</span>' : '') + '</div>' +
      '<div class="rb-match">' + tm(r.a) + '<span class="vs">' + (r.neutral ? 'vs' : 'at') + '</span>' + tm(r.h) + '</div>' +
      '<p class="rb-root">Root for ' + s + '</p><p class="sr">' + esc(sr) + '</p>' +
      '<div class="rb-imp" aria-hidden="true"><span class="n"><s>\u25B2</s>+' + pts(r.gap) + ' points</span><span class="w">if ' + s + ' wins instead of ' + o + '</span></div>' +
      '<p class="rb-nums" aria-hidden="true">' + t + '\u2019s chance: <b>' + pc(r.pRoot) + '</b> if ' + s + ' wins, <b>' + pc(r.pOther) + '</b> if ' + o + ' wins.</p></li>';
  }
  function stateReady(ctx, model) {
    var tn = ctx.index.team_names.indexOf(slugName(ctx));
    if (tn < 0) return stateError();
    var team = nm(ctx, tn), res = compute(tn, S.outcome, ctx, Date.now());
    if (!res.nWindow) { set(head(team, false) + '<p class="rb-msg" role="status">No games in the next 7 days. Check back after the next daily update.</p>'); return; }
    var after = '<div class="rb-after">';
    if (res.nBig > MAXROWS) after += '<p class="rb-hid">Showing the ' + res.rows.length + ' largest of ' + res.nBig + ' games that move this by 1.0 point or more.</p>';
    if (res.nBig && res.nHidden) after += '<p class="rb-hid">' + (res.nHidden === 1 ? '1 game this week moves this by less than 1.0 point and is not shown.' : res.nHidden + ' games this week move this by less than 1.0 point and are not shown.') + '</p>';
    after += '<p class="rb-simn"><span class="bl"><b>' + commas(res.seasons) + ' simulated seasons</b>, ' + esc(MODEL_NAME[model]) + '</span><span class="bl">Simulation analysis, not advice. Data as of ' + esc(stampText(res.asOf)) + '.</span></p>' + howHtml(team, res.seasons) + '</div>';
    var list = res.rows.length ? '<ol class="rb-list" aria-label="Games ranked by how much they move ' + esc(team) + '\u2019s chance">' + res.rows.map(function (r) { return rowHtml(ctx, r, team, S.outcome); }).join('') + '</ol>'
      : '<p class="rb-msg none" role="status">No game this week moves this by 1.0 point or more.</p>';
    set(head(team, !res.hasOwn) + seg() + list + after);
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
  });
  function stateReadySync(after) { var model = S.model, p = cache[model]; if (!p) { run(); return; } var my = ++S.tok; p.then(function (ctx) { if (my === S.tok) { stateReady(ctx, model); if (after) after(); } }); }
  function start() {
    if (started) return; started = true; run();
    var watch = function (card) { new MutationObserver(function () { if (started && modelId() !== S.model) run(); }).observe(card, { attributes: true, attributeFilter: ['data-model'] }); };
    var card = main.querySelector('[data-mdl]');
    if (card) watch(card); else { var mo = new MutationObserver(function () { var c = main.querySelector('[data-mdl]'); if (c) { mo.disconnect(); watch(c); if (modelId() !== S.model) run(); } }); mo.observe(main, { childList: true, subtree: true }); }
  }
})();
