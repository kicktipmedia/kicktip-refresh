/* KickTip answer templates (browser + Node): engine results + baseline -> labeled text and table data.
 * Every answer starts with the same label line. Wording is neutral analysis: no betting language, no school logos, no bookmaker names.
 * Functions return plain objects ({header, lines, table, notes}); the UI decides how to draw them. Results are fractions 0..1 as returned by KTSim.simulate. */
(function (root) {
  "use strict";
  var METRICS = [["ccg", "Reach the conference championship game"], ["title", "Win conference title"], ["cfp12", "Make the 12-team playoff field"], ["bye", "Earn a first-round bye"]];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var GOAL = { playoff: ["cfp12", "make the 12-team playoff field"], conference: ["title", "win the conference title"], title_game: ["ccg", "reach the conference championship game"], bye: ["bye", "earn a first-round bye"] };

  function commas(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function asOfLabel(asOf) {            // "2026-10-23 22:06 MT" -> "Oct 23, 2026, 10:06 PM MT"
    var m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)/.exec(asOf || ""); if (!m) return String(asOf || "");
    var h = parseInt(m[4], 10), ap = h >= 12 ? "PM" : "AM", h12 = h % 12 === 0 ? 12 : h % 12;
    return MONTHS[parseInt(m[2], 10) - 1] + " " + parseInt(m[3], 10) + ", " + m[1] + ", " + h12 + ":" + m[5] + " " + ap + " MT";
  }
  function header(N, asOf, model) { return "Simulation analysis (" + (model || "KickTip model") + "), not betting advice. Based on " + commas(N) + " simulated seasons as of " + asOfLabel(asOf) + "."; }
  /* c1: the model line and the standing footers (same wording in every answer) */
  function modelLine(bundle) { return "Model: " + (bundle.model_label || "KickTip blend") + (bundle.model_default === false ? " (alternate model)" : " (default model)"); }
  var NOISE = "Before numbers come from a fresh run in your browser and can differ from the page by a point or two (random sampling).";
  var TIEBREAK = "Conference tiebreakers follow the published rules; steps that depend on other public rating systems use KickTip's rating as a stand-in, so this does not claim official tiebreaker results.";
  var INPROG = "A game in this scenario is in progress. Our data updates every few hours, so its live score is not used.";
  function footers(bundle, resolved) { var f = { model: modelLine(bundle), noise: NOISE, tiebreak: TIEBREAK, inprogress: resolved && resolved.inprogress && resolved.inprogress.length ? INPROG : null }; return f; }
  function pct(x) { var v = x * 100; if (v > 0 && v < 0.1) return "<0.1%"; if (v > 99.9 && v < 100) return ">99.9%"; return v.toFixed(1) + "%"; }
  function delta(d) { var v = d * 100, s = Math.abs(v).toFixed(1); return (s === "0.0" ? "" : v > 0 ? "+" : "-") + s + " pts"; }   /* a change that rounds to 0.0 prints "0.0 pts", never "-0.0 pts" or "+0.0 pts" */
  function moe(N) { return 1.96 * Math.sqrt(0.25 / N) * Math.SQRT2; }       // 95% half-width in fraction units for the difference of two runs of N seasons (worst case p = 0.5)
  function tn(bundle, t) { return bundle.teams[t].n; }
  function applicable(bundle, t, key) { var c = bundle.teams[t].c; if (c === "ind" && (key === "ccg" || key === "title")) return false; return true; }

  function describe(bundle, resolved) {
    var lines = [], byTeam = {};
    resolved.games.forEach(function (g) {
      if (g.kind === "wins_n_of_m") return;
      if (g.kind === "wins_out" || g.kind === "loses_out") { var t = g.winner === g.home ? g.home : g.away; var tt = g.kind === "wins_out" ? g.winner : (g.winner === g.home ? g.away : g.home); (byTeam[tt] = byTeam[tt] || { kind: g.kind, n: 0 }).n++; return; }
      var loser = g.winner === g.home ? g.away : g.home;
      lines.push(tn(bundle, g.winner) + " beats " + tn(bundle, loser) + (g.neutral ? " (neutral site)" : " (at " + tn(bundle, g.home) + ")") + ", week " + g.week);
    });
    Object.keys(byTeam).forEach(function (t) { var o = byTeam[t]; lines.unshift(tn(bundle, +t) + (o.kind === "wins_out" ? " wins out" : " loses out") + " (" + o.n + " remaining game" + (o.n === 1 ? "" : "s") + ")"); });
    resolved.constraints.forEach(function (c) { lines.push(tn(bundle, c.team) + " wins exactly " + c.wins + " of " + c.games.length + " specified games (all other games play out as simulated)"); });
    return lines;
  }
  function focusTeams(resolved, bundle) {
    var s = {}; resolved.games.forEach(function (g) { s[g.home] = 1; s[g.away] = 1; });
    return Object.keys(s).map(Number).filter(function (t) { return t !== bundle.fcs; });
  }
  /* before = baseline result, after = scenario result (both KTSim.simulate outputs with the same N). */
  function scenarioAnswer(bundle, resolved, before, after, N, asOf, opts) {
    opts = opts || {}; var maxRows = opts.maxRows || 8, minMove = opts.minMove === undefined ? 0.01 : opts.minMove, noise = moe(N);
    var focus = focusTeams(resolved, bundle), score = [];
    for (var t = 0; t < bundle.n; t++) { if (t === bundle.fcs) continue; var d = 0; METRICS.forEach(function (m) { if (applicable(bundle, t, m[0])) d = Math.max(d, Math.abs(after[m[0]][t] - before[m[0]][t])); }); score.push([t, d]); }
    score.sort(function (a, b) { return b[1] - a[1]; });
    var chosen = focus.slice(); score.forEach(function (x) { if (chosen.length < maxRows && chosen.indexOf(x[0]) < 0 && x[1] >= minMove) chosen.push(x[0]); });
    var rows = chosen.map(function (t) {
      var cells = {}; METRICS.forEach(function (m) {
        var k = m[0]; if (!applicable(bundle, t, k)) { cells[k] = null; return; }
        var b = before[k][t], a = after[k][t], d = a - b;
        cells[k] = { before: b, after: a, change: d, before_text: pct(b), after_text: pct(a), change_text: delta(d), meaningful: Math.abs(d) > noise };
      });
      return { team: t, name: tn(bundle, t), conference: bundle.teams[t].c, cells: cells };
    });
    rows.sort(function (x, y) { var fx = focus.indexOf(x.team) >= 0 ? 0 : 1, fy = focus.indexOf(y.team) >= 0 ? 0 : 1; if (fx !== fy) return fx - fy; return 0; });
    return {
      header: header(N, asOf, bundle.model_label), model_label: bundle.model_label || "KickTip blend", footers: footers(bundle, resolved), scenario_lines: describe(bundle, resolved),
      table: { columns: ["Team"].concat(METRICS.map(function (m) { return m[1]; })), metrics: METRICS.map(function (m) { return m[0]; }), rows: rows },
      notes: ["Each cell shows the chance before the scenario, after it, and the change in percentage points.", "Changes smaller than about " + (noise * 100).toFixed(1) + " points are within simulation noise at this many seasons.", "Games not named in the scenario play out as simulated. Conference tiebreaks and the 12-team field follow the KickTip model."]
    };
  }
  /* need answer: per remaining game of `team`, the chance for the chosen goal if the team wins vs loses it (precomputed single-game what-ifs), plus optional wins-out / loses-out runs. */
  function needAnswer(bundle, whatif, getShard, team, goal, base, N, asOf, runs) {
    var G = GOAL[goal] || GOAL.playoff, mi = whatif.metrics.indexOf(G[0]), b = base[G[0]][team], rows = [];
    bundle.games.filter(function (g) { return g.h === team || g.a === team; }).forEach(function (g) {
      var e = getShard(g.wk)[g.id]; if (!e) return;
      var side = g.h === team ? ["h", "a"] : ["a", "h"], val = function (key) { var r = null; e[key].forEach(function (x) { if (x[0] === team) r = x; }); return r ? r[mi + 1] / 1000 : whatif.baseline[team][mi] / 1000; };
      var w = val(side[0]), l = val(side[1]), opp = g.h === team ? g.a : g.h;
      rows.push({ game_id: g.id, week: g.wk, opponent: tn(bundle, opp), site: g.neu ? "neutral" : (g.h === team ? "home" : "away"), if_win: w, if_lose: l, swing: w - l, if_win_text: pct(w), if_lose_text: pct(l), swing_text: delta(w - l) });
    });
    rows.sort(function (x, y) { return y.swing - x.swing; });
    var sc = []; if (runs) ["wins_out", "loses_out"].forEach(function (k) { if (runs[k]) sc.push({ scenario: k === "wins_out" ? "Wins out" : "Loses out", value: runs[k][G[0]][team], text: pct(runs[k][G[0]][team]) }); });
    return { header: header(N, asOf, bundle.model_label), model_label: bundle.model_label || "KickTip blend", footers: footers(bundle, null), goal: goal, goal_label: G[1], team: team, team_name: tn(bundle, team), baseline: b, baseline_text: pct(b), games: rows, scenarios: sc,
             notes: ["Games are listed by how much the result moves the chance of this outcome, largest swing first.", "Each number comes from rerunning the full model with that single game decided; other games play out as simulated."] };
  }
  function baselineAnswer(bundle, base, team, N, asOf) {
    return { header: header(N, asOf, bundle.model_label), model_label: bundle.model_label || "KickTip blend", footers: footers(bundle, null), team: team, team_name: tn(bundle, team), cells: METRICS.filter(function (m) { return applicable(bundle, team, m[0]); }).map(function (m) { return { key: m[0], label: m[1], value: base[m[0]][team], text: pct(base[m[0]][team]) }; }) };
  }
  var CLARIFY = {
    ambiguous_team: "Which team do you mean?", not_modeled: "That school is not in the Division I FBS field this model covers. Pick an FBS team.", no_team: "I did not find a team name. Try something like: What if Utah beats BYU and Texas Tech loses to Arizona?",
    unparsed: "I could not turn part of that into a game result. Try: Team A beats Team B, Team A loses to Team B, Team A wins out, or Team A wins 2 of 3.", unsupported: "I can run what-if scenarios for game results and conference, playoff or bye chances. National title chances are not part of this model.",
    empty: "Type a what-if question.", already_played: "That game has already been played.", no_remaining_game: "There is no remaining regular-season game between those teams.", multiple_games: "Those teams play more than once. Say which game (home or away).",
    margin: "KickTip simulates wins and losses, not scores or margins.", title_scenario: "Conference-title scenarios are not supported yet. Try asking what happens if a team wins out, or if one team beats another in a regular-season game.",
    too_many_items: "That is more than 8 game results in one question. Try up to 8.", site_conflict: "That does not match where the game is scheduled.", conflict: "Those results contradict each other. Remove one.", invalid_count: "That win count does not fit the number of games.", too_many_games: "That is more games than the team has left."
  };
  function clarifyAnswer(bundle, parsed, resolveInfo) {
    var reason = resolveInfo && resolveInfo.reason || parsed.clarify_reason, opts = [];
    if (reason === "ambiguous_team") (parsed.mentions || []).forEach(function (m) { if (m.team === null && !m.not_modeled) m.candidates.forEach(function (t) { opts.push({ alias: m.alias, team: t, name: tn(bundle, t) }); }); });
    var text = CLARIFY[reason] || CLARIFY.unparsed;
    if (reason === "already_played" && resolveInfo && resolveInfo.result) {   // c1: show the result we have
      var r = resolveInfo.result, hw = r.hs > r.as; text = tn(bundle, r.home) + " vs " + tn(bundle, r.away) + " has already been played: " + tn(bundle, hw ? r.home : r.away) + " won " + Math.max(r.hs, r.as) + "-" + Math.min(r.hs, r.as) + " (week " + r.week + "). Only games still to be played can be changed.";
    }
    if (reason === "multiple_games" && resolveInfo && resolveInfo.teams && resolveInfo.teams.length === 1) text = tn(bundle, resolveInfo.teams[0]) + " plays more than once on the next game day. Name the opponent, like " + tn(bundle, resolveInfo.teams[0]) + " beats Team B.";
    return { reason: reason, text: text, options: opts, plain_text: parsed && parsed.plain_text || null };
  }
  function refusalAnswer() { return { text: "KickTip does not give betting advice, picks or lines. It can run what-if simulations of game results and show how conference, playoff and bye chances change. Try: What if Utah beats BYU?" }; }
  /* Grammar: a full team name ("Utah Utes") takes a plural verb (lose, win, beat); short place names ("Utah") take the singular. */
  var PLURAL_END = { minutemen: 1, midshipmen: 1, illini: 1, irish: 1, bison: 1 };
  function isPlural(full) { var w = String(full || "").trim().split(/\s+/).pop().toLowerCase(); return !!PLURAL_END[w] || (/s$/.test(w) && !/ss$/.test(w)); }
  var API = { isPlural: isPlural, header: header, modelLine: modelLine, footers: footers, NOISE: NOISE, TIEBREAK: TIEBREAK, INPROG: INPROG, asOfLabel: asOfLabel, pct: pct, delta: delta, moe: moe, scenarioAnswer: scenarioAnswer, needAnswer: needAnswer, baselineAnswer: baselineAnswer, clarifyAnswer: clarifyAnswer, refusalAnswer: refusalAnswer, METRICS: METRICS, GOAL: GOAL };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.KTAnswer = API;
})(typeof self !== "undefined" ? self : this);
