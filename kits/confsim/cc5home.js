/* cc5 rev 5 (Creative mock home/ d4178e78, Jared GO 1:24 PM MT Oct 31): home "Conference Simulator" tile, placed right after the What If tile (#wl-home).
   The matchup is the engine's default pair (K.favorites starting results -> K.solve on /data/ccg-sim.json), the same pair the simulator shows as "Starting results". No team is shown until it is known. */
(function () {
  "use strict";
  var K = window.KTCcg, wl = document.getElementById("wl-home"); if (!K || !wl || document.getElementById("cs-home")) return;
  var CODE = "big12", NAME = "Big&nbsp;12", URL0 = "/conference/big-12/simulator/";
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var li = document.createElement("li"); li.className = "pk-tile pt-t pt-t2 pk-wi wl cc5ht"; li.id = "cs-home";
  li.innerHTML = '<div class="wl-hd"><svg class="wl-mk" width="37" height="48" viewBox="0 0 37 48" aria-hidden="true" focusable="false"><rect x="1.5" y="1.5" width="34" height="45" rx="7" fill="#121519"/><path d="M8 12h7v8h7M8 36h7v-8h7M22 20v8h7" fill="none" stroke="#33E1EA" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
    '<div class="wl-ht"><h3>Conference Simulator</h3><p class="wl-sub">Flip any game and see who makes your conference championship.</p><p class="wl-tag">Every game left. Official tiebreaker rules.</p></div></div>' +
    '<p class="pt-cap" id="cc5hc">' + NAME + ' championship, starting results</p><p class="csm" id="cc5hm" hidden></p>' +
    '<a class="btn-wi on-light" href="' + URL0 + '">Open the simulator</a>';
  wl.insertAdjacentElement("afterend", li);
  var get = function (u) { return fetch(u, { credentials: "omit" }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); };
  Promise.all([get("/data/ccg-sim.json"), get("/data/ccg-rules.json"), get("/data/pred-lines.json").catch(function () { return null; })]).then(function (a) {
    var conf = a[0].confs[CODE], R = a[1].rules[CODE]; if (!conf || !R) throw new Error("conf");
    var fav = K.favorites(conf, a[2], Date.now() / 1000), res = K.solve(R, conf, fav.picks), m = document.getElementById("cc5hm");
    if (!(res && res.ready && res.pairKnown && res.pair)) { document.getElementById("cc5hc").innerHTML = NAME + " championship: not settled with the starting results yet"; return; }
    var tm = function (i) { var t = conf.teams[i], lg = ""; try { lg = window.KTLogo ? window.KTLogo.team(t.slug, 28, false) : ""; } catch (e) { lg = ""; } return '<span class="csn">' + lg + esc(t.short) + "</span>"; };
    m.innerHTML = tm(res.pair[0]) + " <i>vs</i> " + tm(res.pair[1]); m.hidden = false;
  }).catch(function () { var c = document.getElementById("cc5hc"); if (c) c.innerHTML = "Set every game left and see the " + NAME + " championship."; });
})();
