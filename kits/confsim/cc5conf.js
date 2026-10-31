/* cc5 rev 5 (Creative mock confpage/ f43b5752, Jared GO 1:24 PM MT Oct 31): the conference page opens on the simulator. Replaces the slim What If section (section.wl-sec) with the
   simulator (#sim, run by ccgsim-ui.js, loaded after this file) and an "Open the What If Lab" button (same [data-w2lab] opener as before, chat.js). The lower simulator promo card is hidden.
   Without JavaScript the page keeps its original What If section and promo card. Map from each /conference/<slug>/simulator/ page, written by kits/confsim/feat_c.py. */
(function () {
  "use strict";
  var MAP = /*CC5MAP*/{}, main = document.getElementById("main"), slug = main && main.getAttribute("data-conf"), c = MAP[slug], sec = document.querySelector("section.wl-sec");
  var ok = function () { document.documentElement.classList.add("cc5ok"); };
  if (!c || !sec || document.getElementById("sim")) { ok(); return; }
  var nb = function (s) { return String(s).replace(/[&<>"]/g, function (x) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[x]; }).replace(/ /g, "&nbsp;"); };
  var w = sec.querySelector(".w") || sec; sec.classList.add("cc5cs");
  w.innerHTML = '<h2 class="cc5ch2" id="cc5ch2">' + nb(c[1]) + ' championship simulator</h2><p class="cc5cl">Flip any game and see who makes the ' + nb(c[1]) + ' championship. Standings follow the conference&rsquo;s published rules.</p>' +
    '<div class="sim cc5em" id="sim" data-code="' + c[0] + '" data-name="' + nb(c[1]).replace(/&nbsp;/g, " ") + '" aria-labelledby="cc5ch2"><div id="sim-app"><p class="xhow">Loading the simulator&hellip;</p></div></div>' +
    '<button type="button" class="cc5lab" data-w2lab aria-haspopup="dialog"><span>Want playoff chances instead?</span>Open the What If Lab</button>';
  /* rev 5.1: lift the cc5pages.css height reservation once the simulator has rendered (its grid exists) and the AI box has had a moment to appear */
  var app = document.getElementById("sim-app"), done = false, fin = function () { if (done) return; done = true; setTimeout(ok, document.getElementById("aib") ? 0 : 1500); };
  if (window.MutationObserver) { var mo = new MutationObserver(function () { if (app.querySelector(".simgrid")) { mo.disconnect(); fin(); } }); mo.observe(app, { childList: true, subtree: true }); } else ok();
  [].forEach.call(document.querySelectorAll(".card > h2"), function (h) { if (/^Conference championship game simulator$/.test(h.textContent.trim())) h.parentNode.hidden = true; });
})();
