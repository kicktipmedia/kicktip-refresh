/* Ask KickTip: what-if panel. Everything runs in the visitor's browser: the parser, scenario resolver, season simulation (a Web Worker) and the answer text are scripts served from this site.
   Typed questions stay in the browser unless the visitor uses AI mode (aihome1; off by default, switched by /api/ask-config): with Use AI on, tapping Review sends only the typed text to /api/ask, and nothing else leaves the browser. Run-gate build (Oct 24, 2026): no disclaimer gate, no dialog, no stored acceptance. Opening the panel makes one /api/ask-config request and nothing else loads unless AI mode is on; the simulator, the what-if shards and the engine Worker load only when the person taps Run. The terms text under the Run button (src/terms_copy.py) is the acceptance: tapping Run accepts the terms.
   No inline script, no eval, same-origin requests only. */
(function () {
  'use strict';
  var D = document, main = D.getElementById('main'), pill = D.getElementById('kpill');
  if (!main || !pill) return;

  /* ---------- the Lab (lab1): shared pieces ----------
     Everything the home tile (pk.js) and the bottom sheet draw comes from here, so the two never drift. Exposed as window.KTLab. */
  var W = window, LABN = 'What If Lab by KickTip';   /* the product name, ONE constant: every place the JS draws the name (sheet title, Close label, home tile heading via KTLab.name) reads it. The static page markup reads the matching LABNAME in scripts/lab_html.py (apply-lab.py asserts the two are equal). Always with the shield; never one word. */
  var LABCREDIT = 'Logo created with Grok';   /* attribution line at the foot of the sheet (plain muted text, no link); its own constant, edit here only */
  var LABSUB = 'Rewrite the weekend. See the new playoff picture.';   /* approved subtitle (plain ASCII text, two sentences). Empty string = no subtitle is drawn anywhere. Nothing else to edit: no markup, no other file. */
  function okSlug(c) { return (typeof c === 'string' && /^[a-z0-9-]+$/.test(c)) ? c : ''; }   /* slugs (conference, team) are whitelisted before they reach a URL, an attribute or innerHTML; anything else is treated as 'none' */
  function poss(n) { return n + '\u2019s'; }
  function confForms(cs, cn) {   /* same wording as the old Big 12 title race tile: 'the Big 12', 'the American Conference', 'Conference USA' (no 'the') */
    var cu = cs === 'conference-usa', am = cs === 'american', cdn = am ? 'American Conference' : cn, cnl = cu ? cdn : 'the ' + cdn;
    return { cdn: cdn, cnl: cnl, cnp: cu ? poss(cdn) : 'the ' + poss(cdn), cna: cnl + (am || cu ? ' championship game simulator' : ' conference championship game simulator') };
  }
  function markA(h) {   /* logo A (AI art), decorative; h = 32 (sheet) or 48 (tile), both on the A3 art */
    if (h === 32) return '<img class="wl-mk" src="/assets/brand/lab/what-if-lab-A3-32.png" srcset="/assets/brand/lab/what-if-lab-A3-32.png 1x, /assets/brand/lab/what-if-lab-A3-72.png 2x, /assets/brand/lab/what-if-lab-A3-96.png 3x" width="25" height="32" alt="" aria-hidden="true" decoding="async">';
    if (h === 48) return '<img class="wl-mk" src="/assets/brand/lab/what-if-lab-A3-48.png" srcset="/assets/brand/lab/what-if-lab-A3-48.png 1x, /assets/brand/lab/what-if-lab-A3-96.png 2x, /assets/brand/lab/what-if-lab-A3-144.png 3x" width="37" height="48" alt="" aria-hidden="true" decoding="async">';
    var w = { 32: 25, 48: 37 }[h], d = { 32: 72, 48: 96 }[h], b = '/assets/brand/lab/what-if-lab-A-';
    return '<img class="wl-mk" src="' + b + h + '.png" srcset="' + b + h + '.webp 1x, ' + b + d + '.webp 2x" width="' + w + '" height="' + h + '" alt="" aria-hidden="true" decoding="async">';
  }
  function seg(p, mode) {
    function tb(m, t) { var on = mode === m; return '<button type="button" role="tab" class="wl-tb" id="' + p + '-t-' + m + '" aria-controls="' + p + '-p-' + m + '" aria-selected="' + (on ? 'true' : 'false') + '" tabindex="' + (on ? '0' : '-1') + '" data-wl-m="' + m + '">' + t + '</button>'; }
    return '<div class="wl-seg" role="tablist" aria-label="What if mode">' + tb('team', 'Team run') + tb('conf', 'Conference run') + '</div>';
  }
  function confCard(p, cs, cn) {
    cs = okSlug(cs);
    if (!cs) return '<div class="wl-who"><p class="wl-nm">Conference title race</p></div><p class="pt-cn" id="' + p + '-cn"><span>Choose the remaining games.</span> <span>Each conference uses its own rules.</span></p><button type="button" class="pt-cb" aria-disabled="true" aria-describedby="' + p + '-cn ' + p + '-hint">Run a What if for a conference</button><p class="wl-hint" id="' + p + '-hint">Choose a conference first.</p>';
    var f = confForms(cs, cn);
    return '<div class="wl-who">' + (W.KTLogo ? W.KTLogo.conf(cs, 24, true) : '') + '<p class="wl-nm">' + esc(f.cdn) + ' title race</p></div><p class="pt-cn" id="' + p + '-cn"><span>Choose the remaining games.</span> <span>Uses ' + esc(f.cnp) + ' own rules.</span></p><a class="pt-cb" href="/conference/' + esc(cs) + '/simulator/" aria-label="Run a What if for ' + esc(f.cna) + '" aria-describedby="' + p + '-cn">Run a What if for ' + esc(f.cnl) + '</a>';
  }
  function confPanel(p, cs, cn, confs, lm) {   /* lm = 'team' | 'conf' (the current mode) draws a tab panel; null = a fixed, single panel (conference pages) */
    cs = okSlug(cs);
    var sel = '', tp = lm ? ' id="' + p + '-p-conf" role="tabpanel" aria-labelledby="' + p + '-t-conf" data-wl-m="conf"' + (lm === 'conf' ? '' : ' hidden') : '';
    if (confs) sel = '<label class="wl-sl" for="' + p + '-cs">Conference</label><select class="wl-s" id="' + p + '-cs" data-wl-cs>' + (cs ? '' : '<option value="">Choose a conference</option>') +
      confs.filter(function (c) { return okSlug(c[0]); }).map(function (c) { return '<option value="' + esc(c[0]) + '" data-cn="' + esc(c[1]) + '"' + (c[0] === cs ? ' selected' : '') + '>' + esc(confForms(c[0], c[1]).cdn) + '</option>'; }).join('') + '</select>';
    return '<div class="wl-pn"' + tp + '>' + sel + '<div class="wl-cf" data-p="' + p + '">' + confCard(p, cs, cn) + '</div></div>';
  }
  var LAB = W.KTLab = { name: LABN, sub: LABSUB, mode: 'team', cs: undefined, cn: undefined, team: null, opener: null, markA: markA, seg: seg, confCard: confCard, confPanel: confPanel, confs: function () { return []; }, watch: watch,
    close: function (quiet) { if (panel && !panel.hidden) closePanel(quiet === true); } };
  function labMode(root, m, focus) {
    root.setAttribute('data-mode', m); LAB.mode = m;
    [].forEach.call(root.querySelectorAll('[role="tab"]'), function (t) { var on = t.getAttribute('data-wl-m') === m; t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1; if (on && focus) t.focus(); });
    [].forEach.call(root.querySelectorAll('[role="tabpanel"]'), function (pn) { pn.hidden = pn.getAttribute('data-wl-m') !== m; });
  }
  function labSync(from) {   /* the home tile and the sheet strip share one state (mode + conference): keep the one that is not being touched in step */
    [].forEach.call(D.querySelectorAll('.wl[data-mode]'), function (r) {
      if (r === from) return;
      if (r.querySelector('[role="tab"]')) labMode(r, LAB.mode, false);
      var sl = r.querySelector('[data-wl-cs]'), cf = r.querySelector('.wl-cf');
      if (sl && cf && LAB.cs !== undefined && sl.value !== LAB.cs) { sl.value = LAB.cs; cf.innerHTML = confCard(cf.getAttribute('data-p'), LAB.cs, LAB.cn); }
    });
  }
  D.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.wl [role="tab"]'); if (t) { labMode(t.closest('.wl'), t.getAttribute('data-wl-m'), false); labSync(t.closest('.wl')); return; }
    var d = e.target.closest && e.target.closest('.wl .pt-cb[aria-disabled="true"]'); if (d) { var sl = d.closest('.wl').querySelector('[data-wl-cs]'); if (sl) sl.focus(); }
  });
  D.addEventListener('keydown', function (e) {   /* arrow keys move between the two tabs (automatic activation) */
    var t = e.target.closest && e.target.closest('.wl [role="tab"]'); if (!t) return;
    var k = e.key, m = t.getAttribute('data-wl-m');
    if (k === 'ArrowRight' || k === 'ArrowLeft' || k === 'Home' || k === 'End') { e.preventDefault(); labMode(t.closest('.wl'), (k === 'Home' ? 'team' : k === 'End' ? 'conf' : m === 'team' ? 'conf' : 'team'), true); labSync(t.closest('.wl')); }
  });
  D.addEventListener('change', function (e) {
    var sl = e.target; if (!sl.matches || !sl.matches('[data-wl-cs]')) return;
    var cf = sl.closest('.wl').querySelector('.wl-cf'), o = sl.options[sl.selectedIndex], cn = o ? o.getAttribute('data-cn') : '';
    LAB.cs = sl.value; LAB.cn = cn; cf.innerHTML = confCard(cf.getAttribute('data-p'), sl.value, cn);
    var lv = D.getElementById('pk-live'); if (lv && sl.value) lv.textContent = o.text + ' selected.';
    labSync(sl.closest('.wl'));
  });
  /* the bottom bar hides while the Lab itself is on screen (home): one observer, re-pointed by pk.js after each repaint */
  var wio = null;
  function watch(el) {
    if (!('IntersectionObserver' in W)) return;
    if (wio) { wio.disconnect(); wio = null; }
    D.documentElement.classList.remove('wl-in'); return;   /* home6: the bottom bar stays up at all times */
    wio = new IntersectionObserver(function (es) { D.documentElement.classList.toggle('wl-in', es[es.length - 1].isIntersecting); }, { threshold: 0.35 });
    wio.observe(el);
  }
  function labStrip() {   /* the mode strip at the top of the sheet's start view */
    var pg = main.getAttribute('data-page') || '', P = 'ws', tm = LAB.team, home = pg === 'home', nm = '', slug = '', m;
    if (home && tm) { nm = tm.n; slug = okSlug(tm.s); }
    else if (pg === 'team') { nm = main.getAttribute('data-exa') || ''; m = /\/team\/([^\/]+)\//.exec(W.location.pathname); slug = m ? okSlug(m[1]) : ''; }
    var who = nm ? '<div class="wl-who">' + (slug && W.KTLogo ? W.KTLogo.team(slug, 24, true) : '') + '<p class="wl-nm">' + esc(nm) + '</p>' + (pg === 'home' || pg === 'team' ? '<a class="wl-ch" href="/#choose" data-pk-choose>' + (tm && tm.ex ? 'Choose your team' : 'Change team') + '</a>' : '') + '</div>' : '';
    if (home) {
      var lm = LAB.mode === 'conf' ? 'conf' : 'team';
      return '<div class="wl wl-sh" data-mode="' + lm + '">' + seg(P, lm) + '<div class="wl-pn" id="ws-p-team" role="tabpanel" aria-labelledby="ws-t-team" data-wl-m="team"' + (lm === 'team' ? '' : ' hidden') + '>' + who + '</div>' + confPanel(P, LAB.cs, LAB.cn, LAB.confs(), lm) + '</div>';
    }
    if (pg === 'conference') {
      var cs = okSlug(main.getAttribute('data-conf') || ''), h1 = D.querySelector('main h1'), cn = h1 ? h1.textContent.replace(/\s+race\s*$/i, '') : '';
      if (!cs || cs === 'independents') return '';   /* Independents have no conference race: no strip */
      return '<div class="wl wl-sh" data-mode="conf"><p class="wl-chip">Conference run</p>' + confPanel(P, cs, cn, null, null) + '</div>';
    }
    return '<div class="wl wl-sh" data-mode="team"><p class="wl-chip">Team run</p>' + (who ? '<div class="wl-pn">' + who + '</div>' : '') + '</div>';
  }
  var MKEY = 'kicktip_model', CHUNKS = 10, MINCH = 4, PER = 1000, BUDGET = 7000, SEED0 = 20261;
  function get(s, k) { try { return window[s].getItem(k); } catch (e) { return null; } }
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  /* The model is read, never written, here: ?model= in the URL first, then the pick the page stored (kicktip_model), else the KickTip blend. Unknown or retired values are ignored. */
  function RTX(k) { return '<div class="rtx' + (k === 'c' ? ' aion' : '') + '"><p class="rn rt1"><span class="rtpf">Tapping </span>Run accepts the terms <span class="rtnb">· <span class="rtk">KickTip is not</span><span class="rto">Not</span> a betting site </span>· <button type="button" class="rtt" data-rtt aria-expanded="false" aria-controls="rtp-' + k + '">Terms<span class="w2ch" aria-hidden="true"></span></button></p><p class="rwl">What If uses wins and losses only, not scores or&nbsp;margins.</p><div class="rtp" id="rtp-' + k + '" hidden><p class="rn rtai">' + esc(AI_SHORT) + '</p>' + '<p class="rn">Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></p>' + '<p class="lcr">' + LABCREDIT + '</p></div></div>'; }   /* whatif2b: one-line terms; tapping Run is still the acceptance */
  var AI_SHORT = "Your question is sent to Cloudflare's AI to read it. Numbers come from KickTip's simulator.";   /* B4f: same text as KTAI.SHORT, shown only inside the AI-on Terms panel */
  function rtFit() {   /* B4f: AI on, one line: largest size 13px..11px with the full wording, else the short wording */
    var L = D.querySelectorAll('.pnl .rtx.aion .rt1'), i, el, f, k, sz = [13, 12.5, 12, 11.5, 11], X = D.querySelectorAll('.pnl .rtx:not(.aion) .rt1');
    for (i = 0; i < X.length; i++) { if (X[i].style.fontSize) X[i].style.fontSize = ''; if (X[i].classList.contains('rsh')) X[i].classList.remove('rsh'); X[i].__rtk = null; }   /* B4f2: AI off = the B4b line, no fit size or short wording left behind */
    for (i = 0; i < L.length; i++) { el = L[i]; if (!el.offsetParent || !el.clientWidth) continue; var key = el.clientWidth + '|' + (el.parentNode && el.parentNode.className); if (el.__rtk === key) continue; el.__rtk = key;   /* only refit when the width or state changes: no style writes while typing or deleting */
      for (k = 0; k < 2; k++) { el.classList.toggle('rsh', k === 1); for (f = 0; f < sz.length; f++) { el.style.fontSize = sz[f] + 'px'; if (el.scrollWidth <= el.clientWidth) break; } if (f < sz.length) break; } }
  }
  var RUNTERMS = '<div class="rn rtg"><span class="rtg1">Tapping Run accepts the terms · </span><details class="rtgd"><summary>Terms<span class="w2ch" aria-hidden="true"></span></summary><p>Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></p></details></div>';   /* the FULL under-Run line, always on screen directly under the Run button (built from src/terms_copy.py) */
  var MODELS = { blend: 1, elo: 1, eff: 1 };
  function pickModel() {
    var q = ''; try { q = (new URLSearchParams(window.location.search).get('model') || '').toLowerCase(); } catch (e) { q = ''; }
    if (MODELS[q] === 1) return q;
    var v = get('localStorage', MKEY); return MODELS[v] === 1 ? v : 'blend';
  }

  var panel, scrim, bd, cmp, form, input, send, cnt, closeBtn, view = null;
  var S = { model: 'blend', M: {}, bundle: null, wi: null, scripts: null, worker: null, wid: 0, lastQ: '', choices: {}, parsed: null, res: null, busy: false, seedN: 0, adapt: null, pending: null };
  var shell = [D.querySelector('header.hd'), main, D.querySelector('footer.ft'), D.querySelector('.dsc'), D.querySelector('.src'), pill];
  function setInert(on) { shell.forEach(function (e) { if (e) { if (on) e.setAttribute('inert', ''); else e.removeAttribute('inert'); } }); D.documentElement.style.overflow = on ? 'hidden' : ''; lockScroll(on); }
  var dkP = false;   /* whatif1h: a collapse waiting for the field to lose focus / the keyboard to go down */
  function dkBusy() { if (!panel) return false; return D.activeElement === input || panel.classList.contains('kbf') || D.documentElement.classList.contains('kb-up'); }
  function dkSet(col) { dkP = false; if (col && dkBusy()) { dkP = true; dock(false); } else dock(col); }
  function dkBlur() { setTimeout(function () { if (!dkP || panel.hidden || !DKR[view] || cmp.contains(D.activeElement) || dkBusy()) return; dkP = false; dock(true); if (!D.activeElement || D.activeElement === D.body) dkBar.focus({ preventScroll: true }); }, 0); }
  var dkBar = null, dkOn = false, dkY = 0, DKR = { answer: 1, tb: 1, compare: 1 };   /* whatif1g: result views collapse the dock (phones) */
  function dock(col) { if (!dkBar) return; dkOn = !!col && isNarrow(); cmp.classList.toggle('dkc', dkOn); panel.classList.toggle('dkc-on', dkOn); dkBar.hidden = !dkOn; dkBar.setAttribute('aria-expanded', dkOn ? 'false' : 'true'); dkY = bd.scrollTop; }
  /* B5d: the page header (and the jump bar) are position:sticky. With the body fixed at -scrollY they lost their stuck place and scrolled away under the sheet, then popped back in at the top the moment the lock was released. While the Lab is open each stuck bar is held exactly where it was (position:fixed at the same top) with a same-height spacer in its flow slot, so the page under the sheet never changes and nothing appears at the top on close. */
  function pinSticky() { var out = []; [D.querySelector('header.hd'), D.querySelector('nav.kj')].forEach(function (e) { if (!e) return; var cs = W.getComputedStyle(e); if (cs.position !== 'sticky') return; var r = e.getBoundingClientRect(), st = parseFloat(cs.top) || 0; if (Math.abs(r.top - st) > 1 || r.bottom <= 0) return;
      var sp = D.createElement('div'); sp.setAttribute('aria-hidden', 'true'); sp.style.height = r.height + 'px'; sp.style.margin = cs.margin; e.parentNode.insertBefore(sp, e); var es = e.style; out.push({ e: e, sp: sp, css: es.cssText }); es.position = 'fixed'; es.top = st + 'px'; es.left = '0'; es.right = '0'; es.width = r.width + 'px'; es.marginTop = '0'; }); return out; }
  function unpinSticky(l) { (l || []).forEach(function (p) { p.e.style.cssText = p.css; if (!p.css) p.e.removeAttribute('style'); if (p.sp.parentNode) p.sp.parentNode.removeChild(p.sp); }); }
  var LK = null;   /* whatif1: iOS-safe scroll lock: body fixed at -scrollY while the Lab is open, exact scrollY restored on close */
  function lockScroll(on) { var de = D.documentElement, b = D.body, bs = b.style;
    if (on) { if (LK) return; LK = { y: W.pageYOffset || de.scrollTop || 0, pin: pinSticky() }; bs.position = 'fixed'; bs.top = -LK.y + 'px'; bs.left = '0'; bs.right = '0'; bs.width = '100%'; de.classList.add('kp-lock'); return; }
    if (!LK) return; var y = LK.y; unpinSticky(LK.pin); LK = null; bs.position = bs.top = bs.left = bs.right = bs.width = ''; if (!b.getAttribute('style')) b.removeAttribute('style'); de.classList.remove('kp-lock');
    de.classList.add('kp-rst'); var sb = de.style.scrollBehavior; de.style.scrollBehavior = 'auto'; W.scrollTo(0, y); de.style.scrollBehavior = sb; var RAF = W.requestAnimationFrame || setTimeout; RAF(function () { RAF(function () { de.classList.remove('kp-rst'); }); }); }   /* B5d: kp-rst = scroll restore in progress; the jump bar's show-on-scroll handler ignores scroll until 2 frames after it */

  /* ---------- panel shell ---------- */
  function build() {
    if (panel) return;
    scrim = D.createElement('div'); scrim.className = 'scrim'; scrim.hidden = true;
    panel = D.createElement('section'); panel.id = 'kp'; panel.className = 'pnl'; panel.hidden = true;
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true'); panel.setAttribute('aria-labelledby', 'kpt');
    panel.innerHTML = '<div class="hdp"><div><h2 id="kpt"><img class="kpi" src="/assets/brand/lab/what-if-lab-A3-32.png" srcset="/assets/brand/lab/what-if-lab-A3-32.png 1x, /assets/brand/lab/what-if-lab-A3-72.png 2x" width="25" height="32" alt="" aria-hidden="true"><span>' + LABN + '</span></h2><span class="lab">Simulation analysis</span></div><button type="button" class="cx" aria-label="Close ' + LABN + '">&times;</button></div>' +
      '<div class="bd" id="kbd" tabindex="-1" aria-live="polite"></div>' +
      '<div class="cmp"><form id="kform" autocomplete="off"><div class="fld"><label for="kask">Ask a what-if question</label><input id="kask" type="text" maxlength="300" placeholder="What if BYU wins out?" aria-describedby="kcnt"><span id="kcnt" class="cnt" aria-live="off">0/300</span></div><button class="snd" type="submit" aria-label="Run" disabled>Run</button></form><div class="kchs" role="group" aria-label="Example questions"><button type="button" class="kch" data-q="What if BYU wins out?">What if BYU wins out?</button><button type="button" class="kch" data-q="What if Utah drops one?">What if Utah drops one?</button><button type="button" class="kch" data-q="What if Boise State drops one?">What if Boise State drops one?</button></div>' + RTX('d') + '</div>';
    D.body.appendChild(scrim); D.body.appendChild(panel);
    bd = panel.querySelector('#kbd'); cmp = panel.querySelector('.cmp'); form = panel.querySelector('#kform'); input = panel.querySelector('#kask'); send = panel.querySelector('.snd'); cnt = panel.querySelector('#kcnt'); closeBtn = panel.querySelector('.cx');
    pill.setAttribute('aria-controls', 'kp');
    closeBtn.addEventListener('click', closePanel);
    scrim.addEventListener('click', closePanel);
    input.addEventListener('input', function () { cnt.textContent = input.value.length + '/' + cap(); var dis = !S.run && !input.value.trim(); if (send.disabled !== dis) send.disabled = dis; (W.requestAnimationFrame || setTimeout)(rbCaret); });   /* B4f: iOS drops the caret on backspace; re-set the same selection next frame (no blur, no value write) */
    form.addEventListener('submit', function (e) { e.preventDefault(); if (S.run) return; var t = input.value; if (!t.trim()) return; if (tbTry(t)) return; if (aiGate(t)) return; input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); });   /* aihome1 */
    bd.addEventListener('click', onBodyClick);
    cmp.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.kch'); if (!b) return; input.disabled = false; input.value = b.getAttribute('data-q'); cnt.textContent = input.value.length + '/' + cap(); send.disabled = false; fieldOn(true); });   /* whatif1: a chip only FILLS the box */
    cmp.id = 'kcmp'; dkBar = D.createElement('button'); dkBar.type = 'button'; dkBar.className = 'kdk'; dkBar.id = 'kdkb'; dkBar.hidden = true; dkBar.setAttribute('aria-expanded', 'true'); dkBar.setAttribute('aria-controls', 'kcmp');
    dkBar.innerHTML = '<span>Ask another what if</span><svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true" focusable="false"><path d="M5 14l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"></path></svg>'; cmp.insertBefore(dkBar, cmp.firstChild);
    dkBar.addEventListener('click', function () { dkP = false; dock(false); fieldOn(false); });
    input.addEventListener('blur', dkBlur);
    bd.addEventListener('scroll', function () { if (!DKR[view] || dkOn || D.activeElement === input || panel.classList.contains('kbf')) return; if (Math.abs(bd.scrollTop - dkY) > 24) dock(true); }, { passive: true });
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
    if (S.ai && S.ai.learn) { S.ai.learn = false; cnSync(); var cb = D.getElementById('kcnb'); if (cb) cb.focus(); return; }   /* compact1: Esc closes the notice first (keyboard path, focus to the control) */
    closePanel();
  });
  /* Phones: when the on-screen keyboard is up, lift the panel above it (and cap its height to what is visible) so the question box, Send and the terms line under them are never covered. CSSOM writes only (no inline style attribute in the HTML). */
  var FKR = 0, FKS = false;   /* whatif1e: rAF-throttled; with the keyboard up the sheet is sized and placed to the visual viewport (height = vv.height, top = vv.offsetTop) */
  function fitKeyboard() { if (CLW || CLG) return; if (OPG) { OPP = 1; return; } if (!FKR) FKR = (W.requestAnimationFrame || setTimeout)(fitNow); }   /* B5e: no refit while the sheet is opening (deferred to the end of the slide) or closing (the sheet is leaving; closeNow resets the keyboard state once it is hidden) */
  function RMQ() { return !!(W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function fitNow() {
    FKR = 0; var vv = window.visualViewport; if (!vv || !panel) return; if (CLG && !panel.hidden) return;   /* B5e: keyboard layout frozen while closing */
    /* B5e: removed the scrollTo(0,0) that undid iOS's focus pan. On iOS it fought the pan: iOS re-panned to keep the field visible, we scrolled back, every frame-or-two = the sheet and backdrop jittered (the keyboard-step flash). The sheet is placed at vv.offsetTop instead, so the pan is harmless; the backdrop bleeds past the viewport so nothing behind shows. */
    var kb = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop)), on = !panel.hidden && isNarrow() && kb > 80, ps = panel.style;
    var anc = (D.activeElement === input && input.getClientRects().length) ? input : panel, fl = on !== panel.classList.contains('kbf') && panel.classList.contains('kin') && !CLG && !CLW && !RMQ() ? anc.getBoundingClientRect().top : null; var KC = fl !== null && anc === panel ? D.getElementById('kcmp') : null, kc0 = KC && KC.getClientRects().length ? KC.getBoundingClientRect().top : null;   /* B5f: keyboard dropping with the field unfocused (run, chip remove): the composer is FLIPped too, so it does not snap from above the keyboard to the sheet bottom */   /* B5d: anchor = the field when it has focus, so the field (not just the sheet edge) moves once */
    if (!on && RVH) { RVH = false; bd.style.flex = ''; }   /* B5h: keyboard down ends the Review hold (the B5f composer FLIP covers the move) */
    D.documentElement.classList.toggle('kb-up', on);   /* labtile1: the home link row steps aside while the keyboard is up */
    panel.classList.toggle('kbd', on && rv()); panel.classList.toggle('kbf', on); ps.setProperty('--vvh', on ? Math.round(vv.height) + 'px' : '');   /* compact1: visible height for the notice popover cap */
    if (on) { ps.minHeight = ''; ps.top = Math.round(vv.offsetTop) + 'px'; ps.bottom = 'auto'; ps.height = Math.round(vv.height) + 'px'; ps.maxHeight = 'none'; }
    else { ps.top = ps.bottom = ps.height = ps.maxHeight = ''; FKS = false; }
    if (on && !FKS && D.activeElement === input) { FKS = true; var fiv = function () { if (!panel.classList.contains('kbf')) return; var v2 = W.visualViewport, h = panel.querySelector('.hdp'), r = input.getBoundingClientRect(), top = (h ? h.getBoundingClientRect().bottom : 0) + 8, bot = v2.offsetTop + v2.height - 12; if (r.bottom > bot) panel.scrollTop += Math.ceil(r.bottom - bot); else if (r.top < top) panel.scrollTop -= Math.ceil(top - r.top); }; fiv(); setTimeout(fiv, 120); }   /* B5d: the field is brought into view in the same frame as the re-pin (it used to be 120ms later = a second 34px jump); the 120ms pass is only a fallback and is a no-op when it already fits */   /* the field into view inside the sheet only, never the page. B5: only when it would be hidden, and only by the amount needed */
    if (kc0 !== null) { var cs = KC.style, cdy = kc0 - KC.getBoundingClientRect().top - (fl - panel.getBoundingClientRect().top); if (Math.abs(cdy) > 2) { cs.transition = 'none'; cs.transform = 'translateY(' + Math.round(cdy) + 'px)'; void KC.offsetWidth; cs.transition = 'transform .32s cubic-bezier(.45,0,.25,1)'; cs.transform = ''; setTimeout(function () { if (!cs.transform) cs.transition = ''; }, 360); } } if (fl !== null) { var dy = fl - anc.getBoundingClientRect().top; if (Math.abs(dy) > 2) { ps.transition = 'none'; ps.transform = 'translateY(' + Math.round(dy) + 'px)'; void panel.offsetWidth; ps.transition = view === 'empty' ? 'transform .22s cubic-bezier(.2,.8,.2,1)' : 'transform .3s cubic-bezier(.45,0,.25,1)'; ps.transform = '';   /* B5g: the open -> tap path (empty view) keeps the B5d/B5e slide Jared confirmed; Add another / reopen get a gentler ease (safe now that rbFit2 no longer scrolls #kbd during it) */ setTimeout(function () { if (!ps.transform) ps.transition = ''; rbCaret(); }, view === 'empty' ? 260 : 340);   /* B5h: the 0.3s slide keeps its ease-out tail; the confirmed empty-view slide keeps 260 */ } }   /* B5d: keyboard up/down re-pins the sheet to the visible area; it used to jump there in one frame (343px) while the backdrop snapped to opaque = the "refresh" flash on focus. Now the sheet glides from where it was (FLIP, transform only) and the backdrop colour fades */
  }
  function rbFit() { (W.requestAnimationFrame || setTimeout)(function () { rbFit2(); rbCaret(); }); }
  function rbCaret() { var a = D.activeElement; if (!panel || !a || a.tagName !== 'INPUT' || !panel || !panel.contains(a)) return; try { var s = a.selectionStart, e = a.selectionEnd; if (s !== null) a.setSelectionRange(s, e); } catch (x) {} }   /* B4c: iOS caret repaint */
  function rbVis(e) { return e && e.offsetParent && e.getBoundingClientRect().height > 0 ? e : null; }
  function rbFit2() { if (!panel || CLW || CLG) return; var vv = window.visualViewport, kbf = panel.classList.contains('kbf'), A = S.ai, rb = A && A.rbar, f = panel.querySelector('form');
    if (rb) rb.style.paddingBottom = (view === 'understood' && kbf) ? '16px' : ''; var cm = f && (f.closest('.cmp') || f); if (cm) cm.style.paddingBottom = (view !== 'understood' && kbf) ? '16px' : '';
    if (!vv || !kbf) return; var box = view === 'understood' && rb && !rb.hidden ? rb : (f && f.closest('.cmp')) || f; if (!box) return;
    var run = rbVis(box.querySelector('[data-airun]')) || rbVis(box.querySelector('.snd')), tl = rbVis(box.querySelector('.rtx')); if (!run) return;
    [panel, bd].forEach(function (sc) { if (!sc || !sc.contains(run)) return;   /* B5g: only a scroller that holds the Run button can bring it up; scrolling the answer body (#kbd) moved the page content 46-55px on Add another and did not move Run at all */ var lim = vv.offsetTop + vv.height - 12, bt = Math.max(run.getBoundingClientRect().bottom, tl ? tl.getBoundingClientRect().bottom : 0); if (bt > lim) sc.scrollTop += Math.ceil(bt - lim); }); }
  if (W.MutationObserver) new MutationObserver(function (ms) { if (!ms.some(function (m) { return m.target.id === 'kp'; })) return; setTimeout(rbFit, 200); setTimeout(rbFit, 700); }).observe(D.documentElement, { attributes: true, subtree: true, attributeFilter: ['data-v', 'class'] });
  function rbFitOld() { (W.requestAnimationFrame || setTimeout)(function () { if (!panel) return; var vv = window.visualViewport, A = S.ai, rb = A && A.rbar; if (rb) rb.style.paddingBottom = (view === 'understood' && panel.classList.contains('kbf')) ? '16px' : ''; if (!vv || !rb || rb.hidden || view !== 'understood' || !panel.classList.contains('kbf')) return; var run = rb.querySelector('[data-airun]'), tl = rb.querySelector('.rtx'); if (!run) return; var lim = Math.min(panel.getBoundingClientRect().bottom, vv.offsetTop + vv.height) - 12, bt = Math.max(run.getBoundingClientRect().bottom, tl ? tl.getBoundingClientRect().bottom : 0); if (bt > lim) panel.scrollTop += Math.ceil(bt - lim); }); }   /* B3b */
  if (window.visualViewport) { window.visualViewport.addEventListener('resize', fitKeyboard); window.visualViewport.addEventListener('scroll', fitKeyboard); window.visualViewport.addEventListener('resize', function () { setTimeout(rbFit, 160); }); }
  D.addEventListener('focusin', function (e) { if (panel && panel.contains(e.target)) setTimeout(rbFit, 160); });
  var KB = false;   /* lab1: opened by a real tap on the bottom bar: put the cursor in the question box even on phones (a focus() inside the tap is what raises the keyboard on iOS) */
  var OPG = 0, OPP = 0, CLW = 0, FILL = null;   /* B5e: OPG = opening slide running (refit deferred), CLW = close waiting for the keyboard to go down */
  function openPanel() {
    build(); if (CLT) { clearTimeout(CLT); CLT = 0; } CLG = 0; CLW = 0; panel.style.transform = panel.style.transition = ''; if (FILL) { if (FILL.parentNode) FILL.parentNode.removeChild(FILL); FILL = null; } panel.removeEventListener('transitionend', clEnd);
    var was = !panel.hidden; panel.hidden = false; scrim.hidden = false; setInert(true); pill.setAttribute('aria-expanded', 'true');
    if (!was) { void panel.offsetWidth; } (W.requestAnimationFrame || setTimeout)(function () { panel.classList.add('kin'); scrim.classList.add('kin'); }); if (!was && !RMQ()) { OPG = 1; OPP = 0; setTimeout(function () { OPG = 0; if (OPP) { OPP = 0; fitKeyboard(); } }, 340); }   /* B5d: the sheet used to appear in one frame (hidden -> shown with no transition at all). Now: shown at translateY(100%), one forced reflow, then .kin on the next frame starts the 320ms slide-up + backdrop fade */
    aiInit(); if (S.ai.live) aiOpened();   /* aihome1 (kept, ai1 rebase): one GET /api/ask-config the first time; nothing else unless the flag is on */
    dkP = false; dock(false);   /* whatif1h */
    if (view === null) viewStart(); else if (view === 'empty') viewEmpty(); else settle();   /* the start view is redrawn on every open so the mode strip matches the page now; the question box is untouched */
    KB = false;
  }
  var CLT = 0, CLG = 0;
  function clEnd(e) { if (e && (e.target !== panel || (e.propertyName !== 'transform' && e.propertyName !== 'opacity'))) return; clDone(); }
  function clDone() { if (!CLG) return; var g = CLG; CLG = 0; if (CLT) { clearTimeout(CLT); CLT = 0; } panel.removeEventListener('transitionend', clEnd); g(); }
  function closePanel(quiet) {   /* whatif1h: reopen starts with the dock expanded */
    if (CLG && quiet !== true) return;   /* B5d: already sliding down */
    if (quiet !== true && panel && !panel.hidden && panel.classList.contains('kin')) {   /* B5d: slide down + backdrop fade first; the sheet is hidden, the scroll lock released and scrollY restored only after transitionend (420ms fallback), so nothing under it repaints mid-close */
      var ae = D.activeElement, ps = panel.style, kf = panel.classList.contains('kbf') && !RMQ();
      /* B5e: closing with the keyboard up. The keyboard layout is FROZEN the moment close starts (.kbf, top and height stay; vv resize is ignored while CLG is set; kb state is cleared in closeNow only after the sheet is hidden). A solid strip in the sheet colour is attached under the sheet so the space the keyboard leaves never shows the backdrop, and the sheet + strip slide straight down together. B5d instead let the keyboard-down resize re-anchor the sheet mid-slide (44px hitch up, 509 jump) and switch the backdrop from solid to see-through (pop). */
      if (kf) { var r = panel.getBoundingClientRect(), dist = Math.ceil(W.innerHeight - r.top + 8), tr = 'transform .32s cubic-bezier(.2,.8,.2,1)';
        FILL = D.createElement('div'); FILL.setAttribute('aria-hidden', 'true'); var fs = FILL.style; fs.position = 'fixed'; fs.left = '0'; fs.right = '0'; fs.top = Math.floor(r.bottom - 1) + 'px'; fs.height = '100vh'; fs.background = W.getComputedStyle(panel).backgroundColor; fs.zIndex = '10'; fs.pointerEvents = 'none'; D.body.appendChild(FILL);
        void FILL.offsetWidth; fs.transition = tr; ps.transition = tr; fs.transform = ps.transform = 'translateY(' + dist + 'px)'; }
      CLG = function () { closeNow(quiet); }; if (FKR) { (W.cancelAnimationFrame || clearTimeout)(FKR); FKR = 0; }
      if (ae && panel.contains(ae) && ae.blur) ae.blur();
      panel.classList.remove('kin'); scrim.classList.remove('kin'); pill.setAttribute('aria-expanded', 'false');
      panel.addEventListener('transitionend', clEnd); CLT = setTimeout(clDone, 420); return;
    }
    if (CLG) { CLG = 0; clearTimeout(CLT); CLT = 0; panel.removeEventListener('transitionend', clEnd); }
    closeNow(quiet);
  }
  function closeNow(quiet) {
    panel.classList.remove('kin'); scrim.classList.remove('kin'); panel.style.transform = panel.style.transition = ''; if (FILL) { if (FILL.parentNode) FILL.parentNode.removeChild(FILL); FILL = null; }
    dkP = false; dock(false);   /* focus goes back to what opened it; if that is gone or hidden (the bar hides while the Lab is on screen), to the bar, else to the Lab heading. The question box keeps its text. */
    panel.hidden = true; if (FKR) { (W.cancelAnimationFrame || clearTimeout)(FKR); FKR = 0; } fitNow();   /* whatif1f: keyboard state off synchronously, BEFORE the lock is released and scrollY restored */ scrim.hidden = true; setInert(false); pill.setAttribute('aria-expanded', 'false');
    var o = LAB.opener; LAB.opener = null;
    if (quiet === true) return;
    var t = (o && o.isConnected && o.getClientRects().length) ? o : (pill.getClientRects().length ? pill : D.getElementById('pk-wh'));
    if (t) t.focus({ preventScroll: true });
  }
  D.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('[data-rtt]'); if (!t) return; var pn = D.getElementById(t.getAttribute('aria-controls')); if (!pn) return; var o = t.getAttribute('aria-expanded') !== 'true'; t.setAttribute('aria-expanded', o ? 'true' : 'false'); pn.hidden = !o; });
  D.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-w2lab]'); if (!b) return; e.preventDefault(); pill.click(); });   /* whatif2b: conference slim Lab button opens the Lab sheet (Conference run for this page); nothing runs until Run */
  pill.addEventListener('click', function (e) { if (e.isTrusted) KB = true; openPanel(); });
  function bfClose(e) { if (panel && !panel.hidden && (e.type === 'pagehide' || e.persisted)) closePanel(true); }   /* whatif1d: back/forward cache: never come back with the Lab open and the page pinned */
  D.addEventListener('visibilitychange', function () { if (!D.hidden && panel && !panel.hidden && D.activeElement === input) (W.requestAnimationFrame || setTimeout)(rbCaret); });   /* B5 */
  W.addEventListener('pagehide', bfClose); W.addEventListener('pageshow', bfClose);
  if (D.getElementById('wl-home')) watch(D.getElementById('wl-home'));
  pill.addEventListener('click', function () { loadCompare().then(function () { if (view === 'empty' && window.KTCompare) KTCompare.shown(view, bd, cmpApi()); }); });   /* compare1: load Compare when the panel opens so the start view can show its example card */
  function settle() {   /* focus: the question box, else the close button */
    if (dkOn && dkBar) { dkBar.focus({ preventScroll: true }); return; }   /* whatif1h: collapsed dock: the bar, never the hidden field */
    var t = ((!input.disabled && !cmp.hidden && (!isNarrow() || KB)) ? input : null) || (panel.contains(D.activeElement) && D.activeElement !== D.body ? null : closeBtn);
    if (t === input) fieldOn(false); else if (t) t.focus({ preventScroll: true });   /* B5: focus never scrolls */
  }
  /* B5: one way to put the person back in the question box: dock opened, field enabled, focus without a scroll, the caret set again on the next frame (iOS can lose it after a re-render) */
  function fieldOn(end) {
    if (!input) return; input.disabled = false; if (dkOn) { dkP = false; dock(false); }
    try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); }
    (W.requestAnimationFrame || setTimeout)(function () { if (D.activeElement !== input) return; var n = end || input.selectionStart === null ? input.value.length : input.selectionStart, m = end || input.selectionEnd === null ? n : input.selectionEnd; try { input.setSelectionRange(n, m); } catch (e) {} });
  }
  /* B5: Start over clears the layered conditions, the last question, the toolbox picks, the AI read and the saved Compare what-ifs (the Lab keeps no run history in storage; model and AI settings are preferences and stay) */
  var SO_BTN = '<button type="button" class="kso" data-reset>Start over</button>';
  function startOver() {
    if (S.busy || S.run) return;
    S.lastQ = ''; S.parsed = null; S.res = null; S.choices = {}; S.seedN = 0; S.w2 = null; S.w2d = null; S.w2bc = null; S.skip = null;
    var A = S.ai; if (A) { A.scen = null; A.text = ''; A.read = false; A.fbn = false; A.edited = false; A.tk = null; A.bad = ''; A.via = null; }
    try { if (window.KTCompare && KTCompare.state) { var c = KTCompare.state; c.list = []; c.pending = false; c.cur = null; c.curAns = null; } } catch (e) {}
    input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true;
    var ps = panel.style, kf = panel.classList.contains('kbf'); if (!kf) ps.minHeight = Math.round(panel.getBoundingClientRect().height) + 'px';   /* B5f: Start over flash. The sheet is sized by its content; swapping the results (1100px) for the empty view (110px) collapsed it in one frame (812 -> 473px tall, top edge 32 -> 371) so the backdrop showed through, then the keyboard re-grew it. The height is held until the keyboard layout takes over */
    var KC = D.getElementById('kcmp'), c0 = KC ? KC.getBoundingClientRect().top : null;
    bd.style.transition = 'none'; bd.style.opacity = '0';
    viewEmpty(); fieldOn(true);
    if (c0 !== null) { var cdy = c0 - KC.getBoundingClientRect().top, cs = KC.style; if (Math.abs(cdy) > 2) { if (kf) { cs.transition = 'none'; cs.transform = 'translateY(' + Math.round(cdy) + 'px)'; void KC.offsetWidth; cs.transition = 'transform .26s cubic-bezier(.45,0,.25,1)'; cs.transform = ''; } else { cs.transition = 'none'; cs.opacity = '0'; void KC.offsetWidth; cs.transition = 'opacity .15s ease-out'; cs.opacity = ''; } setTimeout(function () { if (!cs.transform && !cs.opacity) cs.transition = ''; }, 300); } }   /* B5f: keyboard up: the composer glides once; keyboard coming up: it fades in at its new place (a glide would fight the keyboard re-pin) */
    void bd.offsetWidth; bd.style.transition = 'opacity .15s ease-out'; bd.style.opacity = ''; setTimeout(function () { if (!bd.style.opacity) bd.style.transition = ''; }, 200);   /* B5f: short crossfade instead of a hard swap */
    if (!kf) setTimeout(function () { if (!panel.classList.contains('kbf')) { ps.minHeight = ''; } }, 900);   /* no keyboard came up (desktop, hardware keyboard): let go after the swap */
  }
  /* KickTip shield spinner (Creative's spec): a static track plus a cyan stroke that traces the shield outline, holds closed, un-traces, loops (CSS in chat.css; attributes and classes only, no inline style). Reduced motion: steady closed shield. */
  var SHIELD = '<svg class="kshd" viewBox="0 0 278 355" aria-hidden="true" focusable="false"><path class="kst" pathLength="1" d="M139 14L257 58V130C257 154 259 180 256 200C252 220 246 232 236 248C226 264 210 284 198 296C186 308 174 315 164 322C154 329 146 335 139 339C132 335 124 329 114 322C104 315 92 308 80 296C68 284 52 264 42 248C32 232 26 220 22 200C19 180 21 154 21 130V58Z"/><path class="ksm" pathLength="1" d="M139 14L257 58V130C257 154 259 180 256 200C252 220 246 232 236 248C226 264 210 284 198 296C186 308 174 315 164 322C154 329 146 335 139 339C132 335 124 329 114 322C104 315 92 308 80 296C68 284 52 264 42 248C32 232 26 220 22 200C19 180 21 154 21 130V58Z"/></svg>';
  var SPINCARD = '<div class="spin kbb">' + SHIELD + '<div class="kbt"><p class="spcap">Running your scenario</p></div></div>';
  function setRun(on) {   /* the Run button's running state: shield + "Running\u2026", aria-busy, aria-disabled (not disabled, so focus stays), graphite kept, until the view changes */
    S.run = !!on; send.classList.toggle('run', S.run);
    if (S.run) { send.setAttribute('aria-busy', 'true'); send.setAttribute('aria-disabled', 'true'); send.setAttribute('aria-label', 'Running'); send.innerHTML = SHIELD + '<span>Running\u2026</span>'; send.disabled = false; }
    else { send.removeAttribute('aria-busy'); send.removeAttribute('aria-disabled'); send.setAttribute('aria-label', 'Run'); send.textContent = 'Run'; if (rv()) aiMode(); }
  }
  function isNarrow() { return window.matchMedia && window.matchMedia('(max-width:700px)').matches; }
  function kbbShow() { var b = bd.querySelector('.kbb, .st2.kbe'); if (!b || RVH) return;   /* B5h: no inner scroll while the Review hold keeps the field still */ var f = panel.querySelector('form'), h = f ? f.getBoundingClientRect().height : 0; b.style.scrollMarginBottom = Math.round(h + 12) + 'px'; var hp = panel.querySelector('.hdp'), hh = hp ? hp.getBoundingClientRect().height : 0; b.style.scrollMarginTop = Math.round(hh + 8) + 'px'; W.requestAnimationFrame(function () { var r = b.getBoundingClientRect(), br = bd.getBoundingClientRect(), hb = hp ? hp.getBoundingClientRect().bottom : br.top, tl = Math.max(br.top, hb + 8); if (r.top < tl) b.scrollIntoView({ block: 'start' }); else if (r.bottom > br.bottom - 12) b.scrollIntoView({ block: 'nearest' }); });   /* B3: never under the fixed header */ }
  var RVH = false;
  function gl(el, dy) { if (Math.abs(dy) <= 2) return; var cs = el.style; cs.transition = 'none'; cs.transform = 'translateY(' + Math.round(dy) + 'px)'; void el.offsetWidth; cs.transition = 'transform .3s cubic-bezier(.45,0,.25,1)'; cs.transform = ''; setTimeout(function () { if (!cs.transform) cs.transition = ''; }, 340); }   /* B5h: one composer glide */
  function show(v, html, opt) {
    opt = opt || {}; var pv = view, KC = D.getElementById('kcmp'), kcv = KC && KC.getClientRects().length, kf = panel && panel.classList.contains('kbf');
    if (kf && kcv && pv === 'empty' && v !== 'empty' && !RVH) { RVH = true; bd.style.flex = '0 0 ' + Math.round(bd.getBoundingClientRect().height) + 'px'; }   /* B5h: Review jump. With the keyboard up the empty view stacks the composer under its text; every other view pins it to the sheet bottom, so Enter -> thinking -> Review moved the field down 101-167px in one frame. The body keeps its height while the question is read, so the field stays put */
    var rel = RVH && !(v === 'thinking' || v === 'loading'), c0 = rel && kcv ? KC.getBoundingClientRect().top : null;
    view = v; bd.innerHTML = html; bd.scrollTop = 0;
    if (rel) { RVH = false; bd.style.flex = ''; if (c0 !== null && KC.getClientRects().length) gl(KC, c0 - KC.getBoundingClientRect().top); }   /* the hold ends when the read is done; the composer then glides once */
    if (!!S.run !== (v === 'running' || v === 'loading')) setRun(v === 'running' || v === 'loading');
    send.disabled = !S.run && !input.value.trim();
    input.placeholder = 'What if BYU wins out?'; panel.setAttribute('data-v', v); dkSet(DKR[v] === 1);
    if (opt.keep !== undefined) { input.value = opt.keep; cnt.textContent = opt.keep.length + '/' + cap(); send.disabled = !S.run && !opt.keep.trim(); }
    if (opt.focus !== false) settle();
    kbbShow();   /* whatif2b: status bubble clears the composer by 12px */
    if (window.KTCompare) KTCompare.shown(v, bd, cmpApi());   /* compare1 */
    aiChrome(v);   /* aihome1 */
  }
  var LINKS = '<p class="lk"><a href="/disclaimer/">Full disclaimer</a> &middot; <a href="/method/">Method</a></p>';
  var REQ = '';   /* merge: in-card banner dropped (one line per state: the gate's 'Not a betting site') */
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
    show('empty', '<p class="kht">Type a "what if" about any team and see how its chances change.</p><details class="khw" id="khow"><summary>How it works ' + AI_CHEV + '</summary><p class="note">' + emptyNote() + '</p>' + LINKS + labStrip() + '</details>');   /* whatif1: example cards moved to the chips under the box; ex kept for reference */ void ex;
  }
  function viewRefusal(t) {
    show('refusal', bubble(t) + '<div class="st2">' + REQ + '<h3 class="mt">KickTip gives simulation analysis only.</h3><p>We don\'t give advice or recommendations. You can ask how a result would change the race instead.</p>' + pickButtons(1) + '<p class="ksop">' + SO_BTN + '</p>' + LINKS + '</div>');
  }
  function pickButtons(n) { var ex = S.bundle ? examples().slice(0, n) : []; return ex.map(function (e) { return '<button type="button" class="opt" data-q="' + esc(e[1]) + '">' + esc(e[1]) + '</button>'; }).join(''); }
  function viewClarify(t, ci) {
    show('clarify', bubble(t) + '<div class="st2"><h3>Did you mean&hellip;?</h3><p class="note">More than one team matches. Choose one.</p>' +
      ci.options.map(function (o) { return '<button type="button" class="opt" data-pick="' + esc(o.alias) + '|' + o.team + '">' + esc(o.name) + '</button>'; }).join('') + '<button type="button" class="opt" data-else>Something else</button><p class="ksop">' + SO_BTN + '</p></div>');
    S.lastQ = t;
  }
  /* B5b: examples built from the teams the person named (wins out, loses out, beats its next opponent), each checked before it shows */
  function teamEx(t) {
    var B = S.bundle, out = [], seen = {}, p; try { p = KTParse.parse(t, B.aliases, { choices: S.choices }); } catch (e) { return out; }
    (p.mentions || []).forEach(function (m) { if (m.team === null || m.team === undefined || seen[m.team] || Object.keys(seen).length >= 2) return; seen[m.team] = 1;
      var s = B.teams[m.team].s || nm(m.team), nx = B.games.filter(function (g) { return (g.h === m.team || g.a === m.team) && g.h !== B.fcs && g.a !== B.fcs; }).sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; })[0];
      var qs = [s + ' wins out', s + ' loses out']; if (nx) qs.push(s + ' beats ' + (B.teams[nx.h === m.team ? nx.a : nx.h].s || nm(nx.h === m.team ? nx.a : nx.h)));
      qs.forEach(function (q) { if (out.length < 4 && fixOk(q)) out.push('What if ' + q + '?'); });
    });
    return out;
  }
  /* B5i: the "didn't catch that" card names the part it could not read and builds its chips from the visitor's own teams: the teams it read (up to 3, one chip each in turn), else the saved My teams, else the generic examples */
  function b5iTeams(t) {
    var B = S.bundle, ids = [], p; try { p = KTParse.parse(t, B.aliases, { choices: S.choices }); } catch (e) { p = {}; }
    (p.mentions || []).forEach(function (m) { if (m.team !== null && m.team !== undefined && ids.indexOf(m.team) < 0 && ids.length < 3) ids.push(m.team); });
    if (!ids.length) { try { var mt = window.KTMyTeams && KTMyTeams.get ? KTMyTeams.get().teams : []; Object.keys(B.teams).forEach(function (k) { if (ids.length < 3 && mt.indexOf(B.teams[k].g) >= 0) ids.push(+k); }); } catch (e) {} }
    return ids;
  }
  var B5I_NM = { miami: 'Miami (FL)', 'miami-oh': 'Miami (OH) RedHawks', 'southern-utah': 'Southern Utah' };   /* B5i2: approved short names on chips (never a bare Miami, never SUU) */
  function b5iName(id) { var T = S.bundle.teams[id] || {}; return B5I_NM[T.g] || T.s || nm(id); }
  function b5iCut(c) { c = String(c).replace(/\s+/g, ' ').trim(); if (c.length <= 40) return c; var k = c.slice(0, 40), sp = k.lastIndexOf(' '); if (sp >= 20) k = k.slice(0, sp); return k.replace(/[\s,;:&-]+$/, '') + '\u2026'; }   /* B5i2: about 40 characters, cut on a word */
  function b5iChips(ids) {
    var B = S.bundle, rows = ids.map(function (id) { var s = b5iName(id), nx = B.games.filter(function (g) { return (g.h === id || g.a === id) && g.h !== B.fcs && g.a !== B.fcs; }).sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; })[0];
      var qs = [s + ' wins out', s + ' loses out']; if (nx) qs.push(s + ' beats ' + b5iName(nx.h === id ? nx.a : nx.h)); return qs.filter(fixOk); }), out = [];
    for (var k = 0; k < 3 && out.length < 4; k++) rows.forEach(function (r) { if (r[k] && out.length < 4) out.push('What if ' + r[k] + '?'); });
    return out;
  }
  function b5iUnread(t) {
    var B = S.bundle, src = String(t).replace(/^\s*(?:what if|what happens if|if|suppose)\s+/i, '').replace(/[?\s]+$/, ''), raw = src.split(/(\s*(?:[,;]|\band\b|&|\bthen\b|\bplus\b|\balso\b)\s*)/i), parts = [], acc = '';
    function only(c) { var p; try { p = KTParse.parse(c, B.aliases, { choices: S.choices }); } catch (e) { return false; } var w = KTParse.norm(c).split(' ').length, a = 0; (p.mentions || []).forEach(function (m) { a += String(m.alias).split(' ').length; }); return (p.mentions || []).length > 0 && a >= w; }
    for (var i = 0; i < raw.length; i += 2) { var c = raw[i] || ''; if (!/[a-z0-9]/i.test(c)) { acc = ''; continue; } acc += c; if (only(c) && i + 2 < raw.length) { acc += raw[i + 1]; continue; } parts.push(acc.trim()); acc = ''; }   /* a bare team name joins the part after it, as typed ("BYU, Utah and Texas Tech all ...") */
    return parts.filter(function (c) { var p; try { p = KTParse.parse(c, B.aliases, { choices: S.choices }); } catch (e) { return true; } return !(p && !p.clarify && !p.refusal && p.items && p.items.length) && (p.mentions || []).length; }).slice(0, 2);
  }
  function viewNotUnderstood(t) {
    var ids = b5iTeams(t), opts = ids.length ? b5iChips(ids) : [], un = []; try { un = b5iUnread(t).map(function (c) { return String(c).replace(/^[\s"'\u201c\u201d\u2018\u2019]+|[\s"'\u201c\u201d\u2018\u2019]+$/g, ''); }).filter(function (c) { return c; }); } catch (e) { un = []; }   /* B5i3: outer quotes off, empty parts dropped */
    if (!opts.length) examples().forEach(function (e) { opts.push(e[1]); });   /* B5b: generic examples only when no team was recognized */
    show('notunderstood', bubble(t) + '<div class="st2"><span class="ico" aria-hidden="true">?</span><h3>Sorry, I didn\'t catch that</h3>' + (un.length ? '<p class="kskp" role="status"><b data-b5u></b></p>' : '') + '<p class="note">Try a game result, like Team A beats Team B, Team A loses to Team B or Team A wins out.</p>' +
      opts.map(function (q) { return '<button type="button" class="opt" data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '<p class="ksop">' + SO_BTN + '</p></div>');
    var ub = un.length && bd.querySelector('[data-b5u]'); if (ub) ub.textContent = "Couldn't read " + un.map(function (c) { return '"' + b5iCut(c) + '"'; }).join(' or ');   /* B5i2: the typed words go in as text, never as HTML */
    S.lastQ = t;
  }
  var INFO_TITLE = { margin: 'Wins and losses only', title_scenario: 'Not supported yet', too_many_items: 'Up to 8 game results', already_played: 'That game is already final', conflict: 'Those results can\'t both happen' };
  var FIX_TEXT = 'Two of those results involve the same game. Choose how it goes:';
  /* B4e: a "conflict" (two results that cannot both happen, like "BYU and Utah win out" when they still play) offers the fixed versions of the person's own question, one per way the shared game can go; the rest of the question is kept. Each chip is checked with the parser and resolver before it is shown. */
  function fixPhrase(it, opp) {
    var s = function (t) { return S.bundle.teams[t].s || nm(t); };
    if (it.kind === 'wins_out') return s(it.team) + ' wins out' + (opp !== null && opp !== undefined ? ' and beats ' + s(opp) : '');
    if (it.kind === 'loses_out') return s(it.team) + ' loses out';
    if (it.kind === 'beats') return s(it.winner) + ' beats ' + s(it.loser);
    if (it.kind === 'next_win') return s(it.team) + ' wins';
    if (it.kind === 'next_loss') return s(it.team) + ' loses';
    if (it.kind === 'loses_n') return s(it.team) + (it.scope === 'total' ? ' ends with ' + (it.losses === 0 ? 'no losses' : it.losses + (it.losses === 1 ? ' loss' : ' losses')) : ' loses ' + it.losses + ' of the remaining games');
    if (it.kind === 'wins_n_of_m') return s(it.team) + ' wins ' + it.n + ' of the ' + (it.scope === 'remaining' ? 'remaining games' : it.scope + ' ' + it.m);
    return null;
  }
  function fixRes(items) { try { return KTScenario.resolve({ items: items, need: null, baseline_team: null }, S.bundle); } catch (e) { return null; } }
  function fixOk(q) { try { var p = KTParse.parse(q, S.bundle.aliases, { choices: S.choices }); if (p.clarify || p.refusal || p.need || !p.items.length) return false; var r = fixRes(p.items); return !!(r && r.ok); } catch (e) { return false; } }
  /* B5: Add another game starts from the games that ran, in short form ("Utah beats BYU and Texas Tech wins out"), so a long stack still fits the box; checked with the parser first */
  function stackText() {
    var q = (S.lastQ || '').replace(/[?.!\s]+$/, ''), it = S.parsed && S.parsed.items;
    if (it && it.length && S.bundle) { var ps = it.map(function (x) { return fixPhrase(x, null); }); if (ps.every(Boolean)) { var c = ps.join(' and '); if (fixOk(c)) q = c; } }
    return q;
  }
  function stackQ(items) { var ps = items.map(function (x) { return fixPhrase(x, null); }); return ps.every(Boolean) ? 'What if ' + ps.join(' and ') + '?' : ''; }
  /* B5: no dead ends: every "needs a change" card also offers each condition removed (only versions that run) and Start over */
  function rmChips(parsed) {
    var items = parsed && parsed.items || [], out = [];
    if (items.length < 2 || !S.bundle) return '';
    items.forEach(function (it, i) { var rest = items.filter(function (x, j) { return j !== i; }), q = stackQ(rest), w = fixPhrase(it, null); if (q && w && fixOk(q.replace(/^What if |\?$/g, ''))) out.push('<button type="button" class="opt" data-q="' + esc(q) + '">Remove ' + esc(w) + '</button>'); });
    return out.slice(0, 8).join('');
  }
  function fixChips(parsed) {
    var items = parsed && parsed.items || [], out = [], k, j, a, b;
    if (items.length < 2 || items.length > 8) return out;
    for (k = 1; k < items.length && a === undefined; k++) { var r = fixRes(items.slice(0, k + 1)); if (r && !r.ok && r.clarify && r.clarify.reason === 'conflict') for (j = 0; j < k; j++) { var r2 = fixRes([items[j], items[k]]); if (r2 && !r2.ok && r2.clarify && r2.clarify.reason === 'conflict') { a = j; b = k; break; } } }
    if (a === undefined) return out;
    var fa = fixRes([items[a]]), fb = fixRes([items[b]]), opp = {}; if (!fa || !fb || !fa.ok || !fb.ok) return out;
    fa.games.forEach(function (g) { fb.games.forEach(function (h) { if (g.id === h.id && g.winner !== h.winner) { opp[a] = g.winner === g.home ? g.away : g.home; opp[b] = h.winner === h.home ? h.away : h.home; } }); });
    [a, b].forEach(function (keep) {
      var parts = [], bad = false;
      items.forEach(function (it, i) { if (i === a || i === b) { if (i === keep) { var x = fixPhrase(it, opp[i]); if (!x) bad = true; parts.push(x); } } else { var y = fixPhrase(it, null); if (!y) bad = true; parts.push(y); } });
      if (!bad) { var kp = parts[[a, b].indexOf(keep) === 0 ? 0 : 0]; parts = parts.filter(function (x, i) { return parts.indexOf(x) === i; }); parts = parts.map(function (x) { var m = / and beats (.+)$/.exec(x || ''); if (m) { var who = x.replace(/ wins out and beats .+$/, ''); if (parts.indexOf(who + ' beats ' + m[1]) >= 0) return who + ' wins out'; } return x; }); parts = parts.filter(function (x, i) { return parts.indexOf(x) === i; }); }   /* B5e: no repeated game in a fix chip (it read "BYU wins out and beats Utah and BYU beats Utah") */
      var q = bad ? '' : parts.join(' and ');
      if (q && q.length <= cap() && out.indexOf(q) < 0 && fixOk(q)) out.push(q);
    });
    return out.slice(0, 4);
  }
  /* B4e2: keep the fix card in view: its top below the header, its last chip above the composer dock and the keyboard (12px clear); if it cannot all fit, its top wins */
  function fixFit() {
    (W.requestAnimationFrame || setTimeout)(function () {
      var c = D.getElementById('kfix'); if (!c || view !== 'info') return;
      var vv = W.visualViewport, f = panel.querySelector('form'), hp = panel.querySelector('.hdp');
      var bot = Math.min(f ? f.getBoundingClientRect().top : Infinity, vv ? vv.offsetTop + vv.height : W.innerHeight) - 12, top = Math.max(bd.getBoundingClientRect().top, (hp ? hp.getBoundingClientRect().bottom : 0) + 8, vv ? vv.offsetTop + 8 : 0);
      var ch = c.querySelectorAll('[data-fix]'), f0 = ch[0], fl = ch[ch.length - 1];
      [bd, panel].forEach(function (sc) { var r = c.getBoundingClientRect(), lb = fl.getBoundingClientRect().bottom, d = 0; if (lb > bot) { d = Math.min(lb - bot, r.top - top); if (lb - d > bot) d = Math.min(lb - bot, f0.getBoundingClientRect().top - top); } else if (r.top < top) d = r.top - top; if (d) sc.scrollTop += Math.round(d); });
    });
  }
  if (W.visualViewport) W.visualViewport.addEventListener('resize', function () { if (D.getElementById('kfix')) fixFit(); });
  function viewInfo(t, text, ci, parsed) {
    var fx = ci && ci.reason === 'conflict' ? fixChips(parsed || S.parsed) : [];
    if (fx.length) {
      var kbUp = panel.classList.contains('kbf');
      show('info', bubble(t) + '<div class="st2" id="kfix"><span class="ico" aria-hidden="true">?</span><h3>' + esc(INFO_TITLE.conflict) + '</h3><p>' + esc(FIX_TEXT) + '</p>' + fx.map(function (q) { return '<button type="button" class="opt" data-q="' + esc(q) + '" data-fix>' + esc(q) + '</button>'; }).join('') + rmChips(parsed || S.parsed) + '<p class="ksop">' + SO_BTN + '</p></div>', { focus: !kbUp });
      if (kbUp && D.activeElement === input) input.blur();   /* keyboard up: let it close so the chips are not under the composer or off the top */
      fixFit(); setTimeout(fixFit, 200); setTimeout(fixFit, 600);
      return;
    }
    var plain = ci && ci.reason === 'margin' && ci.plain_text ? '<button type="button" class="opt" data-q="' + esc(ci.plain_text) + '">Run it without the margin: ' + esc(ci.plain_text) + '</button>' : '';
    /* B5: too many losses: offer the same stack with that team losing out (only if it runs) */
    var rc = ci && (ci.rc || ci);
    if (!plain && rc && /^loss_range/.test(rc.reason || '') && rc.teams && parsed && parsed.items && S.bundle) { var lq = stackQ(parsed.items.map(function (x) { return (x.team === rc.teams[0] && /^loses_n|^losses|loss/.test(x.kind || '')) ? { kind: 'loses_out', team: x.team } : x; })); if (lq && fixOk(lq.replace(/^What if |\?$/g, ''))) plain = '<button type="button" class="opt" data-q="' + esc(lq) + '">' + esc(lq) + '</button>'; }
    var rm = rmChips(parsed), tx = rm ? [] : teamEx(t).slice(0, plain ? 1 : 2), pk = rm ? '' : (tx.length ? tx.map(function (q) { return '<button type="button" class="opt" data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') : pickButtons(plain ? 1 : 2));   /* B5e: examples built from the teams the person named; the generic ones only when no team was recognized */
    if (/more games than the team has left/.test(text || '') && parsed && parsed.items && S.bundle) { var ti = parsed.items.filter(function (x) { return x.team !== undefined && x.team !== null; })[0]; if (ti) { var tsn = S.bundle.teams[ti.team].s || nm(ti.team), gl = S.bundle.games.filter(function (g) { return g.h === ti.team || g.a === ti.team; }).length; text = gl === 0 ? tsn + ' has no games left.' : 'That is more games than ' + tsn + ' has left. ' + tsn + ' has ' + (gl === 0 ? 'no games' : gl + (gl === 1 ? ' game' : ' games')) + ' left.'; } }   /* B5e: name the team and its count */
    show('info', bubble(t) + '<div class="st2"><span class="ico" aria-hidden="true">?</span><h3>' + esc((ci && INFO_TITLE[ci.reason]) || 'That one needs a change') + '</h3><p>' + esc(text) + '</p>' + plain + rm + pk + '<p class="ksop">' + SO_BTN + '</p></div>');
    S.lastQ = t;
  }
  function viewError(t) {
    var off = typeof navigator !== 'undefined' && navigator.onLine === false;
    show('error', (t ? bubble(t) : '') + '<div class="st2 kbe" role="status"><span class="ico" aria-hidden="true">!</span><h3>' + (off ? 'You\'re offline' : 'Couldn\'t load the data') + '</h3><p>' + (off ? 'We couldn\'t load the data to run this. ' : 'Something went wrong loading the data. ') + (t ? 'Your question is still in the box below.' : 'Check your connection and try again.') + '</p><button type="button" class="opt" data-retry>' + (rv() ? 'Try again' : 'Run again') + '</button>' + (rv() ? '<button type="button" class="opt" data-noai>Don\'t use AI</button>' : '') + '</div>', { keep: t || '' });
    S.lastQ = t || '';
  }
  var REAL = { '401864537': '2026-11-15T04:00Z' };   /* simweeks3: known-real kickoff that looks like a placeholder (Hawaii v North Dakota State, 9:00 PM MT Nov 14): id -> exact ESPN date; checked first */
  function gdate(iso, id) {   /* MT calendar day; placeholder times (04:00Z / 05:00Z) mean "time to be announced", so use the UTC date */
    var tba = !(id !== undefined && REAL[id] === iso) && /T0[45]:00Z$/.test(iso); try { return new Intl.DateTimeFormat('en-US', { timeZone: tba ? 'UTC' : 'America/Denver', weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(iso)); } catch (e) { return iso.slice(0, 10); }
  }
  function chipHtml(parsed, res) {
    var items = parsed.items || [];
    return '<div class="chips" role="group" aria-label="Scenario games">' + items.map(function (it, i) { var tx = esc(itemText(it, res, i)); return '<span class="chip">' + tx + '<button type="button" data-rm="' + i + '" aria-label="Remove: ' + tx + '">&times;</button></span>'; }).join('') + '<button type="button" class="addg" data-add>+ Add another game</button>' + SO_BTN + '</div>' + skipHtml();
  }
  /* B5: a condition that cannot apply is named, the rest still runs */
  function covHtml() { var c = S.parsed && S.parsed.covered; if (!c || !c.length || !S.bundle) return ''; return c.map(function (x) { var a = fixPhrase(x.by, null), b = fixPhrase(x.what, null); return a && b ? '<p class="kskp" role="status">' + '\u201c' + esc(a) + '\u201d already covers \u201c' + esc(b) + '.\u201d</p>' : ''; }).join(''); }   /* B5b */
  function skipRmQ(x) { try { var it = S.parsed && S.parsed.items; if (!it || !it.length) return ''; var q = stackQ(it); return q && fixOk(q.replace(/^What if |\?$/g, '')) && q.replace(/^What if |\?$/g, '').toLowerCase().indexOf(String(x.what || '').toLowerCase()) < 0 ? q : ''; } catch (e) { return ''; } }   /* B5e: Remove on a Left out line re-runs the question without it (only the games that ran; checked first) */
  function skipHtml() { var k = S.skip; if (!k || !k.length) return covHtml(); return k.map(function (x) { var rq = skipRmQ(x); return '<p class="kskp" role="status"><b>Left out: ' + esc(x.what) + '.</b> ' + esc(x.why) + (rq ? ' <button type="button" class="opt kskr" data-q="' + esc(rq) + '">Remove</button>' : '') + '</p>'; }).join('') + covHtml(); }
  function lossRem(it, e) { return it.scope === 'total' ? (e && typeof e.rem_losses === 'number' ? e.rem_losses : null) : it.losses; }   /* router2b: losses among the remaining games; a season-final total needs the resolver's echo (total minus losses so far) */
  function itemText(it, res, i) {
    var e = res && res.echo && res.echo[i], live = res && res.games && res.games.some(function (g) { return g.item === i && g.ip; }), t;
    if (it.kind === 'next_win' || it.kind === 'next_loss') {
      if (e) return nm(it.team) + (it.kind === 'next_win' ? ' beats ' : ' loses to ') + (e.opponent === S.bundle.fcs ? (e.fcs || 'an FCS opponent') : nm(e.opponent)) + ' (next game: ' + gdate(e.date, e.game) + (e.ip ? ', in progress' : '') + ')';
      return nm(it.team) + (it.kind === 'next_win' ? ' wins' : ' loses') + ' next game';
    }
    if (it.kind === 'beats') t = nm(it.winner) + ' beats ' + nm(it.loser) + (live ? ' (in progress)' : '');
    else if (it.kind === 'wins_out') t = nm(it.team) + ' wins out' + (live ? ' (includes a game in progress)' : '');
    else if (it.kind === 'loses_out') t = nm(it.team) + ' loses out' + (live ? ' (includes a game in progress)' : '');
    else if (it.kind === 'loses_n') t = nm(it.team) + (lossRem(it, e) === 0 ? ' wins out' : lossRem(it, e) === null ? ' ends with ' + (it.losses === 0 ? 'no losses' : it.losses + (it.losses === 1 ? ' loss' : ' losses')) : ' loses ' + lossRem(it, e) + ' of the remaining games') + (live ? ' (includes a game in progress)' : '');
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
  /* whatif2: results header (championship hero, named-team playoff rows, share image) above a Why? panel that holds every earlier detail. Numbers come only from the engine run (r.before / r.after, pairs counted in sim.js). */
  function w2pc(x) { var p = Math.round(x * 1e7) / 1e5; if (p > 0 && p < 0.5) return '<1%'; if (p >= 99.9999) return '100%'; if (p >= 99.5) return '>99%'; return Math.round(p) + '%'; }
  function w2named(parsed) { var o = []; (parsed.items || []).forEach(function (it) { [it.winner, it.loser, it.team].forEach(function (x) { if (x !== undefined && x !== null && x !== S.bundle.fcs && o.indexOf(x) < 0) o.push(x); }); }); return o; }
  function w2logo(t, size) { var T = S.bundle.teams[t]; return (window.KTLogo && KTLogo.team(T.g, size)) || ''; }
  function w2data(parsed, r) {
    var B = S.bundle, tm = w2named(parsed), N = r.N, cc = {}, best = null, i;
    tm.forEach(function (t) { var c = B.teams[t].c; if (c && c !== 'ind') cc[c] = (cc[c] || 0) + 1; });
    Object.keys(cc).forEach(function (c) { if (!best || cc[c] > cc[best]) best = c; });
    var C = null; for (i = 0; i < B.confs.length; i++) if (B.confs[i].code === best && B.confs[i].fmt !== 'none') C = B.confs[i];
    var hero = null, P = r.after && r.after.pairs;
    if (C && P) {
      var list = Object.keys(P).filter(function (k) { return k.indexOf(C.code + '|') === 0; }).map(function (k) { var s = k.split('|'); return { a: +s[1], b: +s[2], n: P[k] }; }).sort(function (x, y) { return y.n - x.n; });
      if (list.length && list[0].n > 0) {
        var top = list[0], sure = top.n >= N - 1e-9, ta = top.a, tb = top.b;
        if (tm.indexOf(tb) >= 0 && tm.indexOf(ta) >= 0 && tm.indexOf(tb) < tm.indexOf(ta)) { ta = top.b; tb = top.a; } else if (tm.indexOf(tb) >= 0 && tm.indexOf(ta) < 0) { ta = top.b; tb = top.a; }
        var cs = B.teams[ta].cs || '';
        hero = { conf: C.name, cs: cs, a: ta, b: tb, sure: sure, pct: top.n / N, next: list.slice(1, 3).filter(function (x) { return x.n / N >= 0.005; }).map(function (x) { return { a: x.a, b: x.b, pct: x.n / N }; }),
          champ: sure ? [[ta, r.after.title[ta]], [tb, r.after.title[tb]]] : null, ra: r.after.reach ? r.after.reach[ta] / N : null, rb: r.after.reach ? r.after.reach[tb] / N : null };   /* whatif2b: real reach-the-championship rate from this run */
      }
    }
    var ql = String(S.lastQ || '').toLowerCase(), qpos = function (t) { var T = B.teams[t], k = -1; [nm(t), T.s, T.name, T.short].forEach(function (n) { if (!n) return; var j = ql.indexOf(String(n).toLowerCase()); if (j >= 0 && (k < 0 || j < k)) k = j; }); return k < 0 ? 1e6 : k; };
    var rt = tm.slice().sort(function (u, v) { return qpos(u) - qpos(v); });   /* B2: rows in the order the question names the teams, then the rest */ if (hero && !hero.sure) [hero.a, hero.b].forEach(function (t) { if (rt.indexOf(t) < 0) rt.push(t); });   /* whatif2b: under 100% the hero teams get rows too */
    var rows = rt.map(function (t) { return { t: t, b: r.before.cfp12[t], a: r.after.cfp12[t], atl: hero && hero.sure && t !== hero.a && t !== hero.b && B.teams[t].c === best && r.after.cfp12[t] >= 0.5 }; });
    var chips = (parsed.items || []).map(function (it, k) { return itemText(it, S.w2.res, k); }); if (S.w2.only) chips.push(S.w2.onlyChip);
    var cname = function (c) { for (var k = 0; k < B.confs.length; k++) if (B.confs[k].code === c) return B.confs[k].name; return ''; };
    var rtm = rt.slice(); if (hero) [hero.a, hero.b].forEach(function (t) { if (rtm.indexOf(t) < 0) rtm.push(t); });   /* B2: the hero pairing's teams and every row team, not only the constraint teams */
    var reach = (r.after.reach && r.before.reach) ? rtm.filter(function (t) { var c = B.teams[t].c; return c && c !== 'ind'; }).map(function (t) { return { t: t, named: tm.indexOf(t) >= 0, b: r.before.reach[t] / N, a: r.after.reach[t] / N, conf: cname(B.teams[t].c) }; }) : [];
    var wins = hero ? rtm.filter(function (t) { return B.teams[t].c === best; }).map(function (t) { return { t: t, p: r.after.title[t] }; }).sort(function (u, v) { return v.p - u.p; }) : [];
    var scn = ''; try { scn = w2bcCond(parsed.items || [], function (n) { return ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][n] || String(n); }); } catch (e) { scn = ''; }   /* polish: the scenario is the heading */
    return { q: S.lastQ, scn: scn || String(S.lastQ || ''), all: rows, reach: reach, wins: wins, only: S.w2.only || null, chips: chips, hero: hero, rows: rows.slice(0, 4), more: Math.max(0, rows.length - 4), N: N };
  }
  function w2delta(b, a) { var d = Math.round(a * 100) - Math.round(b * 100); if (!d) return '<span class="w2d">no change</span>'; return '<span class="w2d ' + (d > 0 ? 'up' : 'dn') + '">' + (d > 0 ? '+' : '<span class="vh">minus </span>') + Math.abs(d) + '\u00A0pts</span>'; }   /* polish2 (Creative R2): delta pill '+8 pts' (percentage points) / down pill shows the minus sign from CSS (.w2d.dn::before), so the text has no minus-digit run (suite rule) */
  function w2heroHtml(h) {
    var B = S.bundle, cl = (window.KTLogo && h.cs && KTLogo.conf(h.cs, 32)) || '';
    var lab = h.sure ? esc(h.conf) + ' Championship matchup if this happens' : 'Most likely ' + esc(h.conf) + ' Championship';
    function bd(t, v) { if (v === null || v === undefined) return ''; var pc = w2pc(v), al = nm(t) + ' reaches the ' + h.conf + ' Championship in ' + pc + ' of simulations'; return '<span class="w2bdg' + (pc.length > 3 ? ' w2b3' : '') + '" role="img" aria-label="' + esc(al) + '" title="' + esc(al) + '">' + esc(pc) + '</span>'; }
    function lg(t, v) { return '<span class="w2lw">' + w2logo(t, 64) + bd(t, v) + '</span>'; }
    return '<div class="w2h"><p class="w2l">' + cl + '<span>' + lab + '</span></p><div class="w2mu"><span class="w2tm">' + lg(h.a, h.ra) + '<b>' + esc(nm(h.a)) + '</b></span><span class="w2vs">vs</span><span class="w2tm">' + lg(h.b, h.rb) + '<b>' + esc(nm(h.b)) + '</b></span></div>' +
      '<p class="w2p">in <b>' + w2pc(h.pct) + '</b> of simulations</p>' + (h.sure ? '' : '<p class="w2many">Most likely of many possible matchups.</p>') +
      (!h.sure && h.next.length ? '<p class="w2nx">Next: ' + h.next.slice(0, 2).map(function (x) { return '<span>' + esc(nm(x.a)) + ' vs ' + esc(nm(x.b)) + ' ' + w2pc(x.pct) + '</span>'; }).join(' \u00b7 ') + '</p>' : '') +   /* B3: runner-up line restored (Creative spec) */
      (h.champ ? '<p class="w2n">Wins the ' + esc(h.conf) + ': ' + h.champ.map(function (x) { return esc(nm(x[0])) + ' ' + w2pc(x[1]); }).join(' \u00b7 ') + '</p>' : '') + '</div>';
  }
  function w2Html(d) {
    var h = (d.scn ? '<h3 class="w2q">' + esc(d.scn) + '</h3>' : '') + (d.only ? '<p class="w2o">' + esc(d.only) + '</p>' : '') + (d.hero ? w2heroHtml(d.hero) : '');
    function row(x) { var T = S.bundle.teams[x.t], g = T && T.g ? String(T.g).replace(/[^a-z0-9-]/g, '') : '';   /* polish: team-color stripe (class from tc.css; slate when unknown) */
      return '<div class="w2r w2s' + (g ? ' tc-' + g : '') + '">' + w2logo(x.t, 40) + '<span class="w2nm">' + esc(nm(x.t)) + (x.atl ? '<small>at-large</small>' : '') + '</span><span class="w2v"><span class="w2a">' + w2pc(x.a) + '</span>' + w2delta(x.b, x.a) + '<span class="w2was">was ' + w2pc(x.b) + '</span></span></div>'; }
    var all = d.all || d.rows, rest = all.slice(d.rows.length);
    var rows = d.rows.length ? '<p class="w2rh">Make the 12-team playoff</p>' + d.rows.map(row).join('') +
      (rest.length ? '<div class="w2more" id="w2more" hidden>' + rest.map(row).join('') + '</div><button type="button" class="w2all" data-w2all aria-expanded="false" aria-controls="w2more">Show all ' + all.length + ' teams</button>' : '') : '';
    return h + rows + '<button type="button" class="w2sh" data-w2share>' + (w2canShare() ? 'Share results' : 'Download image') + '</button>';
  }
  function w2canShare() { try { return !!(navigator.canShare && navigator.share && navigator.canShare({ files: [new File([new Blob(['x'], { type: 'image/jpeg' })], 'k.jpg', { type: 'image/jpeg' })] })); } catch (e) { return false; } }
  function w2css() { if (D.getElementById('w2css')) return; var l = D.createElement('link'); l.id = 'w2css'; l.rel = 'stylesheet'; l.href = '/assets/wi2.css?v=8c7b805a18'; D.head.appendChild(l); if (!D.querySelector('link[href^="/assets/tc.css"]')) { var t = D.createElement('link'); t.rel = 'stylesheet'; t.href = '/assets/tc.css?v=cc7b9246d7'; D.head.appendChild(t); } }
  function w2img(src) { return new Promise(function (ok) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = function () { ok(null); }; i.src = src; }); }
  function w2src(t) { var h = w2logo(t, 64), m = /src="\/assets\/logos\/\d+\/(\d+)\.png"/.exec(h); return m ? '/assets/logos/500/' + m[1] + '.png' : null; }
  function w2whyOpen() { var wb = D.getElementById('w2wbody'); return !!(wb && !wb.hidden); }
  function w2bullets(d) {   /* share-v2 SPEC 42d70332: at most 4 bullets, all from this run's on-page data */
    var o = [], h = d.hero;
    if (d.chips.length) o.push('Set by you: ' + d.chips.join(', ') + '. Every other game is simulated.');
    if (h) { var nt = (d.reach || []).filter(function (x) { return x.named && x.t !== h.a && x.t !== h.b && x.conf === h.conf; })[0]; if (nt) o.push(nm(nt.t) + ' reaches the ' + h.conf + ' Championship in ' + w2pc(nt.a) + ' of simulations (was ' + w2pc(nt.b) + ').'); }
    if (false && h && !h.sure && h.next && h.next.length) o.push('Next most likely: ' + h.next.map(function (x) { return nm(x.a) + ' vs ' + nm(x.b) + ' ' + w2pc(x.pct); }).join(' \u00b7 ') + '.');
    if (h && d.wins && d.wins.length) o.push('Wins the ' + h.conf + ': ' + d.wins.map(function (x) { return nm(x.t) + ' ' + w2pc(x.p); }).join(' \u00b7 ') + '.');
    return o.slice(0, 4);
  }
  function w2render(d, whyOpen) {   /* share card v2 (Creative share-v2 SPEC 42d70332): 1080 wide, auto height, one left edge at x=72 */
    if (whyOpen === undefined) whyOpen = w2whyOpen();
    var W = 1080, LX = 72, RX = 1008, INK = '#121519', FIELD = '#262B31', CY = '#33E1EA', PAPER = '#F1F3F4', MUTE = '#C5CBD1', RULE = '#3A414A', AMB = '#F2A65A';
    var c = D.createElement('canvas'); c.width = W; c.height = 10; var x = c.getContext('2d', { alpha: false });   /* opaque 1080-wide card at 1x: smaller PNG */
    var fonts = (D.fonts && D.fonts.load) ? Promise.all(['700 40px "Barlow Condensed"', '400 30px "Source Sans 3"', '500 24px "Source Sans 3"', '600 30px "Source Sans 3"', '700 30px "Source Sans 3"', 'italic 400 40px "Source Sans 3"'].map(function (f) { return D.fonts.load(f).catch(function () {}); })) : Promise.resolve();
    var want = {}; if (d.hero) { want[d.hero.a] = 1; want[d.hero.b] = 1; } d.rows.forEach(function (r) { want[r.t] = 1; });
    var ids = Object.keys(want), cs = d.hero && d.hero.cs && window.KTLogo ? (/src="([^"]+)"/.exec(KTLogo.conf(d.hero.cs, 32) || '') || [])[1] : null;
    var BUL = whyOpen ? w2bullets(d) : [];
    return Promise.all([fonts, Promise.all(ids.map(function (t) { var s = w2src(+t); return s ? w2img(s) : null; })), cs ? w2img(cs.replace('/32/', '/500/')) : null, w2img('/assets/brand/logo/kicktip-header-nosub-transparent.png')]).then(function (z) {
      var L = {}; ids.forEach(function (t, k) { L[t] = z[1][k]; }); var cimg = z[2], wm = z[3], DR = false;
      function F(w, s, fam) { x.font = w + ' ' + s + 'px ' + (fam || '"Source Sans 3"') + ', Arial, sans-serif'; }
      function rr(a, b, w, h, r, f) { if (!DR) return; x.fillStyle = f; x.beginPath(); if (x.roundRect) x.roundRect(a, b, w, h, r); else x.rect(a, b, w, h); x.fill(); }
      function T(t, a, b, col, al) { if (!DR) return; x.fillStyle = col; x.textAlign = al || 'left'; x.fillText(t, a, b); x.textAlign = 'left'; }
      function lines(t, w) { var ws = String(t).split(/\s+/), out = [], l = ''; ws.forEach(function (q) { var tt = l ? l + ' ' + q : q; if (x.measureText(tt).width > w && l) { out.push(l); l = q; } else l = tt; }); if (l) out.push(l); return out; }
      function circ(t, cx, cy, r) { if (!DR) return; x.fillStyle = '#fff'; x.beginPath(); x.arc(cx, cy, r, 0, 7); x.fill(); var im = L[t]; if (im) { var s = r * 1.56; x.drawImage(im, cx - s / 2, cy - s / 2, s, s); } }
      function badge(v, cx, cy) { if (!DR || v === null || v === undefined) return; x.fillStyle = '#4C5560'; x.beginPath(); x.arc(cx, cy, 30, 0, 7); x.fill(); x.fillStyle = '#fff'; x.beginPath(); x.arc(cx, cy, 27, 0, 7); x.fill(); F('500', 24); T(w2pc(v), cx, cy + 8, INK, 'center'); }
      function up(s) { return String(s).toUpperCase(); }
      function lay(o) {   /* one pass; DR=false only measures */
        var y = 56, h = d.hero, i;
        F('italic 400', 40); var ql = lines('\u201C' + d.q + '\u201D', RX - (LX + 36)).slice(0, 3), qh = ql.length * 50;
        rr(LX, y + 4, 8, qh - 8, 0, CY); ql.forEach(function (l, k) { T(l, LX + 36, y + 39 + k * 50, PAPER); }); y += qh;
        y += 40; F('700', 30, '"Barlow Condensed"'); T('WHAT KICKTIP UNDERSTOOD', LX, y + 26, CY); y += 30 + 14;
        F('600', 28); var cx0 = LX, cy0 = y; d.chips.slice(0, 4).forEach(function (t) { t = t.length > 60 ? t.slice(0, 58) + '\u2026' : t; var w = Math.min(RX - LX, x.measureText(t).width + 44); if (cx0 > LX && cx0 + w > RX) { cx0 = LX; cy0 += 70; } rr(cx0, cy0, w, 56, 28, '#8A949F'); rr(cx0 + 2, cy0 + 2, w - 4, 52, 26, FIELD); F('600', 28); T(t, cx0 + 22, cy0 + 38, PAPER); cx0 += w + 14; }); y = d.chips.length ? cy0 + 56 : y;
        if (h) {
          y += 28; var top = y, R = o.logo / 2, py = y + 24;
          F('700', 34, '"Barlow Condensed"'); var lab = up(h.sure ? h.conf + ' Championship matchup if this happens' : 'Most likely ' + h.conf + ' Championship'), lw = x.measureText(lab).width, gw = cimg ? 60 : 0, gx = (W - lw - gw) / 2;
          if (cimg) { rr(gx, py, 48, 48, 8, '#fff'); if (DR) { var cw = 40, chh = cimg.height * 40 / cimg.width; x.drawImage(cimg, gx + 4, py + 24 - chh / 2, cw, chh); } }
          T(lab, gx + gw, py + 36, PAPER); py += 48 + 22;
          var ly = py + R, ax = 390, bx = 690; circ(h.a, ax, ly, R); circ(h.b, bx, ly, R); badge(h.ra, ax + R + 10 - 30, ly + R + 10 - 30); badge(h.rb, bx + R + 10 - 30, ly + R + 10 - 30);
          F('700', 34, '"Barlow Condensed"'); T('VS', 540, ly + 12, MUTE, 'center'); py += o.logo + 46; F('700', 34, '"Barlow Condensed"'); T(up(nm(h.a)), ax, py, PAPER, 'center'); T(up(nm(h.b)), bx, py, PAPER, 'center');
          py += 20; var pc = w2pc(h.pct); F('700', 60, '"Barlow Condensed"'); var pw = x.measureText(pc).width; F('400', 32); var iw = x.measureText('in ').width, sw = x.measureText(' of simulations').width, sx = (W - iw - pw - sw) / 2;
          py += 60; T('in ', sx, py, PAPER); F('700', 60, '"Barlow Condensed"'); T(pc, sx + iw, py, CY); F('400', 32); T(' of simulations', sx + iw + pw, py, PAPER);
          if (!h.sure) { py += 42; F('400', 26); T('Most likely of many possible matchups.', 540, py, MUTE, 'center'); if (h.next && h.next.length) { py += 38; F('400', 28); T('Next: ' + h.next.slice(0, 2).map(function (q) { return nm(q.a) + ' vs ' + nm(q.b) + ' ' + w2pc(q.pct); }).join(' \u00b7 '), 540, py, '#B9C0C8', 'center'); } }   /* B3 */
          else if (h.champ) { py += 42; F('400', 26); T('Wins the ' + h.conf + ': ' + h.champ.map(function (q) { return nm(q[0]) + ' ' + w2pc(q[1]); }).join(' \u00b7 '), 540, py, MUTE, 'center'); }
          py += 24 + 10; if (DR) { /* panel drawn under the content: paint it first in a separate pass */ } y = py; o.heroBox = [top, py - top];
        }
        y += 40; F('700', 30, '"Barlow Condensed"'); T('MAKE THE 12-TEAM PLAYOFF', LX, y + 26, PAPER); y += 30 + 14;
        d.rows.forEach(function (r) { if (DR) { x.fillStyle = RULE; x.fillRect(LX, y, RX - LX, 2); } var rh = 14 + 84 + 14, my = y + 2 + rh / 2; circ(r.t, LX + 42, my, 42);
          F('700', 40); T(nm(r.t), LX + 108, my + (r.atl ? 0 : 14), PAPER); if (r.atl) { F('600', 24); T('at-large', LX + 108, my + 34, MUTE); }
          F('700', o.aft, '"Barlow Condensed"'); x.textAlign = 'right'; T(w2pc(r.a), RX, my + o.aft * 0.36, PAPER, 'right'); var aw = Math.max(150, x.measureText('100%').width + 24);
          var dd = Math.round(r.a * 100) - Math.round(r.b * 100), dt = dd ? (dd > 0 ? '\u25B2 +' : '\u25BC \u2212') + Math.abs(dd) + (Math.abs(dd) === 1 ? ' pt' : ' pts') : 'no change'; F('700', 24); var dw = x.measureText(dt).width + 18;
          if (o.was) { F('400', 28); T('was ' + w2pc(r.b), RX - aw, my - 8, MUTE, 'right'); }
          var pyy = o.was ? my + 6 : my - 18; F('700', 24); if (dd) rr(RX - aw - dw, pyy, dw, 36, 4, dd > 0 ? CY : AMB); T(dt, RX - aw - 9, pyy + 26, dd ? INK : MUTE, 'right');
          y += 2 + rh; });
        if (DR) { x.fillStyle = RULE; x.fillRect(LX, y, RX - LX, 2); } y += 2;
        if (BUL.length) {
          y += 36; var wt = y; F('400', 30); var BL = BUL.map(function (b) { return lines(b, RX - LX - 64 - 30); }), wy = y + 24;
          F('700', 30, '"Barlow Condensed"'); T('WHY', LX + 32, wy + 26, PAPER); wy += 30 + 18;
          var cap = o.whyCap; BL.forEach(function (ls, k) { if (cap !== undefined && k >= cap) return; if (DR) { x.fillStyle = CY; x.beginPath(); x.arc(LX + 32 + 6, wy + 20, 6, 0, 7); x.fill(); } F('400', 30); ls.forEach(function (l, j) { T(l, LX + 32 + 30, wy + 30 + j * 40, PAPER); }); wy += ls.length * 40 + 14; });
          if (cap !== undefined && cap < BL.length) { F('400', 26); T('See more at kicktipmedia.com', LX + 32 + 30, wy + 26, MUTE); wy += 40; }
          wy += 24 - 14; o.whyBox = [wt, wy - wt]; y = wy;
        }
        y += 44; if (DR) { x.fillStyle = RULE; x.fillRect(LX, y, RX - LX, 2); } y += 2 + 28;
        if (DR && wm) { var wh = 46, ww = wm.width * wh / wm.height; x.drawImage(wm, LX, y + 12, ww, wh); }
        F('400', 26); T('kicktipmedia.com', RX, y + 26, MUTE, 'right'); T('Simulation analysis, not betting advice', RX, y + 62, MUTE, 'right'); y += 72 + 48;
        return y;
      }
      var o = { logo: 150, aft: 72, was: true }, MAX = BUL.length ? 1920 : 1350, Hh = lay(o);
      if (Hh > MAX) { o.logo = 128; o.aft = 64; Hh = lay(o); }   /* SPEC shrink order: logo circles and the after % first */
      if (Hh > MAX) { o.was = false; Hh = lay(o); }   /* then the "was" text */
      while (Hh > MAX && BUL.length && (o.whyCap === undefined ? BUL.length : o.whyCap) > 1) { o.whyCap = (o.whyCap === undefined ? BUL.length : o.whyCap) - 1; Hh = lay(o); }
      c.height = Math.min(Math.ceil(Hh), BUL.length ? 2400 : 1350); x = c.getContext('2d'); x.fillStyle = INK; x.fillRect(0, 0, W, c.height);
      DR = true; if (o.heroBox) rr(LX, o.heroBox[0], RX - LX, o.heroBox[1], 12, FIELD); if (o.whyBox) rr(LX, o.whyBox[0], RX - LX, o.whyBox[1], 12, FIELD); lay(o);
      return new Promise(function (ok) { c.toBlob(function (b) { ok(b); }, 'image/jpeg', 0.92);   /* B3: JPEG for the iOS share header thumbnail */ });
    });
  }
  function w2prep(d) { S.w2blob = null; var tok = S.w2tok = {}; w2render(d).then(function (b) { if (S.w2tok === tok) S.w2blob = b; }, function () {}); }
  function w2share(btn) {
    var b = S.w2blob; if (!b) { btn.textContent = 'Preparing image\u2026'; w2render(S.w2d).then(function (bb) { S.w2blob = bb; btn.textContent = w2canShare() ? 'Share results' : 'Download image'; }); return; }
    var f = new File([b], 'KickTip What If.jpg', { type: 'image/jpeg', lastModified: Date.now() }); if (!(b.size > 0 && b.type === f.type)) { S.w2blob = null; btn.textContent = 'Preparing image\u2026'; w2render(S.w2d).then(function (bb) { S.w2blob = bb; btn.textContent = w2canShare() ? 'Share results' : 'Download image'; }); return; }   /* B3: never share an empty or mistyped blob */   /* B2: real PNG File from canvas.toBlob, shared alone (no title/text/url) so iOS can show a thumbnail */
    if (navigator.canShare && navigator.share && navigator.canShare({ files: [f] })) { navigator.share({ files: [f] }).catch(function () {}); return; }
    var u = URL.createObjectURL(b), a = D.createElement('a'); a.href = u; a.download = 'KickTip What If.jpg'; D.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
  }

  /* ccgcard: per-result conference championship picture for a multi-result answer. Deterministic: the most common pairing in each result's own simulations (r.after.pairs), same reading as the single-result header. */
  /* ccgcard3: restate the condition in plain words. loses_n items are grouped by count in question order; no Oxford comma; numbers spelled out. */
  function w2bcCond(items, nw) {
    function list(a) { return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }
    var groups = [], by = {}, parts = [], ok = true;
    items.forEach(function (it) {
      if (it.kind === 'loses_n') { var k = 'l' + it.losses; if (!by[k]) { by[k] = { n: it.losses, t: [] }; groups.push(by[k]); } by[k].t.push(nm(it.team)); }
      else if (it.kind === 'wins_out') groups.push({ s: nm(it.team) + ' wins out' });
      else if (it.kind === 'loses_out') groups.push({ s: nm(it.team) + ' loses out' });
      else if (it.kind === 'beats') groups.push({ s: nm(it.winner) + ' beats ' + nm(it.loser) });
      else ok = false;
    });
    if (!ok || !groups.length) return '';
    var lg = groups.filter(function (g) { return !g.s; }).length;
    groups.forEach(function (g) {
      if (g.s) { parts.push(g.s); return; }
      var gm = g.n === 1 ? 'game' : 'games';
      if (g.t.length === 1) parts.push(g.t[0] + ' loses ' + nw(g.n) + ' more ' + gm);
      else if (groups.length === 1) parts.push(list(g.t) + ' each lose ' + nw(g.n) + ' more ' + gm);
      else parts.push(list(g.t) + ' lose ' + nw(g.n) + ' more each');
    });
    return parts.length < 2 ? parts[0] : parts.slice(0, -1).join(', ') + ', and ' + parts[parts.length - 1];
  }
  /* ccgcard2: plain-words lead from the parse for shared-game branches, e.g. "Utah and BYU play each other, so one loss each means:" */
  function w2bcLead(parsed, live) {
    var sh = live.length && live[0].b.shared; if (!sh || !sh.length) return '';
    var W = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
    function nw(n) { return W[n] || String(n); }
    if (sh.length > 1) return 'These teams play each other in ' + nw(sh.length) + ' remaining games, so each result of those games is shown on its own:';
    var a = sh[0].winner, b = sh[0].loser, items = (parsed && parsed.items) || [];
    function ln(t) { for (var i = 0; i < items.length; i++) if (items[i].team === t && items[i].kind === 'loses_n') return items[i].losses; return null; }
    var others = items.some(function (it) { return [it.team, it.winner, it.loser].some(function (t) { return t !== undefined && t !== null && t !== a && t !== b; }); });
    if (others) {   /* ccgcard3: a team outside the shared game is named: restate the whole condition, then explain the split */
      var p2 = [nm(a), nm(b)];   /* ccgcard4: question order, same as the restatement and the rev 2 lines */
      var c1 = w2bcCond(items, nw);
      return (c1 ? c1 + '. ' : '') + p2[0] + ' and ' + p2[1] + ' play each other, so each result of that game is shown on its own:';
    }
    var la = ln(a), lb = ln(b), head = nm(a) + ' and ' + nm(b) + ' play each other, so ';
    function L(n) { return nw(n) + (n === 1 ? ' loss' : ' losses'); }
    if (la !== null && la === lb) return head + L(la) + ' each means:';
    if (la !== null && lb !== null) return head + nm(a) + ' losing ' + nw(la) + ' and ' + nm(b) + ' losing ' + nw(lb) + ' means:';
    return head + 'each result of that game is shown on its own:';
  }
  function w2bcHtml(parsed, res, outs, f) {
    var B = S.bundle, live = [], ci = 0, gb = (f && f.game_branches) || [], cards = [];
    res.branches.forEach(function (b, i) { if (b.res) live.push({ b: b, i: i, r: outs[ci++] }); });
    live.forEach(function (x, k) {
      var keep = S.w2, d = null; S.w2 = { r: x.r, res: x.b.res };
      try { d = w2data(parsed, x.r); } finally { S.w2 = keep; }
      var lab = gb[x.i] && gb[x.i].label ? String(gb[x.i].label) : (x.b.shared || []).map(function (g) { return nm(g.winner) + ' beats ' + nm(g.loser); }).join(' and ');
      var h = d && d.hero, body;
      if (!h) body = '<p class="w2bn">No conference championship picture for this result.</p>';
      else {
        var pair = '<span class="w2bt">' + w2logo(h.a, 20) + esc(nm(h.a)) + '</span> <span class="w2bv">vs</span> <span class="w2bt">' + w2logo(h.b, 20) + esc(nm(h.b)) + '</span>';
        body = '<p class="w2bc1">' + (h.sure ? esc(h.conf) + ' championship matchup in every simulation' : 'Most likely ' + esc(h.conf) + ' championship matchup') + '</p><p class="w2bp">' + pair + '</p>' +
          (h.sure ? '' : '<p class="w2bs">in ' + w2pc(h.pct) + ' of simulations</p>') +
          (h.next && h.next.length ? '<p class="w2bx">Other matchups: ' + h.next.map(function (y) { return esc(nm(y.a)).replace(/ /g, '&nbsp;') + '&nbsp;vs&nbsp;' + esc(nm(y.b)).replace(/ /g, '&nbsp;') + '&nbsp;' + w2pc(y.pct); }).join(' \u00b7 ') + '</p>' : '');
      }
      cards.push('<div class="w2bk" role="group" aria-label="Result ' + (k + 1) + '"><p class="w2bl"><b>Result ' + (k + 1) + '</b>' + (lab ? ': ' + esc(lab) : '') + '</p>' + body + '</div>');
    });
    if (!cards.length) return '';
    var lead = ''; try { lead = w2bcLead(parsed, live); } catch (e) { lead = ''; }
    return '<section class="w2bcs" aria-label="Conference championship picture for each result"><h3 class="w2bhd">Conference championship picture for each result</h3><p class="mn">Each result was simulated on its own. Simulation analysis&nbsp;only.</p>' + (lead ? '<p class="w2bld">' + esc(lead) + '</p>' : '') + cards.join('') + '</section>';
  }
  function w2reach(d) { if (!d || !d.reach || !d.reach.length) return ''; return '<p class="w2rc"><b>Reach the conference championship</b> (share of simulations, before \u2192 after): ' + d.reach.map(function (x) { return esc(nm(x.t)) + (x.conf ? ' (' + esc(x.conf) + ')' : '') + ' ' + w2pc(x.b) + ' \u2192 ' + w2pc(x.a); }).join(' \u00b7 ') + '</p>'; }
  function w2wrap(inner) { return '<div class="w2why"><button type="button" class="w2wb" data-w2why aria-expanded="false" aria-controls="w2wbody">Why?<span class="w2ch" aria-hidden="true"></span></button><div id="w2wbody" class="w2wbd" hidden>' + inner + '</div></div>'; }
  function viewAnswer(t, parsed, res, ans, N, card, noTables) {
    var w2 = '', d = null; if (S.w2 && S.w2.r) { try { w2css(); d = w2data(parsed, S.w2.r); w2 = (d.hero || d.rows.length) ? w2Html(d) : ''; } catch (e) { w2 = ''; d = null; } }
    var bc = S.w2bc || ''; S.w2bc = null; if (bc) { try { w2css(); } catch (e) {} }
    var det = bc + (card || '') + (noTables ? '' : scenarioTables(ans, parsed, res)) + foot(ans, N) + '<p class="mn">Games not in the scenario play out as simulated.</p>';
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + chipHtml(parsed, res) + (w2 ? w2 + w2wrap(w2reach(d) + det) : det) + REGEN + '<p class="mn">' + onb() + '</p>' + LINKS + '</div>');
    S.w2 = null; S.w2d = w2 ? d : null; if (S.w2d) w2prep(S.w2d);
  }
  function viewNeed(t, ans, N) {
    var rows = ans.games.map(function (g) { return '<tr><td>Wk ' + g.week + ' ' + (g.site === 'away' ? 'at' : 'vs') + ' ' + esc(g.opponent) + (g.site === 'neutral' ? ' (neutral)' : '') + '</td><td class="n">' + esc(g.if_win_text) + '</td><td class="n">' + esc(g.if_lose_text) + '</td><td class="n dl">' + esc(g.swing_text.replace(/^-/, MINUS)) + '</td></tr>'; }).join('');
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + '<p><b>' + esc(ans.team_name) + '</b>: chance to ' + esc(ans.goal_label) + ' right now is <b>' + esc(ans.baseline_text) + '</b>.</p>' +
      (rows ? '<table class="ba"><caption>Chance to ' + esc(ans.goal_label) + ', by result of each remaining game</caption><thead><tr><th>Game</th><th class="n">If win</th><th class="n">If lose</th><th class="n">Swing</th></tr></thead><tbody>' + rows + '</tbody></table>' : '<p>No remaining games.</p>') +
      foot(ans, N, S.wi && S.wi.seasons) + '<p class="mn">' + esc(ans.notes[0]) + ' ' + esc(ans.notes[1]) + '</p>' + REGEN + '<p class="mn">' + onb() + '</p>' + LINKS + '</div>');
  }
  function viewBaseline(t, ans, N) {
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + '<table class="ba"><caption>' + esc(ans.team_name) + ', right now</caption><thead><tr><th>Outcome</th><th class="n">Chance</th></tr></thead><tbody>' +
      ans.cells.map(function (c) { return '<tr><td>' + esc(c.label) + '</td><td class="n">' + esc(c.text) + '</td></tr>'; }).join('') + '</tbody></table>' + foot(ans, N) + REGEN + '<p class="mn">' + onb() + '</p>' + LINKS + '</div>');
  }

  /* ---------- data and engine (requested when the panel opens) ---------- */
  function loadScript(src) {
    return new Promise(function (ok, bad) { var s = D.createElement('script'); s.src = src; s.async = false; s.onload = ok; s.onerror = bad; D.head.appendChild(s); });
  }
  function fetchJson(u) { return fetch(u, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function mUrl(id, f) { return id === 'blend' ? '/data/' + f : '/data/m/' + id + '/' + f; }
  /* One model at a time is current (S.bundle / S.wi); each model's bundle, what-if index and shards are fetched once and kept. The worker gets each bundle once. */
  function useModel(id) { var m = S.M[id]; S.model = id; S.bundle = m.bundle; S.wi = m.wi; miaName(S.bundle); }
  function miaName(B) { try { var c = B && B.aliases && B.aliases.map && B.aliases.map.miami; if (!c || c.length < 2) return; c.forEach(function (t) { var T = B.teams[t]; if (T && T.n === 'Miami') T.n = 'Miami (FL)'; if (T && T.s === 'Miami') T.s = 'Miami (FL)'; });   /* B5g: the short name too, so suggestions read "What if Miami (FL) wins out?" and never bring back Did you mean */ } catch (e) {} }   /* B5f: two Miamis: Miami (FL) is named like Miami (OH) everywhere (chips, labels, result), never a bare Miami */
  function ensureData() {
    var id = pickModel();
    if (!S.scripts) S.scripts = Promise.all([loadScript('/assets/ks/parse.js?v=479524fc87'), loadScript('/assets/ks/scenario.js?v=b47036efd9'), loadScript('/assets/ks/answer.js?v=d98fa6375e')]).then(function () { var w = S.worker = new Worker('/assets/chat-worker.js?v=a49e07625a'); w.addEventListener('error', function (e) { if (S.worker === w) { if (e.preventDefault) e.preventDefault(); workerFailed(); } }); w.addEventListener('messageerror', function () { if (S.worker === w) workerFailed(); }); }).catch(function (e) { S.scripts = null; throw e; });
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
  /* scenario facts card (scn_a1): a deterministic card built from the official-rules solver (ccgsim.js) for conference what-ifs that settle a named team's final record. No AI, no network beyond two same-origin data files, only when the question passes the cheap gate. Set SCNCARD to false to switch the card off; nothing else changes. */
  var SCNCARD = true;
  function loadExplain(f) {   /* f = the checked facts module; the two data files and the solver load only after the cheap gate passes */
    if (!S.ex) S.ex = Promise.all([window.KTCcg ? 0 : loadScript('/assets/ccgsim.js?v=f3d43773c1'), fetchJson('/data/ccg-sim.json'), fetchJson('/data/ccg-rules.json')]).then(function (r) { return window.KTCcg ? { ccg: r[1], rules: r[2] } : null; }).catch(function () { S.ex = null; return null; });
    return S.ex;
  }
  function explainCard(parsed, res, B) {   /* resolves to the facts object or null; never rejects */
    if (!SCNCARD) return Promise.resolve(null);
    return (window.KTExplain ? Promise.resolve() : loadScript('/assets/ks/explain.js?v=5aa5f5d0a1')).then(function () {
      if (!window.KTExplain || !KTExplain.gate(parsed, res, B).ok) return null;
      return loadExplain().then(function (d) {
        if (!d) return null;
        var xo = { parsed: parsed, res: res, bundle: B, ccg: d.ccg, rules: d.rules, KTCcg: window.KTCcg, itemText: itemText }, f = res.branches && KTExplain.buildBranched ? KTExplain.buildBranched(xo) : KTExplain.build(xo);
        return f && f.ok === false ? null : f;
      });
    }).catch(function () { return null; });
  }
  /* scenario write-up (scn_a2): ONE short AI paragraph above the figures of the facts card, ONLY when the Worker flag AI_SCN is on (/api/ask-config says scn:true), Use AI is on, and the facts card was shown. The browser sends only the card's own facts (names and numbers KickTip calculated), never the typed text.
     The reply is checked here, in the browser, by assets/ks/scnai.js: every number, team, conference and rule name must be one of the card's own, hedge words required, banned words, length, plain text. Anything wrong, slow (7 s), capped, flagged off or an error: the card stays exactly as it is (no AI text, no error).
     Set SCNAI to false to switch it off in the page. One write-up per card; the same facts are never sent twice in a visit (cached); at most 3 per visit. */
  var SCNAI = true, SCNAI_FALLBACK_LEAD = false, SCNAI_MAX = 3;
  function scnKnown(B) { var o = []; (B.teams || []).forEach(function (t) { if (t.n) o.push(t.n); if (t.f && t.f !== t.n) o.push(t.f); if (t.s) o.push(t.s); }); return o; }
  function scnShow(el, id, prose, lead) {
    if (!el || !D.body.contains(el) || el.getAttribute('data-scn') !== String(id) || el.querySelector('.sxai')) return;
    var h = el.querySelector('h3'), box = D.createElement('div'), p = D.createElement('p'), g, K = window.KTScnAI;
    box.className = 'sxai'; p.className = 'sxw'; p.textContent = prose; box.appendChild(p);
    if (lead) { p.className = 'sxw sxn'; } else { g = D.createElement('p'); g.className = 'sxg'; g.textContent = K.COPY.tag; box.appendChild(g); }
    if (h && h.nextSibling) h.parentNode.insertBefore(box, h.nextSibling); else el.insertBefore(box, el.firstChild);
  }
  function scnWrite(f, B) {
    try {
      var K = window.KTAI; if (!SCNAI || !f || !K || !K.scnOn || !K.scnOn() || !K.isOn()) return;
      var el = bd.querySelector('.sx'); if (!el) return;
      var id = S.scnSeq = (S.scnSeq || 0) + 1; el.setAttribute('data-scn', String(id));
      if (S.scnCall) { S.scnCall.cancel(); S.scnCall = null; }
      (window.KTScnAI ? Promise.resolve() : loadScript('/assets/ks/scnai.js?v=9f28887139')).then(function () {
        var Q = window.KTScnAI, c = Q && Q.compact(f); if (!c) return;
        var key = JSON.stringify(c), hit = S.scnCache && S.scnCache[key];
        if (hit) return scnShow(el, id, hit);
        if ((S.scnN || 0) >= SCNAI_MAX) return;
        S.scnN = (S.scnN || 0) + 1;
        var A = S.ai, tk = A && A.tk && Date.now() - A.tk.at < 540000 ? A.tk.t : null; if (A) A.tk = null;
        var call = S.scnCall = K.scn(c, tk);
        return call.promise.then(function (r) {
          if (S.scnCall === call) S.scnCall = null;
          if (!r || r.cancelled) return;
          if (!r.ok) { if (SCNAI_FALLBACK_LEAD) scnShow(el, id, Q.COPY.fallbackLead, true); return; }
          var v = Q.validate(r.prose, f, { known: scnKnown(B), vocab: window.KTExplain ? KTExplain.vocab(f) : null });
          if (!v.ok) { if (SCNAI_FALLBACK_LEAD) scnShow(el, id, Q.COPY.fallbackLead, true); return; }
          (S.scnCache = S.scnCache || {})[key] = v.prose; scnShow(el, id, v.prose);
        });
      }).catch(function () { });
    } catch (e) { }
  }
  function runEngine(forced, constraints, baseOnly, onTick, o) {
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
      w.postMessage({ op: 'run', id: id, model: model, forced: forced, constraints: constraints, chunks: (o && o.chunks) || CHUNKS, minChunks: o ? o.minChunks : MINCH, per: PER, budget: o ? o.budget : BUDGET, seedBase: SEED0 + 100 * S.seedN, baseOnly: baseOnly });
    });
  }
  function getShards(weeks) {
    var m = S.M[S.model];
    return Promise.all(weeks.map(function (wk) {
      if (m.shards[wk]) return 0; var f = S.wi.shards[wk]; if (!f) { m.shards[wk] = {}; return 0; }
      return fetchJson(mUrl(S.model, 'whatif/' + f)).then(function (j) { m.shards[wk] = j; });
    }));
  }

  /* ---------- Compare (A/B/C what-ifs). compare.js + compare.css load when the panel opens (same-origin, ?v= tokens) on every page that has the panel; whether Compare is ON is decided inside compare.js (KT_COMPARE_HOME_ONLY, default: everywhere). If either file fails to load, single what-ifs work exactly as before. ---------- */
  var CMP_JS = '/assets/compare.js?v=098fb215c8', CMP_CSS = '/assets/compare.css?v=ff7a4cb4eb';
  function loadCompare() {
    if (S.cmpP) return S.cmpP;
    var css = new Promise(function (ok) { if (D.querySelector('link[href^="/assets/compare.css"]')) { ok(); return; } var l = D.createElement('link'); l.rel = 'stylesheet'; l.href = CMP_CSS; l.onload = l.onerror = function () { ok(); }; D.head.appendChild(l); });
    var js = window.KTCompare ? Promise.resolve() : loadScript(CMP_JS).catch(function () { /* single what-ifs still work */ });
    return (S.cmpP = Promise.all([css, js]));
  }
  function cmpApi() { return { S: S, D: D, bd: bd, input: input, cnt: cnt, show: show, esc: esc, bubble: bubble, REQ: REQ, SPINCARD: SPINCARD, LINKS: LINKS, ONBROWSER: ONBROWSER, onb: onb, cap: cap, foot: foot, runEngine: runEngine, itemText: itemText, commas: commas, viewInfo: viewInfo, viewRefusal: viewRefusal, viewClarify: viewClarify, viewError: viewError, isNarrow: isNarrow }; }

  /* ---------- AI mode on the home panel (aihome1). OFF unless /api/ask-config says enabled:true. ----------
     Flag off (or any config problem): the only thing that happens is one GET /api/ask-config when the panel first opens; nothing is added to the panel and the panel behaves exactly as before.
     Flag on: ai-client.js + ai-box.css (the same two files the conference-page AI box uses, unchanged) load, the panel gets the Use AI switch, Learn more, the short note and the Review button.
     Turnstile loads only when the panel is opened or the box is focused with Use AI on (KTAI.prepare). The question is sent once, when the visitor taps Review (KTAI.ask), nothing is sent while typing, and the token is reset after every ask (inside ai-client.js).
     The AI only reads the question: its answer goes through KTCompare.fromAskResponse and the page's own resolver, the visitor sees what was understood, and nothing runs until they tap Run. Model prose is never shown.
     Any answer other than ok:true (no network, timeout, verification, errors) says "AI unavailable, using standard parser", and the daily limit says "Daily AI limit reached, using standard answers", and the standard parser reads the question in the browser. */
  /* ---------- compact1: compact composer (Use AI on). Strings behind the notice are the approved ones (KTAI.SHORT / KTAI.FULL / REVTERMS); the visible line is variant C1. No new state, no storage, no cookie. ---------- */
  function cmpTerms() { return REVTERMS.replace('<p class="rn rvn">', '<p>').replace('<a href="/disclaimer/">', '<a class="il" href="/disclaimer/">'); }   /* rev2: the notice's acceptance paragraph is the approved REVTERMS string itself (same text, Full terms link gets the .il class), no retyped copy */
  var CMP_LINE = 'KickTip is not a betting site.';   /* variant C1: the only always-visible line; the acceptance wording, Full terms link and the Cloudflare notice are behind "Notice and terms" */
  function cmpLine() { var A = S.ai; return (A && !A.seen ? window.KTAI.SHORT + ' ' : '') + CMP_LINE; }   /* first use: the approved Cloudflare sentence + the C1 line, until the first Review tap or the first open of the notice in this page load (memory only), then folded into the notice */
  function cmpSeen() { var A = S.ai; if (A.seen) return; A.seen = true; var cl = D.getElementById('kcl'); if (cl) cl.textContent = cmpLine(); }
  function aiPaintCompact() {
    var A = S.ai, on = A.on, sw = form.querySelector('.swc');
    if (!sw) {
      sw = D.createElement('button'); sw.type = 'button'; sw.className = 'sw3 swc'; sw.id = 'kaisw'; sw.setAttribute('role', 'switch'); sw.setAttribute('aria-label', 'Use AI to read my question');
      sw.innerHTML = '<span class="trk" aria-hidden="true"><i></i></span><span class="swt">AI <span class="sv"></span></span>'; form.appendChild(sw);
    }
    sw.setAttribute('aria-checked', on ? 'true' : 'false'); sw.querySelector('.sv').textContent = on ? 'On' : 'Off';
    A.box.innerHTML = on ? '<div class="cn"><p class="cnl" id="kcl">' + esc(cmpLine()) + '</p><button type="button" class="cnb" id="kcnb" aria-expanded="' + (A.learn ? 'true' : 'false') + '" aria-controls="kcn">Notice and terms ' + AI_CHEV + '</button></div>' +
      '<div class="lmx cnx" id="kcn" role="region" tabindex="-1" aria-label="Notice and terms"' + (A.learn ? '' : ' hidden') + '>' +
        '<p class="cx1">' + esc(window.KTAI.SHORT) + '</p>' +
        cmpTerms() + '<div class="sep"></div>' +
        '<p>' + esc(window.KTAI.FULL) + '</p><p class="lk2"><a href="/privacy/#ai-mode">Read the privacy page</a></p></div>' : '';
  }
  function cnSync() { var A = S.ai, b = D.getElementById('kcnb'), x = D.getElementById('kcn'); if (b) b.setAttribute('aria-expanded', A.learn ? 'true' : 'false'); if (x) x.hidden = !A.learn; }
  var AI_JS = '/assets/ai-client.js?v=7f66b6f6e3', AI_CSS = '/assets/ai-box.css?v=46b3b821ef';
  var ONB_AI = 'Calculated in your browser from public model data.';
  var REVTERMS = '<p class="rn rvn">Tapping Review accepts the terms. Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></p>';
  var AI_INFO = '<svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="8.2" fill="none" stroke="currentColor" stroke-width="1.8"></circle><path d="M10 9v5" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><circle cx="10" cy="6.2" r="1.2" fill="currentColor"></circle></svg>';
  var AI_SWAP = '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2 5h11M10 2l3 3-3 3M14 11H3M6 8l-3 3 3 3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>';
  var AI_CHEV = '<svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true" focusable="false"><path d="M5 8l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"></path></svg>';
  var AI_NOSEND = { empty: 1, too_long: 1, betting_or_gambling_request: 1, off: 1 };   /* ask() answered before any request left the browser */
  function rv() { return !!(S.ai && S.ai.live && S.ai.on); }   /* Review mode: the AI box is live and Use AI is on */
  function cap() { return 300; }   /* B5: same limit with AI off, so a stack of 8 games fits */
  function onb() { return S.ai && S.ai.read ? ONB_AI : ONBROWSER; }
  function emptyNote() { return 'Tap a question to fill the box, or type your own, then tap ' + (rv() ? 'Review. KickTip shows what it understood before anything runs. ' : 'Run. ') + 'Each run re-simulates the season in your browser. It uses the model selected on this page (the KickTip blend unless you chose another).'; }
  /* ---------- kt-tb4: toolbox hook (Phase 0b). Everything below is inert unless GET /api/ask-config carries "tb" (the one switch in _worker.js). While it is off nothing here runs, nothing is requested, nothing is stored. ---------- */
  var TB_JS = '/assets/tb/hook.js?v=0e2facb68e', TBS = { ids: null, hook: null, hp: null, dead: false, api: null };
  function tbBoot(ids) {
    if (TBS.ids || !Array.isArray(ids)) return;
    var ok = ids.filter(function (x) { return typeof x === 'string' && /^[a-z][a-z0-9_]{2,40}$/.test(x); }).slice(0, 40); if (!ok.length) return;
    TBS.ids = ok; bd.addEventListener('click', tbClick, true);
    TBS.hp = loadScript(TB_JS).then(function () { if (!window.KTTBHook) throw new Error('hook'); TBS.hook = window.KTTBHook.init(ok); }).catch(function () { TBS.dead = true; });
  }
  function tbResume(t, tch) {   /* B4f: a team the visitor already picked in a toolbox "Did you mean" card stays picked (slug -> team index), so the same question is never asked twice */
    if (!tch || typeof tch !== 'object' || !Object.keys(tch).length) { if (aiGate(t)) return; input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); return; }
    input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true;
    ensureData().then(function () { var B = S.bundle, pc = {}, n = 0; Object.keys(tch).forEach(function (a) { for (var i = 0; i < B.teams.length; i++) if (B.teams[i] && B.teams[i].g === tch[a]) { pc[a] = i; n++; break; } }); ask(t, n ? { choices: pc } : {}); }, function () { viewError(t); }); }   /* the question goes the way it always went */
  function tbApiGet() {
    return TBS.api || (TBS.api = {
      loading: function (t) { show('loading', bubble(t) + '<div class="ac" aria-label="Loading answer">' + REQ + SPINCARD + '<p class="meta">Loading the latest schedule and results&hellip;</p><div class="sk w90"></div><div class="sk w70"></div><div class="sk w80"></div></div>', { focus: false }); },
      cards: function (t, html) { S.lastQ = t; input.value = ''; cnt.textContent = '0/' + cap(); show('tb', bubble(t) + html); },
      resume: tbResume,
      edit: function (t) { input.disabled = false; input.value = t; cnt.textContent = input.value.length + '/' + cap(); send.disabled = false; fieldOn(true); }
    });
  }
  function tbTry(t) {   /* true = the toolbox has the question (it ends in a card or in tbResume) */
    if (!TBS.ids || TBS.dead) return false;
    var q = String(t).trim(); if (!q || q.length > cap()) return false;
    if (TBS.hook) return TBS.hook.submit(q, tbApiGet());
    if (!TBS.hp) return false;
    TBS.hp.then(function () { if (!(TBS.hook && TBS.hook.submit(q, tbApiGet()))) tbResume(q); });
    return true;
  }
  function tbRouterOpts() {   /* router1: ask the Worker to try the tool router first, only when ask-config said router:true and the toolbox is loaded; null = exactly the old request */
    try {
      if (!(window.KTAI && window.KTAI.routerOn && window.KTAI.routerOn()) || !TBS.hook || TBS.dead || typeof TBS.hook.routed !== 'function') return null;
      var m = D.getElementById('main'), k = m && m.getAttribute('data-page'), rp = { m: k === 'team' || k === 'conference' ? k : 'home' };
      if (rp.m === 'conference') rp.c = m.getAttribute('data-conf') || '';
      return { router: true, rp: rp };
    } catch (e) { return null; }
  }
  function tbClick(e) {   /* capture phase: taps inside a toolbox card never reach the page's own handler */
    var el = e.target && e.target.closest ? e.target.closest('.tbox button[data-q],.tbox button[data-pick],.tbox button[data-goal],.tbox button[data-conf],.tbox a[data-tb-change]') : null;
    if (!el || !bd.contains(el) || !TBS.hook) return;
    if (TBS.hook.click(el, tbApiGet())) { e.preventDefault(); e.stopPropagation(); }
  }

  function aiInit() {
    if (S.ai) return;
    var A = S.ai = { live: false, on: false, pending: null, read: false, fbn: false, via: 'ai', text: '', scen: [], edited: false, call: null, thinking: false, learn: false, seen: false, bad: '', mounted: false, ts: null };
    var ctl = typeof AbortController === 'function' ? new AbortController() : null, tm = setTimeout(function () { if (ctl) ctl.abort(); }, 5000);
    A.pending = fetch('/api/ask-config', { credentials: 'omit', cache: 'no-store', signal: ctl ? ctl.signal : undefined }).then(function (r) { clearTimeout(tm); return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.tb) tbBoot(j.tb);
      if (!j || j.enabled !== true || typeof j.sitekey !== 'string' || !j.sitekey) return false;
      var css = new Promise(function (ok) { var l = D.createElement('link'); l.rel = 'stylesheet'; l.href = AI_CSS; l.onload = l.onerror = function () { ok(); }; D.head.appendChild(l); });
      return Promise.all([css, window.KTAI ? 0 : loadScript(AI_JS)]).then(function () { return window.KTAI.config(); }).then(function (cfg) { if (!cfg) return false; A.live = true; A.on = window.KTAI.isOn(); aiMount(); return true; });
    }).catch(function () { return false; }).then(function (ok) { clearTimeout(tm); A.pending = null; return ok; });
  }
  function aiMount() {
    var A = S.ai; if (A.mounted || !panel) return; A.mounted = true;
    cmp.classList.add('aic', 'cmpc');
    A.box = D.createElement('div'); A.box.id = 'kaix'; A.ts = D.createElement('div'); A.ts.className = 'ts'; A.ts.id = 'kts';
    A.rvn = D.createElement('div'); A.rvn.innerHTML = REVTERMS; A.rvn = A.rvn.firstChild;
    var run = cmp.querySelector('.rtx') || cmp.querySelector('.rn'); cmp.insertBefore(A.box, run);   /* B1: the terms line now sits in a .rtx wrapper; anchor on it (a nested .rn is not a child of cmp) */ cmp.insertBefore(A.ts, run); cmp.insertBefore(A.rvn, run);
    A.rbar = D.createElement('div'); A.rbar.className = 'rbar'; A.rbar.id = 'krb'; A.rbar.hidden = true; panel.insertBefore(A.rbar, cmp);
    cmp.addEventListener('click', aiCmpClick); cmp.addEventListener('mousedown', function (e) { if (e.target.closest && e.target.closest('#kcnb,#kaisw')) e.preventDefault(); });   /* compact1: tapping the notice control or the switch must not move focus (keyboard stays up) */
    A.rbar.addEventListener('click', aiBarClick); bd.addEventListener('click', aiBodyClick); bd.addEventListener('click', function () { if (S.ai.learn) { S.ai.learn = false; cnSync(); } }); input.addEventListener('focus', aiOpened);
    aiPaintBox(); aiMode();
    var n = bd.querySelector('.note'); if (view === 'empty' && n) n.textContent = emptyNote();
    if (!panel.hidden) aiOpened();
  }
  function aiOpened() { if (rv() && window.KTAI) window.KTAI.prepare(S.ai.ts); }   /* Turnstile: first open or focus with Use AI on, never earlier */
  function aiPaintBox() { aiPaintCompact(); }   /* compact1: the old Use AI row / Learn more markup is no longer rendered (rev2: removed) */
  function aiMode() {   /* labels, cap and terms text follow Use AI */
    var A = S.ai, on = rv(), rn = cmp.querySelector('.rtx') || cmp.querySelector('.rn:not(.rvn)');
    input.maxLength = cap(); cnt.textContent = input.value.length + '/' + cap();
    if (rn) { rn.hidden = rn.classList.contains('rtx') ? false : on; rn.classList.toggle('off', !on); rn.classList.toggle('aion', !!on); }   /* B3: the one-line Run-gate stays visible in every composer state */ A.rvn.hidden = true; var cl = D.getElementById('kcl'); if (cl) cl.textContent = cmpLine();   /* compact1: A.rvn stays in the DOM, hidden */
    input.setAttribute('aria-describedby', on ? 'kcnt kcl' : 'kcnt');
    send.classList.toggle('rev', on);
    if (!S.run && !A.thinking) { send.setAttribute('aria-label', on ? 'Review how KickTip understood my question' : 'Run'); send.textContent = on ? 'Review' : 'Run'; }
    var fl = D.querySelectorAll('.pnl .rtx .rt1'), fi; for (fi = 0; fi < fl.length; fi++) fl[fi].__rtk = null; rtFit(); (W.requestAnimationFrame || setTimeout)(rtFit);   /* B4f2: refit on every AI toggle, both ways */
  }
  function aiChrome(v) {   /* called at the end of show() */
    var A = S.ai; if (!A || !A.live) return;
    var und = v === 'understood', th = v === 'thinking';
    cmp.hidden = und; A.rbar.hidden = !und; if (und) A.rbar.innerHTML = aiBarHtml();
    input.disabled = th;
    if (th) { send.classList.add('run'); send.disabled = true; send.setAttribute('aria-busy', 'true'); send.setAttribute('aria-label', 'Reading your question'); send.innerHTML = SHIELD + '<span>Reading\u2026</span>'; }
    else if (!S.run) { send.classList.remove('run'); send.removeAttribute('aria-busy'); aiMode(); }
    if (A.fbn && !und && !th && v !== 'running' && v !== 'loading' && v !== 'empty') {
      var u = bd.querySelector('.ub'), h = '<p class="fbn" role="status">' + AI_INFO + '<span>' + esc(typeof A.fbn === 'string' ? A.fbn : window.KTAI.FALLBACK) + '</span></p>';
      if (u) u.insertAdjacentHTML('afterend', h); else bd.insertAdjacentHTML('afterbegin', h);
    }
  }
  function aiCmpClick(e) {
    var A = S.ai, b = e.target.closest ? e.target.closest('button') : null; if (!b || !cmp.contains(b) || A.thinking) return;
    if (b.id === 'kaisw') {
      A.on = !A.on; window.KTAI.setOn(A.on); if (!A.on) A.learn = false;
      aiPaintBox(); aiMode(); var n = bd.querySelector('.note'); if (view === 'empty' && n) n.textContent = emptyNote();
      if (A.on) aiOpened(); return;   /* compact1: switch updated in place, no focus() call (keeps the keyboard up) */
    }
    if (b.id === 'kcnb') { A.learn = !A.learn; if (A.learn) cmpSeen(); cnSync(); return; }   /* compact1: no focus() call */
    if (b.id === 'kailm') { A.learn = !A.learn; aiPaintBox(); var l = D.getElementById('kailm'); if (l) l.focus(); }
  }
  function aiGate(t) {   /* the submit handler asks first: true = the AI flow took the question */
    var A = S.ai; if (!A) return false;
    if (A.pending) {   /* the config answer has not arrived yet: wait for it, then do what the page would have done */
      A.pending.then(function () {
        if (S.run || A.thinking) return;
        if (tbTry(t)) return;
        if (rv()) aiReview(t); else { input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); }
      });
      return true;
    }
    if (rv() && !A.thinking) { aiReview(t); return true; }
    return false;
  }
  var W2BADC = /(?:^|[^\w.])(?:[-\u2212\u2013]\s*|minus\s+|negative\s+)\d+(?:[.,]\d+)?\s*(?:more\s+)?(?:loss(?:es)?|games?|wins?)\b|\b\d+\s*(?:[.,]\d+|\/\d+|\s+and\s+a\s+half)\s*(?:more\s+)?(?:loss(?:es)?|games?|wins?)\b|\b(?:half|a half|one and a half)\s+(?:a\s+)?(?:loss|game|win)\b/i;   /* B3: same rule as KTParse.badCount; parse.js may not be loaded yet */
  function aiReview(t) {
    var A = S.ai, g = window.KTAI.guard(t); t = String(t).trim(); cmpSeen();
    A.read = false; A.fbn = false; A.edited = false; A.text = t; A.tk = null;
    if (!g.ok || W2BADC.test(t)) { input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); return; }
    A.v2lines = null; if (window.KTAI.v2On && window.KTAI.v2On()) { aiReviewV2(t); return; }   /* aiv2: AI-primary reader, only when ask-config says v2:true (AI_V2=on); off = everything below, unchanged */   /* B3: bad counts also stay local */   /* empty, too long or gambling words: the standard parser answers, nothing is sent */
    if (AI_LOSSQ.test(String(t).toLowerCase()) || AI_LOSSQ.test(window.KTParse ? KTParse.norm(t) : String(t).toLowerCase())) {   /* B1: parse.js may not be loaded yet on the first question */   /* router2: "end with just one loss" is read by the standard parser (exact losses, the rest wins): no AI call, no cap use */
      ensureData().then(function () { var p = KTParse.parse(t, S.bundle.aliases, { choices: S.choices }); if (p && p.clarify && p.clarify_reason === 'ambiguous_team') { input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); return; }   /* B5g: bare Miami with a count resolves locally too, no AI call */ if (p.intent === 'scenario' && !p.refusal && !p.clarify && p.items && p.items.length && (p.items.some(function (x) { return x.kind === 'loses_n' || x.kind === 'wins_n_of_m'; }) || (/\b(?:no|zero) loss(?:es)?\b/.test(KTParse.norm(t)) && p.items.some(function (x) { return x.kind === 'wins_out'; })))) aiStd(false); else aiSend(t); }, function () { aiSend(t); });
      return;
    }
    ensureData().then(function () { var p = KTParse.parse(t, S.bundle.aliases, { choices: S.choices }); if (p && p.clarify && p.clarify_reason === 'ambiguous_team') { input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); } else aiSend(t); }, function () { aiSend(t); });   /* B5f: an ambiguous team (bare Miami) is resolved here first: Did you mean, no AI call */
  }
  var AI_LOSSQ = /\bloss(?:es)?\b|\bwinless\b|\ball but\b|\b\d{1,2} ?[-\u2013] ?\d{1,2}\b|\b\d{1,2} \d{1,2}\b|\b(?:loses?|drops?|falls?|wins?|takes?|goes down|picks up|goes|finishes|ends) (?:just |only |exactly |a total of )?(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an|another)\b/;   /* B5b: every count form (wins, losses, records) is read by the standard parser first */   /* B5: "drops 2" too */
  /* router2: a read from the AI that cannot be right is never shown as a card. Wins/losses counts must be numbers the visitor typed, and a loss-count question never becomes wins-out / loses-out / wins N. */
  function aiSane(t, scen, cand) {   /* aiv2: cand (the v2 candidate ids) replaces the exact-mention check, so a typo the Worker matched to a real team is kept */
    var q = KTParse.norm(t), W = { 0: 'zero none no', 1: 'one a single once', 2: 'two twice', 3: 'three thrice', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten' };
    function typed(n) { if (new RegExp('(^| )' + n + '( |$)').test(q)) return true; return (W[n] || '').split(' ').some(function (w) { return w && new RegExp('(^| )' + w + '( |$)').test(q); }); }
    var lossQ = /\bloss(?:es)?\b/.test(q) && /\b(?:with|only|just|exactly|no|zero|end|ends|finish|finishes|go|goes|lose|loses)\b/.test(q) || /\b(?:loses?|drops?) (?:just |only |exactly )?(?:\d+|two|three|four|five|six|seven|eight|nine|ten)\b/.test(q);   /* B5: "drops 2" is a loss count, never loses out */
    var men = null; try { var lp = KTParse.parse(t, S.bundle.aliases, { choices: S.choices }); if (lp && lp.mentions && lp.mentions.length) { men = {}; lp.mentions.forEach(function (m) { if (m.team !== null && m.team !== undefined) men[m.team] = 1; (m.candidates || []).forEach(function (c) { men[c] = 1; }); }); } } catch (e) { men = null; }
    if (cand) { men = {}; cand.forEach(function (x) { men[x] = 1; }); }
    function named(it) { if (!men) return true; return ['team', 'winner', 'loser'].every(function (k) { return it[k] === undefined || it[k] === null || men[it[k]]; }); }   /* B5d: an AI read that names a team the visitor did not mention is not shown (falls back to the standard parser) */
    return scen.every(function (s) {
      return (s.parsed.items || []).every(function (it) {
        if (!named(it)) return false;
        if (it.kind === 'wins_n_of_m') return !lossQ && it.n <= it.m && typed(it.n);
        if (it.kind === 'wins_out' || it.kind === 'loses_out') return !lossQ || !!(cand && /\b(?:out|the rest|winless|the table)\b/.test(q));   /* aiv2: "loses out" typed next to a loss count is kept */
        return true;
      });
    });
  }
  function aiSend(t) {   /* B1: never spin forever: a throw falls back to the standard parser, and a 15 s guard covers the whole read */
    try { aiSend0(t); } catch (e) { var A = S.ai; if (A.call) { try { A.call.cancel(); } catch (e2) {} } A.call = null; A.thinking = false; try { aiStd(window.KTAI.fallbackText('error')); } catch (e3) { viewError(t); } }
  }
  function aiSend0(t) {
    var A = S.ai;
    A.thinking = true;
    show('thinking', bubble(t) + '<div class="spin kbb" role="status">' + SHIELD + '<div class="kbt"><p class="spcap">Reading your question\u2026</p><p class="spcap kb2">Nothing is calculated yet.</p></div></div><button type="button" class="gb" data-aicancel>Cancel</button>', { focus: false });
    var call = A.call = window.KTAI.ask('home', null, t, tbRouterOpts());
    var wd = A.wd = setTimeout(function () { if (A.wd !== wd || view !== 'thinking') return; if (A.call === call) { try { call.cancel(); } catch (e) {} } A.call = null; A.thinking = false; try { aiStd(window.KTAI.fallbackText('timeout')); } catch (e) { viewError(t); } }, 15000);
    var dataP = ensureData().then(function () { return loadCompare(); }).then(function () { return true; }, function () { return false; });
    Promise.all([call.promise, dataP]).then(function (a) {
      if (A.call !== call) return;
      var r = a[0]; A.call = null; A.thinking = false;
      if (r.cancelled) return;
      A.tk = r.tk ? { t: r.tk, at: Date.now() } : null;   /* scn_a2: a counted AI answer pays for this question's write-up */
      if (!r.ok && !AI_NOSEND[r.reason]) A.read = true;
      if (r.ok) A.read = true;
      if (r.ok && r.source === 'router' && TBS.hook && TBS.hook.routed) {   /* router1: the Worker's router picked a tool; the toolbox fills the names and shows the card, or the standard parser takes over (no second AI call) */
        TBS.hook.routed(r, t, tbApiGet()).then(function (done) { if (done || A.call) return; if (!a[1]) viewError(t); else aiStd(false); });
        return;
      }
      if (!a[1]) { viewError(t); return; }
      if (r.ok && r.rt && TBS.hook && TBS.hook.routerMiss) TBS.hook.routerMiss(r.rt);   /* router1: it ran and the normal AI answer followed: one fallback counter */
      if (!r.ok) { aiStd(!AI_NOSEND[r.reason] && window.KTAI.fallbackText(r.reason)); return; }
      var I = r.interpretation, resp = { enabled: true, ok: true, source: r.source, interpretation: I };
      if (I && I.status === 'refused') { aiRefusal(t, I.refusal_code); return; }
      var fa = window.KTCompare && window.KTCompare.fromAskResponse ? window.KTCompare.fromAskResponse(resp, S.bundle.aliases, S.choices) : null;
      if (!fa || fa.fallback) { aiStd(false); return; }
      if (!aiSane(t, fa.scenarios)) { aiStd(false); return; }   /* B5b: an AI read that can't be right goes to the standard parser, which runs what it can and names what it left out */   /* router2: impossible or inverted read -> the existing "Sorry, I didn't catch that" card, no wrong card */
      A.via = 'ai'; A.scen = fa.scenarios.map(function (s) { return { label: s.label, parsed: s.parsed }; });
      if (!aiShowUnderstood(true)) aiStd(false);
    });
  }
  /* ---------- aiv2: AI-primary reader (dark unless ask-config v2:true). Rules first; the AI reads what the rules could not, from real team and game lists; any failure = today's path. ---------- */
  var AI2_JS = '/assets/ks/ai2.js?v=64574e81da';
  function v2Load() { return window.KTAI2 ? Promise.resolve() : loadScript(AI2_JS); }
  function v2Complete(t, p) {   /* the rules read the whole question: a scenario with items, one part, nothing named left unread */
    if (!p || p.intent !== 'scenario' || p.refusal || p.clarify || !p.items || !p.items.length) return false;
    var sp; try { sp = KTParse.splitScenarios(t, S.bundle.aliases, { choices: S.choices, max: 3 }); } catch (e) { sp = { parts: [] }; } if (sp.parts.length >= 2) return false;
    var un = []; try { un = b5iUnread(t); } catch (e) { un = []; } if (un.length) return false;
    try { var men = {}; (p.mentions || []).forEach(function (m) { if (m.team !== null && m.team !== undefined) men[m.team] = 1; (m.candidates || []).forEach(function (c) { men[c] = 1; }); }); return !window.KTAI2 || window.KTAI2.cands(t, S.bundle, KTParse, S.choices).every(function (x) { return men[x]; }); } catch (e) { return true; }   /* a typo the rules skipped ("Utha loses 2") is not the whole question */
  }
  function aiReviewV2(t) {
    ensureData().then(function () { return loadCompare(); }).then(function () { return v2Load(); }).then(function () {
      var B = S.bundle, p = KTParse.parse(t, B.aliases, { choices: S.choices }), q = KTParse.norm(t);
      if (p && p.clarify && p.clarify_reason === 'ambiguous_team') { input.value = ''; cnt.textContent = '0/' + cap(); send.disabled = true; ask(t, {}); return; }   /* bare Miami: Did you mean, no AI call (as today) */
      if (v2Complete(t, p)) { aiStd(false); return; }   /* fast path: the rules read all of it, instant, no AI call, no cap use */
      if (p && (p.intent === 'baseline' || p.need) || /\b(?:compare|versus|scenario [abc])\b/.test(q)) { aiSend(t); return; }   /* chances / needs / compare: the existing reader, unchanged */
      var cand = window.KTAI2.cands(t, B, KTParse, S.choices); if (!cand.length) { aiSend(t); return; }   /* no team found: the existing reader (its off-topic and non-FBS answers), unchanged */
      aiSendV2(t, cand);
    }, function () { aiSend(t); });
  }
  function aiSendV2(t, cand) {
    var A = S.ai; A.thinking = true; A.t0 = Date.now();
    show('thinking', bubble(t) + '<div class="spin kbb" role="status">' + SHIELD + '<div class="kbt"><p class="spcap">Reading your question\u2026</p><p class="spcap kb2">Nothing is calculated yet.</p></div></div><button type="button" class="gb" data-aicancel>Cancel</button>', { focus: false });
    var call = A.call = window.KTAI.ask('home', null, t, { v2cand: cand });
    var wd = A.wd = setTimeout(function () { if (A.wd !== wd || view !== 'thinking') return; if (A.call === call) { try { call.cancel(); } catch (e) {} } A.call = null; A.thinking = false; try { aiStd(window.KTAI.fallbackText('timeout')); } catch (e) { viewError(t); } }, 15000);
    call.promise.then(function (r) {
      if (A.call !== call) return;
      A.call = null; A.thinking = false; A.ms = Date.now() - A.t0;
      if (r.cancelled) return;
      A.tk = r.tk ? { t: r.tk, at: Date.now() } : null;
      if (!r.ok && !AI_NOSEND[r.reason]) A.read = true;
      if (r.ok) A.read = true;
      if (!r.ok) { aiStd(!AI_NOSEND[r.reason] && window.KTAI.fallbackText(r.reason)); return; }   /* cap, timeout, verification, errors: today's standard-parser path, same note */
      var I = r.interpretation;
      if (I && I.status === 'refused') { aiRefusal(t, I.refusal_code); return; }
      if (!I || I.v !== 2) { aiStd(false); return; }   /* the Worker's local gate answered (too long, nothing to read): today's path */
      var B = S.bundle, M = window.KTAI2.map(I, B, KTParse, t, cand), ls = window.KTAI2.lines(M, B);
      if (M.refusal) { aiRefusal(t, M.refusal); return; }
      if (M.scen.length && aiSane(t, M.scen, cand)) { A.via = 'ai'; A.scen = M.scen; A.v2lines = ls; aiShowUnderstood(false); return; }   /* what it could read, with what it left out named; a count past the games left keeps Run off with the reason */
      if (v2RulesReadSome(t)) { aiStd(false); return; }   /* the rules can still run part of it (and name the rest): today's path */
      viewAiClarify(t, ls, cand);   /* aiv2: instead of "Sorry, I didn't catch that", say what was missing, with chips from the visitor's own teams */
    }, function () { if (A.call !== call) return; A.call = null; A.thinking = false; try { aiStd(window.KTAI.fallbackText('error')); } catch (e) { viewError(t); } });
  }
  function v2RulesReadSome(t) {   /* true when today's rules path would answer or ask something specific (not the generic card) */
    var B = S.bundle, p = KTParse.parse(t, B.aliases, { choices: S.choices });
    if (p.refusal) return true;
    if (p.clarify && (p.clarify_reason === 'unparsed' || p.clarify_reason === 'no_team' || p.clarify_reason === 'empty')) return !!partParse(t, B);
    return !p.clarify || KTAnswer.clarifyAnswer(B, p, null).reason === 'ambiguous_team';
  }
  function viewAiClarify(t, ls, cand) {
    var ids = (cand || []).filter(function (x) { return S.bundle.teams[x]; }).slice(0, 3), opts = ids.length ? b5iChips(ids) : [];
    if (!opts.length) examples().forEach(function (e) { opts.push(e[1]); });
    if (!ls || !ls.length) ls = ['I could not turn that into a game result.'];
    show('clarify', bubble(t) + '<div class="st2" data-v2="1"><span class="ico" aria-hidden="true">?</span><h3>One more detail</h3>' + ls.map(function (c) { return '<p class="kskp" role="status"><b>' + esc(c) + '</b></p>'; }).join('') + '<p class="note">Try a game result, like Team A beats Team B, Team A loses to Team B or Team A wins out.</p>' +
      opts.map(function (q) { return '<button type="button" class="opt" data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '<p class="ksop">' + SO_BTN + '</p></div>');
    S.lastQ = t;
  }
  function aiRefusal(t, code) {
    var R = window.KTAI.REFUSAL || {};
    show('refusal', bubble(t) + '<div class="st2" role="status">' + REQ + '<p class="big">' + esc(R[code] || R.off_topic || '') + '</p>' + pickButtons(1) + '<p class="ksop">' + SO_BTN + '</p>' + LINKS + '</div>');
    S.lastQ = t;
  }
  function aiStd(fbn) {   /* the standard parser reads the question in the browser; a plain what-if still gets the "here is what I understood" step */
    var A = S.ai, B = S.bundle, t = A.text, sp = { parts: [] }, p;
    A.fbn = fbn || false; A.via = 'std'; S.lastQ = t; A.v2lines = null;
    try { sp = KTParse.splitScenarios(t, B.aliases, { choices: S.choices, max: 3 }); } catch (e) { sp = { parts: [] }; }
    p = KTParse.parse(t, B.aliases, { choices: S.choices });
    if (sp.parts.length < 2 && p.intent === 'scenario' && !p.refusal && !p.clarify && p.items && p.items.length) { A.scen = [{ label: 'A', parsed: p }]; if (aiShowUnderstood(true)) return; }
    ask(t, { aiRead: A.read });
  }
  function aiResolveAll() {
    var A = S.ai, B = S.bundle, ok = true; A.bad = '';
    A.scen.forEach(function (s) { s.res = KTScenario.resolve(s.parsed, B); if (!s.res.ok) { ok = false; if (!A.bad) A.bad = KTAnswer.clarifyAnswer(B, s.parsed, s.res.clarify).text; } });
    return ok;
  }
  function aiShowUnderstood(initial) {
    var A = S.ai; if (!aiResolveAll() && initial) return false;
    show('understood', aiUnderstoodHtml(), { focus: false });
    var h = bd.querySelector('#und-h'); if (h) h.focus();
    return true;
  }
  function nmf(t) { var x = S.bundle.teams[t]; return x.f || x.n; }   /* full school name + nickname ("Washington Huskies"); .n is the short name on the home */
  function aiFull(it) {   /* aiask1h: the Review chip names every resolved team in full before anything runs */
    if (it.kind === 'beats') return nmf(it.winner) + ' beats ' + nmf(it.loser);
    return it.team !== undefined && it.team !== null ? nmf(it.team) : '';
  }
  function aiSub(it, s, i) { var f = aiFull(it), r = aiSub0(it, s, i); return f + (f && r ? ' \u00b7 ' : '') + r; }
  function aiSub0(it, s, i) {
    var r = s.res, g;
    if (!r || !r.ok) return '';
    if (it.kind === 'beats') { g = r.games.filter(function (x) { return x.item === i; })[0]; return g ? gdate(g.date, g.id) + (g.neutral ? ' \u00b7 neutral site' : ' \u00b7 at ' + nm(g.home)) : ''; }
    if (it.kind === 'wins_out' || it.kind === 'loses_out' || it.kind === 'loses_n') { var n = r.games.filter(function (x) { return x.item === i; }).length; return n === 0 ? 'no games left' : n + (n === 1 ? ' game left' : ' games left'); }
    return '';
  }
  function aiChip(si, i) {
    var A = S.ai, s = A.scen[si], it = s.parsed.items[i], full = itemText(it, s.res && s.res.ok ? s.res : null, i), m = /^(.*) \(next game: (.*)\)$/.exec(full), t = m ? m[1] : full, sub = m ? aiFull(it) + ' \u00b7 ' + m[2] : aiSub(it, s, i), sw = it.kind !== 'wins_n_of_m' && it.kind !== 'loses_n';
    var lab = t + (sub ? '. ' + sub : '') + (sw ? '. Tap to switch the winner' : '');
    return '<div class="gc"><button type="button" class="mb' + (sw ? '' : ' st') + '" data-aisw="' + si + ':' + i + '" aria-label="' + esc(lab) + '"><span class="tx"><span class="t">' + (m ? '<span class="tg">Next game</span>' : '') + esc(t) + '</span>' + (sub ? '<span class="s">' + esc(sub) + '</span>' : '') + '</span>' + (sw ? '<span class="sp" aria-hidden="true">' + AI_SWAP + '</span>' : '') + '</button><button type="button" class="rm" data-airm="' + si + ':' + i + '" aria-label="Remove: ' + esc(t) + '"><span aria-hidden="true">\u00d7</span></button></div>';
  }
  function aiUnderstoodHtml() {
    var A = S.ai, multi = A.scen.length > 1;
    return bubble(A.text) + (A.fbn ? '<p class="fbn" role="status">' + AI_INFO + '<span>' + esc(typeof A.fbn === 'string' ? A.fbn : window.KTAI.FALLBACK) + '</span></p>' : '') +
      '<section class="und" aria-labelledby="und-h"><div class="uh"><span class="tag2">' + (A.via === 'ai' ? 'Read by AI' : 'Read by the standard parser') + '</span></div><h3 id="und-h" tabindex="-1">Here is what I understood</h3>' +
      '<p class="nt">This is how KickTip read your words. It is not a forecast. Tap a game to switch the winner. Tap \u00d7 to remove it. Nothing runs until you tap Run.</p>' +
      A.scen.map(function (s, si) { return '<div class="scn" role="group" aria-label="' + (multi ? 'Scenario ' + s.label : 'Your scenario') + '">' + (multi ? '<h4><span class="lt" aria-hidden="true">' + s.label + '</span>Scenario ' + s.label + '</h4>' : '') + s.parsed.items.map(function (it, i) { return aiChip(si, i); }).join('') + '</div>'; }).join('') +
      (A.v2lines && A.v2lines.length ? A.v2lines.map(function (c) { return '<p class="kskp" role="status"><b>' + esc(c) + '</b></p>'; }).join('') : '') + '<p class="oth">' + AI_INFO + '<span>Every game you did not mention is simulated as usual.</span></p><button type="button" class="addg" data-aiadd>+ Add another game</button>' +
      (A.via === 'ai' ? '<div class="ufoot"><button type="button" class="gb lnk" data-noai aria-label="Don\'t use AI. Read my question with the standard parser instead">Don\'t use AI</button></div>' : '') + '</section>';
  }
  function aiBarHtml() {
    var dis = !!S.ai.bad;
    return '<div class="rw"><button type="button" class="gb" data-aiedit>Edit my question</button><button type="button" class="gb pri" data-airun' + (dis ? ' aria-disabled="true" aria-describedby="kwhy"' : '') + '>Run</button></div>' + (dis ? '<p class="why" id="kwhy">' + esc(S.ai.bad) + '</p>' : '') + RTX('c');   /* B4d3: keyboard down shows the full notice line under Run; keyboard up keeps the one-line B4b line (CSS on .kbf) */
  }
  function aiCanon(s) { return 'What if ' + s.parsed.items.map(function (it, k) { return itemText(it, null, k); }).join(' and ') + '?'; }
  function aiQuestion() { var A = S.ai; return (A.edited ? A.scen.map(aiCanon).join(' | ') : A.text).slice(0, cap()); }
  function aiEdit(txt) {   /* back to the box with the text intact */
    var A = S.ai; A.fbn = false; A.thinking = false;
    viewEmpty(); input.disabled = false; input.value = txt === undefined ? A.text : txt; cnt.textContent = input.value.length + '/' + cap(); send.disabled = !input.value.trim();
    if (!isNarrow() || txt !== undefined) fieldOn(true);
  }
  function aiSwapItem(it) {
    var w;
    if (it.kind === 'beats') { w = it.winner; it.winner = it.loser; it.loser = w; it.site = it.site === 'winner_home' ? 'winner_away' : it.site === 'winner_away' ? 'winner_home' : it.site; }
    else if (it.kind === 'next_win') it.kind = 'next_loss'; else if (it.kind === 'next_loss') it.kind = 'next_win';
    else if (it.kind === 'wins_out') it.kind = 'loses_out'; else if (it.kind === 'loses_out') it.kind = 'wins_out';
  }
  function aiRun() {
    var A = S.ai; if (A.bad || S.busy) return;
    var q = aiQuestion();
    if (A.scen.length >= 2 && window.KTCompare && KTCompare.runAi && KTCompare.runAi(q, A.scen, cmpApi())) return;
    ask(q, { parsed: A.scen[0].parsed, aiRead: A.read });
  }
  function aiBarClick(e) {
    var b = e.target.closest ? e.target.closest('button') : null; if (!b) return;
    if (b.hasAttribute('data-aiedit')) aiEdit(S.ai.edited ? aiQuestion() : undefined);
    else if (b.hasAttribute('data-airun')) { if (b.getAttribute('aria-disabled') === 'true') return; aiRun(); }
  }
  function aiBodyClick(e) {
    var A = S.ai, b = e.target.closest ? e.target.closest('button') : null; if (!b || !bd.contains(b)) return;
    var p, si, i;
    if (b.hasAttribute('data-aicancel')) { if (A.call) A.call.cancel(); A.call = null; aiEdit(); return; }
    if (b.hasAttribute('data-aisw') || b.hasAttribute('data-airm')) {
      p = b.getAttribute(b.hasAttribute('data-aisw') ? 'data-aisw' : 'data-airm').split(':'); si = +p[0]; i = +p[1];
      if (b.hasAttribute('data-aisw')) { aiSwapItem(A.scen[si].parsed.items[i]); A.edited = true; aiShowUnderstood(false); var again = bd.querySelector('[data-aisw="' + si + ':' + i + '"]'); if (again) again.focus(); return; }
      A.scen[si].parsed.items.splice(i, 1); if (!A.scen[si].parsed.items.length) A.scen.splice(si, 1);
      if (!A.scen.length) { aiEdit(''); return; }
      A.scen.forEach(function (s, k) { s.label = 'ABC'.charAt(k); }); A.edited = true; aiShowUnderstood(false); return;
    }
    if (b.hasAttribute('data-aiadd')) { aiEdit(aiQuestion().replace(/[?.!\s]+$/, '') + ' and '); return; }
    if (b.hasAttribute('data-noai')) {
      A.on = false; window.KTAI.setOn(false); A.learn = false; aiPaintBox();
      if (view === 'understood' && S.bundle) { A.fbn = false; aiStd(false);   /* the question was already sent once, so the answer keeps the short note */ } else aiEdit(S.lastQ || A.text);
      aiMode();
    }
  }
  function aiNote(opt) {   /* which flags a question carries: asked through the AI box (read), and whether the fallback note shows */
    var A = S.ai; if (!A) return;
    var derived = !!(opt.regen || opt.parsed || opt.choices);
    if (opt.aiRead !== undefined) A.read = !!opt.aiRead; else if (!derived) A.read = false;
    if (!derived && opt.aiRead === undefined) A.fbn = false;
  }

  /* ---------- the question flow ---------- */
  function ask(text, opt) {
    text = String(text).trim().slice(0, cap()); if (!text || S.busy) return;
    opt = opt || {}; aiNote(opt);   /* aihome1 */
    S.skip = null;
    if (!opt.regen) S.seedN = 0;
    S.lastQ = text; S.choices = opt.choices || (opt.parsed ? S.choices : {});
    if (!S.bundle) show('loading', bubble(text) + '<div class="ac" aria-label="Loading answer">' + REQ + SPINCARD + '<p class="meta">Loading the latest schedule and results&hellip;</p><div class="sk w90"></div><div class="sk w70"></div><div class="sk w80"></div></div>', { focus: false });
    ensureData().then(function () { return loadCompare(); }).then(function () { route(text, opt); }, function () { viewError(text); });
  }
  function route(text, opt) {
    var B = S.bundle, parsed = opt.parsed || KTParse.parse(text, B.aliases, { choices: S.choices }), res, ci;
    if (!opt.parsed && window.KTCompare && KTCompare.route(text, opt, cmpApi())) return;   /* compare1 */
    if (parsed.refusal) return viewRefusal(text);
    if (parsed.clarify && !opt.parsed && (parsed.clarify_reason === 'unparsed' || parsed.clarify_reason === 'no_team')) { var pp = partParse(text, B); if (pp) { parsed = pp.parsed; S.skip = pp.skip; } }
    if (parsed.clarify) {
      ci = KTAnswer.clarifyAnswer(B, parsed, null);
      if (ci.reason === 'ambiguous_team' && ci.options.length) return viewClarify(text, ci);
      if (ci.reason === 'unparsed' || ci.reason === 'no_team' || ci.reason === 'empty') return viewNotUnderstood(text);
      return viewInfo(text, ci.text, ci);
    }
    S.parsed = parsed; S.res = null;
    if (parsed.need) return runNeed(text, parsed);
    if (parsed.intent === 'baseline' && parsed.baseline_team !== null) return runBaseline(text, parsed);
    res = KTScenario.resolve(parsed, B, SCNCARD && SCNB ? { branches: true, allImp: allImpOn() } : null);   /* scn_b, scn_b2 */
    if (!res.ok && !(res.clarify && res.clarify.reason === 'conflict' && fixChips(parsed).length)) { var pr = partRes(parsed, B, SCNCARD && SCNB ? { branches: true, allImp: allImpOn() } : null); if (pr) { parsed = pr.parsed; res = pr.res; S.skip = (S.skip || []).concat(pr.skip); S.parsed = parsed; S.lastQ = stackQ(parsed.items) || text; } }
    if (!res.ok) { ci = KTAnswer.clarifyAnswer(B, parsed, res.clarify); ci.rc = res.clarify; return viewInfo(text, ci.text, ci, parsed); }
    S.res = res; S.busy = true;
    if (S.skip && S.skip.length) S.lastQ = stackQ(parsed.items) || S.lastQ;   /* B5: Add another game continues from what ran */
    if (res.branches) return runBranched(text, parsed, res, B);
    viewRunning(text, parsed, res, 0, CHUNKS * PER);
    var exP = explainCard(parsed, res, B);
    runEngine(res.forced, res.constraints, false, tick).then(function (r) {
      S.w2 = { r: r, res: res };   /* whatif2 */
      var ans = KTAnswer.scenarioAnswer(B, res, r.before, r.after, r.N, B.as_of, { maxRows: 8 });
      return exP.then(function (f) {
        var card = ''; try { if (f) { KTExplain.attachSim(f, ans, B); card = KTExplain.render(f, esc); } } catch (e) { card = ''; }
        S.busy = false; viewAnswer(text, parsed, res, ans, r.N, card); if (f && card) scnWrite(f, B);
      });
    }, function () { S.busy = false; viewError(text); });
  }
  /* B5: layering. A stack of conditions runs with every one that can apply; each one that cannot is named with the reason (S.skip, shown under the chips). Nothing is given up silently. */
  function partRes(parsed, B, ro) {
    var items = parsed.items || [], kept = [], skip = [];
    if (items.length < 2) return null;
    items.forEach(function (it) {
      var r; try { r = KTScenario.resolve(Object.assign({}, parsed, { items: kept.concat([it]) }), B, ro); } catch (e) { r = null; }
      if (r && r.ok) kept.push(it);
      else { var ci = KTAnswer.clarifyAnswer(B, Object.assign({}, parsed, { items: [it] }), r && r.clarify || { reason: 'unparsed' }); skip.push({ what: (it.rec && it.kind === 'loses_n') ? nm(it.team) + ' goes ' + String(it.rec[0]) + '-' + String(it.rec[1]) : (fixPhrase(it, null) || itemText(it, null, 0)), why: moreLeft(ci.text, it.team) }); }
    });
    if (!kept.length || !skip.length) return null;
    var np = Object.assign({}, parsed, { items: kept }), res = KTScenario.resolve(np, B, ro);
    return res.ok ? { parsed: np, res: res, skip: skip } : null;
  }
  function moreLeft(tx, tm) { if (!/more games than the team has left/.test(tx || '') || tm === undefined || tm === null || !S.bundle) return tx; var n = S.bundle.teams[tm].s || nm(tm), g = S.bundle.games.filter(function (x) { return x.h === tm || x.a === tm; }).length; return g === 0 ? n + ' has no games left.' : 'That is more games than ' + n + ' has left. ' + n + ' has ' + (g === 0 ? 'no games' : g + (g === 1 ? ' game' : ' games')) + ' left.'; }   /* B5e */
  var UNREAD = 'I could not turn that into a game result.';
  function partParse(text, B) {
    var cl = String(text).replace(/^\s*(?:what if|what happens if|if|suppose)\s+/i, '').replace(/[?.!\s]+$/, '').split(/\s*(?:[,;]|\band\b|\bthen\b|\bplus\b|\balso\b)\s*/i).filter(function (c) { return c && /[a-z]/i.test(c); });
    if (cl.length < 2) return null;
    var kept = [], skip = [];
    cl.forEach(function (c) { var p; try { p = KTParse.parse(kept.concat([c]).join(' and '), B.aliases, { choices: S.choices }); } catch (e) { p = null; } if (p && !p.clarify && !p.refusal && p.intent === 'scenario' && p.items && p.items.length) kept.push(c); else skip.push({ what: c, why: UNREAD }); });
    if (!kept.length || !skip.length) return null;
    var np = KTParse.parse(kept.join(' and '), B.aliases, { choices: S.choices });
    return np.clarify || np.refusal ? null : { parsed: np, skip: skip };
  }
  /* scn_b: a question whose named teams meet in a game still to be played (for example "What if BYU, Utah and Texas Tech all end with just one loss") is answered as up to 4 labelled branches, one per result of that game, each solved by the official-rules solver and simulated on its own. Hypothetical only: nothing live is changed. Set SCNB to false to bring back the "those teams play each other" question; more than 2 shared games, more than 3 teams, more than 1 conference, or a card that cannot be built also keep that question. */
  var SCNB = true;
  function branchClarify(text, parsed, B, why) { var ci = KTAnswer.clarifyAnswer(B, parsed, { reason: why || 'shared_game' }); S.busy = false; return viewInfo(text, ci.text, ci, parsed); }
  /* scn_b2: when EVERY result of the shared games breaks the scenario (for example "Western Kentucky and Delaware each end with 4 losses"), the page used to ask the old "conflict" question. With the scenario write-up flag on (ask-config scn:true) it shows the card instead: the question's title, one line (COPY.bImpAll) and the rules and as-of lines. SCNIMPALL = false brings the old question back for everyone. Nothing is simulated or sent. */
  var SCNIMPALL = true;
  function allImpOn() { return SCNIMPALL && !!(window.KTAI && KTAI.scnOn && KTAI.scnOn()); }
  function viewAllImp(t, parsed, res, card) {
    show('answer', bubble(t) + '<div class="ac" role="article" aria-label="KickTip answer">' + REQ + chipHtml(parsed, res) + card + '<p class="mn">' + onb() + '</p>' + LINKS + '</div>');
  }
  function runBranched(text, parsed, res, B) {
    var live = res.branches.filter(function (b) { return b.res; }), nb = live.length, total = CHUNKS * PER, outs = [], chain = Promise.resolve();
    viewRunning(text, parsed, res, 0, total);
    return explainCard(parsed, res, B).then(function (f) {
      if (!f || !f.game_branches || !window.KTExplain) return branchClarify(text, parsed, B);
      if (!live.length) { var cd = ''; try { cd = f.all_impossible ? KTExplain.render(f, esc) : ''; } catch (e) { cd = ''; } if (!cd) return branchClarify(text, parsed, B, 'conflict'); S.busy = false; return viewAllImp(text, parsed, res, cd); }   /* scn_b2 */
      live.forEach(function (br, k) {
        chain = chain.then(function () {
          return runEngine(br.res.forced, br.res.constraints, false, function (d, t) { tick(Math.min(total, Math.round((k + d / t) * total / nb)), total); }, nb > 1 ? { chunks: 5, minChunks: MINCH, budget: Math.floor(BUDGET / nb) } : null).then(function (r) { outs[k] = r; });
        });
      });
      return chain.then(function () {
        var answers = [], ci = 0, first = null, n = Infinity;
        res.branches.forEach(function (b, i) {
          if (!b.res) { answers[i] = null; return; }
          var r = outs[ci++], ans = KTAnswer.scenarioAnswer(B, b.res, r.before, r.after, r.N, B.as_of, { maxRows: 8 });
          answers[i] = ans; if (!first) first = ans; n = Math.min(n, r.N);
        });
        var card = ''; try { KTExplain.attachSim(f, answers, B); card = KTExplain.render(f, esc); } catch (e) { card = ''; }
        if (!card || !first) return branchClarify(text, parsed, B);
        S.w2 = live.length === 1 ? { r: outs[0], res: live[0].res } : null;   /* whatif2: header only when one branch is possible */
        S.w2bc = null; if (live.length > 1) { try { S.w2bc = w2bcHtml(parsed, res, outs, f); } catch (e) { S.w2bc = null; } }   /* ccgcard: one conference championship card per possible result, from this run's sim pairs (no AI) */
        if (S.w2 && res.branches.length > 1) { var sh1 = (live[0].shared || []).map(function (g) { return nm(g.winner) + ' beats ' + nm(g.loser); }); if (sh1.length) { S.w2.onlyChip = sh1.join(' \u00b7 '); S.w2.only = 'Only one way this can happen: ' + sh1.join(' and ') + '. Any other result there breaks the scenario.'; } }   /* whatif2b: collapse */
        S.busy = false; viewAnswer(text, parsed, res, first, n, card, true); scnWrite(f, B);
      });
    }).catch(function () { S.busy = false; viewError(text); });
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
    if (b.hasAttribute('data-w2why')) { var o = b.getAttribute('aria-expanded') !== 'true', wb = D.getElementById('w2wbody'); b.setAttribute('aria-expanded', o ? 'true' : 'false'); if (wb) wb.hidden = !o; if (S.w2d) w2prep(S.w2d); return; }   /* whatif2: the ready PNG follows the Why? state */
    if (b.hasAttribute('data-w2share')) { w2share(b); return; }
    if (b.hasAttribute('data-w2all')) { var mo = D.getElementById('w2more'), op = b.getAttribute('aria-expanded') !== 'true'; if (mo) mo.hidden = !op; b.setAttribute('aria-expanded', op ? 'true' : 'false'); b.textContent = op ? 'Show fewer teams' : 'Show all ' + ((S.w2d && S.w2d.all && S.w2d.all.length) || '') + ' teams'; return; }   /* polish: full team list */
    if (b.hasAttribute('data-cmp')) { if (window.KTCompare) KTCompare.click(b, cmpApi()); return; }   /* compare1 */
    if (b.hasAttribute('data-q')) {
      if (b.classList.contains('q')) { input.disabled = false; input.value = b.getAttribute('data-q'); cnt.textContent = input.value.length + '/' + cap(); send.disabled = false; fieldOn(true); return; }   /* an example card only FILLS the box; the person taps Run */
      if (b.hasAttribute('data-fix')) { input.value = b.getAttribute('data-q'); cnt.textContent = input.value.length + '/' + cap(); }   /* B4e: a fixed version fills the box and runs */
      ask(b.getAttribute('data-q'), {}); return;
    }
    if (b.hasAttribute('data-pick')) { var p = b.getAttribute('data-pick').split('|'), c = {}; c[p[0]] = +p[1]; var ch = Object.assign({}, S.choices, c); ask(S.lastQ, { choices: ch }); return; }
    if (b.hasAttribute('data-else')) { fieldOn(true); return; }
    if (b.hasAttribute('data-reset')) { startOver(); return; }
    if (b.hasAttribute('data-retry')) { if (S.lastQ) { if (rv()) aiReview(S.lastQ); else ask(S.lastQ, {}); } else viewStart(); return; }
    if (b.hasAttribute('data-regen') && S.lastQ) { S.seedN++; ask(S.lastQ, { regen: true, parsed: S.parsed || undefined }); return; }
    if (b.hasAttribute('data-add')) { input.disabled = false; input.value = stackText() + ' and '; cnt.textContent = input.value.length + '/' + cap(); send.disabled = false; fieldOn(true); return; }
    if (b.hasAttribute('data-rm') && S.parsed) {
      var i = +b.getAttribute('data-rm'), np = JSON.parse(JSON.stringify(S.parsed)); np.items.splice(i, 1);
      if (!np.items.length) { viewEmpty(); return; }
      var t = 'What if ' + np.items.map(function (it, k) { return itemText(it, null, k); }).join(' and ') + '?'; S.lastQ = t; ask(t, { parsed: np });
    }
  }
  (function () { var q = 0; function go() { if (q) return; q = requestAnimationFrame(function () { q = 0; rtFit(); rbCaret(); if (mo) mo.takeRecords(); }); }   /* B4f: refit on any panel change, resize or keyboard; its own class changes are dropped */
    var mo = null; try { mo = new MutationObserver(go); mo.observe(D.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'hidden'] }); } catch (e) {}
    addEventListener('resize', go); D.addEventListener('focusin', function (e) { if (e.target && e.target.tagName === 'INPUT') { go(); setTimeout(go, 300); } }); if (window.visualViewport) visualViewport.addEventListener('resize', go); go(); })();
})();
/* merged revb: exactly one visible 'not a betting site' line. While any page banner (.tb) is on screen, body gets kt-tbv and the Lab gate
   hides its '· Not a betting site' (chat.css); with no banner in view the gate keeps it. */
(function () { var D = document, W = window, on = {}, n = 0;
  function set() { D.body && D.body.classList.toggle('kt-tbv', n > 0); }
  function go() { var b = D.querySelectorAll('.tb'); if (!b.length || !W.IntersectionObserver) return;
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { var i = e.target.__ktb; var v = e.isIntersecting && e.intersectionRect.height > 0; if (v && !on[i]) { on[i] = 1; n++; } else if (!v && on[i]) { on[i] = 0; n--; } }); set(); });
    [].forEach.call(b, function (x, i) { x.__ktb = i + 1; io.observe(x); }); }
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', go); else go(); })();
/* merged revb2 (kt-tbcut): the Lab scrim is lighter over the on-screen page banner strip (contrast >= 4.5:1). Sets --kt-tb0/--kt-tb1 (px, relative to the scrim box). */
(function () { var D = document, W = window, R = D.documentElement, q = 0;
  function upd() { q = 0; var t = 0, b = 0; [].forEach.call(D.querySelectorAll('.tb'), function (x) { var r = x.getBoundingClientRect(); if (r.height > 0 && r.bottom > 0 && r.top < W.innerHeight && !b) { t = Math.max(0, r.top); b = Math.min(W.innerHeight, r.bottom); } });
    var sc = D.querySelector('.scrim'), o = sc ? sc.getBoundingClientRect().top : 0; if (b) { t -= o; b -= o; }   /* mask coords are relative to the scrim box */
    R.style.setProperty('--kt-tb0', t + 'px'); R.style.setProperty('--kt-tb1', b + 'px'); }
  function req() { if (!q) { q = 1; (W.requestAnimationFrame || setTimeout)(upd); } }
  W.addEventListener('scroll', req, { passive: true }); W.addEventListener('resize', req);
  if (W.MutationObserver) new MutationObserver(function () { req(); setTimeout(upd, 450); }).observe(R, { attributes: true, childList: true, subtree: true, attributeFilter: ['class'] });
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', upd); else upd(); })();
