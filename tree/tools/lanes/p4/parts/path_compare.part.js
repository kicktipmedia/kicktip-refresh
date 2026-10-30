  var COPY = {
    tCg: "{ta} and {tb}: path to the conference championship game", tField: "{ta} and {tb}: path to the 12-team playoff field", tBye: "{ta} and {tb}: path to a first-round bye",
    uCg: "how {ta} and {tb} compare on the path to the conference championship game", uField: "how {ta} and {tb} compare on the path to the 12-team playoff field", uBye: "how {ta} and {tb} compare on the path to a first-round bye",
    capCg: "Path to the conference championship game, side by side", capField: "Path to the 12-team playoff field, side by side", capBye: "Path to a first-round bye, side by side",
    colMeasure: "Measure", colTeam: "{ta}", colTeamB: "{tb}", cellA: "{a}", cellB: "{b}",
    rGameChance: "Estimated chance to reach the conference championship game", rFieldChance: "Estimated chance to make the playoff field", rByeChance: "Estimated chance to earn a first-round bye",
    rRecord: "Conference record", rLeft: "Conference games left", rStatus: "Race status", rMinWins: "Fewest conference wins that keep a path",
    rGamesLeft: "Regular-season games left", rUsual: "Final record that usually works", rLoss: "Most losses that usually work",
    cIn: "In the race", cTie: "In the race, only if a tiebreaker step goes its way", cOut: "Out of the race on our reading of the rules", cUnk: "Not worked out", cNoGame: "No conference game", cNW: "Not worked out", cNA: "Not available", cNone: "No final record reaches it",
    nHiGame: "{team} has the higher estimated chance to reach the conference championship game.", nHiField: "{team} has the higher estimated chance to make the playoff field.", nHiBye: "{team} has the higher estimated chance to earn a first-round bye.",
    nMeet: "{ta} and {tb} play each other in week {wk}, so only one of them can win that game.",
    nBasis: "A path means some set of results from the games left gets the team into the game. It says nothing about how likely that is, and it is not a chance estimate.",
    nNeutral: "Race status is our reading of the conference's published tiebreaker rules, not a chance estimate.",
    nUsual: "A final record usually works when the estimated chance at that record is at least {half}.", nDegraded: "Some by-record numbers are not available in this update.",
    lField: "See the full playoff field"
  };
  var GOAL_KEY = { championship_game: "Cg", playoff: "Field", bye: "Bye" };
  TB.register({
    id: "path_compare", set: 2, priority: "P2", live: false, kind: "lookup", card: "table", whichGoal: true,
    description: "Two teams side by side on the path to the conference championship game, the 12-team playoff field, or a first-round bye.",
    modes: ["home", "conference", "team"],
    params: { teams: { type: "teams", max: 2, required: true }, goal: { type: "enum", values: ["championship_game", "playoff", "bye"], required: true } },
    data: optionalData(["sim-bundle", "pred-teams", "tb/ccg-alive", "tb/ccg-paths", "tb/path-by-stage", "tb/needs-by-record"], OPTIONAL),
    examples: ["Compare Utah's and Arizona's path to a bye.", "Who has the easier path to the conference championship game, BYU or Utah?", "Compare Indiana and Ohio State on the path to the playoff field."],
    consts: [], gates: [], copy: COPY,

    run: function (params, data, ctx) {
      var B = data["sim-bundle"], t = params.teams, goal = params.goal;
      if (!t || t.length !== 2 || t[0] === t[1]) return { ok: false, reason: "bad_param" };
      var fs = t.map(function (s) { var f = teamFacts(s, goal, data, ctx); if (f) { f.goal = goal; f.focus = "overview"; } return f; });
      if (!fs[0] || !fs[1]) return { ok: false, reason: "not_modeled" };
      if (goal === "championship_game") { var bad = fs.some(function (f) { return !f.ind && !f.cg; }); if (bad) return { ok: false, reason: "not_modeled" }; }
      else if (fs.some(function (f) { return !f.tables && !f.chain; })) return { ok: false, reason: "not_modeled" };
      var a = ctx.idx[t[0]], b = ctx.idx[t[1]], meet = null;
      B.games.forEach(function (g) { if (!meet && ((g.h === a && g.a === b) || (g.h === b && g.a === a))) meet = { id: g.id, week: g.wk }; });
      return { ok: true, tool: "path_compare", params: params, asof: { label: C.asofLabel(B.as_of), files: [{ file: "sim-bundle", label: C.asofLabel(B.as_of) }] }, facts: { goal: goal, teams: fs, meet: meet, half: HALF } };
    },

    render: function (res) {
      var f = res.facts, g = f.goal, gk = GOAL_KEY[g], V = {}, rows = [], notes = [], links = [], T0 = f.teams[0], T1 = f.teams[1];
      V.ta = { t: "text", v: T0.team.name, src: "facts.teams.0.team.name" }; V.tb = { t: "text", v: T1.team.name, src: "facts.teams.1.team.name" };
      function P(v, s) { return { t: "pct", v: v, src: s }; } function I(v, s) { return { t: "int", v: v, src: s }; } function RC(r, s) { return { t: "rec", v: [r.w, r.l], src: s }; }
      /* one row: label template, then per team a [template, slot] pair (static status cells carry no slot) */
      function row(label, pa, pb, src) { var vals = {}; if (pa[1]) vals.a = pa[1]; if (pb[1]) vals.b = pb[1]; rows.push({ cells: [label, pa[0], pb[0]], vals: vals, src: src }); }
      function pctCell(v, s) { return v === null ? [COPY.cNoGame] : [COPY.cellA, P(v, s)]; }
      function pctCellB(v, s) { return v === null ? [COPY.cNoGame] : [COPY.cellB, P(v, s)]; }
      var idx = [0, 1];
      if (g === "championship_game") {
        row(COPY.rGameChance, pctCell(T0.game_chance, "facts.teams.0.game_chance"), pctCellB(T1.game_chance, "facts.teams.1.game_chance"), "facts.teams.game_chance");
        function cgCell(t, i, side, kind) {
          var cg = t.cg, p = "facts.teams." + i + ".cg.", c = side === "a" ? COPY.cellA : COPY.cellB;
          if (t.ind) return [COPY.cNoGame];
          if (kind === "rec") return [c, RC(cg.rec, p + "rec")];
          if (kind === "left") return [c, I(cg.left, p + "left")];
          if (kind === "status") return [cg.status === "in" ? COPY.cIn : cg.status === "tie" ? COPY.cTie : cg.status === "out" ? COPY.cOut : COPY.cUnk];
          return cg.paths && cg.minw !== null ? [c, I(cg.minw, p + "minw")] : [COPY.cNW];
        }
        [["rec", COPY.rRecord], ["left", COPY.rLeft], ["status", COPY.rStatus], ["min", COPY.rMinWins]].forEach(function (k) { row(k[1], cgCell(T0, 0, "a", k[0]), cgCell(T1, 1, "b", k[0]), "facts.teams." + k[0]); });
        notes.push(COPY.nBasis, COPY.nNeutral);
        var hi = T0.game_chance !== null && T1.game_chance !== null && C.fmt.pct(T0.game_chance) !== C.fmt.pct(T1.game_chance) ? (T0.game_chance > T1.game_chance ? 0 : 1) : null;
        if (hi !== null) { V.team = { t: "text", v: f.teams[hi].team.name, src: "facts.teams." + hi + ".team.name" }; notes.push(COPY.nHiGame); }
      } else {
        var pk = g === "playoff" ? "field_chance" : "bye_chance";
        row(g === "playoff" ? COPY.rFieldChance : COPY.rByeChance, [COPY.cellA, P(T0[pk], "facts.teams.0." + pk)], [COPY.cellB, P(T1[pk], "facts.teams.1." + pk)], "facts.teams." + pk);
        row(COPY.rGameChance, pctCell(T0.game_chance, "facts.teams.0.game_chance"), pctCellB(T1.game_chance, "facts.teams.1.game_chance"), "facts.teams.game_chance");
        row(COPY.rGamesLeft, [COPY.cellA, I(T0.left, "facts.teams.0.left")], [COPY.cellB, I(T1.left, "facts.teams.1.left")], "facts.teams.left");
        var us = function (t, i, side) { var c = side === "a" ? COPY.cellA : COPY.cellB; return t.tables ? (t.cross ? [c, RC(t.cross.rec, "facts.teams." + i + ".cross.rec")] : [COPY.cNone]) : [COPY.cNA]; };
        var ls = function (t, i, side) { var c = side === "a" ? COPY.cellA : COPY.cellB; return t.tables ? (t.cross ? [c, I(t.cross.losses, "facts.teams." + i + ".cross.losses")] : [COPY.cNone]) : [COPY.cNA]; };
        row(COPY.rUsual, us(T0, 0, "a"), us(T1, 1, "b"), "facts.teams.cross"); row(COPY.rLoss, ls(T0, 0, "a"), ls(T1, 1, "b"), "facts.teams.cross.losses");
        V.half = P(f.half, "facts.half"); notes.push(COPY.nUsual);
        if (!T0.tables || !T1.tables) notes.push(COPY.nDegraded);
        var h2 = C.fmt.pct(T0[pk]) !== C.fmt.pct(T1[pk]) ? (T0[pk] > T1[pk] ? 0 : 1) : null;
        if (h2 !== null) { V.team = { t: "text", v: f.teams[h2].team.name, src: "facts.teams." + h2 + ".team.name" }; notes.push(g === "playoff" ? COPY.nHiField : COPY.nHiBye); }
        links.push({ label: COPY.lField, href: "/#field" });
      }
      if (f.meet) { V.wk = { t: "int", v: f.meet.week, src: "facts.meet.week" }; notes.push(COPY.nMeet); }
      return { type: "table", title: COPY["t" + gk], understood: COPY["u" + gk], vals: V, caption: COPY["cap" + gk], cols: [COPY.colMeasure, COPY.colTeam, COPY.colTeamB], rows: rows, notes: notes, links: links };
    }
  });
