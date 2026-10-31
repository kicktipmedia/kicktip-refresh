  /* cc5: scenario result view (Creative rev 3 mock d3c61dfa, Jared OK 12:39 PM MT Oct 31). Championship card with both teams' records, then the full standings with conference and overall W-L,
     changed-team marks against the starting results (BASE = K.solve on fav.picks, set in init) and T places. Display only: K.solve and the tiebreaker steps are not touched. */
  var BASE = null, NB = function (s) { return esc(s).replace(/ /g, "&nbsp;"); };
  function ccOv(r) { var n = (conf.nc && conf.nc[r.i]) || { w: 0, g: 0, left: 0 }; return { w: r.w + n.w, l: r.g + n.g - r.w - n.w, left: n.left || 0 }; }
  function ccGroups(res) {   /* [{name, rows}] in display order: one group, or one per division (Sun Belt) */
    var rows = res.table.slice(), div = R.fmt === "div" && conf.div;
    if (!div) return [{ name: "", rows: rows }];
    var dn = []; conf.div.forEach(function (d) { if (dn.indexOf(d) < 0) dn.push(d); }); dn.sort();
    return dn.map(function (d) { var rs = rows.filter(function (r) { return conf.div[r.i] === d; }), k = 0, rk = 1, prev = null; rs = rs.map(function (r) { k++; if (prev === null || Math.abs(prev - r.pct) > 1e-9) { rk = k; prev = r.pct; } return Object.assign({}, r, { rank: rk }); }); rs.forEach(function (r) { r.tied = rs.filter(function (z) { return z.rank === r.rank; }).length > 1; }); return { name: d, rows: rs }; });
  }
  function ccPlaces(res) {   /* gen.py places(): the pair takes 1-2 (in a division, its champion takes 1); everyone else uses the rank, T for ties */
    var pair = (res.ready && res.pairKnown && res.pair) || [], out = {}, gs = ccGroups(res);
    gs.forEach(function (gp) {
      var rows = gp.rows.slice().sort(function (x, y) { var px = pair.indexOf(x.i), py = pair.indexOf(y.i); return x.rank - y.rank || (px < 0 ? 1 : 0) - (py < 0 ? 1 : 0) || px - py || (x.name < y.name ? -1 : x.name > y.name ? 1 : 0); });
      rows.forEach(function (x, k) {
        var lab, same = gp.rows.filter(function (y) { return y.rank === x.rank; });
        if (pair.indexOf(x.i) >= 0) lab = String(k + 1);
        else { lab = (x.tied ? "T" : "") + x.rank; if (x.tied && same.some(function (y) { return pair.indexOf(y.i) >= 0; })) lab = (same.filter(function (y) { return pair.indexOf(y.i) < 0; }).length === 1 ? "" : "T") + (k + 1); }
        out[x.i] = { p: k + 1, lab: lab, r: x };
      });
      gp.sorted = rows;
    });
    return { pl: out, groups: gs, pair: pair };
  }
  function ccFlips() {   /* the games the visitor changed from the starting results, in date order */
    return rem().filter(function (g) { var s = state(g); return (s === "chg" || s === "set") && picks[g.id] !== undefined && picks[g.id] !== null; }).sort(function (a, b) { return (a.wk || 0) - (b.wk || 0) || (a.date < b.date ? -1 : 1); });
  }
  function ccDay(g) { var d = dmt(g.date, g.id), t = dmt(new Date().toISOString()); return d.k === t.k ? "Today" : d.m + "&nbsp;" + d.d; }
  /* cc5 venue line from rules data: MT first, one host sentence */
  function ccMT(w) { return String(w || "").replace(/^([A-Z][a-z]{2} [A-Z][a-z]{2} \d+), (\d+:\d\d [AP]M) ([ECP]T) \((\d+:\d\d [AP]M) MT\)/, "$1, $4 MT ($2 $3)"); }
  function ccHost(t) { var R0 = R.ccg || {}; if (!R0.when) return ""; var w = ccMT(R0.when), hs = R0.host;
    if (!hs || hs === "neutral") return '<p class="y s">' + esc((w + (R0.site ? ", " + R0.site : "")).replace(/\.?$/, ".")) + "</p>";
    var who = hs === "higher_seed" ? "The higher seed hosts" : "The " + (R.fmt === "div" && conf.div ? "division champion" : "team") + " with the better conference record hosts";
    return '<p class="y s">' + esc(w + ". " + who + (t ? ": " + T(t[0]) : "") + ".") + "</p>"; }
  function ccCard(t, res) {
    w4card(t, res);   /* keeps W4data (share image) exactly as before */
    var fl = ccFlips(), P = ccPlaces(res), div = R.fmt === "div" && conf.div, cn = NB(NAME);
    var h = '<p class="cc5l">Your changes (' + fl.length + ")</p>";
    if (fl.length) h += '<ul class="cc5ch">' + fl.map(function (g) { var w = picks[g.id] === 1 ? g.h : g.a, l = w === g.h ? g.a : g.h; return '<li class="cc5fc"><span class="cc5ft">Flipped &middot; ' + ccDay(g) + "</span>If " + NB(T(l)) + " loses to " + NB(T(w)) + "</li>"; }).join("") + "</ul>";
    h += '<p class="cc5n">' + esc(w4restTxt(w4rest(), fl.length)) + "</p>";
    var top = res.table.filter(function (r) { return r.rank === res.table.filter(function (z) { return z.i === t[0]; })[0].rank; }), pill = "";
    if (!div && top.length > 1 && top.some(function (r) { return r.i === t[0]; })) pill = "Won a " + top.length + "-way tie at " + top[0].w + "-" + top[0].l;
    var side = function (i, k) { var r = P.pl[i].r, o = ccOv(r), sd = div ? NB(conf.div[i]) + "&nbsp;division" : "No.&nbsp;" + k + " seed"; return '<div class="cc5s">' + LG(i, 40, false) + '<div class="cc5t"><div class="cc5sd">' + sd + '</div><div class="cc5nm">' + NB(T(i)) + '</div><div class="cc5r">' + r.w + "-" + r.l + "&nbsp;<span>" + cn + "&nbsp;&middot;&nbsp;" + o.w + "-" + o.l + "</span></div></div></div>"; };
    h += '<section class="cc5c" aria-label="' + esc(NAME) + ' championship"><div class="cc5top"><b>' + cn + " championship</b>" + (pill ? "<span>" + esc(pill) + "</span>" : "") + "</div>";
    h += '<div class="cc5vs">' + side(t[0], 1) + "<i>vs</i>" + side(t[1], 2) + "</div>";
    if (BASE && BASE.ready && BASE.pairKnown && BASE.pair) h += '<div class="cc5b">Starting results: ' + NB(T(BASE.pair[0])) + " vs " + NB(T(BASE.pair[1])) + "</div>";
    if (res.why && res.why.length) h += '<details class="cc5w"><summary>Why these two? (tiebreakers)</summary><ol>' + res.why.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("") + "</ol></details>";
    h += "</section>" + ccHost(t) + '<button type="button" class="w4sh" data-w4="share">' + (!w4canShare() ? "Download image" : "Share results") + "</button>";
    return h;
  }
  function ccTable(res) {
    var P = ccPlaces(res), B = BASE && res.ready ? ccPlaces(BASE) : null, bp = (B && B.pair) || [], flipT = {}, h = "", div = R.fmt === "div" && conf.div;
    ccFlips().forEach(function (g) { flipT[g.h] = 1; flipT[g.a] = 1; });
    P.groups.forEach(function (gp) {
      if (div) h += '<tr class="dvh"><th colspan="4" scope="colgroup">' + esc(gp.name) + " division</th></tr>";
      gp.sorted.forEach(function (x) {
        var i = x.i, s = P.pl[i], b = B && B.pl[i], o = ccOv(x), inS = P.pair.indexOf(i) >= 0, inB = bp.indexOf(i) >= 0, mk = "", was = "", tags = "";
        var ch = !!b && (x.w !== b.r.w || x.l !== b.r.l || s.lab !== b.lab || inS !== inB), mv = b ? b.p - s.p : 0;
        if (ch) { mk = mv > 0 ? '<span class="cc5mv up"><span aria-hidden="true">&#9650;' + mv + '</span><span class="vh">up ' + mv + "</span></span>" : mv < 0 ? '<span class="cc5mv"><span aria-hidden="true">&#9660;' + (-mv) + '</span><span class="vh">down ' + (-mv) + "</span></span>" : '<span class="cc5mv">Changed</span>'; was = "<small>was&nbsp;" + b.lab + "&nbsp;&middot;&nbsp;" + b.r.w + "-" + b.r.l + "</small>"; }
        if (inS) tags += '<span class="cc5tg in">Championship</span>'; if (flipT[i]) tags += '<span class="cc5tg fl">Game&nbsp;flipped</span>';
        var pl = /^T/.test(s.lab) ? '<span aria-hidden="true">' + s.lab + '</span><span class="vh">Tied for ' + s.lab.slice(1) + "</span>" : s.lab;
        h += '<tr class="' + (ch ? "chg" : "") + (inS ? " inp" : "") + '"><td class="pl">' + pl + '</td><td class="tm"><div class="cc5tw">' + LG(i, 28, false) + "<div><b>" + esc(x.name) + "</b>" + (mk ? "&nbsp;" + mk : "") + '<div class="cc5tgs">' + tags + was + '</div></div></div></td><td class="n"><b>' + x.w + "-" + x.l + '</b></td><td class="n o">' + o.w + "-" + o.l + (o.left ? "*" : "") + "</td></tr>";
      });
    });
    $("stb").innerHTML = h; $("sh").innerHTML = (res.ready ? "Final " : "") + NB(NAME) + " standings"; $("cclg").hidden = !B;
    var any = res.table.some(function (r) { return ccOv(r).left > 0; });
    $("ccnc").hidden = !any;
    $("smore").hidden = true;
  }
