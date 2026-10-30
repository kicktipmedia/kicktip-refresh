/* KickTip conference championship game simulator: page script (browser only). Engine: ccgsim.js (official published tiebreaker rules only).
   Starting results: ESPN's pre-game favorite where one is listed (/data/pred-lines.json, same 24 h rule as /games/), otherwise the team with the better record (computed from /data/ccg-sim.json); only WHICH side is used, no number is shown. Favorite wording: K.FAV_COPY (ccgsim.js).
   Nothing is stored: picks live in memory and clear when the page is left or reloaded. No inline style attributes (CSP style-src 'self'); widths use CSSOM setProperty. */
(function () {
  "use strict";
  var K = window.KTCcg, root = document.getElementById("sim"); if (!K || !root) return;
  var CODE = root.getAttribute("data-code"), NAME = root.getAttribute("data-name"), SHOW_T = 6;
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var list = function (a) { return a.length < 3 ? a.join(" and ") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]; };
  var plural = function (n, one, many) { return n + " " + (n === 1 ? one : many); };
  var IC = {
    star: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.6l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.1 4.1 13.4 5 9.1l-3.3-3 4.4-.5z" fill="none" stroke="#121519" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    swap: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 5h10M9 2l3 3-3 3M14 11H4M7 8l-3 3 3 3" fill="none" stroke="#121519" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    home: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8L8 2.5 14 8M3.8 7v6.7h8.4V7" fill="none" stroke="#121519" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    rec: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 14V9M8 14V3M13 14V6" fill="none" stroke="#121519" stroke-width="2.6" stroke-linecap="round"/></svg>',
    flag: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 1.5v13M3.5 2.5h9l-2 3.2 2 3.2h-9" fill="#121519" stroke="#121519" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>',
    check: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 8.5l3.5 3.5 7.5-8" fill="none" stroke="#121519" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    warn: '<svg class="ic" width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M11 2.5 20.5 19H1.5Z" fill="#fff" stroke="#121519" stroke-width="2" stroke-linejoin="round"/><path d="M11 8.5v5" stroke="#121519" stroke-width="2.2" stroke-linecap="round"/><circle cx="11" cy="16.2" r="1.2" fill="#121519"/></svg>',
    dice: '<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#262B31" stroke-width="2" aria-hidden="true"><rect x="2" y="2" width="14" height="14" rx="3"/><circle cx="6.5" cy="6.5" r="1" fill="#262B31"/><circle cx="11.5" cy="11.5" r="1" fill="#262B31"/></svg>'
  };
  var FC = K.FAV_COPY, SEED = { fav: ["r-fav", "star", FC.fav], rec: ["r-rec", "rec", FC.rec], home: ["r-rec", "home", FC.home], chg: ["r-chg", "swap", "Changed by you"], clr: ["r-clr", "swap", "Cleared by you"], nol: ["r-nol", "flag", FC.nol], set: ["r-set", "check", FC.set] };
  var D, R, conf, fav, picks = {}, lastMsg = "", annT = 0, expandT = false, curW = null, WEEKS = [], order = [], rowEl = {}, last = null;

  function fail(msg) { root.querySelector("#sim-app").innerHTML = '<p class="xhow">' + esc(msg) + "</p>"; }
  function mt(iso) { try { return new Intl.DateTimeFormat("en-US", { timeZone: "America/Denver", weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(iso)) + " MT"; } catch (e) { return ""; } }
  var T = function (i) { return conf.teams[i].short; };
  /* self-hosted ESPN team logo tile from lg.js (same markup as the rest of the site; same-origin images only; a failed image turns into the initials tile). "" when lg.js is not available. */
  var LG = function (i, size, lazy) { try { return window.KTLogo ? window.KTLogo.team(conf.teams[i].slug, size, lazy) : ""; } catch (e) { return ""; } };
  var MT = "America/Denver";
  function dmt(iso) { try { var p = {}; new Intl.DateTimeFormat("en-US", { timeZone: MT, month: "short", day: "numeric" }).formatToParts(new Date(iso)).forEach(function (x) { p[x.type] = x.value; }); return { m: p.month, d: +p.day, k: p.month + p.day }; } catch (e) { return { m: "", d: 0, k: "" }; } }

  function state(g) { var f = fav.defaults[g.id], p = picks[g.id]; if (f === undefined) return p === undefined ? "nol" : "set"; if (p === f) return fav.src[g.id] === "rec" ? "rec" : fav.src[g.id] === "home" ? "home" : "fav"; return p === undefined ? "clr" : "chg"; }
  function counts() { var y = 0, z = 0, f = 0, r = 0, x = 0; conf.games.forEach(function (g) { if (g.w !== null) return; x++; var s = state(g); if (s === "fav") f++; else if (s === "rec" || s === "home") r++; else if (s === "nol") z++; else y++; }); return { x: x, y: y, z: z, f: f, r: r }; }
  var rem = function () { return conf.games.filter(function (g) { return g.w === null; }); };

  /* ---------- strip ---------- */
  function renderStrip(res) {
    var c = counts(), seg = function (n) { return (c.x ? n / c.x * 100 : 0).toFixed(2) + "%"; };
    var h = '<div class="nums"><div class="pn"><b>' + c.x + '</b><span>games left</span></div><div class="pn"><b>' + c.y + '</b><span>changed by you</span></div>' + (c.r ? '<div class="pn z"><b>' + c.r + '</b><span>' + FC.countRec + '</span></div>' : "") + (c.z ? '<div class="pn z"><b>' + c.z + '</b><span>' + FC.countNol + '</span></div>' : "") + "</div>" +
      '<div class="pbar" aria-hidden="true"><i class="b1"></i><i class="b3"></i><i class="b2"></i></div><ul class="lg2" aria-hidden="true">' + (fav.withLine ? '<li><s class="s1"></s>' + FC.legendFav + '</li>' : "") + (fav.noLine ? '<li><s class="s3"></s>' + FC.legendRec + '</li>' : "") + '<li><s class="s2"></s>Changed by you</li>' + (c.z ? '<li><s class="s4"></s>' + FC.legendNol + '</li>' : "") + "</ul>";
    $("strip").innerHTML = h;
    var bs = $("strip").querySelectorAll(".pbar i"); bs[0].style.setProperty("width", seg(c.f)); bs[1].style.setProperty("width", seg(c.r)); bs[2].style.setProperty("width", seg(c.y));
    return c;
  }

  /* ---------- conference championship game box ---------- */
  var NUMW = ["", "One", "Two", "Three"];
  function hosted() { return !!(R.ccg && R.ccg.host && R.ccg.host !== "neutral"); }
  function pairText(o) { return hosted() ? T(o.teams[0]) + " hosts " + T(o.teams[1]) : T(o.teams[0]) + " vs " + T(o.teams[1]); }
  function mt2(i, size) { return '<span class="mt">' + LG(i, size, false) + "<span>" + esc(T(i)) + "</span></span>"; }
  function pairHtml(o, size) { return mt2(o.teams[0], size) + '<span class="vs">' + (hosted() ? "hosts" : "vs") + "</span>" + mt2(o.teams[1], size); }
  function condText(o) { var cs = o.conds.slice(0, 2).map(function (c) { return c.charAt(0).toLowerCase() === c.charAt(0) ? c : c; }); return cs.length ? "This pairing happens if " + cs.join(", or if ") + (o.conds.length > 2 ? ", or in " + (o.conds.length - 2) + " other " + (o.conds.length - 2 === 1 ? "case" : "cases") : "") + "." : ""; }
  function renderBox(res) {
    var box = $("ccg"), n = res.left, msg = "", html = "", cls = "ccg", earlyPair = null, barH = "";
    if (!res.ready && n > 0 && n <= 10) earlyPair = K.early(R, conf, picks, 10);
    if (res.ready && res.box.kind === "decided" || earlyPair) {
      var t = earlyPair || res.pair, why;
      if (earlyPair) why = list(t.map(T)) + " are the top two however the " + (n === 1 ? "unset game goes" : n + " unset games go") + ".";
      else { var hasTie = res.sections && res.sections.some(function (s) { return s.lines.length; }); why = res.pair.map(T).join(" and ") + (hasTie ? " finish first and second after the published tiebreakers. The standings show each step." : " finish first and second on conference record."); }
      html = '<p class="k">CCG</p><p class="m lgm"><span class="mp">Conference championship game:</span>' + mt2(t[0], 28) + '<span class="vs">vs</span>' + mt2(t[1], 28) + '</p><p class="y">' + esc(why) + "</p>" + hostLine(res, t);
      barH = '<span class="bt">' + LG(t[0], 24, false) + "<span>" + esc(T(t[0])) + '</span></span><span class="vs">vs</span><span class="bt">' + LG(t[1], 24, false) + "<span>" + esc(T(t[1])) + "</span></span>";
      msg = "Conference championship game: " + T(t[0]) + " vs " + T(t[1]) + ". " + why;
    } else if (res.ready) {   // not resolvable
      cls = "ccg flag"; var os = res.outcomes || [], shown = os.slice(0, 3), more = os.length - shown.length, pairKnown = res.pairKnown;
      var head = pairKnown ? "The pairing is set; the host is not" : (NUMW[Math.min(os.length, 3)] + (os.length > 3 ? " or more" : "") + " pairings are possible");
      var tied = (res.sections || []).filter(function (s) { return s.unresolved || s.lines.length; });
      var allw = os.length === 2 ? "both" : "all " + (os.length > 3 ? "the" : NUMW[os.length].toLowerCase());
      var showTxt = "so it shows " + allw + " possible " + (pairKnown ? "hosts" : "pairings") + ".";
      var tiedTxt = tied.length ? list(tied[0].teams.map(T)) + " are tied" + tied[0].desc + " for " + tied[0].what + "." : "";
      var un = null; (res.sections || []).forEach(function (sc) { sc.lines.forEach(function (l) { if (l.unres && !un) un = l; }); });
      var intro = tiedTxt, stepName;
      var pre = (R.pre || []).filter(function (x) { return x.optional; })[0];
      if (pre && un && un.step === (pre.short || pre.name)) stepName = " " + pre.t + " " + cap1(showTxt);
      else if (un && un.step && un.step !== "remaining steps") stepName = " The next published step is " + un.step + "; this tool does not have it, " + showTxt;
      else stepName = " The published steps this tool has do not settle it, " + showTxt;
      if (res.analysis && res.analysis.readings) { var rd = R.alt ? R.alt.box : "The ACC's wording on teams with different numbers of conference games can be read two ways, and the two readings give different pairings for the conference championship game"; stepName = un ? stepName + " " + rd + "; each reading is shown as its own pairing." : " " + rd + ", " + showTxt; }
      if (!tiedTxt) { intro = ""; stepName = stepName.replace(/^ /, ""); }
      html = '<p class="k">' + IC.warn + "Tie the tool cannot settle</p><p class=\"m\">" + head + '</p><p class="y">' + esc(intro + stepName) + "</p>" +
        shown.map(function (o, i) { return '<div class="pr"><p class="pk">' + (pairKnown ? "Possible host " : "Possible pairing ") + (i + 1) + '</p><p class="pm lgm">' + pairHtml(o, 24) + '</p><p class="pw">' + esc(condText(o)) + "</p></div>"; }).join("") + (more > 0 ? '<p class="y s">and ' + plural(more, "more pairing", "more pairings") + "</p>" : "");
      msg = "Tie not resolvable by this tool. " + intro + stepName + " " + shown.map(function (o, i) { return (pairKnown ? "Possible host " : "Possible pairing ") + (i + 1) + ": " + pairText(o) + "."; }).join(" ");
    } else {
      var top = res.why[0] || "";
      html = '<p class="k">CCG</p><p class="m">Not decided yet: ' + plural(n, "game", "games") + ' unset</p><p class="y">' + esc(top) + "</p>";
      msg = "Conference championship game not decided yet, " + plural(n, "game", "games") + " unset. " + top;
    }
    box.className = cls; box.innerHTML = html; updBar(box, barH); return msg;
  }
  /* The conference championship game box stays visible while the list is scrolled: a fixed one-line mirror of the box (aria-hidden; the box and #ann carry the real text). Shown only once the real box has scrolled above the top of the screen and while the simulator card is still on screen. */
  var barOn = { box: false, card: true };
  function updBar(box, barH) {
    var bar = $("ccgc"); if (!bar) return; var m = box.querySelector(".m"), flag = box.classList.contains("flag"), t = m ? (m.querySelector(".mp") ? "" : m.textContent) : "";
    var ck = bar.querySelector(".ck"), ic = bar.querySelector(".ic");
    if (flag) t = t.replace(/ (are|is) possible$/, " possible");
    bar.classList.toggle("tie", flag); ck.textContent = flag ? "" : "CCG"; if (flag) ic.removeAttribute("hidden"); else ic.setAttribute("hidden", ""); bar.querySelector("b").innerHTML = barH || '<span class="bx">' + esc(t) + "</span>"; fitBar();
  }
  /* keep the whole pairing on the one line: shrink the headline a step at a time (CSSOM only), drop the small label as a last resort; the ellipsis is only the final fallback */
  function fitBar() {
    var bar = $("ccgc"); if (!bar) return; var b = bar.querySelector("b"), ck = bar.querySelector(".ck"), base = window.innerWidth <= 360 ? 18 : 20, sz, pass;
    b.style.removeProperty("font-size"); ck.style.removeProperty("display");
    for (pass = 0; pass < 2; pass++) {
      for (sz = base; sz >= 14 && b.scrollWidth > b.clientWidth + 0.5; sz--) b.style.setProperty("font-size", sz + "px");
      if (b.scrollWidth <= b.clientWidth + 0.5 || pass) break;
      ck.style.setProperty("display", "none"); b.style.removeProperty("font-size");
    }
  }
  function barShow() { var bar = $("ccgc"); if (!bar) return; var on = barOn.box && barOn.card; bar.classList.toggle("on", on); document.documentElement.style.setProperty("--sim-sb", on ? "44px" : "0px"); }
  function watchBar() {
    window.addEventListener("resize", fitBar); if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitBar);
    if (!("IntersectionObserver" in window)) return;
    new IntersectionObserver(function (es) { var e = es[es.length - 1]; barOn.box = !e.isIntersecting && e.boundingClientRect.bottom < 80; barShow(); }, { rootMargin: "-56px 0px 0px 0px", threshold: 0 }).observe($("ccg"));
    new IntersectionObserver(function (es) { var e = es[es.length - 1]; barOn.card = e.isIntersecting; barShow(); }, { rootMargin: "-56px 0px 0px 0px", threshold: 0 }).observe(root);
  }
  function cap1(t) { return t.charAt(0).toUpperCase() + t.slice(1); }
  function hostLine(res, t) { var R0 = R.ccg || {}; if (!R0.when) return ""; var hn = hosted() && t ? " " + T(t[0]) + " hosts." : ""; return '<p class="y s">' + esc((R0.when || "") + (R0.site ? ", " + R0.site : "") + (R0.host && R0.host !== "neutral" ? (R0.host === "higher_seed" ? ". The higher seed hosts." : ". The team with the better conference record hosts.") : ".") + hn) + "</p>"; }

  /* ---------- standings ---------- */
  var tbOpen = {};
  function tkey(s) { return s.teams.slice().sort().join("-") + ":" + s.rec; }
  function renderTable(res) {
    var rows = res.table.slice(), a = res.analysis, secs = (a && a.sections) || [];
    if (res.ready && res.pairKnown && res.pair) rows.sort(function (x, y) { if (x.rank !== y.rank) return x.rank - y.rank; var ix = res.pair.indexOf(x.i), iy = res.pair.indexOf(y.i); return (ix < 0 ? 9 : ix) - (iy < 0 ? 9 : iy); });
    var h = "", ex = expandT, shown = SHOW_T, div = R.fmt === "div" && conf.div, dpos = {}, divHead = {};
    if (div) {   // two divisions: each is listed on its own, ranked within the division; each division champion plays in the conference championship game
      var dn = []; conf.div.forEach(function (d) { if (dn.indexOf(d) < 0) dn.push(d); }); dn.sort();
      var nr = []; dn.forEach(function (d) { var rk = 1, pos = 0, prev = null, k = 0; rows.filter(function (r) { return conf.div[r.i] === d; }).forEach(function (r) { k++; if (prev === null || Math.abs(prev - r.pct) > 1e-9) { rk = k; prev = r.pct; } var q = Object.assign({}, r, { rank: rk, drank: rk, pos: pos++ }); var same = rows.filter(function (z) { return conf.div[z.i] === d && Math.abs(z.pct - r.pct) < 1e-9; }).length; q.tied = same > 1; nr.push(q); }); });
      rows = nr; shown = 3 * dn.length; rows.forEach(function (r, i) { dpos[i] = r.pos; if (r.pos === 0) divHead[i] = conf.div[r.i]; });
    }
    rows.forEach(function (r, i) {
      var hid = (div ? dpos[i] >= 3 : i >= shown) && !ex, pill = "", lead = div ? (!res.ready && !r.tied && r.rank === 1) : (!res.ready && !r.tied && r.rank <= 2);
      if (div && divHead[i] !== undefined) h += '<tr class="dvh"><th colspan="3" scope="colgroup">' + esc(divHead[i]) + " division</th></tr>";
      if (r.spot === "in") pill = '<span class="xpill">Reach CCG</span>'; else if (r.spot === "possible") pill = '<span class="xpill pos">Possible spot</span>';
      else if (lead) pill = '<span class="xpill">' + (div ? "Division leader now" : "In the top two now") + "</span>";
      var rk = r.tied ? '<span aria-hidden="true">T' + r.rank + '</span><span class="vh">Tied for ' + r.rank + "</span>" : r.rank;
      var cls = (r.spot === "in" || lead ? "in" : (r.spot === "possible" ? "pos" : ""));
      h += '<tr class="' + cls + '"' + (hid ? " hidden" : "") + '><td class="r">' + rk + '</td><td><div class="tcell">' + LG(r.i, 24, hid) + '<div class="tx"><span class="tn2">' + esc(r.name) + "</span>" + pill + '</div></div></td><td class="c"><b>' + r.w + "-" + r.l + "</b><small>" + (r.left ? r.left + " unset" : "final") + "</small></td></tr>";
      secs.forEach(function (s) {
        if (!s.lines.length && !s.unresolved) return;
        var members = s.teams, lastIdx = -1; rows.forEach(function (q, k) { if (members.indexOf(q.i) >= 0) lastIdx = k; });
        if (lastIdx !== i) return;
        var key = tkey(s), open = !!tbOpen[key], labs = [];
        s.lines.forEach(function (l) { if (l.lab && labs.indexOf(l.lab) < 0) labs.push(l.lab); });
        var one = s.unresolved ? (labs.length ? "Tied teams were separated by: " + labs.join(", ") + ". Then: tie not resolvable by this tool." : "Tied" + s.desc + ": tie not resolvable by this tool.") : (labs.length ? "Tied teams were separated by: " + labs.join(", ") + "." : "Tied" + s.desc + ": " + list(members.map(T)) + ".");
        var full = '<p>Tied' + esc(s.desc) + " for " + esc(s.what) + ": " + esc(list(members.map(T))) + ".</p><ul>" + s.lines.map(function (l) { return "<li>" + esc(l.text) + "</li>"; }).join("") + "</ul>";
        h += '<tr class="tbn' + (s.unresolved ? " unr" : "") + '"' + (hid ? " hidden" : "") + '><td colspan="3"><p class="tbs">' + (s.unresolved ? IC.warn : "") + esc(one) + '</p><button type="button" class="tbx" data-k="' + esc(key) + '" aria-expanded="' + open + '" aria-controls="tbd' + i + '">How this tie was handled</button><div class="tbd" id="tbd' + i + '"' + (open ? "" : " hidden") + ">" + full + "</div></td></tr>";
      });
      if (!div && i === 1) h += '<tr class="cut"' + (shown < 2 && !ex ? " hidden" : "") + '><td colspan="3"><div>CCG cutoff</div></td></tr>';
    });
    $("stb").innerHTML = h;
    var b = $("smore"); b.hidden = rows.length <= shown; if (div) b.hidden = rows.length <= shown; b.textContent = ex ? "Show top " + shown + " only" : "Show all " + rows.length + " teams"; b.setAttribute("aria-expanded", String(ex));
  }

  /* ---------- games ---------- */
  function buildGames() {
    var ol = $("games"); ol.innerHTML = ""; rowEl = {}; var all = rem(), ws = {}, seen = {};
    all.forEach(function (g) { var w = g.wk || 0; ws[w] = (ws[w] || 0) + 1; });
    WEEKS = Object.keys(ws).map(Number).sort(function (a, b) { return a - b; });
    all.forEach(function (g) {
      var w = g.wk || 0, k = (seen[w] = (seen[w] || 0) + 1), li = document.createElement("li"), id = "g" + g.id;
      li.setAttribute("data-w", w);
      li.innerHTML = '<div class="gcard" role="group" aria-labelledby="' + id + '"><span class="gtl" id="' + id + '">Game ' + k + " of " + ws[w] + ": " + esc(T(g.h) + " vs " + T(g.a)) + '<span class="gst">' + esc(mt(g.date) + (g.neu ? ", neutral site" : "")) + '</span></span><p class="gt"></p><div class="pair">' +
        [1, 0].map(function (s) { var tm = s ? g.h : g.a; return '<button type="button" class="wb" data-g="' + g.id + '" data-s="' + s + '" aria-pressed="false"><span class="ck" aria-hidden="true"></span>' + LG(tm, 24, true) + '<span class="wt">' + esc(T(tm)) + " wins</span></button>"; }).join("") +
        '</div><div class="grs"><button type="button" class="lnk" data-r="' + g.id + '"></button></div></div>';
      rowEl[g.id] = li; ol.appendChild(li);
    });
  }
  function paint(g) {
    var li = rowEl[g.id]; if (!li) return; var st = state(g), s = SEED[st], card = li.firstChild; card.className = "gcard " + s[0];
    li.querySelector(".gt").innerHTML = IC[s[1]] + "<span>" + s[2] + "</span>" + (st === "rec" ? '<span class="vh">. ' + esc(FC.recNote) + ".</span>" : st === "home" ? '<span class="vh">. ' + esc(FC.homeNote) + ".</span>" : "");
    li.querySelectorAll(".wb").forEach(function (b) { b.setAttribute("aria-pressed", String(picks[g.id] === +b.getAttribute("data-s"))); });
    var r = li.querySelector(".lnk"), nm = T(g.h) + " vs " + T(g.a); var src = fav.src[g.id], rl = src === "rec" ? "Reset to better record" : src === "home" ? "Reset to home team" : "Reset to favorite"; r.hidden = st === "fav" || st === "rec" || st === "home" || st === "nol"; r.textContent = st === "set" ? "Unset this game" : rl;
    r.setAttribute("aria-label", (st === "set" ? "Unset game, " : rl + ", ") + nm);
  }

  /* ---------- weeks: sticky week tabs, one week at a time ---------- */
  function wgames(w) { return rem().filter(function (g) { return (g.wk || 0) === w; }); }
  function wstat(w) { var gs = wgames(w), ch = 0, un = 0; gs.forEach(function (g) { var st = state(g); if (st === "chg" || st === "clr" || st === "set") ch++; if (picks[g.id] === undefined) un++; }); return { n: gs.length, ch: ch, un: un }; }
  function drange(w) { var ds = wgames(w).map(function (g) { return dmt(g.date); }); if (!ds.length) return ""; ds.sort(function (a, b) { return a.m === b.m ? a.d - b.d : new Date(a.m + " 1 2026") - new Date(b.m + " 1 2026"); }); var a = ds[0], b = ds[ds.length - 1]; return a.m === b.m ? (a.d === b.d ? a.m + " " + a.d : a.m + " " + a.d + "\u2013" + b.d) : a.m + " " + a.d + "\u2013" + b.m + " " + b.d; }
  function wsay(w) { var s = wstat(w); return "Week " + w + ", " + plural(s.n, "game", "games") + (s.ch ? ", " + s.ch + " changed" : ""); }
  function buildWeeks() {
    var many = WEEKS.length > 1, nav = $("wkstrip"); nav.hidden = !many;
    nav.innerHTML = '<ul>' + WEEKS.map(function (w) { return '<li><button type="button" class="tab" data-w="' + w + '"><span class="n">Wk ' + w + '</span><span class="c"></span><span class="bd" aria-hidden="true" hidden></span></button></li>'; }).join("") + "</ul>";
  }
  function paintWeeks() {
    var tabs = $("wkstrip").querySelectorAll(".tab");
    Array.prototype.forEach.call(tabs, function (b) {
      var w = +b.getAttribute("data-w"), s = wstat(w), bd = b.querySelector(".bd");
      if (w === curW) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
      b.setAttribute("aria-label", wsay(w)); b.querySelector(".c").textContent = plural(s.n, "game", "games");
      bd.hidden = !s.ch; bd.textContent = s.ch || "";
    });
    var s = wstat(curW); $("wph").textContent = "Week " + curW;
    $("wsub").textContent = drange(curW) + " \u00B7 " + plural(s.n, "game", "games") + (s.ch ? " \u00B7 " + s.ch + " changed" : "");
  }
  function paintNav() {
    var i = WEEKS.indexOf(curW), n = WEEKS[i + 1], p = WEEKS[i - 1], h = "";
    var chev = function (d) { return '<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="' + d + '" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'; };
    if (n !== undefined) h += '<button type="button" class="wnav pri" data-go="' + n + '"><span>Next week<small>Week ' + n + ", " + plural(wstat(n).n, "game", "games") + "</small></span>" + chev("M8 4l7 7-7 7") + "</button>";
    else if (WEEKS.length > 1) h += '<button type="button" class="wnav pri" data-ccg="1"><span>See CCG box</span>' + chev("M5 14l6-6 6 6") + "</button>";
    if (p !== undefined) h += '<button type="button" class="wnav" data-go="' + p + '">' + chev("M14 4l-7 7 7 7") + "<span>Previous week<small>Week " + p + "</small></span></button>";
    $("wnavs").innerHTML = h;
  }
  function showWeek() {
    rem().forEach(function (g) { rowEl[g.id].hidden = (g.wk || 0) !== curW; });
    $("games").setAttribute("aria-labelledby", "wph"); paintNav();
    var cb = $("wkstrip").querySelector('.tab[aria-current="true"]'), ul = $("wkstrip").querySelector("ul");
    paintWeeks(); cb = $("wkstrip").querySelector('.tab[aria-current="true"]');
    if (cb && ul && ul.scrollWidth > ul.clientWidth) ul.scrollLeft = cb.parentNode.offsetLeft - (ul.clientWidth - cb.offsetWidth) / 2;
  }
  function setWeek(w, how) {
    if (w === curW) return; curW = w; showWeek(); announce(wsay(w));
    var h = $("wph");
    if (how === "next") { h.scrollIntoView({ block: "start" }); h.focus({ preventScroll: true }); }
    else if (how === "tab") { if (h.getBoundingClientRect().top < (parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--kt-bar-h")) || 0) + 44 + 58 + 8) h.scrollIntoView({ block: "start" }); }
  }
  function startWeek() {
    var q = /[?&]wk=(\d+)/.exec(location.search), w = q ? +q[1] : null;
    if (w !== null && WEEKS.indexOf(w) >= 0) return w;
    var u = WEEKS.filter(function (x) { return wstat(x).un > 0; })[0];
    return u !== undefined ? u : WEEKS[0];
  }

  /* ---------- render ---------- */
  function announce(msg) { lastMsg = msg; clearTimeout(annT); annT = setTimeout(function () { $("ann").textContent = ""; $("ann").textContent = lastMsg; }, 400); }
  function render(prefix) {
    var res = K.solve(R, conf, picks); last = res;
    var c = renderStrip(res), msg = renderBox(res); renderTable(res);
    rem().forEach(paint); if (curW !== null) paintWeeks();
    var dis = function (id, v) { var e = $(id); e.setAttribute("aria-disabled", String(v)); e.classList.toggle("off", v); };
    dis("rfav", K.changedCount(conf, picks, fav.defaults) === 0); dis("clr", res.left === rem().length);
    announce((prefix ? prefix + " " : "") + c.x + " games left, " + c.y + " changed by you" + (c.r ? ", " + c.r + " " + FC.countRec : "") + (c.z ? ", " + c.z + " " + FC.countNol : "") + ". " + msg);
    root.setAttribute("data-ready", "1"); root.setAttribute("data-left", res.left); root.setAttribute("data-kind", res.box.kind);
  }

  /* ---------- wiring ---------- */
  function wire() {
    $("games").addEventListener("click", function (e) {
      var r = e.target.closest(".lnk"); if (r) { var id = r.getAttribute("data-r"), g = conf.games.find(function (x) { return x.id === id; }); picks = state(g) === "set" ? K.unset(picks, id) : K.resetGame(picks, id, fav.defaults); render(); rowEl[id].querySelector(".wb").focus(); return; }
      var b = e.target.closest(".wb"); if (!b) return; var gid = b.getAttribute("data-g"), s = +b.getAttribute("data-s"); if (picks[gid] !== s) { picks = K.flip(conf, picks, gid, s); render(); }
    });
    $("stb").addEventListener("click", function (e) { var b = e.target.closest(".tbx"); if (!b) return; var k = b.getAttribute("data-k"); tbOpen[k] = !tbOpen[k]; renderTable(last); var nb = Array.prototype.filter.call($("stb").querySelectorAll(".tbx"), function (x) { return x.getAttribute("data-k") === k; })[0]; if (nb) nb.focus(); });
    $("weeks").addEventListener("click", function (e) {
      var t = e.target.closest(".tab"); if (t) { setWeek(+t.getAttribute("data-w"), "tab"); return; }
      t = e.target.closest("[data-go]"); if (t) { setWeek(+t.getAttribute("data-go"), "next"); return; }
      t = e.target.closest("[data-ccg]"); if (t) { var c = $("ccg"); c.scrollIntoView({ block: "start" }); c.focus({ preventScroll: true }); }
    });
    $("smore").onclick = function () { expandT = !expandT; renderTable(last); };
    $("rfav").onclick = function () { if (this.getAttribute("aria-disabled") === "true") return; picks = Object.assign({}, fav.defaults); render("Reset to favorites."); };
    $("clr").onclick = function () { if (this.getAttribute("aria-disabled") === "true") return; picks = {}; render("Cleared all games."); };
    $("rnd").onclick = function () { picks = {}; rem().forEach(function (g) { picks[g.id] = Math.random() < 0.5 ? 1 : 0; }); render("Random winners set."); };
  }
  function shell() {
    root.querySelector("#sim-app").innerHTML =
      '<div class="ccgc" id="ccgc" aria-hidden="true"><div class="in"><svg class="ic" hidden width="20" height="20" viewBox="0 0 22 22" aria-hidden="true"><path d="M11 2.5 20.5 19H1.5Z" fill="#fff" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M11 8.5v5" stroke="#121519" stroke-width="2.2" stroke-linecap="round"/><circle cx="11" cy="16.2" r="1.3" fill="#121519"/></svg><span class="ck"></span><b></b></div></div><div class="strip" id="strip"></div><div class="ccg" id="ccg" tabindex="-1"></div><p class="vh" id="ann" role="status" aria-live="polite" aria-atomic="true"></p>' +
      '<div class="acts2"><button type="button" class="sbtn" id="rfav" aria-disabled="true">Reset to favorites</button><button type="button" class="sbtn" id="clr">Clear all</button><button type="button" class="sbtn" id="rnd">' + IC.dice + 'Random</button></div>' +
      '<p class="xhow" id="favnote"></p>' +
      '<section id="weeks" aria-labelledby="gh"><h2 id="gh">Remaining games</h2><p class="xhow" id="how">' + FC.how + '</p><p class="slk"><a href="#sh">See standings</a></p>' +
      '<nav class="wkstrip" id="wkstrip" aria-label="Weeks"></nav><div id="wpanel"><h3 class="wph" id="wph" tabindex="-1"></h3><p class="wsub" id="wsub"></p><ol class="games" id="games" aria-labelledby="wph"></ol><div class="wnavs" id="wnavs"></div></div></section>' +
      '<h2 id="sh">Standings</h2><details class="dtl"><summary>How ties are broken</summary><div id="steps"></div></details>' +
      '<div class="tw2"><table class="xst" aria-labelledby="sh"><thead><tr><th class="r" scope="col">Rank</th><th scope="col">Team</th><th class="c" scope="col">Conf.</th></tr></thead><tbody id="stb"></tbody></table></div>' +
      '<button type="button" class="sbtn more" id="smore" aria-expanded="false" aria-controls="stb"></button>' +
      '<p class="ns">Nothing is stored. Your changes stay on this page and clear when you leave or reload.</p>';
  }
  function steps() {
    var li = function (a) { return a.map(function (s) { return "<li>" + esc(s.t || s.name || s.k) + "</li>"; }).join(""); }, h = "";
    if (R.pre && R.pre.length) h += "<p><b>Before any tiebreaker</b></p><ol>" + li(R.pre) + "</ol>";
    h += "<p><b>Two teams tied</b></p><ol>" + li(R.two) + "</ol><p><b>Three or more teams tied</b></p><ol>" + li(R.multi) + "</ol>";
    if (R.host && R.host.length) h += "<p><b>Who hosts (when the two have the same conference record)</b></p><ol>" + li(R.host) + "</ol>";
    if (R.fmt === "div") h += "<p>The conference championship game is played between the " + Object.keys(R.divisions).sort().join(" and ") + " division champions. Each division's champion is found with the lists above.</p>";
    h += "<p>Steps are tried in order; when one splits a tie, the rest restart for any teams still tied (see the conference text for the exact wording).</p>";
    (R.notes || []).forEach(function (n) { h += "<p>" + esc(n) + "</p>"; });
    if (R.doc) h += '<p class="srcl"><a href="' + esc(R.doc.url) + '" rel="noopener">Official rules: ' + esc(R.doc.title) + "</a></p><p>" + (R.doc.version ? "Version: " + esc(R.doc.version) + ". " : "") + "Checked " + esc(R.doc.checked || "") + ".</p>";
    $("steps").innerHTML = h;
  }
  function init(sim, rules, lines) {
    D = sim; R = rules.rules[CODE]; conf = D.confs[CODE]; if (!R || !conf) return fail("This conference's simulator is not available yet.");
    fav = K.favorites(conf, lines, Date.now() / 1000); picks = Object.assign({}, fav.picks);
    shell(); steps(); buildGames(); wire();
    $("favnote").textContent = fav.note; $("favnote").hidden = !fav.note;
    if (!rem().length) { $("how").textContent = "No conference games are left; these are the final standings."; $("wkstrip").hidden = true; $("wpanel").hidden = true; document.querySelector(".slk").hidden = true; }
    if (WEEKS.length) { curW = startWeek(); buildWeeks(); showWeek(); } render(); watchBar();
  }
  function get(u) { return fetch(u, { credentials: "omit" }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  Promise.all([get("/data/ccg-sim.json"), get("/data/ccg-rules.json"), get("/data/pred-lines.json").catch(function () { return null; })]).then(function (a) { init(a[0], a[1], a[2]); }).catch(function () { fail("The simulator data could not be loaded. Reload the page to try again."); });
})();
