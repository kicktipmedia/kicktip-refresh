/* KickTip Top 25 (/top25/). No frameworks, no cookies, no storage, no third-party requests.
   Data: pred-teams.json (chances, names; the model on screen) and pred-top25.json (that model's rank order of all 138 FBS teams), fetched by kt.js on arrival
   like every other page, plus /data/polls.json (same origin; AP Top 25 and Coaches Poll as ESPN published them, written at refresh by src/polls.py).
   Every rank, difference and sentence below is computed from those files; nothing is typed in. kt.js calls KTTop25.draw() each time the model changes.
   The Run scenario button only clicks the Ask KickTip pill: the scenario panel (chat.js) owns everything after that. */
(function () {
  'use strict';
  var D = document, MINUS = '\u2212', pollsP = null, tok = 0;
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function LG() { return window.KTLogo || { team: function () { return ''; } }; }
  function pct(p) { if (p === null || p === undefined) return 'n/a'; var v = Math.round(p * 100); if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%'; }
  function cellPct(p) { return p === null || p === undefined ? '<span class="lk">n/a</span>' : '<span class="bar" data-w="' + Math.round(Math.max(p > 0 ? 2 : 0, p * 48)) + '"></span>' + pct(p); }
  function loadPolls() {
    if (!pollsP) pollsP = fetch('/data/polls.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('polls'); return r.json(); }).catch(function () { return null; });
    return pollsP;
  }
  var PN = { ap: 'AP', coaches: 'Coaches' }, PLONG = { ap: 'the AP poll', coaches: 'the Coaches poll' };
  /* poll state: {on:bool, rank:{slug:n}}; on=false means "not out" (or could not load): every cell is a dash, never a stale rank */
  function pollState(P, k) {
    var p = P && P.polls && P.polls[k]; if (!p || !p.released) return { on: false, rank: {}, asof: '' };
    var m = {}; p.ranks.forEach(function (x) { m[x[1]] = x[0]; }); return { on: true, rank: m, asof: p.asof };
  }
  function spots(d) { var n = Math.abs(d); return n + (n === 1 ? ' spot' : ' spots'); }
  function diffText(d) { return d === 0 ? '0' : d > 0 ? '+' + d : MINUS + Math.abs(d); }
  function sentence(name, k, d) { /* screen-reader phrase for one difference cell */
    return 'KickTip ranks ' + name + ' ' + (d === 0 ? 'the same as ' : spots(d) + (d > 0 ? ' higher than ' : ' lower than ')) + PLONG[k] + '.';
  }
  function words(ps, kt, slug) { /* the plain-words line on a phone card; no arrows */
    var seen = false, parts = [], any = false;
    ['ap', 'coaches'].forEach(function (k) {
      var s = ps[k]; if (!s.on) return; any = true; var r = s.rank[slug];
      if (r === undefined) { parts.push('not ranked by ' + PN[k]); return; }
      var d = r - kt, ph = d === 0 ? 'the same as' : (seen ? Math.abs(d) : spots(d)) + (d > 0 ? ' higher than' : ' lower than'); seen = true;
      parts.push(ph + ' ' + PN[k]);
    });
    if (!any) return 'Poll ranks are not out yet.';
    var allNR = ['ap', 'coaches'].every(function (k) { return !ps[k].on || ps[k].rank[slug] === undefined; });
    if (allNR) return ps.ap.on && ps.coaches.on ? 'Not ranked by either poll.' : 'Not ranked by ' + (ps.ap.on ? 'AP' : 'Coaches') + '.';
    var s = parts.join(', '); return (/^not ranked/.test(parts[0]) ? s.charAt(0).toUpperCase() + s.slice(1) : 'KickTip is ' + s) + '.';
  }
  function pollCell(s, slug) { return !s.on ? '<span class="lk" aria-hidden="true">\u2014</span><span class="vh">not released yet</span>' : s.rank[slug] === undefined ? '<span class="lk">NR</span><span class="vh"> not ranked</span>' : String(s.rank[slug]); }
  function diffCell(s, k, slug, kt, nm) {
    if (!s.on) return '<span class="lk" aria-hidden="true">\u2014</span><span class="vh">not released yet</span>';
    var r = s.rank[slug]; if (r === undefined) return '<span class="lk">NR</span><span class="vh"> ' + esc(nm) + ' is not ranked by ' + PLONG[k] + '.</span>';
    var d = r - kt; return '<span class="vh">' + esc(sentence(nm, k, d)) + '</span><span class="t25-pill" aria-hidden="true">' + diffText(d) + '</span>';
  }
  function cardCell(label, s, slug) { var r = s.on ? s.rank[slug] : undefined; return '<div class="t25-c"><span>' + label + '</span><b' + (r === undefined ? ' class="nr"' : '') + '>' + (!s.on ? '\u2014' : r === undefined ? 'NR' : r) + '</b></div>'; }
  function rowHTML(e, kt, T, ps, pre) {
    var slug = e[0], t = T[slug], nm = t.n, rec = e[1] + '-' + e[2], href = '/team/' + slug + '/', did = pre + '-' + slug;
    var tr = '<tr><td class="n t25-n">' + kt + '</td><td><span class="tnm">' + LG().team(slug, 28, kt > 6) + '<a class="tl" href="' + href + '">' + esc(nm) + '</a></span></td>' +
      '<td class="n">' + pollCell(ps.ap, slug) + '</td><td class="n">' + pollCell(ps.coaches, slug) + '</td>' +
      '<td class="n">' + diffCell(ps.ap, 'ap', slug, kt, nm) + '</td><td class="n">' + diffCell(ps.coaches, 'coaches', slug, kt, nm) + '</td>' +
      '<td>' + esc(t.cn) + '</td><td class="n">' + rec + '</td><td class="n">' + cellPct(t.p) + '</td></tr>';
    var kc = '<div class="t25-c t25-k"><span>KickTip</span><b>' + kt + '</b></div>';
    var li = '<li class="t25-r"><div class="t25-top"><div class="t25-rk"><b>' + kt + '</b><span>KickTip</span></div>' +
      '<div class="t25-id"><span class="tnm">' + LG().team(slug, 28, kt > 6) + '<a class="tl" href="' + href + '">' + esc(nm) + '</a></span><span class="t25-sub">' + esc(t.cn) + ' &middot; ' + rec + '</span></div>' +
      '<button type="button" class="t25-chv" aria-expanded="false" aria-controls="' + did + '" aria-label="More about ' + esc(nm) + '"><i class="chv" aria-hidden="true"></i></button></div>' +
      '<div class="t25-cells">' + kc + cardCell('AP', ps.ap, slug) + cardCell('Coaches', ps.coaches, slug) + '</div><p class="t25-words">' + esc(words(ps, kt, slug)) + '</p>' +
      '<div class="t25-det" id="' + did + '" hidden><dl><div><dt>Make the 12</dt><dd>' + pct(t.p) + '</dd></div><div><dt>First-round bye</dt><dd>' + pct(t.b) + '</dd></div><div><dt>Reach CCG</dt><dd>' + pct(t.c) + '</dd></div><div><dt>Win conference</dt><dd>' + pct(t.w) + '</dd></div></dl><p class="ccgdef">CCG = conference championship game</p>' +
      '<a class="t25-tp" href="' + href + '">Team page</a></div></li>';
    return [tr, li];
  }
  function fill(tbody, ol, rows) { tbody.innerHTML = rows.map(function (r) { return r[0]; }).join(''); ol.innerHTML = rows.map(function (r) { return r[1]; }).join(''); }
  function asof(ps, R) {
    var el = D.querySelector('[data-t25asof]'); if (!el) return;
    function one(k) { return ps[k].on ? PN[k] + ' poll as of ' + esc(ps[k].asof) + ' MT.' : PN[k] + ' poll: not released yet.'; }
    el.innerHTML = '<span>' + one('ap') + ' ' + one('coaches') + '</span> <span>KickTip updated ' + esc(R.asof) + ' MT.</span>';
  }
  function draw(T, R, model, done) {
    if (!T || !R) return; var my = ++tok;
    loadPolls().then(function (P) {
      if (my !== tok) return;
      var ps = { ap: pollState(P, 'ap'), coaches: pollState(P, 'coaches') };
      var kt = {}; R.teams.forEach(function (e, i) { kt[e[0]] = i + 1; });
      var top = R.teams.slice(0, 25), tb = D.querySelector('#t25 tbody'), ol = D.getElementById('t25l'); if (!tb || !ol) return;
      fill(tb, ol, top.map(function (e, i) { return rowHTML(e, i + 1, T, ps, 'd'); }));
      var ent = {}; R.teams.forEach(function (e) { ent[e[0]] = e; });
      var out = Object.keys(kt).filter(function (s) { return kt[s] > 25 && T[s] && ['ap', 'coaches'].some(function (k) { return ps[k].rank[s] !== undefined; }); });
      function bestOf(s) { return Math.min.apply(null, ['ap', 'coaches'].map(function (k) { return ps[k].rank[s] === undefined ? 999 : ps[k].rank[s]; })); }
      out.sort(function (a, b) { return bestOf(a) - bestOf(b) || kt[a] - kt[b] || T[a].n.localeCompare(T[b].n); });
      var os = D.getElementById('t25out'), ot = D.querySelector('#t25o tbody'), oo = D.getElementById('t25ol');
      if (os && ot && oo) { os.hidden = !out.length; if (out.length) fill(ot, oo, out.map(function (s) { return rowHTML(ent[s], kt[s], T, ps, 'o'); })); else { ot.innerHTML = ''; oo.innerHTML = ''; } }
      asof(ps, R);
      var m = D.querySelector('[data-t25model]'); if (m && model) m.textContent = 'Ranked by the ' + model + ' rating. Choose another model above and the ranking changes with it.';
      [].forEach.call(D.querySelectorAll('.bar[data-w]'), function (b) { b.style.width = b.getAttribute('data-w') + 'px'; b.removeAttribute('data-w'); });
      if (done) done();
      D.getElementById('main').setAttribute('data-t25', '1');   /* status flag for tests */
    });
  }
  D.addEventListener('click', function (e) {
    var c = e.target.closest && e.target.closest('.t25-chv');
    if (c) { var d = D.getElementById(c.getAttribute('aria-controls')), o = d.hidden; d.hidden = !o; c.setAttribute('aria-expanded', String(o)); return; }
    var r = e.target.closest && e.target.closest('[data-t25run]');
    if (r) { var p = D.getElementById('kpill'); if (p) p.click(); }
  });
  window.KTTop25 = { draw: draw };
})();
