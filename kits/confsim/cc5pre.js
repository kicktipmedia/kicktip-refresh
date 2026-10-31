/* cc5 rev 5.1: runs in <head> before first paint (home, the 10 conference pages, the 10 simulator pages). Sets html.cc5js so cc5pages.css can reserve the simulator's height while it
   loads (no layout jump), then lifts it (html.cc5ok) once the simulator has rendered (its grid exists, plus 1.5 s for the AI box), on the first tap/key (states can get shorter:
   tie, not settled), or after 10 s as a fail-safe. The reservations are at most the smallest rendered height, so lifting them never leaves a gap or moves content.
   Without JavaScript nothing is reserved and the page keeps its original content. */
(function () {
  var d = document.documentElement, done = false, ok = function () { if (done) return; done = true; d.classList.add("cc5ok"); };
  d.classList.add("cc5js"); setTimeout(ok, 10000);
  ["pointerdown", "keydown"].forEach(function (t) { addEventListener(t, ok, { capture: true, once: true }); });
  document.addEventListener("DOMContentLoaded", function () {
    var app = document.getElementById("sim-app"), fin = function () { setTimeout(ok, document.getElementById("aib") ? 0 : 1500); };
    if (!app) return ok(); if (app.querySelector(".simgrid")) return fin(); if (!window.MutationObserver) return ok();
    var mo = new MutationObserver(function () { if (app.querySelector(".simgrid")) { mo.disconnect(); fin(); } }); mo.observe(app, { childList: true, subtree: true });
  });
})();
