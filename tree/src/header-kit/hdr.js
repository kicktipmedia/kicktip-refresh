/* KickTip sticky header (src/header-kit/hdr.js). Loaded synchronously in <head> so html.hdjs is set before first paint. Sets classes and one CSS variable only (CSP style-src 'self': no inline styles, CSSOM only).
   Behaviour: .kh-stuck while the banner has scrolled away; option P Menu button (aria-expanded/aria-controls, Esc, scrim tap, link tap and Ask all close it, focus moves to the first panel link on open and returns to the button on Esc/scrim, focus stays inside while open, page scroll frozen via html.kh-lock); option Q strip fades. */
(function () {
  var D = document, H = D.documentElement; H.classList.add('hdjs');
  function init() {
    var hd = D.querySelector('header.hd'); if (!hd) return;
    var btn = D.getElementById('kh-btn'), panel = D.getElementById('kh-panel'), sc = D.getElementById('kh-scrim');
    var mq = window.matchMedia ? window.matchMedia('(max-width:759px)') : null;
    var tb = D.querySelector('.tb');
    if (tb && 'IntersectionObserver' in window) new IntersectionObserver(function (es) { var e = es[es.length - 1]; hd.classList.toggle('kh-stuck', !e.isIntersecting && e.boundingClientRect.bottom <= 0); }, { threshold: 0 }).observe(tb);
    var strip = hd.querySelector('.kht');   /* option Q only */
    if (strip) {
      var fade = function () { strip.classList.toggle('kh-l', strip.scrollLeft > 4); strip.classList.toggle('kh-r', strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 28); };
      strip.addEventListener('scroll', fade, { passive: true }); window.addEventListener('resize', fade);
      var cur = strip.querySelector('[aria-current=page]'); if (cur && strip.scrollWidth > strip.clientWidth) { var need = cur.offsetLeft + cur.offsetWidth - (strip.clientWidth - 36); if (need > 0) strip.scrollLeft = need; }
      strip.addEventListener('focusin', function (e) { var t = e.target, l = t.offsetLeft, r = l + t.offsetWidth; if (l < strip.scrollLeft + 36) strip.scrollLeft = Math.max(0, l - 36); else if (r > strip.scrollLeft + strip.clientWidth - 36) strip.scrollLeft = r - strip.clientWidth + 36; });
      fade();
    }
    if (!btn || !panel) return;   /* option P below */
    function isOpen() { return btn.getAttribute('aria-expanded') === 'true'; }
    function set(o, back) {
      if (o === isOpen()) return;
      btn.setAttribute('aria-expanded', o ? 'true' : 'false'); hd.classList.toggle('hd--open', o); H.classList.toggle('kh-lock', o);
      if (o) hd.style.setProperty('--kh-max', Math.max(160, Math.floor(window.innerHeight - hd.getBoundingClientRect().bottom)) + 'px');
      if (o) { var first = panel.querySelector('a[href]'); if (first) first.focus({ preventScroll: true }); }   /* open: focus moves into the panel (first link); Esc / Close / scrim return it to the Menu button */
      else if (back) btn.focus();
    }
    btn.addEventListener('click', function () { set(!isOpen(), false); });
    if (sc) sc.addEventListener('click', function () { set(false, true); });
    panel.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a, .ac-si')) set(false, false); });   /* a link tap, or the Sign in button (the sheet opens over the page): close the menu first */
    D.addEventListener('keydown', function (e) {
      if (!isOpen() || e.defaultPrevented || D.getElementById('ac-menu')) return;   /* the account menu (opened from the chip in this panel) owns Esc and Tab while it is up */
      if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); set(false, true); return; }
      if (e.key !== 'Tab') return;
      var f = [btn].concat([].slice.call(panel.querySelectorAll('a[href], button'))), i = f.indexOf(D.activeElement);   /* keep Tab inside Menu + its links while the scrim covers the page */
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
    });
    var pill = D.getElementById('kpill'); if (pill) pill.addEventListener('click', function () { set(false, false); }, true);   /* Ask KickTip takes over: close the menu first (capture: before chat.js reads the page state) */
    if (mq) { var chg = function () { if (!mq.matches) set(false, false); }; if (mq.addEventListener) mq.addEventListener('change', chg); else if (mq.addListener) mq.addListener(chg); }
    window.addEventListener('pageshow', function (e) { if (e.persisted) set(false, false); });
  }
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', init); else init();
})();
