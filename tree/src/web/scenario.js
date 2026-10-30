/* KickTip scenario resolver (browser + Node): turns the parser's structured output into engine inputs.
 *   KTScenario.resolve(parsed, bundle) -> {ok, forced:{gameId:1|0}, constraints:[{team,games,wins}], games:[{id, home, away, winner, kind}], need, baseline_team, clarify:null|{reason, ...}}
 * No prose here; reasons are codes the UI turns into text (answer.js). forced: 1 = home team wins. */
(function (root) {
  "use strict";
  var MAX_ITEMS = 8;   // c1: at most 8 game results (clauses) per question; the engine itself has no limit (see MULTIGAME-ANSWER.md)
  function resolve(parsed, bundle) {
    var out = { ok: false, forced: {}, constraints: [], games: [], echo: [], inprogress: [], need: parsed.need || null, baseline_team: parsed.baseline_team, clarify: null };
    if (parsed.refusal || parsed.clarify) { out.clarify = { reason: parsed.refusal ? "refusal" : parsed.clarify_reason }; return out; }
    var G = bundle.games, fcs = bundle.fcs;
    var teamGames = function (t) { return G.filter(function (g) { return g.h === t || g.a === t; }).sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : (a.id < b.id ? -1 : 1); }); };
    var cur = -1;
    function setForced(g, winner, kind) {
      var v = winner === g.h ? 1 : 0;
      if (g.id in out.forced && out.forced[g.id] !== v) return false;
      if (!(g.id in out.forced)) out.games.push({ id: g.id, item: cur, home: g.h, away: g.a, winner: winner, kind: kind, week: g.wk, neutral: !!g.neu, date: g.date, ip: g.ip || 0 });
      if (g.ip && out.inprogress.indexOf(g.id) < 0) out.inprogress.push(g.id);
      out.forced[g.id] = v; return true;
    }
    var items = parsed.items || [];
    if (items.length > MAX_ITEMS) { out.clarify = { reason: "too_many_items", max: MAX_ITEMS, n: items.length }; return out; }
    for (var i = 0; i < items.length; i++) {
      var it = items[i], gs, k; cur = i;
      if (it.kind === "beats") {
        gs = G.filter(function (g) { return (g.h === it.winner && g.a === it.loser) || (g.h === it.loser && g.a === it.winner); });
        if (!gs.length) {
          var played = (bundle.played || []).filter(function (p) { return (p[0] === it.winner && p[1] === it.loser) || (p[0] === it.loser && p[1] === it.winner); });
          out.clarify = { reason: played.length ? "already_played" : "no_remaining_game", teams: [it.winner, it.loser] };
          if (played.length) { var q = played[played.length - 1]; out.clarify.result = { home: q[0], away: q[1], hs: q[2], as: q[3], week: q[4] }; }
          return out;
        }
        if (gs.length > 1 && it.site) gs = gs.filter(function (g) { return it.site === "winner_home" ? g.h === it.winner : g.a === it.winner; });
        if (gs.length > 1) { out.clarify = { reason: "multiple_games", teams: [it.winner, it.loser] }; return out; }
        if (it.site && !gs[0].neu && ((it.site === "winner_home") !== (gs[0].h === it.winner))) { out.clarify = { reason: "site_conflict", teams: [it.winner, it.loser], home: gs[0].h }; return out; }
        if (!setForced(gs[0], it.winner, "beats")) { out.clarify = { reason: "conflict", teams: [it.winner, it.loser] }; return out; }
      } else if (it.kind === "next_win" || it.kind === "next_loss") {
        // c1: bare "X wins" / "X loses" = X's next remaining game (earliest date; a game in progress counts). Two games on the same day cannot be told apart: ask.
        gs = teamGames(it.team);
        if (!gs.length) { out.clarify = { reason: "no_remaining_game", teams: [it.team] }; return out; }
        if (gs.length > 1 && gs[0].date.slice(0, 10) === gs[1].date.slice(0, 10)) { out.clarify = { reason: "multiple_games", teams: [it.team] }; return out; }
        var og = gs[0], opp1 = og.h === it.team ? og.a : og.h;
        if (!setForced(og, it.kind === "next_win" ? it.team : opp1, it.kind)) { out.clarify = { reason: "conflict", teams: [it.team] }; return out; }
        out.echo[i] = { game: og.id, team: it.team, opponent: opp1, winner: it.kind === "next_win" ? it.team : opp1, home: og.h, away: og.a, week: og.wk, date: og.date, neutral: !!og.neu, ip: og.ip || 0, fcs: og.fcs || null };
      } else if (it.kind === "wins_out" || it.kind === "loses_out") {
        gs = teamGames(it.team);
        if (!gs.length) { out.clarify = { reason: "no_remaining_game", teams: [it.team] }; return out; }
        for (k = 0; k < gs.length; k++) {
          var opp = gs[k].h === it.team ? gs[k].a : gs[k].h, w = it.kind === "wins_out" ? it.team : opp;
          if (!setForced(gs[k], w, it.kind)) { out.clarify = { reason: "conflict", teams: [it.team] }; return out; }
        }
      } else if (it.kind === "wins_n_of_m") {
        gs = teamGames(it.team);
        if (it.n > it.m || it.m < 1) { out.clarify = { reason: "invalid_count", teams: [it.team] }; return out; }
        if (it.m > gs.length) { out.clarify = { reason: "too_many_games", teams: [it.team], remaining: gs.length }; return out; }
        gs = it.scope === "last" ? gs.slice(gs.length - it.m) : gs.slice(0, it.m);
        if (gs.some(function (g) { return g.id in out.forced; })) { out.clarify = { reason: "conflict", teams: [it.team] }; return out; }
        out.constraints.push({ team: it.team, games: gs.map(function (g) { return g.id; }), wins: it.n });
        gs.forEach(function (g) { out.games.push({ id: g.id, item: i, home: g.h, away: g.a, winner: null, kind: "wins_n_of_m", week: g.wk, neutral: !!g.neu, team: it.team, date: g.date, ip: g.ip || 0 }); if (g.ip && out.inprogress.indexOf(g.id) < 0) out.inprogress.push(g.id); });
      }
    }
    // a team can have constraints from two clauses only if they never share a game
    var seen = {}; for (var c = 0; c < out.constraints.length; c++) for (var q = 0; q < out.constraints[c].games.length; q++) { var id = out.constraints[c].games[q]; if (seen[id]) { out.clarify = { reason: "conflict" }; return out; } seen[id] = 1; }
    out.ok = true; return out;
  }
  var API = { resolve: resolve, MAX_ITEMS: MAX_ITEMS };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.KTScenario = API;
})(typeof self !== "undefined" ? self : this);
