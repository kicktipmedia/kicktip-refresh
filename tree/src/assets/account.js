/* KickTip account UI (phase 2): header Sign in / account chip, sign-in sheet, account menu, merge confirm, delete confirm. Vanilla JS, no third-party script of any kind.
   The "Sign in with Google" control is a plain same-origin link to /api/auth/google/start (a full-page navigation; Google's page then redirects back). No request leaves this site until that tap.
   Nothing is stored before sign-in. After sign-in, one device flag (kicktip_acct = first letter of the name, to draw the header chip without a flash) and, if the person taps Not now, one 14-day snooze (kicktip_nudge).
   While signed in, My teams reads and writes the account (window.KTMyTeams.useAccount); the on-device keys are left exactly as they were and come back on sign-out. */
(function () {
  'use strict';
  var D = document, W = window, MT = W.KTMyTeams; if (!MT) return;
  var HK = 'kicktip_acct', NK = 'kicktip_nudge', DAY = 86400000, CAPA = 50;
  var BANNER = '__BANNER_INNER__', SIGNIN = '__SIGNIN_HTML__', PRIVACY = '__PRIVACY_LINE__';
  var me = null, cfg = null, ov = null, opener = null, menuOpen = false, chain = Promise.resolve(), pendingLocal = [];
  var GLOGO = '<svg class="ac-glogo" width="20" height="20" viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return [].slice.call((r || D).querySelectorAll(s)); }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function api(method, path, body) {
    var o = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    return fetch(path, o).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { status: r.status, ok: r.ok, j: j }; }); });
  }
  function lsGet(k) { try { return W.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { W.localStorage.setItem(k, v); } catch (e) { /* refused: the header chip simply waits for the session check */ } }
  function lsDel(k) { try { W.localStorage.removeItem(k); } catch (e) { /* nothing to remove */ } }
  function snoozed() { try { var o = JSON.parse(lsGet(NK) || 'null'); return !!(o && o.v === 1 && Date.now() - o.t < 14 * DAY); } catch (e) { return false; } }
  function device() { try { return W.matchMedia('(pointer:coarse)').matches ? 'phone' : 'computer'; } catch (e) { return 'device'; } }
  function refresh() { var g = MT.get(); MT.set(g.teams, g.lead, false); }

  /* ---------- header ---------- */
  function header() {
    var nav = $('.nav'); if (!nav) return; var el = $('.ac-hd', nav);
    if (!el) { el = D.createElement('span'); el.className = 'ac-hd'; nav.appendChild(el); }
    if (!me) { el.innerHTML = '<button type="button" class="ac-si" data-acct="open">Sign in</button>'; return; }
    el.innerHTML = '<button type="button" class="ac-chip" data-acct="menu" aria-haspopup="true" aria-expanded="' + menuOpen + '" aria-controls="ac-menu" aria-label="Account menu"><span class="ac-in" aria-hidden="true">' + esc(me.initial || '?') + '</span><span class="ac-cl" aria-hidden="true">Account</span></button>';
  }
  function menu() {
    closeMenu(); var chip = $('.ac-chip'); if (!chip) return;
    var m = D.createElement('div'); m.id = 'ac-menu'; m.className = 'ac-menu'; m.setAttribute('role', 'group'); m.setAttribute('aria-label', 'Account');
    var n = MT.get().teams.length;
    m.innerHTML = '<p class="ac-k">Signed in as</p><p class="ac-em">' + esc(me.email) + '</p><p class="ac-row"><span>Saved teams</span><b>' + n + ' of ' + CAPA + '</b></p><a class="ac-it" href="/#my-teams">My teams</a><button type="button" class="ac-it" data-acct="signout">Sign out</button><button type="button" class="ac-it ac-dng" data-acct="delete">Delete my account</button>';
    D.body.appendChild(m); menuOpen = true; chip.setAttribute('aria-expanded', 'true');
    var r = chip.getBoundingClientRect(), w = Math.min(300, W.innerWidth - 16); m.style.width = w + 'px'; m.style.top = Math.round(r.bottom + 6) + 'px'; m.style.left = Math.max(8, Math.min(W.innerWidth - w - 8, Math.round(r.right - w))) + 'px'; m.style.top = Math.max(8, Math.min(Math.round(r.bottom + 6), W.innerHeight - m.offsetHeight - 8)) + 'px';   /* short windows: keep the whole menu on screen */
    var first = $('.ac-it', m); if (first) first.focus();
  }
  function closeMenu(refocus) { var m = $('#ac-menu'); if (m) m.remove(); menuOpen = false; var chip = $('.ac-chip'); if (chip) { chip.setAttribute('aria-expanded', 'false'); if (refocus) chip.focus(); } }

  /* ---------- dialog shell (one overlay, banner on top, focus trap, Esc, close X) ---------- */
  function shell() {
    if (ov) return ov; ov = D.createElement('div'); ov.className = 'ac-ov'; ov.hidden = true; D.body.appendChild(ov);
    ov.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return; var f = $$('a[href], button:not([disabled]), select, input, [tabindex="0"]', ov).filter(function (x) { return x.offsetParent !== null || x === D.activeElement; }); if (!f.length) return;
      var a = D.activeElement, i = f.indexOf(a);
      if (e.shiftKey && (i <= 0)) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
    });
    ov.addEventListener('click', function (e) { if (e.target === ov) closeDialog(); });
    return ov;
  }
  function inertBg(on) { [].forEach.call(D.body.children, function (c) { if (c === ov || c.tagName === 'SCRIPT') return; if (on) { c.setAttribute('inert', ''); c.setAttribute('data-ac-inert', '1'); } else if (c.getAttribute('data-ac-inert')) { c.removeAttribute('inert'); c.removeAttribute('data-ac-inert'); } }); }
  function openDialog(html, focusSel) {
    closeMenu(); shell(); opener = opener || D.activeElement;
    ov.innerHTML = '<div class="ac-sheet" role="dialog" aria-modal="true" aria-labelledby="ac-t"><div class="ac-bn" role="note">' + BANNER + '</div><div class="ac-card"><button type="button" class="ac-x" data-acct="close" aria-label="Close"><span aria-hidden="true">\u00D7</span></button>' + html + '</div></div>';
    ov.hidden = false; inertBg(true); D.documentElement.classList.add('ac-lock');
    var f = $(focusSel || '.ac-x', ov); if (f) f.focus();
  }
  function closeDialog() {
    if (!ov || ov.hidden) return; ov.hidden = true; ov.innerHTML = ''; inertBg(false); D.documentElement.classList.remove('ac-lock');
    var o = opener; opener = null; if (o && D.body.contains(o) && o.offsetParent !== null && o.focus) o.focus(); else { var any = [$('.ac-si'), $('.ac-chip'), $('#kh-btn')].filter(function (x) { return x && x.offsetParent !== null; })[0]; if (any) any.focus(); }   /* sticky header: below 760px the Sign in control sits in the closed Menu panel, so focus returns to the Menu button */
  }

  /* ---------- sign-in sheet (A1 default, A1b focus, A6 error) ---------- */
  function signInSheet(err) {
    var r = encodeURIComponent(W.location.pathname || '/');
    openDialog('<h2 id="ac-t">Keep My teams on every device</h2><p class="ac-p">Sign in to open your saved teams on your phone, tablet or computer.</p>' +
      (err ? '<p class="ac-err" role="alert"><span aria-hidden="true">!</span> Sign-in did not finish. Your teams are still saved on this device.</p>' : '') +
      '<div class="ac-gw" data-gw><a class="ac-g" href="/api/auth/google/start?r=' + r + '">' + GLOGO + '<span>Sign in with Google</span></a>' + SIGNIN + '</div>' +
      '<button type="button" class="ac-nn" data-acct="notnow">Not now</button><p class="ac-cap">Keep it on this device only. \u201CNot now\u201D asks again in 14 days.</p>' +
      '<p class="rn s ac-fine">We store your Google account id, your email and your followed teams and headline-number choices until you delete your account. ' + esc(PRIVACY) + ' <a href="/privacy/">Privacy</a></p>', '.ac-g');
    if (cfg === null) probe().then(function () { if (cfg === false) soon(); }); else if (cfg === false) soon();
  }
  function soon() { var gw = $('[data-gw]', ov || D); if (gw) { gw.innerHTML = '<p class="ac-soon" role="status">Sign-in is coming soon. My teams already works on this device without it.</p>'; var x = $('.ac-x', ov); if (x) x.focus(); } }
  function probe() { return api('GET', '/api/auth/session').then(function (r) { cfg = !!(r.j && r.j.configured); return r.j; }, function () { return null; }); }

  /* ---------- merge confirm (A4, for teams) ---------- */
  function mergeSheet(local, server) {
    var room = CAPA - server.teams.length, add = local.teams.slice(0, Math.max(0, room)), names = MT.names(add);
    if (!add.length) { MT.say('Your account already holds ' + CAPA + ' teams. Remove one to add another.'); return; }
    openDialog('<h2 id="ac-t">Add the ' + add.length + (add.length === 1 ? ' team' : ' teams') + ' from this ' + device() + '?</h2><p class="ac-p">They will be saved to your account so you can open them on any device. They also stay on this ' + device() + '.</p>' +
      '<ul class="ac-ul">' + names.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>' + (local.teams.length > add.length ? '<p class="ac-p">An account holds up to ' + CAPA + ' teams, so only the first ' + add.length + ' fit.</p>' : '') +
      '<div class="ac-act"><button type="button" class="ac-pri" data-acct="merge-yes">Add</button><button type="button" class="ac-nn" data-acct="merge-no">Not now</button></div>' +
      '<p class="ac-cap">\u201CNot now\u201D keeps them on this ' + device() + '. You can add them later from My teams.</p>', '.ac-pri');
    ov.__merge = { add: add, local: local, server: server };
  }
  function doMerge() {
    var m = ov && ov.__merge; if (!m) return; var teams = m.server.teams.concat(m.add), lead = {};
    m.server.teams.forEach(function (s) { if (m.server.lead[s]) lead[s] = m.server.lead[s]; }); m.add.forEach(function (s) { if (m.local.lead[s]) lead[s] = m.local.lead[s]; });
    var btn = $('.ac-pri', ov); if (btn) { btn.setAttribute('aria-disabled', 'true'); btn.textContent = 'Adding'; }
    api('PUT', '/api/teams', { teams: teams, lead: lead }).then(function (r) {
      if (r.status === 401) { closeDialog(); signedOut('You were signed out. Your teams on this device are shown.'); return; }
      if (!r.ok) { closeDialog(); MT.say(failMsg(r)); return; }
      closeDialog(); pendingLocal = []; MT.useAccount(acctFor(r.j)); MT.say('Added ' + m.add.length + (m.add.length === 1 ? ' team' : ' teams') + ' to your account.');
    }, function () { closeDialog(); MT.say(failMsg({ status: 0 })); });
  }

  /* ---------- delete confirm ---------- */
  function deleteSheet() {
    openDialog('<h2 id="ac-t">Delete your account?</h2><p class="ac-p">This removes your email, your followed teams and your headline-number choices from our server. Teams saved on this device stay.</p>' +
      '<div class="ac-act"><button type="button" class="ac-pri ac-danger" data-acct="delete-yes">Yes, delete my account</button><button type="button" class="ac-nn" data-acct="close">Keep my account</button></div><p class="ac-msg" role="status" data-ac-msg></p>', '.ac-nn');
  }
  function doDelete() {
    var b = $('.ac-danger', ov); if (b) { b.setAttribute('aria-disabled', 'true'); }
    api('POST', '/api/account/delete').then(function (r) {
      if (r.ok) { closeDialog(); signedOut('Your account was deleted. Teams saved on this device are shown.'); return; }
      var m = $('[data-ac-msg]', ov); if (b) b.removeAttribute('aria-disabled');
      if (m) m.textContent = r.status === 429 ? 'Too many delete requests today. Try again tomorrow.' : r.status === 401 ? 'You are already signed out.' : 'Could not delete the account. Try again.';
      if (r.status === 401) { closeDialog(); signedOut('You were signed out. Your teams on this device are shown.'); }
    }, function () { var m = $('[data-ac-msg]', ov); if (b) b.removeAttribute('aria-disabled'); if (m) m.textContent = 'Could not reach KickTip. Check your connection and try again.'; });
  }

  /* ---------- session state ---------- */
  function failMsg(r) { return r.status === 429 ? 'You have saved a lot in a short time. Try again in an hour.' : r.status === 409 ? 'An account keeps up to ' + CAPA + ' teams. Remove one to add another.' : 'Could not save to your account. Your list was reloaded from your account.'; }
  function acctFor(j) { return { cap: j.cap || CAPA, teams: j.teams || [], lead: j.lead || {}, save: function (teams, lead) {
    chain = chain.then(function () { return api('PUT', '/api/teams', { teams: teams, lead: lead }); }).then(function (r) {
      if (r.status === 401) { signedOut('You were signed out. Your teams on this device are shown.'); return; }
      if (!r.ok) { MT.say(failMsg(r)); return loadServer().then(function (s) { if (s) MT.useAccount(acctFor(s)); }); }
    }, function () { MT.say('Could not reach KickTip. Your change is shown here but not saved to your account yet.'); });
    return chain;
  } }; }
  function loadServer() { return api('GET', '/api/teams').then(function (r) { return r.ok ? r.j : null; }, function () { return null; }); }
  function setMe(j) { me = j && j.signedIn ? { email: j.email, name: j.name, initial: j.initial } : null; if (me) lsSet(HK, JSON.stringify({ v: 1, i: me.initial })); else lsDel(HK); header(); }
  function signedOut(message) { me = null; lsDel(HK); closeMenu(); MT.leaveAccount(); header(); if (message) MT.say(message); }
  function enter(first) {   /* signed in: show the account's list; offer the merge when this device has teams the account lacks */
    return loadServer().then(function (s) {
      if (!s) { MT.say('Could not load your account\u2019s teams. Your teams on this device are shown.'); return; }
      var local = MT.readLocal(); MT.useAccount(acctFor(s));
      pendingLocal = local.teams.filter(function (t) { return s.teams.indexOf(t) < 0; });
      if (pendingLocal.length && first) { opener = null; mergeSheet(local, s); } else refresh();
    });
  }
  function check() {
    return api('GET', '/api/auth/session').then(function (r) { cfg = !!(r.j && r.j.configured); setMe(r.j); return !!me; }, function () { return false; });
  }

  /* ---------- wiring ---------- */
  MT.nudge = function () { return me || cfg === false ? '' : ' <button type="button" class="mt-lkb mt-inl" data-acct="open">Sign in to keep up to ' + CAPA + '.</button>'; };
  MT.extra = function () {
    if (me) {
      var add = pendingLocal.length ? ' <button type="button" class="mt-lkb" data-acct="merge">Add the ' + pendingLocal.length + ' from this ' + device() + '</button>' : '';
      return '<p class="mt-sub mt-acl">Saved to your account (' + esc(me.email) + ').' + add + ' <button type="button" class="mt-lkb" data-acct="signout">Sign out</button> <button type="button" class="mt-lkb" data-acct="delete">Delete my account</button></p>';
    }
    if (cfg === false || snoozed() || !MT.get().teams.length) return '';
    return '<p class="mt-sub mt-acl">Keep these on every device. <button type="button" class="mt-lkb" data-acct="open">Sign in</button></p>';
  };
  D.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-acct]') : null; if (!b) { if (menuOpen && (!e.target.closest('#ac-menu') || e.target.closest('#ac-menu a')) && !e.target.closest('.ac-chip')) closeMenu(); return; }
    var a = b.getAttribute('data-acct');
    if (a === 'open') { opener = b; signInSheet(false); }
    else if (a === 'close') closeDialog();
    else if (a === 'notnow') { lsSet(NK, JSON.stringify({ v: 1, t: Date.now() })); closeDialog(); refresh(); }
    else if (a === 'menu') { if (menuOpen) closeMenu(true); else menu(); }
    else if (a === 'signout') {
      api('POST', '/api/auth/logout').then(function (r) { if (r.ok) signedOut('Signed out. Teams saved on this device are shown.'); else MT.say('Could not sign out. Try again.'); }, function () { MT.say('Could not reach KickTip. You are still signed in.'); });
    }
    else if (a === 'delete') { opener = b.closest('#ac-menu') ? $('.ac-chip') : b; deleteSheet(); }
    else if (a === 'delete-yes') doDelete();
    else if (a === 'merge') { opener = b; var s = { teams: MT.get().teams, lead: MT.get().lead }; mergeSheet(MT.readLocal(), s); }
    else if (a === 'merge-yes') doMerge();
    else if (a === 'merge-no') { closeDialog(); refresh(); }
  });
  D.addEventListener('keydown', function (e) { if (e.key === 'Escape' && ov && !ov.hidden) { e.preventDefault(); closeDialog(); return; } if (e.key === 'Escape' && menuOpen) { e.preventDefault(); closeMenu(true); } });
  D.addEventListener('focusin', function (e) { if (menuOpen && !e.target.closest('#ac-menu') && !e.target.closest('.ac-chip')) closeMenu(); });

  var q = ''; try { q = new URLSearchParams(W.location.search).get('signin') || ''; } catch (e) { /* old browser */ }
  var hint = null; try { hint = JSON.parse(lsGet(HK) || 'null'); } catch (e) { hint = null; }
  if (hint && hint.v === 1 && typeof hint.i === 'string') me = { email: '', name: '', initial: hint.i.slice(0, 1) };
  header();
  if (q) { try { var u = new URL(W.location.href); u.searchParams.delete('signin'); W.history.replaceState(null, '', u.pathname + u.search + u.hash); } catch (e) { /* leave the URL */ } }
  if (q === 'ok') check().then(function (ok) { if (ok) enter(true); else signInSheet(true); });
  else if (q === 'error' || q === 'cancelled') { me = null; header(); probe().then(function () { signInSheet(true); }); }
  else if (me) check().then(function (ok) { if (ok) enter(false); else { header(); } });
})();
