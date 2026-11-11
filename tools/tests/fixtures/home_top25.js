/* KickTip home Top 25 block (section#top25 on the home page). No frameworks, no cookies, no storage, no third-party requests.
   Data: pred-teams.json (chances, names; the model on screen) and pred-top25.json (that model's rank order of all 138 FBS teams), fetched by kt.js on arrival like every other home number,
   plus /data/polls.json (same origin; AP Top 25 and Coaches Poll as ESPN published them). Every rank and number below is computed from those files; nothing is typed in.
   kt.js calls KTTop25.draw() each time the model changes (and KTTop25.fail() if pred-top25.json could not load; the rest of the home page keeps working).
   Expand state lives in aria-expanded attributes only: nothing is stored. Markup shell is static in index.html; this file fills the rows. */
(function () {
  'use strict';
  var D = document, pollsP = null, tok = 0, PN = { ap: 'AP', coaches: 'Coaches' };
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function LG() { return window.KTLogo || { team: function () { return ''; } }; }
  function pct(p) { if (p === null || p === undefined) return 'n/a'; var v = Math.round(p * 100); if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%'; }
  function pctSay(s) { return s === '<1%' ? 'less than 1%' : s === '>99%' ? 'more than 99%' : s; }
  function loadPolls() {
    if (!pollsP) pollsP = fetch('/data/polls.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('polls'); return r.json(); }).catch(function () { return null; });
    return pollsP;
  }
  /* poll state: {on:bool, rank:{slug:n}}; on=false means "not out" (or could not load): every cell is a dash, never a stale rank */
  function pollState(P, k) {
    var p = P && P.polls && P.polls[k]; if (!p || !p.released) return { on: false, rank: {}, asof: '' };
    var m = {}; p.ranks.forEach(function (x) { m[x[1]] = x[0]; }); return { on: true, rank: m, asof: p.asof };
  }
  function pv(s, slug) { return !s.on ? '\u2014' : s.rank[slug] === undefined ? 'NR' : String(s.rank[slug]); }
  function say(s, k, slug) { return !s.on ? PN[k] + ' not released yet' : s.rank[slug] === undefined ? 'not ranked by ' + PN[k] : PN[k] + ' ' + s.rank[slug]; }
  function label(nm, kt, rec, ps, slug, p) {
    return nm + ', KickTip rank ' + kt + '. Record ' + rec + '. ' + say(ps.ap, 'ap', slug) + ', ' + say(ps.coaches, 'coaches', slug) + '. Chance to make the 12-team playoff field ' + pctSay(p) + '.';
  }
  function row(e, kt, T, ps, out, lazy) {
    var slug = e[0], t = T[slug], nm = t.n, rec = e[1] + '-' + e[2], p = pct(t.p);
    return '<li><a class="h25-r' + (out ? ' h25-ro' : '') + '" href="/team/' + slug + '/" aria-label="' + esc(label(nm, kt, rec, ps, slug, p)) + '"><span class="h25-rk" aria-hidden="true">' + kt + '</span>' +
      LG().team(slug, 44, lazy) +
      '<span class="h25-tx" aria-hidden="true"><span class="h25-nm">' + esc(nm) + '</span><span class="h25-sb">' + rec + ' \u00b7 AP ' + pv(ps.ap, slug) + ' \u00b7 Coaches ' + pv(ps.coaches, slug) + '</span></span>' +
      '<span class="h25-pc" aria-hidden="true"><b>' + p + '</b><small>playoff field</small></span></a></li>';
  }
  function q(s) { return D.querySelector(s); }
  function mt(s) { s = String(s); return /\d:\d\d|[ap]\.?m\b/i.test(s) && !/\bMT$/.test(s) ? s + ' MT' : s; }   /* ' MT' only when the stamp has a time; a date-only stamp (Oct 25) gets none */
  function asof(ps) {
    var el = q('[data-t25asof]'); if (!el) return;
    function one(k) { return ps[k].on ? PN[k] + ' poll as of ' + esc(mt(ps[k].asof)) + '.' : PN[k] + ' poll: not released yet.'; }
    el.innerHTML = '<span>' + one('ap') + ' ' + one('coaches') + '</span>';
  }
  function outLabel(open, n) { var w = n + (n === 1 ? ' team' : ' teams'); return open ? 'Hide the ' + w + ' outside the KickTip 25' : 'Show ' + w + ' ranked in a poll, outside the KickTip 25'; }
  function setLabel(btn, text) { var s = btn.querySelector('span'); if (s) s.textContent = text; }
  function draw(T, R, model, done) {
    if (!T || !R) return; var my = ++tok, root = q('[data-t25]'); if (!root) return;
    loadPolls().then(function (P) {
      if (my !== tok) return;
      var ps = { ap: pollState(P, 'ap'), coaches: pollState(P, 'coaches') };
      var kt = {}, ent = {}; R.teams.forEach(function (e, i) { kt[e[0]] = i + 1; ent[e[0]] = e; });
      var top = R.teams.slice(0, 25).filter(function (e) { return T[e[0]]; });
      var l1 = q('[data-t25l]'), l2 = q('[data-t25r]'), lo = q('[data-t25ol]'); if (!l1 || !l2 || !lo) return;
      l1.innerHTML = top.slice(0, 5).map(function (e, i) { return row(e, i + 1, T, ps, false, false); }).join('');
      l2.innerHTML = top.slice(5).map(function (e, i) { return row(e, i + 6, T, ps, false, true); }).join('');
      l1.classList.remove('h25-ph');
      var out = Object.keys(kt).filter(function (s) { return kt[s] > 25 && T[s] && ['ap', 'coaches'].some(function (k) { return ps[k].rank[s] !== undefined; }); });
      function bestOf(s) { return Math.min.apply(null, ['ap', 'coaches'].map(function (k) { return ps[k].rank[s] === undefined ? 999 : ps[k].rank[s]; })); }
      out.sort(function (a, b) { return bestOf(a) - bestOf(b) || kt[a] - kt[b] || T[a].n.localeCompare(T[b].n); });
      lo.innerHTML = out.map(function (s) { return row(ent[s], kt[s], T, ps, true, true); }).join('');
      var ob = q('[data-t25o]'), os = q('[data-t25out]');
      if (ob && os) { ob.hidden = !out.length; if (!out.length) { os.hidden = true; ob.setAttribute('aria-expanded', 'false'); } setLabel(ob, outLabel(ob.getAttribute('aria-expanded') === 'true', out.length)); ob.setAttribute('data-n', String(out.length)); }
      var eb = q('[data-t25eb]'); if (eb) eb.textContent = model ? 'Rating: ' + model : '';
      asof(ps); var xb = q('[data-t25x]'); if (xb) xb.hidden = false;
      var er = q('[data-t25err]'); if (er) er.hidden = true;
      if (done) done();
      D.getElementById('main').setAttribute('data-t25', '1');   /* status flag for tests */
    });
  }
  function fail() {   /* pred-top25.json could not load: say so; the rest of the home page is unaffected */
    var l1 = q('[data-t25l]'), er = q('[data-t25err]'); if (l1) { l1.innerHTML = ''; l1.classList.remove('h25-ph'); } if (er) er.hidden = false;
    var xb = q('[data-t25x]'); if (xb) xb.hidden = true; var mo = q('.h25-more'); if (mo) mo.hidden = true; D.getElementById('main').setAttribute('data-t25', '0');
  }
  D.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button[data-t25x],button[data-t25o],button[data-t25c]'); if (!b) return;
    var s = b.closest('.t25h'), m = s.querySelector('.h25-more'), x = s.querySelector('[data-t25x]'), o = s.querySelector('[data-t25o]'), outs = s.querySelector('[data-t25out]');
    if (b.hasAttribute('data-t25o')) { var open = o.getAttribute('aria-expanded') !== 'true'; o.setAttribute('aria-expanded', String(open)); outs.hidden = !open; setLabel(o, outLabel(open, +o.getAttribute('data-n') || 0)); return; }
    var ex = b.hasAttribute('data-t25c') ? false : x.getAttribute('aria-expanded') !== 'true';
    x.setAttribute('aria-expanded', String(ex)); m.hidden = !ex; setLabel(x, ex ? 'Show top 5 only' : 'Show all 25');
    if (!ex && b.hasAttribute('data-t25c')) x.focus();
  });
  window.KTTop25 = { draw: draw, fail: fail };
})();
/* A link to /#field, /#top25, /#conferences, /#choose or /#my-teams makes the browser jump before the page's data-drawn sections have their height, so it lands short (the same on the old /#field).
   Re-align to the target while the page settles (first 4 s), and stop the moment the visitor scrolls, touches, clicks or presses a key. No storage. */
(function () {
  'use strict';
  var D = document, mn = D.getElementById('main'), id = (location.hash || '').slice(1);
  if (!mn || mn.getAttribute('data-page') !== 'home' || ['top25', 'field', 'conferences', 'choose', 'my-teams'].indexOf(id) < 0) return;
  var moved = false, t0 = Date.now(), ro = null;
  function stop() { moved = true; if (ro) ro.disconnect(); }
  ['wheel', 'touchstart', 'keydown', 'pointerdown', 'mousedown'].forEach(function (ev) { window.addEventListener(ev, stop, { passive: true, once: true }); });
  function align() { if (moved || Date.now() - t0 > 4000) return; var el = D.getElementById(id); if (el) el.scrollIntoView(); }
  if (window.ResizeObserver) { ro = new ResizeObserver(align); ro.observe(D.body); setTimeout(function () { if (ro) ro.disconnect(); }, 4200); }
  window.addEventListener('load', align);
})();
