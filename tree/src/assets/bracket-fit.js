/* KickTip /playoff/ only: "Fit to screen" bracket view, remembered, plus the game sheet.
   Three views (Fit to screen is offered up to 1100 px wide; at 1101 px and up the page is exactly the plain full bracket): Full bracket (default, stores nothing), Fit to screen (key kt-bracket-view = fit), By round (= rounds). Storage may be unavailable: every access is try/catch and the choice then lasts for this visit only.
   Fit scales the whole bracket to the box (never above 1x). Below MIN (0.65x, team names under about 12 px: portrait phones) a Fit choice shows the existing stacked By round view instead and says so; it re-checks on resize and orientation change.
   In Fit each game card is one button that opens a sheet with both teams at full size and their team-page links. kt.js is not changed: this file adds its own button and listens in the capture phase so it sees the Full / By round clicks first.
   No inline style attributes (CSP style-src 'self'): CSS variables are set with el.style.setProperty. Nothing here changes bracket numbers, seeds or the bracket logic. */
(function () {
  'use strict';
  var D = document, W = window, KEY = 'kt-bracket-view', MIN = 0.65;
  var bt = D.querySelector('[data-bkt]'), w = D.querySelector('#bracket .bkw'), bk = w && w.querySelector('.bk'), hint = D.querySelector('#bracket .bkh');
  if (!bt || !w || !bk) return;
  var card = w.parentNode, narrow = W.matchMedia ? W.matchMedia('(max-width:700px)') : { matches: false }, wide = W.matchMedia ? W.matchMedia('(min-width:1101px)') : { matches: false };   /* wide = kt.css shows the whole bracket and no toggle: this file changes nothing there */
  var REGION = w.getAttribute('aria-label') || '';
  var TIPS = { fit: 'Tap or click a game for its details.', rounds: 'Phones held upright use the stacked By round view, so the text stays readable. Turn your phone sideways, or use a wider window, to see the whole bracket.' };

  function getPref() { try { var v = W.localStorage.getItem(KEY); return v === 'fit' || v === 'rounds' ? v : 'full'; } catch (e) { return 'full'; } }
  function setPref(v) { try { if (v === 'fit' || v === 'rounds') W.localStorage.setItem(KEY, v); else W.localStorage.removeItem(KEY); } catch (e) { /* storage unavailable: this visit only */ } }
  var pref = getPref(), eff = 'full', lastW = -1, lastH = -1, raf = 0;
  function effNow() { return wide.matches ? 'full' : (pref === 'fit' && scaleNow() < MIN ? 'rounds' : pref); }   /* 1101 px and up: always the plain full bracket (the saved choice is kept for narrower screens) */

  /* ---- the Fit button and its note, added next to the two buttons kt.js owns ---- */
  var fb = D.createElement('button'); fb.type = 'button'; fb.className = 'bkb'; fb.setAttribute('data-bkfit', ''); fb.setAttribute('aria-pressed', 'false'); fb.textContent = 'Fit to screen';
  bt.insertBefore(fb, bt.children[1] || null);
  var note = D.createElement('p'); note.className = 'bkfn'; note.hidden = true; note.setAttribute('data-bkfnote', ''); bt.parentNode.insertBefore(note, bt.nextSibling);
  var vb = [].slice.call(bt.querySelectorAll('[data-bkview]'));
  bt.addEventListener('click', function (e) {   /* capture phase: runs before kt.js's own button handlers */
    var b = e.target.closest ? e.target.closest('button') : null; if (!b || !bt.contains(b)) return;
    if (b === fb) pref = 'fit'; else if (b.hasAttribute('data-bkview')) pref = b.getAttribute('data-bkview'); else return;
    setPref(pref); apply(true);
  }, true);

  /* ---- geometry ---- */
  function natW() { return narrow.matches ? 1104 : 1040; }   /* the bracket's natural width: 4 columns of 236 px (252 px up to 700 px wide) + 3 gaps of 32 px */
  function availW() { var cs = W.getComputedStyle(card); return card.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0); }
  function scaleNow() { var a = availW(); return a > 0 ? Math.min(1, a / natW()) : 1; }
  function num(s) { return String(Math.round(s * 1000) / 1000); }

  /* ---- game cards as buttons (Fit only) ---- */
  function games() { return [].slice.call(bk.querySelectorAll('.g')); }
  function labelOf(g) { return (g.getAttribute('aria-label') || (g.querySelector('.gl') || {}).textContent || 'Game') + '. Opens the game details.'; }
  function addBtns() {
    games().forEach(function (g) {
      var b = g.querySelector('.bkgo');
      if (!b) { b = D.createElement('button'); b.type = 'button'; b.className = 'bkgo'; b.setAttribute('aria-haspopup', 'dialog'); g.appendChild(b); }
      var t = labelOf(g); if (b.getAttribute('aria-label') !== t) b.setAttribute('aria-label', t);
      [].forEach.call(g.children, function (c) { if (c !== b) c.inert = true; });   /* the names and links inside are read through the button; the sheet has the real links */
    });
  }
  function dropBtns() {
    games().forEach(function (g) { var b = g.querySelector('.bkgo'); if (b) g.removeChild(b); [].forEach.call(g.children, function (c) { c.inert = false; c.removeAttribute('inert'); }); });
  }

  /* ---- view logic ---- */
  function setView(v) { w.setAttribute('data-view', v); bk.setAttribute('data-bk', v); }
  function layout() {   /* Fit geometry: set the variables, then measure the natural height at that width */
    var s = scaleNow(), n = s >= 1 ? '100%' : natW() + 'px';
    w.style.setProperty('--bkn', n); w.style.setProperty('--bks', num(s));
    var h = bk.offsetHeight; w.style.setProperty('--bkfh', Math.ceil(h * s) + 'px'); lastW = availW(); lastH = h;
  }
  function apply(force) {
    var want = wide.matches ? 'full' : pref, s = scaleNow(), next = effNow();
    var changed = next !== eff; eff = next;
    if (eff === 'fit') {
      if (!w.classList.contains('bkfit')) { w.classList.add('bkfit'); w.removeAttribute('tabindex'); }
      setView('full'); layout(); addBtns();
      w.setAttribute('aria-label', 'Playoff bracket, fitted to the screen. Each game opens its details.');
    } else {
      if (w.classList.contains('bkfit')) { w.classList.remove('bkfit'); w.setAttribute('tabindex', '0'); dropBtns(); ['--bkn', '--bks', '--bkfh'].forEach(function (p) { w.style.removeProperty(p); }); }
      closeSheet(false);
      if (changed || force || want !== 'full') { setView(eff === 'rounds' ? 'rounds' : 'full'); }
      w.setAttribute('aria-label', REGION);
    }
    if (hint) hint.hidden = eff !== 'full';
    fb.hidden = wide.matches; fb.setAttribute('aria-pressed', want === 'fit' ? 'true' : 'false');
    vb.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-bkview') === want ? 'true' : 'false'); });
    var tip = eff === 'fit' ? TIPS.fit : (want === 'fit' ? TIPS.rounds : ''); note.textContent = tip; note.hidden = !tip;
  }
  function soon() { if (raf) return; raf = W.requestAnimationFrame ? W.requestAnimationFrame(function () { raf = 0; if (availW() !== lastW || eff !== effNow()) apply(false); else if (eff === 'fit' && bk.offsetHeight !== lastH) layout(); }) : (apply(false), 0); }
  W.addEventListener('resize', soon);
  W.addEventListener('orientationchange', function () { soon(); W.setTimeout(function () { raf = 0; apply(false); }, 300); });   /* iOS reports the new size a moment late */
  if (narrow.addEventListener) narrow.addEventListener('change', soon);
  if (wide.addEventListener) wide.addEventListener('change', soon);
  if (W.ResizeObserver) { var ro = new W.ResizeObserver(soon); ro.observe(card); ro.observe(bk); }
  if (W.MutationObserver) {   /* kt.js fills team names after the data arrives: refresh labels and height */
    new W.MutationObserver(function (recs) {
      if (eff !== 'fit') return;
      for (var i = 0; i < recs.length; i++) { var t = recs[i].target; if (!(t.classList && t.classList.contains('bkgo')) && !(recs[i].addedNodes[0] && recs[i].addedNodes[0].className === 'bkgo') && !(recs[i].removedNodes[0] && recs[i].removedNodes[0].className === 'bkgo')) { addBtns(); soon(); return; } }
    }).observe(bk, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-label'] });
  }

  /* ---- the sheet ---- */
  var scrim = null, dlg = null, sbody, stitle, sround, sx, from = null;
  function build() {
    scrim = D.createElement('div'); scrim.className = 'bks-scrim'; scrim.hidden = true;
    scrim.innerHTML = '<div class="bks" role="dialog" aria-modal="true" aria-labelledby="bks-t" tabindex="-1"><div class="bks-h"><div><p class="bks-r" id="bks-r"></p><h2 id="bks-t"></h2></div><button type="button" class="bks-x" aria-label="Close game details">Close</button></div><div class="bks-b"></div>'
      + '<p class="bks-n">Percentages are each team\u2019s chance to make the 12 (model), not the chance of winning this game. KickTip does not publish playoff-game probabilities.</p></div>';
    D.body.appendChild(scrim); dlg = scrim.firstChild; sbody = dlg.querySelector('.bks-b'); stitle = dlg.querySelector('#bks-t'); sround = dlg.querySelector('#bks-r'); sx = dlg.querySelector('.bks-x');
    sx.addEventListener('click', function () { closeSheet(true); });
    scrim.addEventListener('click', function (e) { if (e.target === scrim) closeSheet(true); });
    scrim.addEventListener('keydown', function (e) {   /* Escape is handled once, by onDocKey on the document (this event bubbles up to it) */
      if (e.key !== 'Tab') return;
      var f = [].slice.call(dlg.querySelectorAll('a[href],button')).filter(function (x) { return x.offsetParent !== null; }); if (!f.length) return;
      var i = f.indexOf(D.activeElement);
      if (e.shiftKey && (i <= 0)) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && (i === f.length - 1 || i < 0 && D.activeElement === dlg)) { e.preventDefault(); f[0].focus(); }
    });
  }
  /* While the sheet is open: the page behind is inert and cannot scroll. Both are set with the DOM / CSSOM (no style attribute in the markup) and the previous state is put back exactly. */
  var lock = null;
  function onDocKey(e) { if ((e.key === 'Escape' || e.key === 'Esc') && scrim && !scrim.hidden) { e.preventDefault(); closeSheet(true); } }
  function pinPage() {
    if (lock) return;
    var root = D.documentElement, main = D.querySelector('main'), sbw = W.innerWidth - root.clientWidth;
    lock = { main: main && !scrim.contains(main) ? main : null, ov: root.style.overflow, pr: root.style.paddingRight, hadInert: false };
    if (lock.main) { lock.hadInert = lock.main.inert === true || lock.main.hasAttribute('inert'); lock.main.inert = true; }
    if (sbw > 0) root.style.paddingRight = (parseFloat(W.getComputedStyle(root).paddingRight) || 0) + sbw + 'px';   /* keep the layout width when the scrollbar goes away */
    root.style.overflow = 'hidden';
    D.addEventListener('keydown', onDocKey);
  }
  function releasePage() {
    if (!lock) return; var root = D.documentElement, l = lock; lock = null;
    D.removeEventListener('keydown', onDocKey);
    root.style.overflow = l.ov; root.style.paddingRight = l.pr; if (!root.getAttribute('style')) root.removeAttribute('style');
    if (l.main && !l.hadInert) { l.main.inert = false; l.main.removeAttribute('inert'); }
  }
  function openSheet(g, trigger) {
    if (!scrim) build();
    var rd = g.closest ? g.closest('.rd') : null, h3 = rd && rd.querySelector('h3'), gl = g.querySelector('.gl');
    sround.textContent = h3 ? h3.textContent : ''; stitle.textContent = gl ? gl.textContent : 'Game';
    while (sbody.firstChild) sbody.removeChild(sbody.firstChild);
    [].forEach.call(g.querySelectorAll('.sl'), function (sl) {
      var row = D.createElement('div'); row.className = 'bks-s' + (sl.classList.contains('bye') ? ' bye' : '') + (sl.classList.contains('ph') ? ' ph' : '');
      [].forEach.call(sl.childNodes, function (c) { var k = c.cloneNode(true); if (k.removeAttribute) { k.removeAttribute('inert'); k.removeAttribute('data-seed'); k.removeAttribute('data-win'); } row.appendChild(k); });
      sbody.appendChild(row);
    });
    from = trigger; scrim.hidden = false; pinPage(); dlg.scrollTop = 0; dlg.focus();
  }
  function closeSheet(refocus) {
    if (!scrim || scrim.hidden) return; scrim.hidden = true; releasePage(); var f = from; from = null;
    if (refocus && f && D.body.contains(f)) f.focus();
  }
  bk.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.bkgo') : null; if (!b || eff !== 'fit') return;
    openSheet(b.parentNode, b);
  });

  apply(false);
})();
