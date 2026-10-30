/* Ask KickTip: what-if panel. Everything runs in the visitor's browser: the parser, scenario resolver, season simulation (a Web Worker) and the answer text are scripts served from this site.
   Typed questions are never sent anywhere. Run-gate build (Oct 24, 2026): no disclaimer gate, no dialog, no stored acceptance. Opening the panel loads nothing; the simulator, the what-if shards and the engine Worker load only when the person taps Run. The terms line under the Run button (src/terms_copy.py) is the acceptance: tapping Run accepts the terms.
   No inline script, no eval, same-origin requests only. */
(function () {
  'use strict';
  var D = document, main = D.getElementById('main'), pill = D.getElementById('kpill');
  if (!main || !pill) return;
  var MKEY = 'kicktip_model', CHUNKS = 10, MINCH = 4, PER = 1000, BUDGET = 7000, SEED0 = 20261;
  function get(s, k) { try { return window[s].getItem(k); } catch (e) { return null; } }
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  /* The model is read, never written, here: ?model= in the URL first, then the pick the page stored (kicktip_model), else the KickTip blend. Unknown or retired values are ignored. */
  var RUNTERMS = '__RUN_FULL_HTML__';   /* the FULL under-Run line, always on screen directly under the Run button (built from src/terms_copy.py) */
  var MODELS = { blend: 1, elo: 1, eff: 1 };
  function pickModel() {
    var q = ''; try { q = (new URLSearchParams(window.location.search).get('model') || '').toLowerCase(); } catch (e) { q = ''; }
    if (MODELS[q] === 1) return q;
    var v = get('localStorage', MKEY); return MODELS[v] === 1 ? v : 'blend';
  }

  var panel, scrim, bd, cmp, form, input, send, cnt, closeBtn, view = null;
  var S = { model: 'blend', M: {}, bundle: null, wi: null, scripts: null, worker: null, wid: 0, lastQ: '', choices: {}, parsed: null, res: null, busy: false, seedN: 0, adapt: null, pending: null };
  var shell = [D.querySelector('header.hd'), main, D.querySelector('footer.ft'), D.querySelector('.src'), pill];
  function setInert(on) { shell.forEach(function (e) { if (e) { if (on) e.setAttribute('inert', ''); else e.removeAttribute('inert'); } }); D.documentElement.style.overflow = on ? 'hidden' : ''; }

  /* ---------- panel shell ---------- */
  function build() {
    if (panel) return;
    scrim = D.createElement('div'); scrim.className = 'scrim'; scrim.hidden = true;
    panel = D.createElement('section'); panel.id = 'kp'; panel.className = 'pnl'; panel.hidden = true;
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true'); panel.setAttribute('aria-labelledby', 'kpt');
    panel.innerHTML = '<div class="hdp"><div><span class="grab" aria-hidden="true"></span><h2 id="kpt">Ask KickTip</h2><span class="lab">Simulation analysis, not betting advice</span></div><button type="button" class="cx" aria-label="Close Ask KickTip">&times;</button></div>' +
      '<div class="bd" id="kbd" tabindex="-1" aria-live="polite"></div>' +
      '<div class="cmp"><form id="kform" autocomplete="off"><div class="fld"><label for="kask">Ask a what-if question</label><input id="kask" type="text" maxlength="200" placeholder="What if BYU loses?" aria-describedby="kcnt"><span id="kcnt" class="cnt" aria-live="off">0/200</span></div><button class="snd" type="submit" aria-label="Run" disabled>Run</button></form>' + RUNTERMS + '</div>';
    D.body.appendChild(scrim); D.body.appendChild(panel);
    bd = panel.querySelector('#kbd'); cmp = panel.querySelector('.cmp'); form = panel.querySelector('#kform'); input = panel.querySelector('#kask'); send = panel.querySelector('.snd'); cnt = panel.querySelector('#kcnt'); closeBtn = panel.querySelector('.cx');
    pill.setAttribute('aria-controls', 'kp');
    closeBtn.addEventListener('click', closePanel);
    scrim.addEventListener('click', closePanel);
    input.addEventListener('input', function () { cnt.textContent = input.value.length + '/200'; send.disabled = !S.run && !input.value.trim(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); if (S.run) return; var t = input.value; if (!t.trim()) return; input.value = ''; cnt.textContent = '0/200'; send.disabled = true; ask(t, {}); });
    bd.addEventListener('click', onBodyClick);
    panel.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var f = [].filter.call(panel.querySelectorAll('button,a[href],input'), function (x) { return !x.disabled && !x.hidden && x.offsetParent !== null; });
      if (!f.length) return;
      var a = f[0], z = f[f.length - 1];
      if (e.shiftKey && D.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && D.activeElement === z) { e.preventDefault(); a.focus(); }
    });
  }
  D.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || !panel || panel.hidden) return;
    closePanel();
  });
  /* Phones: when the on-screen keyboard is up, lift the panel above it (and cap its height to what is visible) so the question box, Send and the terms line under them are never covered. CSSOM writes only (no inline style attribute in the HTML). */
  function fitKeyboard() {
    var vv = window.visualViewport; if (!vv || !panel) return;
    var kb = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop)), on = !panel.hidden && isNarrow() && kb > 80;
    panel.style.bottom = on ? kb + 'px' : ''; panel.style.height = on ? Math.min(Math.round(vv.height) - 8, Math.round(window.innerHeight * 0.88)) + 'px' : '';
  }
  if (window.visualViewport) { window.visualViewport.addEventListener('resize', fitKeyboard); window.visualViewport.addEventListener('scroll', fitKeyboard); }
  function openPanel() {
    build(); panel.hidden = false; scrim.hidden = false; setInert(true); pill.setAttribute('aria-expanded', 'true');
    if (view === null) viewStart(); else settle();
  }
  function closePanel() { panel.hidden = true; fitKeyboard(); scrim.hidden = true; setInert(false); pill.setAttribute('aria-expanded', 'false'); pill.focus(); }
  pill.addEventListener('click', openPanel);
  function settle() {   /* focus: the question box, else the close button */
    var t = ((!input.disabled && !cmp.hidden && !isNarrow()) ? input : null) || (panel.contains(D.activeElement) && D.activeElement !== D.body ? null : closeBtn);
    if (t) t.focus();
  }
  /* KickTip shield spinner (Creative's spec): a static track plus a cyan stroke that traces the shield outline, holds closed, un-traces, loops (CSS in chat.css; attributes and classes only, no inline style). Reduced motion: steady closed shield. */
  var SHIELD = '<svg class="kshd" viewBox="0 0 278 355" aria-hidden="true" focusable="false"><path class="kst" pathLength="1" d="M139 14L257 58V130C257 154 259 180 256 200C252 220 246 232 236 248C226 264 210 284 198 296C186 308 174 315 164 322C154 329 146 335 139 339C132 335 124 329 114 322C104 315 92 308 80 296C68 284 52 264 42 248C32 232 26 220 22 200C19 180 21 154 21 130V58Z"/><path class="ksm" pathLength="1" d="M139 14L257 58V130C257 154 259 180 256 200C252 220 246 232 236 248C226 264 210 284 198 296C186 308 174 315 164 322C154 329 146 335 139 339C132 335 124 329 114 322C104 315 92 308 80 296C68 284 52 264 42 248C32 232 26 220 22 200C19 180 21 154 21 130V58Z"/></svg>';
  var SPINCARD = '<div class="spin">' + SHIELD + '<p class="spcap">Running your scenario</p></div>';
  function setRun(on) {   /* the Run button's running state: shield + "Running\u2026", aria-busy, aria-disabled (not disabled, so focus stays), graphite kept, until the view changes */
    S.run = !!on; send.classList.toggle('run', S.run);
    if (S.run) { send.setAttribute('aria-busy', 'true'); send.setAttribute('aria-disabled', 'true'); send.setAttribute('aria-label', 'Running'); send.innerHTML = SHIELD + '<span>Running\u2026</span>'; send.disabled = false; }
    else { send.removeAttribute('aria-busy'); send.removeAttribute('aria-disabled'); send.setAttribute('aria-label', 'Run'); send.textContent = 'Run'; }
  }
  function isNarrow() { return window.matchMedia && window.matchMedia('(max-width:700px)').matches; }
  function show(v, html, opt) {
    opt = opt || {}; view = v; bd.innerHTML = html; bd.scrollTop = 0;
    if (!!S.run !== (v === 'running' || v === 'loading')) setRun(v === 'running' || v === 'loading');
    send.disabled = !S.run && !input.value.trim();
    input.placeholder = 'What if BYU loses?';
    if (opt.keep !== undefined) { input.value = opt.keep; cnt.textContent = opt.keep.length + '/200'; send.disabled = !S.run && !opt.keep.trim(); }
    if (opt.focus !== false) settle();
  }
  var LINKS = '<p class="lk"><a href="/disclaimer/">Full disclaimer</a> &middot; <a href="/method/">Method</a></p>';
  var REQ = '<span class="req">Simulation analysis, not betting advice</span>';
  function bubble(t) { return '<div class="ub">' + esc(t) + '</div>'; }
  var ONBROWSER = 'Calculated in your browser from public model data. Your question is not sent to any server.';

  /* ---------- views ---------- */
  function viewStart() { viewEmpty(); }   /* nothing is fetched when the panel opens: the example cards are plain text from the page (data-exa / data-exb) */
  function nm(t) { return S.bundle.teams[t].n; }
  function qn(t) { var T = S.bundle.teams[t], m = S.bundle.aliases && S.bundle.aliases.map && S.bundle.aliases.map[T.n.toLowerCase()]; return m && m.length === 1 ? T.n : T.f; }   /* name to type in an example question: the short name unless it is ambiguous (Utah, Miami) */
  function qv(t, sing, plur) { var T = S.bundle.teams[t], m = S.bundle.aliases && S.bundle.aliases.map && S.bundle.aliases.map[T.n.toLowerCase()], full = !(m && m.length === 1); return qn(t) + ' ' + (full && KTAnswer.isPlural(T.f) ? plur : sing); }   /* name + verb that agrees with it: "Utah Utes lose", "Houston wins" */
  function examples() {
    var B = S.bundle, page = main.getAttribute('data-page'), tslug = main.getAttribute('data-team'), cslug = main.getAttribute('data-conf'), fcs = B.fcs;
    var gs = B.games.filter(function (g) {
      if (g.h === fcs || g.a === fcs) return false;
      if (page === 'team') return B.teams[g.h].g === tslug || B.teams[g.a].g === tslug;
      if (page === 'conference') return B.teams[g.h].cs === cslug || B.teams[g.a].cs === cslug;
      return true;
    }).sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : (a.id < b.id ? -1 : 1); });
    if (page !== 'team' && gs.length) {   /* playoff and conference pages: the strongest matchups in the next ten days, so the answer has something to show */
      var cut = new Date(new Date(gs[0].date).getTime() + 10 * 864e5).toISOString(), rt = B.model.rating;
      gs = gs.filter(function (g) { return g.date <= cut; }).sort(function (x, y) { return (rt[y.h] + rt[y.a]) - (rt[x.h] + rt[x.a]); });
    }
    var a = gs[0], b = null, i;
    if (!a) return [];
    for (i = 1; i < gs.length; i++) if (gs[i].h !== a.h && gs[i].h !== a.a && gs[i].a !== a.h && gs[i].a !== a.a) { b = gs[i]; break; }
    var subj = page === 'team' ? (B.teams[a.h].g === tslug ? a.h : a.a) : a.h, opp = subj === a.h ? a.a : a.h, out = [];
    out.push(['One game', 'What if ' + qv(subj, 'loses', 'lose') + ' to ' + qn(opp) + '?']);
    if (b) out.push(['Combo: two games', 'What if ' + qv(subj, 'loses', 'lose') + ' to ' + qn(opp) + ' and ' + qv(b.a, 'beats', 'beat') + ' ' + qn(b.h) + '?']);
    out.push(['Rest of season', 'What if ' + qv(subj, 'wins', 'win') + ' out?']);
    out.push(['What it takes', 'What does ' + qn(subj) + ' need to make the playoff?']);
    return out;
  }
  function staticExamples() {   /* question cards that need no data: team names come from the page (data-exa / data-exb, full names so they parse without ambiguity) */
    var a = main.getAttribute('data-exa') || 'BYU Cougars', b = main.getAttribute('data-exb') || a;
    return [['Next game', 'What if ' + a + ' loses its next game?'], ['Rest of season', 'What if ' + a + ' wins out?'], ['What it takes', 'What does ' + b + ' need to make the playoff?']];
  }
  function viewEmpty() {
    var ex = staticExamples();
    show('empty', '<h3>Ask a what-if</h3><p class="note">Tap a question to fill the box, or type your own, then tap Run. Each run re-simulates the season in your browser. It uses the model selected on this page (the KickTip blend unless you picked another).</p>' +
      ex.map(function (e) { return '<button type="button" class="q" data-q="' + esc(e[1]) + '"><small>' + esc(e[0]) + '</small>' + esc(e[1]) + '</button>'; }).join('') + LINKS);
  }
  function viewRefusal(t) {
    show('refusal', bubble(t) + '<div class="st2">' + REQ + '<h3 class="mt">KickTip gives simulation analysis only.</h3><p>We don\'t give betting advice or recommendations. You can ask how a result would change the race instead.</p>' + pickButtons(1) + LINKS + '</div>');
  }
  function pickButtons(n) { var ex = S.bundle ? examples().slice(0, n) : []; return ex.map(function (e) { return '<button type="button" class="opt" data-q="' + esc(e[1]) + '">' + esc(e[1]) + '</button>'; }).join(''); }
  function viewClarify(t, ci) {
    show('clarify', bubble(t) + '<div class="st2"><h3>Did you mean&hellip;?</h3><p class="note">More than one team matches. Pick one.</p>' +
      ci.options.map(function (o) { return '<button type="button" class="opt" data-pick="' + esc(o.alias) + '|' + o.team + '">' + esc(o.name) + '</button>'; }).join('') + '<button type="button" class="opt" data-else>Something else</button></div>');
    S.lastQ = t;
  }
  function viewNotUnderstood(t) {
    var gs = S.bundle.games.filter(function (g) { return g.h !== S.bundle.fcs && g.a !== S.bundle.fcs; }), ex = examples(), opts = [];
    ex.forEach(function (e) { opts.push(e[1]); });
    show('notunderstood', bubble(t) + '<div class="st2"><span class="ico" aria-hidden="true">?</span><h3>Sorry, I didn\'t catch that</h3><p class="note">Try a game result, like Team A beats Team B, Team A loses to Team B or Team A wins out.</p>' +
      opts.map(function (q) { return '<button type="button" class="opt" data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '</div>');
  }
  var INFO_TITLE = { margin: 'Wins and losses only', title_scenario: 'Not supported yet', too_many_items: 'Up to 8 game results', already_played: 'That game is already final' };
  function viewInfo(t, text, ci) {
    var plain = ci && ci.reason === 'margin' && ci.plain_text ? '<button type="button" class="opt" data-q="' + esc(ci.plain_text) + '">Run it without the margin: ' + esc(ci.plain_text) + '</button>' : '';
    var pk = pickButtons(plain ? 1 : 2);
    show('info', bubble(t) + '<div class="st2"><span class="ico" aria-hidden="true">?</span><h3>' + esc((ci && INFO_TITLE[ci.reason]) || 'That one needs a change') + '</h3><p>' + esc(text) + '</p>' + plain + pk + '</div>');
  }
  function viewError(t) {
    var off = typeof navigator !== 'undefined' && navigator.onLine === false;
    show('error', (t ? bubble(t) : '') + '<div class="st2"><span class="ico" aria-hidden="true">!</span><h3>' + (off ? 'You\'re offline' : 'Couldn\'t load the data') + '</h3><p>' + (off ? 'We couldn\'t load the data to run this. ' : 'Something went wrong loading the data. ') + (t ? 'Your question is still in the box below.' : 'Check your connection and try again.') + '</p><button type="button" class="opt" data-retry>Run again</button></div>', { keep: t || '' });
    S.lastQ = t || '';
  }
  function gdate(iso) {   /* MT calendar day; placeholder times (04:00Z / 05:00Z) mean "time to be announced", so use the UTC date */
    var tba = /T0[45]:00Z$/.test(iso); try { return new Intl.DateTimeFormat('en-US', { timeZone: tba ? 'UTC' : 'America/Denver', weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(iso)); } catch (e) { return iso.slice(0, 10); }
  }
  function chipHtml(parsed, res) {
    var items = parsed.items || [];
    return '<div class="chips" role="group" aria-label="Scenario games">' + items.map(function (it, i) { var tx = esc(itemText(it, res, i)); return '<span class="chip">' + tx + '<button type="button" data-rm="' + i + '" aria-label="Remove: ' + tx + '">&times;</button></span>'; }).join('') + '<button type="button" class="addg" data-add>+ Add another game</button></div>';
  }
  function itemText(it, res, i) {
    var e = res && res.echo && res.echo[i], live = res && res.games && res.games.some(function (g) { return g.item === i && g.ip; }), t;
    if (it.kind === 'next_win' || it.kind === 'next_loss') {
      if (e) return nm(it.team) + (it.kind === 'next_win' ? ' beats ' : ' loses to ') + (e.opponent === S.bundle.fcs ? (e.fcs || 'an FCS opponent') : nm(e.opponent)) + ' (next game: ' + gdate(e.date) + (e.ip ? ', in progress' : '') + ')';
      return nm(it.team) + (it.kind === 'next_win' ? ' wins' : ' loses') + ' next game';
    }
    if (it.kind === 'beats') t = nm(it.winner) + ' beats ' + nm(it.loser) + (live ? ' (in progress)' : '');
    else if (it.kind === 'wins_out') t = nm(it.team) + ' wins out' + (live ? ' (includes a game in progress)' : '');
    else if (it.kind === 'loses_out') t = nm(it.team) + ' loses out' + (live ? ' (includes a game in progress)' : '');
    else t = nm(it.team) + ' wins ' + it.n + ' of ' + (it.scope === 'remaining' ? 'the remaining games' : 'the ' + it.scope + ' ' + it.m) + (live ? ' (includes a game in progress)' : '');
    return t;
  }
  function viewRunning(t, parsed, res, done, total) {
    var p = total ? Math.round(done * 100 / total) : 0;
    show('running', bubble(t) + '<div class="ac">' + REQ + SPINCARD + (parsed && parsed.items && parsed.items.length ? '<div class="chips" role="group" aria-label="Scenario games">' + parsed.items.map(function (it, i) { return '<span class="chip chip-r">' + esc(itemText(it, res, i)) + '</span>'; }).join('') + '</div>' : '') +
      '<div class="prog" role="progressbar" aria-label="Simulation progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + p + '"><span></span></div><p class="meta" id="kprog">' + (done ? commas(done) + ' of ' + commas(total) + ' seasons' : 'Starting') + ' &middot; runs in your browser</p></div>', { focus: false });
    bd.querySelector('.prog span').style.width = p + '%';
  }
  function tick(done, total) {
    var bar = bd.querySelector('.prog'); if (!bar) return; var p = Math.round(done * 100 / total);
    bar.setAttribute('aria-valuenow', p); bar.firstChild.style.width = p + '%'; var m = bd.querySelector('#kprog'); if (m) m.textContent = commas(done) + ' of ' + commas(total) + ' seasons \u00b7 runs in your browser';
  }
  function commas(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  var MINUS = '\u2212';
  function chg(c) {
    var s = c.change_text.replace(/^-/, MINUS), up = c.change_text.charAt(0) === '+', dn = c.change_text.charAt(0) === '-';
    return '<td class="n ' + (c.meaningful ? 'dl' : 'dim') + '">' + (c.meaningful ? (up ? '\u25B2 ' : dn ? '\u25BC ' : '') : '') + esc(s) + '</td>';
  }
  function scenarioTables(ans, parsed, res) {
    var prim = {}; (parsed.items || []).forEach(function (it) { [it.winner, it.loser, it.team].forEach(function (x) { if (x !== undefined && x !== null) prim[x] = 1; }); });
    var rows = ans.table.rows, p = rows.filter(function (r) { return prim[r.team]; }).slice(0, 4), o = rows.filter(function (r) { return !prim[r.team]; }), all = p.slice();
    o.forEach(function (r) { if (all.length < 6) all.push(r); });
    var M = ans.table.metrics, labels = ans.table.columns.slice(1);
    return all.map(function (r) {
      var body = M.map(function (k, i) { var c = r.cells[k]; if (!c) return ''; if (c.before < 0.001 && c.after < 0.001) return ''; return '<tr><td>' + esc(labels[i]) + '</td><td class="n">' + esc(c.before_text) + '</td><td class="n">' + esc(c.after_text) + '</td>' + chg(c) + '</tr>'; }).join('');
      if (!body) return '<p class="mn">' + esc(r.name) + ': under 0.1% for each of these outcomes, before and after.</p>';
      return '<table class="ba"><caption>' + esc(r.name) + (prim[r.team] ? '' : ' (also moved)') + '</caption><thead><tr><th>Outcome</th><th class="n">Before</th><th class="n">After</th><th class="n">Change</th></tr></thead><tbody>' + body + '</tbody></table>';
    }).join('');
  }
  var REGEN = '<button type="button" class="opt rgn" data-regen>Run again (new random sample)</button>';
  function foot(ans, N, perGame) {   /* N is the number of seasons actually simulated for this answer (fewer than 10,000 on a slow device); perGame is the fixed size of the stored single-game runs behind a need table */
    var f = ans.footers, asOf = KTAnswer.asOfLabel(S.bundle.as_of);
    return '<p class="meta">' + commas(N) + ' simulated seasons' + (perGame ? ' for the chance right now, ' + commas(perGame) + ' for each game result in the table' : '') + ', as of ' + esc(asOf) + '</p><p class="mn mdl">' + esc(f.model) + '</p>' + (f.inprogress ? '<p class="mn">' + esc(f.inprogress) + '</p>' : '') +
      '<p class="mn">' + esc(f.noise) + '</p><p class="mn">' + esc(f.tiebreak) + '</p>';
  }
  function viewAnswer(t, parsed, res, ans, N) {
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + chipHtml(parsed, res) + scenarioTables(ans, parsed, res) + foot(ans, N) +
      '<p class="mn">Games not in the scenario play out as simulated.</p>' + REGEN + '<p class="mn">' + ONBROWSER + '</p>' + LINKS + '</div>');
  }
  function viewNeed(t, ans, N) {
    var rows = ans.games.map(function (g) { return '<tr><td>Wk ' + g.week + ' ' + (g.site === 'away' ? 'at' : 'vs') + ' ' + esc(g.opponent) + (g.site === 'neutral' ? ' (neutral)' : '') + '</td><td class="n">' + esc(g.if_win_text) + '</td><td class="n">' + esc(g.if_lose_text) + '</td><td class="n dl">' + esc(g.swing_text.replace(/^-/, MINUS)) + '</td></tr>'; }).join('');
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + '<p><b>' + esc(ans.team_name) + '</b>: chance to ' + esc(ans.goal_label) + ' right now is <b>' + esc(ans.baseline_text) + '</b>.</p>' +
      (rows ? '<table class="ba"><caption>Chance to ' + esc(ans.goal_label) + ', by result of each remaining game</caption><thead><tr><th>Game</th><th class="n">If win</th><th class="n">If lose</th><th class="n">Swing</th></tr></thead><tbody>' + rows + '</tbody></table>' : '<p>No remaining games.</p>') +
      foot(ans, N, S.wi && S.wi.seasons) + '<p class="mn">' + esc(ans.notes[0]) + ' ' + esc(ans.notes[1]) + '</p>' + REGEN + '<p class="mn">' + ONBROWSER + '</p>' + LINKS + '</div>');
  }
  function viewBaseline(t, ans, N) {
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + '<table class="ba"><caption>' + esc(ans.team_name) + ', right now</caption><thead><tr><th>Outcome</th><th class="n">Chance</th></tr></thead><tbody>' +
      ans.cells.map(function (c) { return '<tr><td>' + esc(c.label) + '</td><td class="n">' + esc(c.text) + '</td></tr>'; }).join('') + '</tbody></table>' + foot(ans, N) + REGEN + '<p class="mn">' + ONBROWSER + '</p>' + LINKS + '</div>');
  }

  /* ---------- data and engine (requested when the panel opens) ---------- */
  function loadScript(src) {
    return new Promise(function (ok, bad) { var s = D.createElement('script'); s.src = src; s.async = false; s.onload = ok; s.onerror = bad; D.head.appendChild(s); });
  }
  function fetchJson(u) { return fetch(u, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function mUrl(id, f) { return id === 'blend' ? '/data/' + f : '/data/m/' + id + '/' + f; }
  /* One model at a time is current (S.bundle / S.wi); each model's bundle, what-if index and shards are fetched once and kept. The worker gets each bundle once. */
  function useModel(id) { var m = S.M[id]; S.model = id; S.bundle = m.bundle; S.wi = m.wi; }
  function ensureData() {
    var id = pickModel();
    if (!S.scripts) S.scripts = Promise.all([loadScript('/assets/ks/parse.js'), loadScript('/assets/ks/scenario.js'), loadScript('/assets/ks/answer.js')]).then(function () { var w = S.worker = new Worker('/assets/chat-worker.js'); w.addEventListener('error', function (e) { if (S.worker === w) { if (e.preventDefault) e.preventDefault(); workerFailed(); } }); w.addEventListener('messageerror', function () { if (S.worker === w) workerFailed(); }); }).catch(function (e) { S.scripts = null; throw e; });
    var m = S.M[id];
    if (!m) m = S.M[id] = { p: null, bundle: null, wi: null, shards: {} };
    if (!m.p) m.p = Promise.all([S.scripts, fetchJson(mUrl(id, 'sim-bundle.json')), fetchJson(mUrl(id, 'whatif/index.json'))]).then(function (r) {
      m.bundle = r[1]; m.wi = r[2]; m.bundle.teams.forEach(function (t) { t.f = t.n; if (t.s) t.n = t.s; });
      if (!S.worker) throw new Error('worker');
      S.worker.postMessage({ op: 'bundle', model: id, bundle: m.bundle });
    }).catch(function (e) { m.p = null; throw e; });
    return m.p.then(function () { useModel(id); });
  }
  /* The engine Worker failed to load or crashed (error / messageerror): drop it, forget it was ever ready (the next question builds a new one and re-sends the bundle) and fail the run in flight, so the panel shows the error state with Try again instead of waiting forever. */
  function workerFailed() {
    var w = S.worker, f = S.pending; S.worker = null; S.scripts = null; S.pending = null;
    Object.keys(S.M).forEach(function (k) { S.M[k].p = null; });
    try { if (w) w.terminate(); } catch (e) { /* already gone */ }
    if (f) f(new Error('worker'));
  }
  function runEngine(forced, constraints, baseOnly, onTick) {
    return new Promise(function (ok, bad) {
      var id = ++S.wid, w = S.worker, model = S.model;
      if (!w) { bad(new Error('worker')); return; }
      S.pending = bad;
      function on(e) {
        var m = e.data; if (m.id !== id) return;
        if (m.type === 'progress') onTick(m.done, m.total);
        else { w.removeEventListener('message', on); if (S.pending === bad) S.pending = null; if (m.type === 'done') ok(m); else bad(new Error('engine')); }
      }
      w.addEventListener('message', on);
      w.postMessage({ op: 'run', id: id, model: model, forced: forced, constraints: constraints, chunks: CHUNKS, minChunks: MINCH, per: PER, budget: BUDGET, seedBase: SEED0 + 100 * S.seedN, baseOnly: baseOnly });
    });
  }
  function getShards(weeks) {
    var m = S.M[S.model];
    return Promise.all(weeks.map(function (wk) {
      if (m.shards[wk]) return 0; var f = S.wi.shards[wk]; if (!f) { m.shards[wk] = {}; return 0; }
      return fetchJson(mUrl(S.model, 'whatif/' + f)).then(function (j) { m.shards[wk] = j; });
    }));
  }

  /* ---------- the question flow ---------- */
  function ask(text, opt) {
    text = String(text).trim().slice(0, 200); if (!text || S.busy) return;
    opt = opt || {};
    if (!opt.regen) S.seedN = 0;
    S.lastQ = text; S.choices = opt.choices || (opt.parsed ? S.choices : {});
    if (!S.bundle) show('loading', bubble(text) + '<div class="ac" aria-label="Loading answer">' + REQ + SPINCARD + '<p class="meta">Loading the latest schedule and results&hellip;</p><div class="sk w90"></div><div class="sk w70"></div><div class="sk w80"></div></div>', { focus: false });
    ensureData().then(function () { route(text, opt); }, function () { viewError(text); });
  }
  function route(text, opt) {
    var B = S.bundle, parsed = opt.parsed || KTParse.parse(text, B.aliases, { choices: S.choices }), res, ci;
    if (parsed.refusal) return viewRefusal(text);
    if (parsed.clarify) {
      ci = KTAnswer.clarifyAnswer(B, parsed, null);
      if (ci.reason === 'ambiguous_team' && ci.options.length) return viewClarify(text, ci);
      if (ci.reason === 'unparsed' || ci.reason === 'no_team' || ci.reason === 'empty') return viewNotUnderstood(text);
      return viewInfo(text, ci.text, ci);
    }
    S.parsed = parsed; S.res = null;
    if (parsed.need) return runNeed(text, parsed);
    if (parsed.intent === 'baseline' && parsed.baseline_team !== null) return runBaseline(text, parsed);
    res = KTScenario.resolve(parsed, B);
    if (!res.ok) { ci = KTAnswer.clarifyAnswer(B, parsed, res.clarify); return viewInfo(text, ci.text, ci); }
    S.res = res; S.busy = true;
    viewRunning(text, parsed, res, 0, CHUNKS * PER);
    runEngine(res.forced, res.constraints, false, tick).then(function (r) {
      var ans = KTAnswer.scenarioAnswer(B, res, r.before, r.after, r.N, B.as_of, { maxRows: 8 });
      S.busy = false; viewAnswer(text, parsed, res, ans, r.N);
    }, function () { S.busy = false; viewError(text); });
  }
  function runBaseline(text, parsed) {
    S.busy = true; viewRunning(text, null, null, 0, CHUNKS * PER);
    runEngine({}, [], true, tick).then(function (r) { S.busy = false; viewBaseline(text, KTAnswer.baselineAnswer(S.bundle, r.before, parsed.baseline_team, r.N, S.bundle.as_of), r.N); }, function () { S.busy = false; viewError(text); });
  }
  function runNeed(text, parsed) {
    var B = S.bundle, team = parsed.need.team, weeks = [], sh = S.M[S.model].shards;
    B.games.forEach(function (g) { if ((g.h === team || g.a === team) && weeks.indexOf(g.wk) < 0) weeks.push(g.wk); });
    S.busy = true; viewRunning(text, null, null, 0, CHUNKS * PER);
    Promise.all([getShards(weeks), runEngine({}, [], true, tick)]).then(function (x) {
      var r = x[1], ans = KTAnswer.needAnswer(B, S.wi, function (wk) { return sh[wk] || {}; }, team, parsed.need.goal, r.before, r.N, B.as_of, null);
      S.busy = false; viewNeed(text, ans, r.N);
    }, function () { S.busy = false; viewError(text); });
  }

  function onBodyClick(e) {
    var b = e.target.closest ? e.target.closest('button') : null; if (!b || !bd.contains(b)) return;
    if (b.hasAttribute('data-q')) {
      if (b.classList.contains('q')) { input.disabled = false; input.value = b.getAttribute('data-q'); cnt.textContent = input.value.length + '/200'; send.disabled = false; input.focus(); return; }   /* an example card only FILLS the box; the person taps Run */
      ask(b.getAttribute('data-q'), {}); return;
    }
    if (b.hasAttribute('data-pick')) { var p = b.getAttribute('data-pick').split('|'), c = {}; c[p[0]] = +p[1]; var ch = Object.assign({}, S.choices, c); ask(S.lastQ, { choices: ch }); return; }
    if (b.hasAttribute('data-else')) { input.disabled = false; input.focus(); return; }
    if (b.hasAttribute('data-retry')) { if (S.lastQ) ask(S.lastQ, {}); else viewStart(); return; }
    if (b.hasAttribute('data-regen') && S.lastQ) { S.seedN++; ask(S.lastQ, { regen: true, parsed: S.parsed || undefined }); return; }
    if (b.hasAttribute('data-add')) { input.disabled = false; input.value = S.lastQ.replace(/[?.!\s]+$/, '') + ' and '; cnt.textContent = input.value.length + '/200'; send.disabled = false; input.focus(); input.setSelectionRange(input.value.length, input.value.length); return; }
    if (b.hasAttribute('data-rm') && S.parsed) {
      var i = +b.getAttribute('data-rm'), np = JSON.parse(JSON.stringify(S.parsed)); np.items.splice(i, 1);
      if (!np.items.length) { viewEmpty(); return; }
      var t = 'What if ' + np.items.map(function (it, k) { return itemText(it, null, k); }).join(' and ') + '?'; S.lastQ = t; ask(t, { parsed: np });
    }
  }
})();
