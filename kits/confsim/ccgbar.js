/* cc5 rev 5.2: compact sticky result bar (Creative ccgbar.js 21ae50e3, generalized to every conference). Desktop >=1100px only; narrower widths: no bar, rev 5.1 .ccgc unchanged.
   Watches #sim-app until the simulator renders #ccg, mirrors the result banner (.cc5c) and the "changed by you" count, and pins once #ccg has scrolled under the header. */
(function () {
  var mq = matchMedia("(min-width: 1100px)"), rm = matchMedia("(prefers-reduced-motion: reduce)"), d = document.documentElement, started = false;
  function t(e, s) { var n = e && e.querySelector(s); return n ? n.textContent.replace(/\s+/g, " ").trim() : ""; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function start(ccg) {
    if (started) return; started = true;
    var bar = document.createElement("div"); bar.id = "ccgbar"; bar.setAttribute("role", "region"); bar.setAttribute("aria-label", "Your result, compact");
    bar.innerHTML = '<div class="cb-in"></div>'; document.body.appendChild(bar);
    var nav = document.querySelector("header.hd"), key = "", vis = false, on = false;
    function navH() { if (!nav) return 0; var p = getComputedStyle(nav).position; return p === "sticky" || p === "fixed" ? Math.round(nav.getBoundingClientRect().bottom) : 0; }
    function sync() {
      var dk = mq.matches; d.classList.toggle("cb-js", dk && !!ccg.querySelector(".cc5c"));   /* no banner (undecided state): rev 5.1 .ccgc keeps working on desktop too */ d.style.setProperty("--cb-top", navH() + "px");
      var show = dk && on; bar.classList.toggle("on", show); d.style.setProperty("--cb-sb", show ? "68px" : "0px");
    }
    function render() {
      var c = ccg.querySelector(".cc5c"); if (!c) { bar.firstChild.innerHTML = ""; on = false; sync(); return; }
      var top = c.querySelector(".cc5top"), ttl = t(top, "b"), pill = t(top, ".cc5pl"), cn = ttl.replace(/\s*championship$/i, "");
      var ts = [].map.call(c.querySelectorAll(".cc5s"), function (s) {
        var im = s.querySelector("img"), r = t(s, ".cc5r"); if (cn) r = r.split(cn).join("").replace(/\s*·\s*/, " · ").replace(/\s+/g, " ").trim();
        return { img: im ? im.getAttribute("src") : "", seed: t(s, ".cc5sd").replace(/\s*seed$/i, ""), nm: t(s, ".cc5nm"), rec: r };
      });
      var chg = t(document.getElementById("strip"), ".pn:nth-child(2) b") || "0";
      bar.firstChild.innerHTML = '<span class="cb-lb">Your result &middot; <b>' + esc(ttl) + "</b></span>" + (pill ? '<span class="cb-pl">' + esc(pill) + "</span>" : "") + '<div class="cb-vs">' +
        ts.map(function (x) { return '<div class="cb-tm"><span class="cb-fr">' + (x.img ? '<img src="' + esc(x.img) + '" alt="">' : "") + '</span><span class="cb-nm"><small>' + esc(x.seed) + "</small>" + esc(x.nm) + '<span class="cb-rc">' + esc(x.rec) + "</span></span></div>"; }).join("<i>vs</i>") +
        '</div><div class="cb-rt"><span class="cb-ch">Changed: <b>' + esc(chg) + '</b></span><a class="cb-bk" href="#ccg">Back to result &uarr;</a></div>';
      var k = ts.map(function (x) { return x.nm; }).join("|");
      if (key && k !== key && !rm.matches) { bar.classList.remove("cb-fl"); void bar.offsetWidth; bar.classList.add("cb-fl"); }
      key = k; sync();
    }
    bar.addEventListener("click", function (e) { var a = e.target.closest("a.cb-bk"); if (!a) return; e.preventDefault();
      ccg.scrollIntoView({ behavior: rm.matches ? "auto" : "smooth", block: "start" }); ccg.focus({ preventScroll: true }); });
    function chk() { var r = ccg.getBoundingClientRect(), h = navH(); var n = !!ccg.querySelector(".cc5c") && r.bottom <= h; if (n !== on) { on = n; sync(); } }
    addEventListener("scroll", chk, { passive: true }); addEventListener("resize", function () { sync(); chk(); });
    if (window.IntersectionObserver) new IntersectionObserver(chk, { threshold: [0, 1] }).observe(ccg);
    if (mq.addEventListener) mq.addEventListener("change", sync);
    var mo = new MutationObserver(render); mo.observe(ccg, { subtree: true, childList: true, characterData: true });
    var st = document.getElementById("strip"); if (st) mo.observe(st, { subtree: true, childList: true, characterData: true });
    window.ccgBar = { render: render }; render(); chk();
  }
  function find() { var c = document.getElementById("ccg"); if (c) { start(c); return true; } return false; }
  function boot() { if (find()) return; var app = document.getElementById("sim-app") || document.body; if (!window.MutationObserver) return;
    var mo = new MutationObserver(function () { if (find()) mo.disconnect(); }); mo.observe(app, { childList: true, subtree: true }); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
