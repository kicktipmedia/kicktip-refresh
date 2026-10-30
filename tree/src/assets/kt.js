/* KickTip prediction renderer. No frameworks, no cookies, no external requests. The page's data loads on arrival; there is no pop-up or acceptance screen.
   Terms are accepted by use (banner and under-Run text, copy in src/terms_copy.py). Storage: only the model pick (kicktip_model), written when the visitor picks. */
(function () {
  'use strict';
  var D = document, main = D.getElementById('main');
  /* ---------- model pick (v6a rev2). One small localStorage key (value = an alternate id; the default is stored as NO key). Written only when the visitor picks. ?model= in the URL (shared links) wins over the stored value. Storage may be blocked: every access is try/catch and falls back to the default silently. ---------- */
  var MKEY = '__MODEL_KEY__', ALT = '__ALT_MODELS__'.split(',');
  function okAlt(v) { return !!v && ALT.indexOf(v) >= 0; }
  function lsGet() { try { return window.localStorage.getItem(MKEY); } catch (e) { return null; } }
  function lsSet(v) { try { if (v) window.localStorage.setItem(MKEY, v); else window.localStorage.removeItem(MKEY); } catch (e) { /* blocked: default, silently */ } }
  function urlRaw() { try { return new URLSearchParams(window.location.search).get('model'); } catch (e) { return null; } }
  function urlPick() { var v = urlRaw(); return okAlt(v) ? v : null; }
  function setUrl(id) { /* keep the address bar consistent with the pick (so reload and shared links match); canonical in the HTML stays param-free */
    try { var u = new URL(window.location.href); if (id) u.searchParams.set('model', id); else u.searchParams.delete('model'); window.history.replaceState(null, '', u.pathname + u.search + u.hash); } catch (e) { /* ignore */ }
  }
  function tagLinks(id) { /* internal page links carry ?model=<alt> while an alternate is picked, so shared links reproduce it; none for the default */
    [].forEach.call(D.querySelectorAll('a[href]'), function (a) {
      var m = /^(\/(?!\/)[^?#.]*)(\?[^#]*)?(#.*)?$/.exec(a.getAttribute('href') || ''); if (!m || /^\/(data|assets)\//.test(m[1])) return;
      var q = (m[2] || '').replace(/^\?/, '').split('&').filter(function (x) { return x && x.indexOf('model=') !== 0; }); if (id) q.push('model=' + id);
      a.setAttribute('href', m[1] + (q.length ? '?' + q.join('&') : '') + (m[3] || ''));
    });
  }
  tagLinks(urlPick() || (okAlt(lsGet()) ? lsGet() : null));
  if (!main || !main.getAttribute('data-need')) return;
  var need = (main.getAttribute('data-need') || '').split(',').filter(Boolean);
  var needLines = need.indexOf('pred-lines') >= 0; need = need.filter(function (n) { return n !== 'pred-lines'; });   /* market lines are one model-independent file, fetched once, on arrival, with the other /data/pred-*.json files */
  var loaded = false;

  /* ---------- formatting ---------- */
  var MINUS = '\u2212';
  function pct(p) {
    if (p === null || p === undefined) return 'n/a';
    var v = Math.round(p * 100);
    if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%';
  }
  function bar(p) { return '<span class="bar" data-w="' + Math.round(Math.max(p > 0 ? 2 : 0, p * 48)) + '"></span>'; }
  function cellPct(p) { return p === null || p === undefined ? '<span class="lk">n/a</span>' : bar(p) + pct(p); }
  function line(s, h, a) { if (s === null || s === undefined) return null; if (s === 0) return 'Even'; var n = Math.abs(s).toFixed(1); return s < 0 ? h + ' ' + MINUS + n : a + ' ' + MINUS + n; }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function sized(root) {
    [].forEach.call(root.querySelectorAll('.bar[data-w]'), function (b) { b.style.width = b.getAttribute('data-w') + 'px'; b.removeAttribute('data-w'); });
    [].forEach.call(root.querySelectorAll('i[data-pw]'), function (b) { b.style.width = b.getAttribute('data-pw') + '%'; b.removeAttribute('data-pw'); });   /* CSSOM, not an inline style attribute (CSP) */
  }

  /* ---------- data (fetched on arrival) ---------- */
  function fetchSet(id) { /* id null = the default model (/data/pred-*.json); otherwise that model's files under /data/m/<id>/ */
    var base = id ? '/data/m/' + id + '/' : '/data/';
    return Promise.all(need.map(function (n) { return fetch(base + n + '.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(n); return r.json(); }); })).then(function (r) {
      var d = {}; need.forEach(function (n, i) { d[n.replace('pred-', '')] = r[i]; }); return d;
    });
  }
  var cache = {}, cur = null, card = null, defId = null;
  function startLoad() {
    if (loaded) return; loaded = true;
    var st = lsGet();      /* a stale or unknown stored value (an old id, 'blend', anything else) is ignored and left alone: nothing is written or removed unless the visitor picks */
    var raw = urlRaw(); if (raw !== null && !okAlt(raw)) setUrl(null);   /* unknown ?model= value: ignored and dropped from the address bar */
    var want = urlPick() || (okAlt(st) ? st : null);                      /* URL beats stored */
    var pDef = fetchSet(null), pWant = want ? fetchSet(want).catch(function () { return null; }) : Promise.resolve(null);
    var pLines = needLines ? fetch('/data/pred-lines.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('lines'); return r.json(); }).catch(function () { return false; }) : Promise.resolve(null);
    Promise.all([pDef, pLines]).then(function (rr) {
      var d = rr[0]; LINES = rr[1];
      var models = d.teams && d.teams.models; defId = d.teams && d.teams.model ? d.teams.model.id : 'default'; cache[defId] = d;
      return pWant.then(function (w) {
        var use = d; cur = defId;
        if (w && want && models && models.some(function (m) { return m.id === want; })) { cache[want] = w; cur = want; use = w; }   /* the picked model's numbers are the FIRST numbers drawn: no flash of the default */
        render(use); if (models) modelCard(models, cur); main.setAttribute('data-loaded', '1');   /* status flag for tests and assistive tech */
        if (cur !== defId && !urlPick()) setUrl(cur);   /* a restored pick shows in the address bar so a copied URL reproduces it (nothing is written to storage) */
      });
    }).catch(function () { loaded = false; var m = D.querySelector('[data-loadmsg]'); if (m) { m.textContent = 'Predictions could not load. Reload the page to try again.'; m.parentNode.hidden = false; } });
  }
  /* ---------- model control. Built here from the loaded data, so the static pages carry no model name or number. ---------- */
  function modelCard(models, def) {
    var by = {}; models.forEach(function (m) { by[m.id] = m; });
    function btn(m) { return '<button type="button" class="mb" data-m="' + esc(m.id) + '" aria-pressed="false">' + esc(m.btn || m.name) + '</button>'; }
    var first = models.filter(function (m) { return m.default; }), more = models.filter(function (m) { return !m.default; });
    var el = D.createElement('section'); el.className = 'mdl'; el.setAttribute('data-mdl', ''); el.setAttribute('aria-label', 'Choose a model');
    el.innerHTML = '<div class="mdh"><b>Model</b><span class="mdb" data-mdb></span></div>' +
      '<div class="mdt" role="group" aria-label="Model">' + first.map(btn).join('') + (more.length ? '<button type="button" class="mb mbm" data-more aria-expanded="false" aria-controls="mdmore">More models<i class="chv" aria-hidden="true"></i></button>' : '') + '</div>' +
      (more.length ? '<div class="mdt mdm" id="mdmore" role="group" aria-label="More models" hidden>' + more.map(btn).join('') + '</div>' : '') +
      '<p class="mdd"><span data-mdd aria-live="polite"></span> <button type="button" class="mdw" data-why aria-expanded="false" aria-controls="mdfull">What\u2019s this?</button></p>' +
      '<div class="mdf" id="mdfull" hidden><p data-mdfull></p><p class="mdn">These are estimates from a statistical model, not a market line and not a recommendation. <a href="/method/#models">How the models differ</a> &middot; <a href="/method/#accuracy">How accurate are they?</a>' +
      (main.getAttribute('data-page') === 'playoff' ? ' The order of the bracket is the same for every model; the chances beside each team follow the model you pick.' : '') + '</p>' +
      '<p class="mdr"><button type="button" class="mdu" data-reset hidden>Use the default model</button></p></div>';
    var anchor = D.querySelector('[data-loadbar]'), host = anchor ? anchor.parentNode : main.querySelector('.w') || main;
    host.insertBefore(el, anchor ? anchor.nextSibling : host.firstChild); card = el;
    var moreBtn = el.querySelector('[data-more]'), moreRow = el.querySelector('.mdm'), why = el.querySelector('[data-why]'), full = el.querySelector('.mdf'), reset = el.querySelector('[data-reset]');
    function show(id, msg) {
      var m = by[id]; [].forEach.call(el.querySelectorAll('[data-m]'), function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-m') === id ? 'true' : 'false'); });
      if (moreBtn && !m.default && moreRow.hidden) { moreRow.hidden = false; moreBtn.setAttribute('aria-expanded', 'true'); }   /* a pick that lives under More opens that row so the selected (dark, checked) button is visible */
      el.querySelector('[data-mdb]').textContent = m.default ? 'Default model' : 'Alternate model'; el.setAttribute('data-model', id);
      el.querySelector('[data-mdd]').innerHTML = esc(m.short || m.blurb) + (msg ? ' <span class="mdx">' + esc(msg) + '</span>' : '');
      el.querySelector('[data-mdfull]').innerHTML = '<b>' + esc(m.name) + '.</b> ' + esc(m.blurb); reset.hidden = !!m.default;
    }
    function persist(id) { lsSet(by[id].default ? null : id); setUrl(by[id].default ? null : id); }   /* only a visitor's pick reaches this; the default removes the key */
    var tok = 0;   /* last click wins: a slower earlier fetch can never overwrite a later pick */
    function press(id) { [].forEach.call(el.querySelectorAll('[data-m]'), function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-m') === id ? 'true' : 'false'); }); }
    function apply(id) { cur = id; el.removeAttribute('aria-busy'); render(cache[id]); show(id); persist(id); }
    function pick(id) {
      var my = ++tok;
      if (id === cur) { el.removeAttribute('aria-busy'); show(cur); return; }   /* back to the model on screen: cancels any pending load */
      press(id);                                                                  /* the pressed state follows the click at once */
      if (cache[id]) { apply(id); return; }
      el.setAttribute('aria-busy', 'true');
      fetchSet(id).then(function (d) { cache[id] = d; if (my === tok) apply(id); })
        .catch(function () { if (my !== tok) return; el.removeAttribute('aria-busy'); show(cur, 'That model could not load, so the page still shows the one above.'); });
    }
    [].forEach.call(el.querySelectorAll('[data-m]'), function (b) { b.addEventListener('click', function () { pick(b.getAttribute('data-m')); }); });
    if (moreBtn) moreBtn.addEventListener('click', function () { var o = moreRow.hidden; moreRow.hidden = !o; moreBtn.setAttribute('aria-expanded', String(o)); });
    why.addEventListener('click', function () { var o = full.hidden; full.hidden = !o; why.setAttribute('aria-expanded', String(o)); });
    reset.addEventListener('click', function () { pick(defId); });
    show(def);
  }

  /* ---------- market line, KickTip line and gap (SPEC-4 section 1, Creative D1-D4). Everything here runs on arrival with the other precomputed data; /data/pred-lines.json holds numbers only.
     Market line = [spread, read time (epoch s), kickoff (epoch s, 0 if TBA)], home side, negative = home favored. 'Line closed' = game started or line older than 24 h (decided in the browser, so it is right between refreshes).
     Gap = |market - KickTip| from the UNROUNDED KickTip line when the engine stored it (g[2]), else the displayed line; one decimal; shown only when both exist and the line is open; plain text, never coloured. ---------- */
  var LINES = null, DAY = 86400;
  function mtTime(sec) { try { return new Date(sec * 1000).toLocaleString('en-US', { timeZone: 'America/Denver', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) + ' MT'; } catch (e) { return ''; } }
  function say(s, h, a) { return s === 0 ? 'Even' : (s < 0 ? h : a) + ' minus ' + Math.abs(s).toFixed(1); }
  function gapOf(m, k) { return (Math.round(Math.abs(m - k) * 10 + 1e-9) / 10).toFixed(1); }
  function lval(s, h, a) { return '<span aria-hidden="true">' + esc(line(s, h, a)) + '</span><span class="vh">' + esc(say(s, h, a)) + '</span>'; }
  function lineInfo(el, g) {
    var h = el.getAttribute('data-h'), a = el.getAttribute('data-a'), L = LINES && LINES.l ? LINES.l[el.getAttribute('data-gk')] : null, now = Date.now() / 1000, k = +el.getAttribute('data-k') || 0;
    var ks = g && g[0] !== null && g[0] !== undefined ? g[1] : null, kr = ks === null ? null : (g[2] !== null && g[2] !== undefined ? g[2] : g[1]);
    var r = { h: h, a: a, ks: ks, off: LINES === false, L: L || null, closed: false, started: k > 0 && now >= k, gap: null };
    if (L) { r.closed = (L[2] > 0 && now >= L[2]) || (now - L[1] > DAY); if (!r.closed && kr !== null) r.gap = gapOf(L[0], kr); }
    return r;
  }
  function mkCell(i, tbl) {   /* [visible html, summary text] for the market line */
    if (i.off) return ['<span class="nm">Market line not available right now.</span>', 'Market line not available right now'];
    if (i.L && !i.closed) return [lval(i.L[0], i.h, i.a) + (tbl ? '<small>' + esc(mtTime(i.L[1])) + '</small>' : ''), 'Market line ' + line(i.L[0], i.h, i.a)];
    if (i.L) return ['<span class="cl">Line closed</span><small>Last line: ' + esc(line(i.L[0], i.h, i.a)) + ', ' + esc(mtTime(i.L[1])) + '</small>', 'Line closed'];
    if (i.started) return ['<span class="nm">No market line was posted before kickoff.</span>', 'No market line was posted'];
    return ['<span class="nm">Market line not posted yet.</span>' + (tbl ? '' : '<span class="nm2">Lines usually appear within about a day of kickoff.</span>'), 'Market line not posted yet'];
  }
  function lnBlock(el, i) {
    var id = 'ln-' + el.getAttribute('data-id'), rows = '', sum = [], m = mkCell(i, false), open = el.getAttribute('data-open');
    if (open === null) open = window.matchMedia && window.matchMedia('(min-width: 768px)').matches ? '1' : '0';
    rows += '<div class="r"><dt>Market line' + (i.L && !i.closed ? '<small>' + esc(mtTime(i.L[1])) + '</small>' : i.L ? '<small>Last line: ' + esc(line(i.L[0], i.h, i.a)) + ', ' + esc(mtTime(i.L[1])) + '</small>' : '') + '</dt><dd' + (i.L && !i.closed ? '' : ' class="nm"') + '>' + (i.L && i.closed ? '<span class="cl">Line closed</span>' : m[0]) + '</dd></div>'; sum.push(m[1]);
    if (i.ks !== null) { rows += '<div class="r"><dt>KickTip line</dt><dd>' + lval(i.ks, i.h, i.a) + '</dd></div>'; sum.push('KickTip line ' + line(i.ks, i.h, i.a)); }
    if (i.gap !== null) rows += '<div class="r"><dt>Gap</dt><dd>' + i.gap + ' points</dd></div>';
    return '<button type="button" class="gbt" aria-expanded="' + (open === '1') + '" aria-controls="' + id + '"><span>Lines</span><span class="gsm">' + esc(sum.join(' \u00B7 ')) + '</span><i class="gcv" aria-hidden="true"></i></button><div class="gnb" id="' + id + '"' + (open === '1' ? '' : ' hidden') + '><dl>' + rows + '</dl></div>';
  }
  function fillGame(el, g) {
    var h = el.getAttribute('data-h'), a = el.getAttribute('data-a'), i = lineInfo(el, g), cells = el.querySelectorAll('[data-c]');
    [].forEach.call(cells, function (c) {
      var k = c.getAttribute('data-c'), hh = '';
      if (k === 'wp') {
        if (g && g[0] !== null && g[0] !== undefined) { var hp = g[0] >= 0.5; hh = c.tagName === 'TD' ? esc(hp ? h : a) + ' ' + pct(hp ? g[0] : 1 - g[0]) : '<span class="gwl">KickTip win chance</span><span class="gwr"><span>' + esc(a) + ' ' + pct(1 - g[0]) + '</span><span>' + esc(h) + ' ' + pct(g[0]) + '</span></span><span class="gpb" aria-hidden="true"><i data-pw="' + Math.round(g[0] * 1000) / 10 + '"></i></span>'; }
        else hh = g === undefined ? '<span class="lk">n/a</span>' : '<span class="lk">Not modeled (FCS opponent)</span>';
      } else if (k === 'kl') hh = i.ks !== null ? lval(i.ks, h, a) : '<span class="lk">n/a</span>';
      else if (k === 'mk') hh = mkCell(i, true)[0];
      else if (k === 'gap') hh = i.gap !== null ? i.gap + ' points' : '<span class="lk" aria-label="No gap">\u2013</span>';
      else if (k === 'ln') hh = g === undefined && !i.L ? '' : lnBlock(el, i);
      c.innerHTML = hh;
    });
    sized(el);
  }
  D.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.gbt') : null; if (!b || !main.contains(b)) return;
    var open = b.getAttribute('aria-expanded') !== 'true', box = D.getElementById(b.getAttribute('aria-controls')), art = b.closest('[data-gk]');
    b.setAttribute('aria-expanded', String(open)); if (box) box.hidden = !open; if (art) art.setAttribute('data-open', open ? '1' : '0');
  });
  /* slate (/games/): neutral column sorts and a conference filter. Default sort = date. No sort is ever applied by gap on load, and nothing is highlighted. */
  var sortKey = 'd', sortDir = 1, sortBound = false;
  function gapNum(el) { var g = null; try { g = cur && cache[cur] && cache[cur].games.g[el.getAttribute('data-gk')]; } catch (e) { g = null; } var i = lineInfo(el, g); return i.gap === null ? null : +i.gap; }
  function slate() {
    var sel = D.getElementById('gsel'), srt = D.getElementById('gsort'), box = D.querySelector('[data-slate]'); if (!sel || !box) return;
    box.hidden = false; var ctl = D.querySelector('[data-slate-ctl]'); if (ctl) ctl.hidden = false;
    if (!sortBound) {
      sortBound = true; sel.addEventListener('change', slate);
      srt.addEventListener('change', function () { var v = srt.value; sortKey = v.charAt(0); sortDir = v.charAt(1) === 'D' ? -1 : 1; slate(); });
      [].forEach.call(D.querySelectorAll('[data-sort]'), function (b) { b.addEventListener('click', function () { var k = b.getAttribute('data-sort'); if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; } srt.value = k + (sortDir < 0 ? 'D' : 'A'); slate(); }); });
    }
    var f = sel.value, parents = [], n = 0;
    [].forEach.call(D.querySelectorAll('[data-slate] [data-gk]'), function (el) { if (parents.indexOf(el.parentNode) < 0) parents.push(el.parentNode); });
    parents.forEach(function (p) {
      var items = [].slice.call(p.children).filter(function (x) { return x.hasAttribute('data-gk'); });
      items.sort(function (x, y) {
        var r = 0, dx = +x.getAttribute('data-d'), dy = +y.getAttribute('data-d');
        if (sortKey === 'c') { var cx = x.getAttribute('data-cn'), cy = y.getAttribute('data-cn'); r = cx < cy ? -1 : cx > cy ? 1 : 0; r = r * sortDir; }
        else if (sortKey === 'g') { var gx = gapNum(x), gy = gapNum(y); if (gx === null && gy === null) r = 0; else if (gx === null) return 1; else if (gy === null) return -1; else r = (gx - gy) * sortDir; }
        else r = (dx - dy) * sortDir;
        return r || (dx - dy) || (x.getAttribute('data-gk') < y.getAttribute('data-gk') ? -1 : 1);
      });
      items.forEach(function (el) { p.appendChild(el); el.hidden = !(f === 'all' || (' ' + el.getAttribute('data-cf') + ' ').indexOf(' ' + f + ' ') >= 0); if (!el.hidden && p.tagName === 'TBODY') n++; });
    });
    [].forEach.call(D.querySelectorAll('[data-sort]'), function (b) { var th = b.parentNode, on = b.getAttribute('data-sort') === sortKey; th.setAttribute('aria-sort', on ? (sortDir < 0 ? 'descending' : 'ascending') : 'none'); });
    var cnt = D.querySelector('[data-slate-count]'); if (cnt) { var vis = D.querySelectorAll('.gcl [data-gk]:not([hidden])').length; cnt.textContent = vis + (vis === 1 ? ' game' : ' games'); }
  }
  function render(d) {
    var T = d.teams && d.teams.teams, page = main.getAttribute('data-page');
    if (T) { [].forEach.call(D.querySelectorAll('td[data-f]'), function (td) { var t = T[td.getAttribute('data-t')]; if (!t) return; td.innerHTML = cellPct(t[td.getAttribute('data-f')]); }); }
    if (d.games) { [].forEach.call(D.querySelectorAll('[data-gk]'), function (el) { fillGame(el, d.games.g[el.getAttribute('data-gk')]); }); if (page === 'slate') slate(); }
    if (page === 'home' && T) topTable(T);
    if (page === 'conference' && T) destiny(T);
    chipT = T || null; closePop(false); if (page === 'conference' && T) chipsConf(T); if (page === 'home' || page === 'conference') chipEvents();
    if (page === 'team' && T) teamTiles(T, d.paths);
    if (page === 'playoff' && T) playoff(T, d.teams.field);
    if (page === 'top25' && T && window.KTTop25) window.KTTop25.draw(T, d.top25, d.teams.model && d.teams.model.name, function () { tagLinks(cur && cur !== defId ? cur : null); });   /* /top25/: assets/top25.js draws the rows (rank order from pred-top25.json) and calls back once they are in the page */
    sized(D); tagLinks(cur && cur !== defId ? cur : null);
    try { D.dispatchEvent(new CustomEvent('kt:render', { detail: { T: T || null, model: cur, def: defId } })); } catch (e) { /* My teams (assets/myteams.js) listens; nothing else depends on it */ }
  }
  /* ---------- 'why it moved' chip (spec 2a, Creative mockups C1-C5). src/moves.py decides everything (threshold, no-previous-snapshot, model-change days, popover text) and puts [rounded signed points, popover text]
     under key m of a team in pred-teams.json; this code only draws it, from the model on screen. Nothing is stored or fetched here. Tap, Enter or Space opens the popover; Esc, Close or an outside tap closes it
     (Esc returns focus to the chip). Focus stays on the chip when it opens; Close is the next Tab stop. ---------- */
  var chipT = null, pop = null, popFor = null, chipOn = false, UP = '\u25B2', DN = '\u25BC', SGN = { up: '+', dn: MINUS };   /* the minus is U+2212 like the lines; one constant */
  function chipHTML(k, t) {
    if (!t || !t.m) return ''; var up = t.m[0] > 0, n = Math.abs(t.m[0]);
    return '<button type="button" class="mv ' + (up ? 'up' : 'dn') + '" data-mv="' + esc(k) + '" aria-expanded="false" aria-haspopup="dialog" aria-label="' + esc(t.n) + ': ' + (up ? 'up ' : 'down ') + n + ' points since the last daily update. Show why."><span class="pl"><s aria-hidden="true">' + (up ? UP : DN) + '</s>' + (up ? SGN.up : SGN.dn) + n + '</span></button>';
  }
  function chipsConf(T) {
    [].forEach.call(D.querySelectorAll('.mv'), function (b) { b.parentNode.removeChild(b); });
    [].forEach.call(D.querySelectorAll('td[data-f="p"][data-t]'), function (td) {
      var k = td.getAttribute('data-t'), h = chipHTML(k, T[k]); if (!h) return;
      var nm = td.parentNode.querySelector('.tnm'), a = nm && nm.querySelector('a.tl'); if (!a) return;
      var w = a.parentNode; if (!w.classList.contains('tcn')) { w = D.createElement('span'); w.className = 'tcn'; nm.insertBefore(w, a); w.appendChild(a); }
      w.insertAdjacentHTML('beforeend', h);
    });
  }
  function closePop(refocus) {
    if (!pop || pop.hidden) return; var b = popFor; pop.hidden = true; popFor = null;
    if (b) { b.setAttribute('aria-expanded', 'false'); b.removeAttribute('aria-controls'); if (refocus && D.body.contains(b)) b.focus(); }
  }
  function openPop(b) {
    var t = chipT && chipT[b.getAttribute('data-mv')]; if (!t || !t.m) return;
    if (!pop) {
      pop = D.createElement('div'); pop.className = 'mvpop'; pop.id = 'mvpop'; pop.setAttribute('role', 'dialog'); pop.hidden = true;
      pop.innerHTML = '<span class="mvc" aria-hidden="true"></span><p class="mvt"></p><button type="button" class="mvx">Close</button>'; D.body.appendChild(pop);
      pop.querySelector('.mvx').addEventListener('click', function () { closePop(true); });
    }
    pop.setAttribute('aria-label', 'Why ' + t.n + ' moved'); pop.querySelector('.mvt').textContent = t.m[1]; pop.hidden = false;
    b.setAttribute('aria-expanded', 'true'); b.setAttribute('aria-controls', 'mvpop'); popFor = b;
    var r = b.getBoundingClientRect(), vw = D.documentElement.clientWidth, sx = window.pageXOffset || 0, sy = window.pageYOffset || 0, wide = vw >= 768, w = wide ? 400 : vw - 20, left;
    if (wide) left = Math.max(10, Math.min(r.left - 8, vw - w - 10)); else left = 10;   /* phones: 10 px from each edge; 1280: 400 px wide under the chip */
    pop.style.width = w + 'px'; pop.style.left = (sx + left) + 'px'; pop.style.top = (sy + r.bottom + 2) + 'px';
    pop.querySelector('.mvc').style.left = Math.max(14, Math.min(r.left + r.width / 2 - left - 7, w - 28)) + 'px';
  }
  function chipEvents() {
    if (chipOn) return; chipOn = true;
    D.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('.mv') : null;
      if (b) { if (popFor === b) closePop(true); else { closePop(false); openPop(b); } return; }
      if (popFor && !(pop && pop.contains(e.target))) closePop(false);
    });
    D.addEventListener('keydown', function (e) {
      if (!popFor) return;
      if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); closePop(true); return; }
      if (e.key !== 'Tab') return; var x = pop.querySelector('.mvx'), a = D.activeElement;
      if (a === popFor && !e.shiftKey) { e.preventDefault(); x.focus(); }               /* Close is the next Tab stop after the chip */
      else if (a === x) { e.preventDefault(); if (e.shiftKey) popFor.focus(); else closePop(true); }   /* Tab past Close: close and carry on from the chip */
    });
    D.addEventListener('focusin', function (e) { if (popFor && e.target !== popFor && !(pop && pop.contains(e.target))) closePop(false); });
  }
  function LG() { return window.KTLogo || { team: function () { return ''; }, conf: function () { return ''; } }; } /* logo tiles come from lg.js (same markup as the static pages) */
  function arr(T) { return Object.keys(T).map(function (k) { var t = T[k]; t.k = k; return t; }); }
  function rowTop(t, i, logo, chip) {
    var nm = '<a class="tl" href="/team/' + t.k + '/">' + esc(t.n) + '</a>'; var cp = chip ? chipHTML(t.k, t) : ''; if (cp) nm = '<span class="tcn">' + nm + cp + '</span>';
    return '<tr><td class="n">' + (i + 1) + '</td><td>' + (logo ? '<span class="tnm">' + LG().team(t.k, 24, i >= 6) + nm + '</span>' : nm) + '</td><td>' + esc(t.cn) + '</td><td class="n">' + cellPct(t.p) + '</td><td class="n">' + cellPct(t.b) + '</td><td class="n">' + cellPct(t.c) + '</td><td class="n">' + cellPct(t.w) + '</td></tr>';
  }
  function topTable(T) { var b = D.querySelector('#top12 tbody'); if (!b) return; b.innerHTML = arr(T).sort(function (x, y) { return y.p - x.p || x.n.localeCompare(y.n); }).slice(0, 12).map(function (t, i) { return rowTop(t, i, true, true); }).join(''); }
  function playoff(T, f) {
    var b = D.querySelector('#chances tbody'); if (b) b.innerHTML = arr(T).sort(function (x, y) { return y.p - x.p || x.n.localeCompare(y.n); }).slice(0, 25).map(function (t, i) { return rowTop(t, i, false); }).join('');
    f = f || []; bracket(T, f);
    var fb = D.querySelector('#field tbody'); if (!fb) return;
    fb.innerHTML = f.map(function (e, i) { var t = T[e[0]], s = i + 1; return '<tr><td class="n">' + s + '</td><td><span class="tnm">' + LG().team(e[0], 24, true) + '<a class="tl" href="/team/' + e[0] + '/">' + esc(t.n) + '</a></span></td><td><span class="tnm">' + LG().conf(t.cs, 20, true) + '<span>' + esc(t.cn) + '</span></span></td><td>' + (s <= 4 ? 'First-round bye' : s <= 8 ? 'Hosts a first-round game' : 'Plays on the road') + (e[1] ? ' (conference leader)' : '') + '</td></tr>'; }).join('');
  }
  /* b9 bracket: fills the static bracket skeleton. Seeds, names, conference and the model's make-the-12 (and bye) chance come from pred-teams.json only. */
  function bracket(T, f) {
    var seed = {}; f.forEach(function (e, i) { seed[i + 1] = { k: e[0], lead: e[1], t: T[e[0]] }; });
    function nm(i) { return seed[i] ? seed[i].t.n : 'seed ' + i; }
    [].forEach.call(D.querySelectorAll('[data-seed]'), function (el) {
      var i = +el.getAttribute('data-seed'), e = seed[i]; if (!e) return; var t = e.t, bye = i <= 4;
      var info = esc(t.cn) + (e.lead ? ' &middot; conference leader' : '') + '<br>Make the 12: ' + pct(t.p) + ' (model)' + (bye ? '<br>First-round bye: ' + pct(t.b) + ' (model)' : '');
      el.innerHTML = LG().team(e.k, 28, false) + '<a class="tl" href="/team/' + e.k + '/"><span class="tn">' + esc(t.n) + '</span><span class="ti">' + info + '</span></a>';
    });
    [].forEach.call(D.querySelectorAll('[data-win]'), function (el) {
      var k = el.getAttribute('data-win').split('-'); if (k.length === 2 && seed[k[0]] && seed[k[1]]) el.textContent = 'Winner of ' + nm(k[0]) + ' vs ' + nm(k[1]);
    });
    [].forEach.call(D.querySelectorAll('#bracket .g[aria-label]'), function (g) {
      var gm = g.parentNode.getAttribute('data-g') || '', m = /^(r1|qf)-(\d+)$/.exec(gm); if (!m) return; var i = +m[2];
      if (m[1] === 'r1') g.setAttribute('aria-label', 'First round: No. ' + i + ' ' + nm(i) + ' hosts No. ' + (17 - i) + ' ' + nm(17 - i));
      else { var o = { 4: [5, 12], 1: [8, 9], 3: [6, 11], 2: [7, 10] }[i]; g.setAttribute('aria-label', 'Quarterfinal: No. ' + i + ' ' + nm(i) + ' (first-round bye) plays the winner of No. ' + o[0] + ' ' + nm(o[0]) + ' vs No. ' + o[1] + ' ' + nm(o[1])); }
    });
    var bt = D.querySelector('[data-bkt]'), w = D.querySelector('#bracket .bkw'), hint = D.querySelector('#bracket .bkh');
    if (bt && w && !bt.getAttribute('data-ready')) {
      bt.setAttribute('data-ready', '1'); bt.hidden = false;
      [].forEach.call(bt.querySelectorAll('[data-bkview]'), function (b) {
        b.addEventListener('click', function () {
          var v = b.getAttribute('data-bkview'); w.setAttribute('data-view', v); w.querySelector('.bk').setAttribute('data-bk', v); if (hint) hint.hidden = v !== 'full';
          [].forEach.call(bt.querySelectorAll('[data-bkview]'), function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        });
      });
    }
  }
  function destiny(T) {
    var ul = D.querySelector('#dest'); if (!ul) return; var cs = main.getAttribute('data-conf');
    var rows = arr(T).filter(function (t) { return t.cs === cs && t.x !== null && t.x !== undefined; }).sort(function (a, b) { return b.x - a.x; }).filter(function (t) { return t.x >= 0.02; });
    ul.innerHTML = rows.length ? rows.map(function (t) { var c = t.x >= 0.9 ? ['p1', 'IN WITH WINS'] : ['p2', 'NEEDS HELP']; return '<li><span class="pill ' + c[0] + '">' + c[1] + '</span>' + esc(t.n) + ': if it wins out, ' + pct(t.x) + ' to reach the conference championship game.</li>'; }).join('') : '<li>No team has a better than 2% chance to reach the conference championship game by winning out.</li>';
  }
  function teamTiles(T, P) {
    var k = main.getAttribute('data-team'), t = T[k]; if (!t) return;
    var m = { c: t.c, w: t.w, p: t.p, b: t.b };
    [].forEach.call(D.querySelectorAll('[data-tile]'), function (e) { var v = m[e.getAttribute('data-tile')]; e.textContent = v === null || v === undefined ? 'n/a' : pct(v); });
    var pb = D.querySelector('#paths tbody'), pp = P && P.t[k];
    if (pb && pp && pp.rows.length) pb.innerHTML = pp.rows.map(function (r) { return '<tr><td class="n">' + r[0] + '</td><td class="n">' + pct(r[1]) + '</td><td class="n">' + (r[2] === null ? '<span class="lk">too few simulated seasons</span>' : cellPct(r[2])) + '</td></tr>'; }).join('');
    var wo = D.querySelector('[data-wo]'); if (wo && pp) wo.textContent = pp.wo === null || pp.wo === undefined ? 'n/a' : pct(pp.wo);
  }

  startLoad();
})();
