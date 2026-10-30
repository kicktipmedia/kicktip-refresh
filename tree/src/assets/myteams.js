/* KickTip My teams (phase 1, local only). No frameworks, no cookies, no third-party requests, no inline styles (strict CSP).
   Storage: nothing is read for display until the page needs it and NOTHING is written until the visitor taps Save (or Remove / Clear). Two keys:
     kicktip_teams = {"v":1,"t":["utah","byu"]}   kicktip_lead = {"v":1,"m":{"utah":"p"}}   (m: team -> headline number, the race number shown first: p Make the 12, c Reach CCG, w Win conference, b First-round bye)
   Storage may be refused by the browser: every access is try/catch; the list then lives in memory for this page view and a notice says so.
   The Run/Save terms text under the Save buttons is drawn from build-time copy (src/terms_copy.py). Phase 2 (sign-in) plugs into window.KTMyTeams (cap, merge, change hook). */
(function () {
  'use strict';
  var D = document, W = window, main = D.getElementById('main');
  var KT = 'kicktip_teams', KL = 'kicktip_lead', VER = 1, CAP_LOCAL = __CAP_LOCAL__, SLUGRE = /^[a-z0-9][a-z0-9-]{0,47}$/;
  var LEADS = [['p', 'Make the 12'], ['c', 'Reach CCG'], ['w', 'Win conference'], ['b', 'First-round bye']], LEADNAME = {}; LEADS.forEach(function (x) { LEADNAME[x[0]] = x[1]; });
  var SAVE_HTML = '__SAVE_HTML__', PRIV_SHORT = '__PRIVACY_SHORT__', MINUS = '\u2212', STAR_ON = '\u2605', STAR_OFF = '\u2606';
  var capNow = CAP_LOCAL, listeners = [], noStore = false, T = null, info = { model: null, def: null }, editing = false, draft = null, status = '', clearAsk = false;
  var st = { teams: [], lead: {} };   /* what is saved (or, if storage is noStore, what this page view holds) */

  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return [].slice.call((r || D).querySelectorAll(s)); }
  function pct(p) { if (p === null || p === undefined) return 'n/a'; var v = Math.round(p * 100); if (p > 0 && v < 1) return '<1%'; if (p < 1 && v >= 100) return '>99%'; return v + '%'; }

  /* ---------- storage ---------- */
  function parse(raw, key) { if (!raw) return null; try { var o = JSON.parse(raw); return o && o.v === VER && o[key] ? o : null; } catch (e) { return null; } }
  function cleanTeams(a, cap) { var out = []; if (!Array.isArray(a)) return out; a.forEach(function (s) { if (typeof s === 'string' && SLUGRE.test(s) && out.indexOf(s) < 0 && out.length < cap) out.push(s); }); return out; }
  function cleanLead(m, teams) { var o = {}; if (m && typeof m === 'object') teams.forEach(function (s) { if (typeof m[s] === 'string' && LEADNAME[m[s]]) o[s] = m[s]; }); return o; }
  function load() {
    var t = null, l = null;
    try { t = parse(W.localStorage.getItem(KT), 't'); l = parse(W.localStorage.getItem(KL), 'm'); } catch (e) { noStore = true; }
    var teams = cleanTeams(t && t.t, CAP_LOCAL); st = { teams: teams, lead: cleanLead(l && l.m, teams) };
  }
  var acct = null;   /* phase 2: when signed in, { cap, save(teams, lead) -> Promise }; the device keys are then left exactly as they were */
  function persist() {   /* the ONLY writer. Returns false if the browser refuses (nothing is lost: the list stays in memory for this page view) */
    if (acct) { acct.save(st.teams.slice(), JSON.parse(JSON.stringify(st.lead))); return true; }
    try {
      if (!st.teams.length) { W.localStorage.removeItem(KT); W.localStorage.removeItem(KL); }
      else { W.localStorage.setItem(KT, JSON.stringify({ v: VER, t: st.teams })); W.localStorage.setItem(KL, JSON.stringify({ v: VER, m: st.lead })); }
      noStore = false; return true;
    } catch (e) { noStore = true; return false; }
  }
  function changed() { listeners.forEach(function (f) { try { f(st); } catch (e) { /* a listener never breaks the page */ } }); renderAll(); }
  function defLead(slug) {
    var t = T && T[slug]; if (!t) return 'p'; if (t.c === null || t.c === undefined) return 'p';
    var ps = Object.keys(T).map(function (k) { return T[k].p || 0; }).sort(function (a, b) { return b - a; });
    return (t.p || 0) >= (ps[24] || 0) && (t.p || 0) > 0 ? 'p' : 'w';   /* top-25 by make-the-12 chance leads with it; everyone else with Win conference */
  }
  function leadOf(slug) { var l = st.lead[slug]; var t = T && T[slug]; if (l && t && t[l] === null) l = null; return l || defLead(slug); }
  function isSaved(s) { return st.teams.indexOf(s) >= 0; }
  function known(s) { return !T || !!T[s]; }

  /* ---------- the public hooks (phase 2 plugs in here) ---------- */
  W.KTMyTeams = {
    cap: function () { return capNow; }, setCap: function (n) { capNow = n; renderAll(); },
    get: function () { return { teams: st.teams.slice(), lead: JSON.parse(JSON.stringify(st.lead)) }; },
    set: function (teams, lead, write) { st = { teams: cleanTeams(teams, 50), lead: cleanLead(lead, cleanTeams(teams, 50)) }; if (write !== false) persist(); changed(); },
    on: function (f) { listeners.push(f); }, nudge: function () { return ''; }, extra: function () { return ''; }, known: known, say: function (m) { say(m); },
    readLocal: function () { var t = null, l = null; try { t = parse(W.localStorage.getItem(KT), 't'); l = parse(W.localStorage.getItem(KL), 'm'); } catch (e) { /* refused */ } var teams = cleanTeams(t && t.t, CAP_LOCAL); return { teams: teams, lead: cleanLead(l && l.m, teams) }; },
    useAccount: function (a) { acct = a; capNow = a.cap; var teams = cleanTeams(a.teams, a.cap); st = { teams: teams, lead: cleanLead(a.lead, teams) }; editing = false; draft = null; changed(); },
    leaveAccount: function () { acct = null; capNow = CAP_LOCAL; editing = false; draft = null; load(); changed(); },
    signedIn: function () { return !!acct; }, names: function (slugs) { return slugs.map(nm); }
  };
  var nudgeFn = function () { return W.KTMyTeams.nudge(); };

  /* ---------- actions ---------- */
  function capMsg() { return 'You can keep up to ' + capNow + ' teams' + (capNow === CAP_LOCAL ? ' on this device' : '') + '. Remove one to add another.'; }
  function capHtml() { return esc(capMsg()) + nudgeFn(); }
  function say(m, html) { status = m; $$('[data-mtstatus]').forEach(function (el) { if (html) el.innerHTML = m; else el.textContent = m; }); }
  function addTeam(slug) {
    if (isSaved(slug)) return { ok: true };
    if (st.teams.length >= capNow) return { ok: false, reason: 'cap' };
    st.teams.push(slug); st.lead[slug] = defLead(slug); var ok = persist(); changed(); return { ok: true, stored: ok };
  }
  function removeTeam(slug) { st.teams = st.teams.filter(function (s) { return s !== slug; }); delete st.lead[slug]; persist(); changed(); }
  function clearAll() { st = { teams: [], lead: {} }; persist(); clearAsk = false; editing = false; draft = null; changed(); }

  /* ---------- logos, names ---------- */
  function logo(slug, size) { return W.KTLogo ? W.KTLogo.team(slug, size, true) : ''; }
  function nm(slug) { return T && T[slug] ? T[slug].n : slug; }

  /* ---------- header count ---------- */
  function badge() {
    $$('.nav a[href$="#my-teams"]').forEach(function (a) {
      var b = $('.mt-nb', a); if (!b) { b = D.createElement('span'); b.className = 'mt-nb'; a.appendChild(b); }
      var n = st.teams.length; b.hidden = !n; b.innerHTML = n ? '<span aria-hidden="true">' + n + '</span><span class="vh">, ' + n + ' saved</span>' : '';
    });
  }

  /* ---------- the Save control on a team page ---------- */
  function teamSave() {
    $$('[data-mtsave]').forEach(function (box) {
      var slug = box.getAttribute('data-slug'), name = (T && T[slug] && T[slug].n) || box.getAttribute('data-name'), on = isSaved(slug);
      var b = $('.mt-sv', box);
      if (!b) {
        box.innerHTML = '<button type="button" class="mt-sv" aria-pressed="false"></button>' + SAVE_HTML + '<p class="mt-msg" data-mtstatus role="status"></p>';
        b = $('.mt-sv', box); b.addEventListener('click', function () {
          var s = box.getAttribute('data-slug');
          if (isSaved(s)) { removeTeam(s); say('Removed ' + nm(s) + ' from My teams.'); return; }
          var r = addTeam(s); if (!r.ok) say(capHtml() + ' <a href="/#my-teams">Open My teams</a>', true); else say(r.stored === false ? 'Saved for this page view only: this browser is blocking storage, so My teams will not be remembered.' : 'Saved ' + nm(s) + ' to My teams.');
        });
        box.hidden = false;
      }
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.setAttribute('aria-label', on ? 'Saved. Remove ' + name + ' from My teams' : 'Save ' + name + ' to My teams');
      b.innerHTML = '<i aria-hidden="true">' + (on ? STAR_ON : STAR_OFF) + '</i><span>' + (on ? 'Saved to My teams' : 'Save to My teams') + '</span>';
    });
  }

  /* ---------- stars inside team lists (Top 12, standings, playoff tables) ---------- */
  function listStars() {
    $$('.tw.tk-n').forEach(function (tw) {
      if (!tw.hasAttribute('data-mtln')) {
        tw.setAttribute('data-mtln', '1');
        var p = D.createElement('p'); p.className = 'rn s mt-ln'; p.innerHTML = 'Tap the star by a team to save it to My teams. ' + SAVE_HTML.replace(/^<p[^>]*>/, '').replace(/<\/p>$/, '');
        var hint = tw.previousElementSibling && tw.previousElementSibling.classList.contains('hint') ? tw.previousElementSibling : tw; tw.parentNode.insertBefore(p, hint);
      }
      $$('.tnm', tw).forEach(function (cell) {
        var a = $('a.tl', cell); if (!a) return; var m = /^\/team\/([a-z0-9-]+)\//.exec(a.getAttribute('href') || ''); if (!m) return;
        var slug = m[1], on = isSaved(slug), b = $('.mt-ls', cell), name = (T && T[slug] && T[slug].n) || a.textContent;
        if (!b) {
          b = D.createElement('button'); b.type = 'button'; b.className = 'mt-ls'; b.setAttribute('data-slug', slug); cell.appendChild(b);
          b.addEventListener('click', function () {
            var s = b.getAttribute('data-slug'); if (isSaved(s)) { removeTeam(s); say('Removed ' + nm(s) + ' from My teams.'); } else { var r = addTeam(s); if (!r.ok) say(capHtml() + ' <a href="/#my-teams">Open My teams</a>', true); else say('Saved ' + nm(s) + ' to My teams.'); }
            var again = $('.mt-ls[data-slug="' + s + '"]'); if (again) again.focus();
          });
        }
        b.setAttribute('aria-pressed', on ? 'true' : 'false'); b.setAttribute('aria-label', on ? 'Saved. Remove ' + name + ' from My teams' : 'Save ' + name + ' to My teams');
        b.innerHTML = '<i aria-hidden="true">' + (on ? STAR_ON : STAR_OFF) + '</i>';
      });
    });
    var pg = main && main.getAttribute('data-page');
    if ((pg === 'home' || pg === 'conference' || pg === 'playoff') && !$('.mt-live')) { var live = D.createElement('p'); live.className = 'vh mt-live'; live.setAttribute('role', 'status'); live.setAttribute('data-mtstatus', ''); (main || D.body).appendChild(live); }
  }

  /* ---------- next game data (sim-bundle for dates, pred-games for the numbers of the model on screen) ---------- */
  var bundleP = null, gamesP = {};
  function getJSON(u) { return fetch(u, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function bundle() { return bundleP || (bundleP = getJSON('/data/sim-bundle.json').catch(function (e) { bundleP = null; throw e; })); }
  function games(model) { var u = model && model !== info.def ? '/data/m/' + model + '/pred-games.json' : '/data/pred-games.json'; return gamesP[u] || (gamesP[u] = getJSON(u).catch(function (e) { delete gamesP[u]; throw e; })); }
  function lineText(s, h, a) { if (s === null || s === undefined) return null; if (s === 0) return 'Even'; var n = Math.abs(s).toFixed(1); return (s < 0 ? h : a) + ' ' + MINUS + n; }
  var FMT = null;
  function when(iso) {
    try {
      FMT = FMT || new Intl.DateTimeFormat('en-US', { timeZone: 'America/Denver', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
      var o = {}; FMT.formatToParts(new Date(iso.replace(/Z$/, ':00Z'))).forEach(function (p) { o[p.type] = p.value; });
      return o.weekday + ' ' + o.month + ' ' + o.day + ' \u00B7 ' + o.hour + ':' + o.minute + ' ' + (o.dayPeriod || '') + ' MT';
    } catch (e) { return ''; }
  }
  function nextGame(b, slug) {
    var idx = {}; b.teams.forEach(function (t, i) { if (t.g) idx[t.g] = i; }); var me = idx[slug]; if (me === undefined) return null;
    var now = Date.now(), best = null;
    b.games.forEach(function (g) {
      if (g.h !== me && g.a !== me) return; var t = Date.parse(g.date.replace(/Z$/, ':00Z')); if (isNaN(t)) return;
      if (!g.ip && t < now - 4 * 36e5) return;    /* kicked off hours ago and not marked live: the next daily refresh will drop it */
      if (!best || t < best.t) best = { g: g, t: t };
    });
    if (!best) return { none: true };
    var g = best.g, home = g.h === me, oppI = home ? g.a : g.h, ot = b.teams[oppI];
    var slugOf = function (i) { var x = b.teams[i]; return x && x.g ? x.g : 'fcs'; };
    return { g: g, home: home, ip: !!g.ip, date: g.date, opp: ot && ot.s ? ot.s : (g.fcs || 'FCS opponent'), oppSlug: ot && ot.g ? ot.g : null, key: slugOf(g.h) + '~' + slugOf(g.a), neutral: !!g.neu, hName: b.teams[g.h].s || '', aName: b.teams[g.a] && b.teams[g.a].s ? b.teams[g.a].s : (g.fcs || 'FCS opponent') };
  }
  function fillNext(card, slug, model) {
    var box = $('.mt-x', card);
    Promise.all([bundle(), games(model)]).then(function (r) {
      if (!D.body.contains(card)) return; var ng = nextGame(r[0], slug), gm = r[1].g || {};
      if (!ng) { box.innerHTML = '<p class="mt-tag">Next game</p><p class="mt-dt">Schedule not available</p>'; return; }
      if (ng.none) { box.innerHTML = '<p class="mt-tag">Next game</p><p class="mt-dt">No games left on the schedule</p>'; return; }
      var g = gm[ng.key], me = nm(slug), pw = null, ml = null;
      if (g && g[0] !== null && g[0] !== undefined) { pw = ng.home ? g[0] : 1 - g[0]; }
      if (g && g[2] !== null && g[2] !== undefined) ml = lineText(g[2], ng.hName, ng.aName);
      box.innerHTML = '<p class="mt-tag">Next game</p><p class="mt-dt">' + (ng.ip ? 'In progress \u00B7 ' : '') + esc(when(ng.date)) + '</p>' +
        '<p class="mt-op">' + (ng.oppSlug ? logo(ng.oppSlug, 24) : '') + '<span>' + (ng.neutral ? 'vs' : ng.home ? 'vs' : 'at') + ' ' + esc(ng.opp) + '</span></p>' +
        (pw === null ? '<p class="mt-kv"><span>KickTip win chance</span><b>' + (ng.ip ? 'Game in progress' : 'Not modeled') + '</b></p>' :
          '<p class="mt-kv"><span>KickTip win chance</span><b>' + esc(me) + ' ' + pct(pw) + '</b></p><span class="mt-bar" aria-hidden="true"><i data-w="' + Math.round(pw * 100) + '"></i></span>') +
        (ml ? '<p class="mt-kv"><span>Market line</span><b>' + esc(ml) + '</b></p>' : '<p class="mt-kv"><span>Market line</span><b class="mt-no">No market line yet</b></p>');
      $$('.mt-bar i[data-w]', box).forEach(function (i) { i.style.width = i.getAttribute('data-w') + '%'; i.removeAttribute('data-w'); });
    }).catch(function () { box.innerHTML = '<p class="mt-tag">Next game</p><p class="mt-dt">Could not load. Reload the page to try again.</p>'; });
  }

  /* ---------- the My teams section (home) ---------- */
  var root = null;
  function confs() { var m = {}, order = []; Object.keys(T).forEach(function (s) { var t = T[s]; if (!m[t.cs]) { m[t.cs] = { cs: t.cs, n: t.cn, teams: [] }; order.push(t.cs); } m[t.cs].teams.push(s); }); order.sort(function (a, b) { return m[a].n.localeCompare(m[b].n); }); order.forEach(function (c) { m[c].teams.sort(function (a, b) { return T[a].n.localeCompare(T[b].n); }); }); return { m: m, order: order }; }
  var edConf = null, edAll = false;
  function renderEditor() {
    var C = confs(); if (!edConf || !C.m[edConf]) { var first = draft.teams[0] || st.teams[0]; edConf = first && T[first] ? T[first].cs : 'big-12'; if (!C.m[edConf]) edConf = C.order[0]; }
    var cur = C.m[edConf], list = cur.teams.slice(), shown = edAll ? list : list.filter(function (s, i) { return i < 8 || draft.teams.indexOf(s) >= 0; });
    var full = draft.teams.length >= capNow;
    var h = '<div class="mt-card mt-ed"><h2 id="mteh" tabindex="-1">Choose your teams</h2><p class="mt-rule">Up to ' + capNow + ' teams, from any conference.</p>' +
      '<p class="mt-d">Their numbers show here, above the Top 12. Nothing is saved until you tap Save.</p>' +
      '<span class="mt-tag" aria-hidden="true">Conference</span><select id="mtconf" class="mt-sel" aria-label="Conference">' + C.order.map(function (c) { return '<option value="' + esc(c) + '"' + (c === edConf ? ' selected' : '') + '>' + esc(C.m[c].n) + '</option>'; }).join('') + '</select>' +
      '<div class="mt-chips" role="group" aria-label="' + esc(cur.n) + ' teams">' + shown.map(function (s) {
        var on = draft.teams.indexOf(s) >= 0, dis = full && !on;
        return '<button type="button" class="mt-chip" data-t="' + s + '" aria-pressed="' + on + '"' + (dis ? ' aria-disabled="true"' : '') + '>' + logo(s, 24) + '<span>' + esc(T[s].n) + '</span></button>';
      }).join('') + (list.length > shown.length || edAll ? '<button type="button" class="mt-chip mt-more" data-more aria-expanded="' + edAll + '">' + (edAll ? 'Show fewer' : 'Show all ' + list.length) + '</button>' : '') + '</div>' +
      '<p class="mt-count" data-mtstatus role="status" aria-live="polite">' + esc(status || (draft.teams.length + ' of ' + capNow + ' chosen')) + '</p>' + W.KTMyTeams.extra();
    if (draft.teams.length) {
      h += '<h3 class="mt-h3">Your teams and headline numbers</h3><ul class="mt-yl">' + draft.teams.map(function (s) {
        var t = T[s], cur = draft.lead[s] || defLead(s);
        var opts = LEADS.filter(function (x) { return t[x[0]] !== null && t[x[0]] !== undefined; });
        return '<li><span class="mt-yn">' + logo(s, 24) + '<b>' + esc(t.n) + '</b></span><select id="mtl-' + s + '" class="mt-sel mt-ls2" data-lead="' + s + '" aria-label="Headline number for ' + esc(t.n) + '">' +
          opts.map(function (x) { return '<option value="' + x[0] + '"' + (x[0] === cur ? ' selected' : '') + '>' + x[1] + '</option>'; }).join('') + '</select>' +
          '<button type="button" class="mt-rm" data-rm="' + s + '" aria-label="Remove ' + esc(t.n) + ' from my choices"><span aria-hidden="true">\u00D7</span></button></li>';
      }).join('') + '</ul><p class="ccgdef">CCG = conference championship game</p>';
    }
    h += '<div class="mt-act"><button type="button" class="mt-save" data-save' + (draft.teams.length ? '' : ' aria-disabled="true"') + '>Save</button>' + (st.teams.length || editing ? '<button type="button" class="mt-cancel" data-cancel>Cancel</button>' : '') + '</div>' + SAVE_HTML + (noStore ? noStoreNote() : '') + '</div>';
    root.innerHTML = h;
  }
  function noStoreNote() { return '<p class="mt-warn" role="status">This browser is blocking storage, so your teams will not be remembered after this page view.</p>'; }
  function renderStrip() {
    var n = st.teams.length, any = st.teams.some(function (s) { return leadOf(s) === 'c'; });
    var cards = st.teams.filter(known).map(function (s) {
      var t = T[s], l = leadOf(s), v = t[l];
      return '<article class="mt-c" aria-label="' + esc(t.n) + '" data-t="' + s + '"><div class="mt-ch">' + logo(s, 34) + '<h3>' + esc(t.n) + '</h3></div>' +
        '<p class="mt-tag mt-lt">' + LEADNAME[l] + '</p><p class="mt-n">' + pct(v) + '</p><div class="mt-x"><p class="mt-tag">Next game</p><p class="mt-dt">Loading</p></div>' +
        '<div class="mt-lk"><a class="mt-b" href="' + href('/team/' + s + '/') + '">Open team page<span class="vh"> for ' + esc(t.n) + '</span></a><a class="mt-b mt-b2" href="' + href('/team/' + s + '/#rootables') + '">Rootables<span class="vh"> for ' + esc(t.n) + '</span></a></div></article>';
    }).join('');
    var h = '<div class="mt-hd"><h2 id="mth" tabindex="-1">My teams</h2><div class="mt-ac"><button type="button" class="mt-pb" data-edit>Edit teams</button>' +
      (clearAsk ? '' : '<button type="button" class="mt-lkb" data-clear>Clear</button>') + '</div></div>' +
      '<p class="mt-sub">' + n + ' of ' + capNow + ' teams \u00B7 Information only, not betting advice.</p>' + W.KTMyTeams.extra() +
      (clearAsk ? '<div class="mt-ask" role="alertdialog" aria-labelledby="mtca"><p id="mtca">Remove all ' + n + ' teams and your headline-number choices from this device?</p><div class="mt-act"><button type="button" class="mt-pb mt-danger" data-clear-yes>Yes, clear</button><button type="button" class="mt-pb" data-clear-no>Keep them</button></div></div>' : '') +
      (any ? '<p class="ccgdef">CCG = conference championship game</p>' : '') +
      '<div class="mt-scr" role="region" aria-label="My teams. Scroll sideways to see all ' + n + '." tabindex="0">' + cards + '</div>' +
      '<p class="mt-count vh" data-mtstatus role="status" aria-live="polite">' + esc(status) + '</p>' + (noStore ? noStoreNote() : '');
    root.innerHTML = '<div class="mt-wrap">' + h + '</div>';
    $$('.mt-c', root).forEach(function (c) { fillNext(c, c.getAttribute('data-t'), info.model); });
  }
  function href(p) { return info.model && info.model !== info.def ? p.replace(/(#.*)?$/, function (m) { return '?model=' + info.model + (m || ''); }) : p; }
  function renderHome() {
    var sec = $('#my-teams'); if (!sec || !T) return; root = $('#mt-root', sec); sec.hidden = false;
    if (!st.teams.length && !editing) { editing = true; draft = { teams: [], lead: {} }; }   /* empty state is the editor (mockup B1); nothing is stored by showing it */
    if (editing) { if (!draft) draft = { teams: st.teams.slice(), lead: JSON.parse(JSON.stringify(st.lead)) }; renderEditor(); } else renderStrip();
    root.insertAdjacentHTML('beforeend', '<p class="rn s mt-pv">' + esc(PRIV_SHORT) + ' <a href="/privacy/">Privacy</a></p>');   /* the SHORT cookie line (one place: src/privacy_copy.py) + the privacy page link */
    $$('[data-w]', root).forEach(function (i) { i.style.width = i.getAttribute('data-w') + '%'; i.removeAttribute('data-w'); });
  }
  function focusHd(id) { var e = $(id); if (e) e.focus(); }
  function renderAll() { badge(); teamSave(); if (T) { listStars(); renderHome(); } }

  /* ---------- events on the section (delegated; one listener set) ---------- */
  function bind() {
    var sec = $('#my-teams'); if (!sec || sec.hasAttribute('data-bound')) return; sec.setAttribute('data-bound', '1');
    sec.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || !sec.contains(b)) return;
      if (b.hasAttribute('data-edit')) { editing = true; draft = { teams: st.teams.slice(), lead: JSON.parse(JSON.stringify(st.lead)) }; status = ''; renderHome(); focusHd('#mteh'); return; }
      if (b.hasAttribute('data-clear')) { clearAsk = true; renderHome(); var y = $('[data-clear-yes]', sec); if (y) y.focus(); return; }
      if (b.hasAttribute('data-clear-no')) { clearAsk = false; renderHome(); focusHd('[data-clear]'); return; }
      if (b.hasAttribute('data-clear-yes')) { clearAll(); status = 'Cleared My teams.'; renderHome(); focusHd('#mteh'); return; }
      if (b.hasAttribute('data-cancel')) { editing = false; draft = null; status = ''; renderHome(); focusHd('[data-edit]'); return; }
      if (b.hasAttribute('data-more')) { edAll = !edAll; renderHome(); var m = $('[data-more]', sec); if (m) m.focus(); return; }
      if (b.hasAttribute('data-rm')) { var s = b.getAttribute('data-rm'); draft.teams = draft.teams.filter(function (x) { return x !== s; }); delete draft.lead[s]; status = ''; renderHome(); focusHd('#mteh'); return; }
      if (b.classList.contains('mt-chip') && b.hasAttribute('data-t')) {
        var t = b.getAttribute('data-t'), i = draft.teams.indexOf(t);
        if (i >= 0) { draft.teams.splice(i, 1); delete draft.lead[t]; status = ''; }
        else if (draft.teams.length >= capNow) { status = capMsg(); var cs = $('.mt-count', sec); if (cs) cs.innerHTML = capHtml(); return; }
        else { draft.teams.push(t); draft.lead[t] = defLead(t); status = ''; }
        renderHome(); var again = $('.mt-chip[data-t="' + t + '"]', sec); if (again) again.focus(); return;
      }
      if (b.hasAttribute('data-save')) {
        if (b.getAttribute('aria-disabled') === 'true') return;
        st = { teams: draft.teams.slice(), lead: cleanLead(draft.lead, draft.teams) };
        var ok = persist(); editing = false; draft = null; status = ok ? 'Saved ' + st.teams.length + (st.teams.length === 1 ? ' team.' : ' teams.') : 'Saved for this page view only.'; changed(); focusHd('#mth'); return;
      }
    });
    sec.addEventListener('change', function (e) {
      var s = e.target; if (!draft) return;
      if (s.id === 'mtconf') { edConf = s.value; edAll = false; renderHome(); focusHd('#mtconf'); return; }
      if (s.hasAttribute('data-lead')) { draft.lead[s.getAttribute('data-lead')] = s.value; }
    });
  }

  W.addEventListener('storage', function (e) { if (!acct && (e.key === KT || e.key === KL)) { load(); renderAll(); } });
  D.addEventListener('kt:render', function (e) { var d = e.detail || {}; T = d.T || T; info = { model: d.model, def: d.def }; bind(); renderAll(); });
  load(); badge(); teamSave();
})();
