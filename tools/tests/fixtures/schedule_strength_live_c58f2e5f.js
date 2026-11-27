/* Tool: schedule_strength (Set 2b, wave 1). How tough the opponents played and still to play are, by KickTip's own measure.
 * Facts only, no forecast. Data: data/sim-bundle.json only (played = finished games, games = unplayed games, model.rating = the KickTip team rating, teams = names and conferences).
 * Definition (D2): the mean model.rating of FBS opponents. Played = played[], remaining = games[]; FCS opponents are counted apart; neutral games count the same; home field is not adjusted.
 * Schedule rank = rank of that mean among the FBS teams that have at least one FBS opponent in that view (1 = toughest; ties by team slug). */
(function (root) {
  "use strict";
  var TB = root.KTTB || (typeof require !== "undefined" ? require("./registry.js") : null), C = TB.core;

  var COPY = {
    titleTeamLeft: "{team}: strength of the schedule left",
    titleTeamPlayed: "{team}: strength of the schedule so far",
    titleConfLeft: "{conf}: strength of the schedule left",
    titleConfPlayed: "{conf}: strength of the schedule so far",
    titleToughLeft: "Toughest schedules left",
    titleToughPlayed: "Toughest schedules so far",
    titleEasyLeft: "Easiest schedules left",
    titleEasyPlayed: "Easiest schedules so far",
    uTeamLeft: "how tough the opponents left for {team} are, by KickTip's measure",
    uTeamPlayed: "how tough the opponents {team} has played are, by KickTip's measure",
    uConfLeft: "how tough the opponents left are for each {conf} team, by KickTip's measure",
    uConfPlayed: "how tough the opponents played are for each {conf} team, by KickTip's measure",
    uToughLeft: "which teams have the toughest schedules left, by KickTip's measure",
    uToughPlayed: "which teams have played the toughest schedules, by KickTip's measure",
    uEasyLeft: "which teams have the easiest schedules left, by KickTip's measure",
    uEasyPlayed: "which teams have played the easiest schedules, by KickTip's measure",
    caption: "Schedule strength rank (1 = toughest, KickTip's measure)",
    colMeasure: "Schedule",
    colTeam: "Team",
    colMean: "Average KickTip rating",
    colRank: "Rank",
    colLeft: "Games left",
    colPlayed: "Games played",
    rowPlayed: "Opponents played ({games} FBS games)",
    rowLeft: "Opponents left ({games} FBS games)",
    rowOppLeft: "Left: {opp}",
    rowOppPlayed: "Played: {opp}",
    cMean: "{mean}",
    cRankOf: "{rk} of {of}",
    cRank: "{rk}",
    cNone: "None",
    cGames: "{games}",
    cTeamName: "{team}",
    cTeamConf: "{team} ({conf})",
    nOppRank: "On the opponent rows, Rank is KickTip rank (computer rating, not a poll).",
    nCurrent: "Past opponents are rated by their current rating, not their rating on the day.",
    nFcs: "FCS opponents are not counted.",
    nFcsLeft: "FCS games left, not counted ({fcs}).",
    nFcsPlayed: "FCS games played, not counted ({fcsp}).",
    nEmptyLeft: "No games left.",
    nEmptyPlayed: "No games played.",
    nNoFbsLeft: "No FBS games left.",
    nNoFbsPlayed: "No FBS games played.",
    nOfLeft: "Rank is out of {of} teams with at least one FBS opponent left.",
    nOfPlayed: "Rank is out of {of} teams with at least one FBS opponent played.",
    nSortTough: "Sorted from the toughest schedule to the easiest.",
    nSortEasy: "Sorted from the easiest schedule to the toughest.",
    nShown: "Showing {shown} of {of} teams.",
    nIndep: "Independent teams are listed together; each is ranked against all FBS teams."
  };

  /* the renderer checks literal digits against each copy entry's own digits list, so declare them per entry (consts only covers the static lint) */
  function withDigits(c) {
    var o = {};
    Object.keys(c).forEach(function (k) { var d = C.stripTerms(c[k]).replace(/\{[a-z0-9_]+\}/gi, " ").match(C.LITERAL_DIGITS); o[k] = d && d.length ? { t: c[k], digits: d } : c[k]; });
    return o;
  }

  /* SCHEDULE (this block is copied word for word into team_compare.js; a test proves the text and the results equal on every team) */
  function scheduleTable(B) {
    var F = B.fcs, rt = B.model.rating, st = [], i;
    for (i = 0; i < B.teams.length; i++) st.push(i === F || !B.teams[i].g ? null : { played: { sum: 0, n: 0, fcs: 0 }, remaining: { sum: 0, n: 0, fcs: 0 } });
    function add(t, view, opp) { var s = st[t]; if (!s) return; if (opp === F) s[view].fcs++; else { s[view].sum += rt[opp]; s[view].n++; } }
    B.played.forEach(function (g) { add(g[0], "played", g[1]); add(g[1], "played", g[0]); });
    B.games.forEach(function (g) { add(g.h, "remaining", g.a); add(g.a, "remaining", g.h); });
    ["played", "remaining"].forEach(function (view) {
      var list = [];
      st.forEach(function (s, t) { if (s) { s[view].mean = s[view].n > 0 ? s[view].sum / s[view].n : null; if (s[view].n > 0) list.push(t); } });
      list.sort(function (a, b) { return st[b][view].mean - st[a][view].mean || (B.teams[a].g < B.teams[b].g ? -1 : B.teams[a].g > B.teams[b].g ? 1 : 0); });
      list.forEach(function (t, k) { st[t][view].rank = k + 1; st[t][view].of = list.length; });
    });
    return st;
  }
  /* END SCHEDULE */

  function ktRanks(B) {   /* KickTip rank of every FBS team by model.rating (1 = highest; ties by index): the same order team_snapshot shows */
    var idx = [], rk = [], i;
    for (i = 0; i < B.teams.length; i++) { if (i !== B.fcs && B.teams[i].g) idx.push(i); rk.push(null); }
    idx.sort(function (a, b) { return B.model.rating[b] - B.model.rating[a] || a - b; });
    idx.forEach(function (t, k) { rk[t] = k + 1; });
    return rk;
  }

  TB.register({
    id: "schedule_strength",
    set: 2, priority: "P1", live: false,
    kind: "lookup", card: "table",
    description: "How tough the opponents played and still to play are, by KickTip's own measure: one team, one conference or the national list.",
    modes: ["home", "conference", "team"],
    params: {
      team: { type: "team" },
      conference: { type: "conf" },
      view: { type: "enum", values: ["played", "remaining", "both"], default: "remaining" },
      n: { type: "int", min: 1, max: 10, typed: true },
      order: { type: "enum", values: ["toughest", "easiest"], default: "toughest" }
    },
    data: ["sim-bundle"],
    examples: ["How hard is BYU's remaining schedule?", "Toughest schedule left in the Big 12", "Who has the easiest schedule left?"],
    consts: ["1"],
    gates: [],
    copy: withDigits(COPY),

    run: function (params, data, ctx) {
      var B = data["sim-bundle"], team = params.team || null, conf = params.conference || null, view = params.view || "remaining", n = params.n || 5, order = params.order || "toughest";
      if (team && conf) return { ok: false, reason: "bad_param" };
      var st = scheduleTable(B), kr = ktRanks(B), asof = { label: C.asofLabel(B.as_of), files: [{ file: "sim-bundle", label: C.asofLabel(B.as_of) }] };
      function nm(i) { return B.teams[i].s; }
      function confName(c) { var k; for (k = 0; k < C.CONFS.length; k++) if (C.CONFS[k][0] === c) return C.CONFS[k][1]; return c; }
      function pack(i, v) { var s = st[i][v]; return { games: s.n, fcs: s.fcs, mean: s.mean, rank: s.rank === undefined ? null : s.rank, of: s.of === undefined ? null : s.of }; }
      var facts;
      if (team) {
        var t = ctx.idx[team]; if (t === undefined || !st[t]) return { ok: false, reason: "not_modeled" };
        var opps = { remaining: [], played: [] };
        B.games.forEach(function (g) { if (g.h === t || g.a === t) { var o = g.h === t ? g.a : g.h; if (o !== B.fcs) opps.remaining.push({ slug: B.teams[o].g, name: nm(o), rating: B.model.rating[o], rank: kr[o] }); } });
        B.played.forEach(function (g) { if (g[0] === t || g[1] === t) { var o = g[0] === t ? g[1] : g[0]; if (o !== B.fcs) opps.played.push({ slug: B.teams[o].g, name: nm(o), rating: B.model.rating[o], rank: kr[o] }); } });
        ["remaining", "played"].forEach(function (v) { opps[v].sort(function (a, b) { return a.rank - b.rank; }); });
        facts = { mode: "team", view: view, team: { slug: team, name: nm(t), conf: B.teams[t].c }, remaining: pack(t, "remaining"), played: pack(t, "played"), opps: opps };
      } else {
        var vk = view === "played" ? "played" : "remaining";
        if (view === "both") return { ok: false, reason: "not_applicable" };
        var rows = [], i;
        for (i = 0; i < B.teams.length; i++) {
          if (!st[i]) continue;
          if (conf && B.teams[i].c !== conf) continue;
          var p = pack(i, vk); rows.push({ slug: B.teams[i].g, name: nm(i), conf: B.teams[i].c, conf_name: confName(B.teams[i].c), games: p.games, fcs: p.fcs, mean: p.mean, rank: p.rank, of: p.of });
        }
        if (!rows.length) return { ok: false, reason: "not_modeled" };
        if (conf) {
          rows.sort(function (a, b) { var d = (a.rank === null ? 1e9 : a.rank) - (b.rank === null ? 1e9 : b.rank); if (order === "easiest" && a.rank !== null && b.rank !== null) d = -d; return d || (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0); });   /* toolbox9: order=easiest reverses the ranked rows (teams with no rank stay last) */
          facts = { mode: "conference", view: vk, order: order, conf: { id: conf, name: confName(conf) }, rows: rows, of: st.reduce(function (m, s) { return s && s[vk].of ? s[vk].of : m; }, 0), independent: conf === "ind" };
        } else {
          var have = rows.filter(function (r) { return r.rank !== null; }), total = have.length;
          have.sort(function (a, b) { return order === "easiest" ? b.rank - a.rank : a.rank - b.rank; });
          facts = { mode: "national", view: vk, order: order, rows: have.slice(0, n), top: n, shown: Math.min(n, total), of: total };
        }
      }
      return { ok: true, tool: "schedule_strength", params: params, asof: asof, facts: facts };
    },

    render: function (r) {
      var F = r.facts, V = {}, rows = [], notes = [], cols, title, und;
      if (F.mode === "team") {
        var left = F.view !== "played";
        V.team = { t: "text", v: F.team.name, src: "facts.team.name" };
        title = left ? COPY.titleTeamLeft : COPY.titleTeamPlayed; und = left ? COPY.uTeamLeft : COPY.uTeamPlayed;
        cols = [COPY.colMeasure, COPY.colMean, COPY.colRank];
        var order = left ? ["remaining", "played"] : ["played", "remaining"];
        order.forEach(function (v) {
          var s = F[v], b = "facts." + v + ".", vals = { games: { t: "int", v: s.games, src: b + "games" } }, cells = [v === "remaining" ? COPY.rowLeft : COPY.rowPlayed];
          if (s.games > 0) { vals.mean = { t: "num1", v: s.mean, src: b + "mean" }; vals.rk = { t: "rank", v: s.rank, src: b + "rank" }; vals.of = { t: "int", v: s.of, src: b + "of" }; cells.push(COPY.cMean, COPY.cRankOf); }
          else cells.push(COPY.cNone, COPY.cNone);
          rows.push({ cells: cells, src: "facts." + v, vals: vals });
        });
        order.forEach(function (v) {
          if (v === "played" && F.view === "remaining") return;
          if (v === "remaining" && F.view === "played") return;
          F.opps[v].forEach(function (o, k) {
            var b = "facts.opps." + v + "." + k + ".";
            rows.push({ cells: [v === "remaining" ? COPY.rowOppLeft : COPY.rowOppPlayed, COPY.cMean, COPY.cRank], src: "facts.opps." + v + "." + k, vals: { opp: { t: "text", v: o.name, src: b + "name" }, mean: { t: "num1", v: o.rating, src: b + "rating" }, rk: { t: "rank", v: o.rank, src: b + "rank" } } });
          });
        });
        if (F.view !== "played") { if (F.remaining.games + F.remaining.fcs === 0) notes.push(COPY.nEmptyLeft); else if (F.remaining.games === 0) notes.push(COPY.nNoFbsLeft); }
        if (F.view !== "remaining") { if (F.played.games + F.played.fcs === 0) notes.push(COPY.nEmptyPlayed); else if (F.played.games === 0) notes.push(COPY.nNoFbsPlayed); }
        if (F.remaining.fcs > 0) { V.fcs = { t: "int", v: F.remaining.fcs, src: "facts.remaining.fcs" }; notes.push(COPY.nFcsLeft); }
        if (F.played.fcs > 0) { V.fcsp = { t: "int", v: F.played.fcs, src: "facts.played.fcs" }; notes.push(COPY.nFcsPlayed); }
        notes.push(COPY.nFcs, COPY.nOppRank, COPY.nCurrent);
      } else {
        var isL = F.view !== "played";
        cols = [COPY.colTeam, isL ? COPY.colLeft : COPY.colPlayed, COPY.colMean, COPY.colRank];
        if (F.mode === "conference") {
          V.conf = { t: "text", v: F.conf.name, src: "facts.conf.name" };
          title = isL ? COPY.titleConfLeft : COPY.titleConfPlayed; und = isL ? COPY.uConfLeft : COPY.uConfPlayed;
        } else {
          title = F.order === "easiest" ? (isL ? COPY.titleEasyLeft : COPY.titleEasyPlayed) : (isL ? COPY.titleToughLeft : COPY.titleToughPlayed);
          und = F.order === "easiest" ? (isL ? COPY.uEasyLeft : COPY.uEasyPlayed) : (isL ? COPY.uToughLeft : COPY.uToughPlayed);
        }
        F.rows.forEach(function (x, k) {
          var p = "facts.rows." + k + ".", vals = { games: { t: "int", v: x.games, src: p + "games" }, team: { t: "text", v: x.name, src: p + "name" } }, cells = [F.mode === "national" ? COPY.cTeamConf : COPY.cTeamName, COPY.cGames];
          if (F.mode === "national") vals.conf = { t: "text", v: x.conf_name, src: p + "conf_name" };
          if (x.rank !== null) { vals.mean = { t: "num1", v: x.mean, src: p + "mean" }; vals.rk = { t: "rank", v: x.rank, src: p + "rank" }; cells.push(COPY.cMean, COPY.cRank); }
          else cells.push(COPY.cNone, COPY.cNone);
          rows.push({ cells: cells, src: "facts.rows." + k, vals: vals });
        });
        V.of = { t: "int", v: F.of, src: "facts.of" };
        if (F.mode === "conference") {
          notes.push(isL ? COPY.nOfLeft : COPY.nOfPlayed, F.order === "easiest" ? COPY.nSortEasy : COPY.nSortTough);
          if (F.independent) notes.push(COPY.nIndep);
        } else {
          V.shown = { t: "int", v: F.shown, src: "facts.shown" };
          notes.push(COPY.nShown, F.order === "easiest" ? COPY.nSortEasy : COPY.nSortTough, isL ? COPY.nOfLeft : COPY.nOfPlayed);
        }
        notes.push(COPY.nFcs, COPY.nCurrent);
      }
      return { type: "table", title: title, understood: und, vals: V, caption: COPY.caption, cols: cols, rows: rows, notes: notes, chips: [] };
    }
  });
  if (typeof module !== "undefined" && module.exports) module.exports = TB;
})(typeof self !== "undefined" ? self : globalThis);
