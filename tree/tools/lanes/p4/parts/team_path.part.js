  var GOAL_KEY = { championship_game: "Cg", playoff: "Field", bye: "Bye" };
  var COPY = {
    tCg: "{team}: path to the conference championship game", tField: "{team}: path to the 12-team playoff field", tBye: "{team}: path to a first-round bye",
    uCg: "{team}'s path to the conference championship game", uCgMin: "the fewest wins {team} needs to keep a path to the conference championship game",
    uCgLoss: "how many games {team} can lose and still keep a path to the conference championship game", uCgHelp: "which other results help {team} reach the conference championship game",
    uCgKey: "which games {team} cannot lose on its path to the conference championship game",
    uField: "{team}'s path to the 12-team playoff field", uFieldMin: "the finishing record that usually works for {team} to make the 12-team playoff field",
    uFieldLoss: "how many games {team} can lose and still usually make the 12-team playoff field", uFieldHelp: "{team}'s path to the 12-team playoff field", uFieldKey: "which games matter most for {team}'s path to the 12-team playoff field",
    uBye: "{team}'s path to a first-round bye", uByeMin: "the finishing record that usually works for {team} to earn a first-round bye",
    uByeLoss: "how many games {team} can lose and still usually earn a first-round bye", uByeHelp: "{team}'s path to a first-round bye", uByeKey: "which games matter most for {team}'s path to a first-round bye",
    /* conference stage */
    hStand: "Where {team} stands", hTab: "What each win total means", hMust: "Games {team} cannot lose and keep a path", hWo: "If {team} wins out",
    sIn: "{team} is in the race for the conference championship game.", sTie: "{team} is in the race, but only if a tiebreaker step KickTip cannot see goes its way.",
    sOut: "{team} is out of the race on our reading of the rules.", sUnk: "{team}'s race status is not worked out yet.",
    rMany: "Conference record {rec} with {left} games left. Best possible finish {best}.", rOne: "Conference record {rec} with one game left. Best possible finish {best}.", rNone: "Conference record {rec} with no games left. Best possible finish {best}.",
    tA: "Win {k} of {left} ({rec}): reaches the game whatever the other results are.", tH: "Win {k} of {left} ({rec}): reaches the game only if other results help.",
    tT: "Win {k} of {left} ({rec}): reaches the game only if a tiebreaker step KickTip cannot see goes its way.", tN: "Win {k} of {left} ({rec}): no path on our reading of the rules.",
    tP: "Win {k} of {left} ({rec}): some sets of results get it in, but whether it needs help is not worked out.", tU: "Win {k} of {left} ({rec}): not worked out. The search was too large to finish.",
    eTab: "No conference games are left.",
    sMinZero: "A path remains even if {team} loses all {left} of its remaining conference games.", sMin: "Winning fewer than {k} of its {left} remaining conference games leaves no path on our reading of the rules.",
    sMinOne: "A path needs a win in {team}'s one remaining conference game.", sMinZeroOne: "A path remains whether {team} wins or loses its one remaining conference game.",
    sLoss: "{team} can lose {n} of its {left} remaining conference games and still keep a path.", sLossNone: "{team} cannot afford to lose any of its {left} remaining conference games.",
    sNoMin: "The fewest wins that keep a path is not worked out yet: some win totals above are marked not worked out.", sNoPaths: "Win-total detail is not available in this update. Race status comes from the conference's published tiebreaker rules.",
    mHome: "{opp} (home, week {wk})", mAway: "At {opp} (week {wk})", mNeutral: "{opp} (neutral site, week {wk})", eMust: "No remaining game is proven to be one it cannot lose.",
    wA: "If {team} wins out, it reaches the game whatever the other results are.", wT: "If {team} wins out, it still needs a tiebreaker step KickTip cannot see to go its way.",
    wN: "Even if {team} wins out, there is no path on our reading of the rules.", wNeeds: "If {team} wins out, it still needs other results to go its way.",
    wHelp: "If {team} wins out, it gets in with these other results, however the remaining games go:", wNone: "Which other results would get {team} in is not worked out yet.", wOne: "{winner} beats {loser} (week {wk})",
    /* independents and simulation stages */
    hInd: "No conference game", pInd: "{team} plays as an independent, so it has no conference championship game.",
    hNow: "Right now", nowField: "Estimated chance to make the playoff field: {pct}", nowBye: "Estimated chance to earn a first-round bye: {pct}", nowGame: "Estimated chance to reach the conference championship game: {pct}",
    lMany: "{left} regular-season games are left.", lOne: "One regular-season game is left.", lNone: "No regular-season games are left.",
    hRecField: "Chance to make the playoff field, by final record", hRecBye: "Chance to earn a first-round bye, by final record", itRec: "{rec}: {pct}, in {share} of simulated seasons", eRec: "No final record has enough simulated seasons to show.",
    hUsual: "The finishing record that usually works", uUsual: "A final record of {rec} or better usually works: the estimated chance is at least {half} there.",
    uLow: "A final record of {rec} or better gives an estimated chance of at least {low}.", uLoss: "Most losses that usually work: {n}.", uNone: "No simulated final record reaches an estimated chance of {half}.",
    hStage: "Stage by stage", sGame: "Reach the conference championship game: {pct}", sWinIt: "Win the game once there: {pct}",
    sMiss: "If {team} misses the game ({share} of simulated seasons): {field} to make the playoff field, {bye} to earn a first-round bye.",
    sLose: "If {team} plays and loses ({share} of simulated seasons): {field} to make the playoff field, {bye} to earn a first-round bye.",
    sWinS: "If {team} plays and wins ({share} of simulated seasons): {field} to make the playoff field, {bye} to earn a first-round bye.",
    sNoGame: "{team} has no conference game: {field} to make the playoff field, {bye} to earn a first-round bye.",
    hGames: "Game by game, biggest change first", itHome: "{opp} (home, week {wk}): {win} if {team} wins, {lose} if it loses", itAway: "At {opp} (week {wk}): {win} if {team} wins, {lose} if it loses", itNeutral: "{opp} (neutral site, week {wk}): {win} if {team} wins, {lose} if it loses", eGames: "No games left.",
    /* notes and links */
    nBasis: "A path means some set of results from the games left gets the team into the game. It says nothing about how likely that is, and it is not a chance estimate.",
    nNeutral: "Race status is our reading of the conference's published tiebreaker rules, not a chance estimate.", nUnchecked: "A person has not yet checked this conference's rules text against its source.",
    nPartial: "A person who compared that reading with the published text found steps KickTip does not yet match, so some calls could change.", nVerified: "This conference's tiebreaker text has been checked by a person against its source.",
    nCount: "Win totals count conference games only.", nCap: "Win totals marked not worked out are ones whose search was too large to finish. KickTip does not guess them.",
    lRanking: "Some tiebreakers use an outside ranking. Where one would decide, a team counts as in the race.", lDraw: "Some tiebreakers end in a draw. Where one would decide, a team counts as in the race.",
    lImmunity: "One tiebreaker step depends on a late-season ranking and the final game. A team counts as in the race if it could pass that step.", lReadings: "The published rules can be read two ways here. A team counts as in the race if either reading puts it in.",
    lUnequal: "Teams here play different numbers of conference games, and KickTip follows the conference's rule for that case.", lDivisions: "The two division winners meet, so each team is judged within its own division.",
    lOld: "The newest tiebreaker text KickTip found is for an earlier season or may be stale.",
    nGames: "Each game shows the estimated chance if {team} wins it and if it loses it, from {seasons} simulated seasons. Small moves are within the noise.",
    nRec: "Only final records that happen in at least {minshare} of simulated seasons are shown. Losses count every game, including any against an FCS opponent.",
    nStage: "Stage-by-stage chances come from {seasons} simulated seasons. A state that happens in under {minshare} of them is not shown.", nDegraded: "The by-record and stage-by-stage tables are not available in this update.",
    lField: "See the full playoff field"
  };
  var LIMIT_NOTE = { ranking_step: "lRanking", draw_step: "lDraw", immunity_step: "lImmunity", two_readings: "lReadings", unequal_schedules: "lUnequal", divisions: "lDivisions", rules_text_not_2026: "lOld" };
  var FOCUS = ["overview", "min_record", "losses_allowed", "help", "key_games"], FKEY = { overview: "", min_record: "Min", losses_allowed: "Loss", help: "Help", key_games: "Key" };

  TB.register({
    id: "team_path", set: 2, priority: "P1", live: false, kind: "lookup", card: "list", whichGoal: true,
    description: "A team's path to the conference championship game, the 12-team playoff field, or a first-round bye: win totals, results that help, and chances by stage.",
    modes: ["home", "conference", "team"],
    params: { team: { type: "team", required: true }, goal: { type: "enum", values: ["championship_game", "playoff", "bye"], required: true }, focus: { type: "enum", values: FOCUS, default: "overview" } },
    data: optionalData(["sim-bundle", "pred-teams", "tb/ccg-alive", "tb/ccg-paths", "tb/path-by-stage", "tb/needs-by-record"], OPTIONAL),
    examples: ["What is Utah's path to the conference championship game?", "How can BYU reach the conference championship game?", "What is Indiana's path to a first-round bye?", "How can Ohio State get into the playoff field?", "How many games can Utah lose and still reach the conference championship game?"],
    consts: [], gates: [], copy: COPY,

    run: function (params, data, ctx) {
      var B = data["sim-bundle"], goal = params.goal, team = params.team, f = teamFacts(team, goal, data, ctx);
      if (!f) return { ok: false, reason: "not_modeled" };
      if (goal === "championship_game" && !f.ind && !f.cg) return { ok: false, reason: "not_modeled" };   /* stale or missing race file: the honest "Not covered here" card, never invented */
      if (goal !== "championship_game" && !f.tables && !f.chain) return { ok: false, reason: "not_modeled" };
      f.goal = goal; f.focus = params.focus || "overview";
      return { ok: true, tool: "team_path", params: params, asof: { label: C.asofLabel(B.as_of), files: [{ file: "sim-bundle", label: C.asofLabel(B.as_of) }] }, facts: f };
    },

    render: function (res) {
      var f = res.facts, g = f.goal, gk = GOAL_KEY[g], fk = FKEY[f.focus], V = {}, groups = [], notes = [], links = [], T = "facts.team.name";
      function tm() { return { t: "text", v: f.team.name, src: T }; }
      V.team = tm();
      function N(v, src) { return { t: "pct", v: v, src: src }; }
      function I(v, src) { return { t: "int", v: v, src: src }; }
      function R(w, l, src) { return { t: "rec", v: [w, l], src: src }; }
      var understood = COPY["u" + gk + (fk || "")] || COPY["u" + gk];
      if (g === "championship_game" && f.ind) {
        groups.push({ heading: COPY.hInd, items: [{ tpl: COPY.pInd, vals: { team: tm() }, src: "facts.ind" }], empty: COPY.eGames });
        nowGroup(groups, f, "playoff"); nowGroup(groups, f, "bye", true);
        links.push({ label: COPY.lField, href: "/#field" });
        return { type: "list", title: COPY.tCg, understood: understood, vals: V, groups: groups, notes: notes, links: links };
      }
      if (g === "championship_game") conferenceCard(f, fk, groups, notes, V, tm);
      else fieldCard(f, g, fk, groups, notes, V, tm, links);
      return { type: "list", title: COPY["t" + gk], understood: understood, vals: V, groups: groups, notes: notes, links: links };
    }
  });
  function nowGroup(groups, f, goal, append) {
    var items = [{ tpl: goal === "playoff" ? COPY.nowField : COPY.nowBye, vals: { pct: { t: "pct", v: goal === "playoff" ? f.field_chance : f.bye_chance, src: goal === "playoff" ? "facts.field_chance" : "facts.bye_chance" } }, src: "facts." + (goal === "playoff" ? "field_chance" : "bye_chance") }];
    if (append) groups[groups.length - 1].items = groups[groups.length - 1].items.concat(items); else groups.push({ heading: COPY.hNow, items: items, empty: COPY.eGames });
  }
  function conferenceCard(f, fk, groups, notes, V, tm) {
    var cg = f.cg, want = { "": ["stand", "sum", "must", "tab", "wo"], Min: ["stand", "sum", "tab"], Loss: ["stand", "sum", "must"], Help: ["stand", "wo"], Key: ["stand", "must"] }[fk];
    if (cg.status === "out") want = ["stand"];
    function has(x) { return want.indexOf(x) >= 0; }
    var L = cg.left, stand = null;
    if (has("stand")) {
      var st = cg.status === "in" ? COPY.sIn : cg.status === "tie" ? COPY.sTie : cg.status === "out" ? COPY.sOut : COPY.sUnk, rtpl = L === 0 ? COPY.rNone : L === 1 ? COPY.rOne : COPY.rMany;
      V.rec = { t: "rec", v: [cg.rec.w, cg.rec.l], src: "facts.cg.rec" }; V.best = { t: "rec", v: [cg.best.w, cg.best.l], src: "facts.cg.best" }; V.left = { t: "int", v: L, src: "facts.cg.left" };
      stand = { heading: COPY.hStand, items: [{ tpl: st, vals: { team: tm() }, src: "facts.cg.status" }, { tpl: rtpl, vals: {}, src: "facts.cg.rec" }], empty: COPY.eGames }; groups.push(stand);
    }
    if (!cg.paths) { notes.push(COPY.sNoPaths); }
    else {
      if (has("sum") && L > 0) {
        var k = cg.minw, LV = { t: "int", v: L, src: "facts.cg.left" };
        if (k === null) stand.items.push({ tpl: COPY.sNoMin, vals: {}, src: "facts.cg.minw" });
        else if (L === 1) stand.items.push({ tpl: k === 0 ? COPY.sMinZeroOne : COPY.sMinOne, vals: { team: tm() }, src: "facts.cg.minw" });
        else if (k === 0) stand.items.push({ tpl: COPY.sMinZero, vals: { team: tm(), left: LV }, src: "facts.cg.minw" });
        else {
          stand.items.push({ tpl: COPY.sMin, vals: { k: { t: "int", v: k, src: "facts.cg.minw" }, left: LV }, src: "facts.cg.minw" });
          stand.items.push(k === L ? { tpl: COPY.sLossNone, vals: { team: tm(), left: LV }, src: "facts.cg.losses_allowed" } : { tpl: COPY.sLoss, vals: { team: tm(), n: { t: "int", v: cg.losses_allowed, src: "facts.cg.losses_allowed" }, left: LV }, src: "facts.cg.losses_allowed" });
        }
      }
      if (has("must")) groups.push({ heading: COPY.hMust, items: cg.must.map(function (m, i) { var b = "facts.cg.must." + i + "."; return { tpl: m.site === "home" ? COPY.mHome : m.site === "away" ? COPY.mAway : COPY.mNeutral, vals: { opp: { t: "text", v: m.opp_name, src: b + "opp_name" }, wk: { t: "int", v: m.week, src: b + "week" } }, src: "facts.cg.must." + i }; }), empty: COPY.eMust });
      if (has("tab")) groups.push({ heading: COPY.hTab, items: cg.tab.slice().reverse().map(function (t, i0) {
        var i = cg.tab.length - 1 - i0, b = "facts.cg.tab." + i + ".";
        return { tpl: COPY["t" + t.code], vals: { k: { t: "int", v: t.wins, src: b + "wins" }, left: { t: "int", v: L, src: "facts.cg.left" }, rec: { t: "rec", v: [t.rec.w, t.rec.l], src: b + "rec" } }, src: "facts.cg.tab." + i };
      }), empty: COPY.eTab });
      if (has("wo") && L > 0) {
        var c = cg.tab[L].code, wi = [];
        if (c === "A") wi.push({ tpl: COPY.wA, vals: { team: tm() }, src: "facts.cg.tab." + L });
        else if (c === "T") wi.push({ tpl: COPY.wT, vals: { team: tm() }, src: "facts.cg.tab." + L });
        else if (c === "N") wi.push({ tpl: COPY.wN, vals: { team: tm() }, src: "facts.cg.tab." + L });
        else if (c === "H" && cg.help) { wi.push({ tpl: COPY.wHelp, vals: { team: tm() }, src: "facts.cg.help" }); cg.help.forEach(function (h, i) { var b = "facts.cg.help." + i + "."; wi.push({ tpl: COPY.wOne, vals: { winner: { t: "text", v: h.winner_name, src: b + "winner_name" }, loser: { t: "text", v: h.loser_name, src: b + "loser_name" }, wk: { t: "int", v: h.week, src: b + "week" } }, src: "facts.cg.help." + i }); }); }
        else if (c === "H") wi.push({ tpl: COPY.wNeeds, vals: { team: tm() }, src: "facts.cg.tab." + L });
        else wi.push({ tpl: COPY.wNone, vals: { team: tm() }, src: "facts.cg.tab." + L });
        groups.push({ heading: COPY.hWo, items: wi, empty: COPY.eGames });
      }
    }
    notes.push(COPY.nBasis);
    if (cg.verified) notes.push(COPY.nVerified); else { notes.push(COPY.nNeutral); if (cg.analyst === "none") notes.push(COPY.nUnchecked); else if (cg.analyst !== "verified") notes.push(COPY.nPartial); }
    if (cg.paths) { notes.push(COPY.nCount); if (!cg.exh) notes.push(COPY.nCap); }
    cg.limits.forEach(function (l) { if (LIMIT_NOTE[l]) notes.push(COPY[LIMIT_NOTE[l]]); });
  }
  function fieldCard(f, g, fk, groups, notes, V, tm, links) {
    var field = g === "playoff", pk = field ? "field" : "bye", cap = field ? "Field" : "Bye";
    var now = [{ tpl: field ? COPY.nowField : COPY.nowBye, vals: { pct: { t: "pct", v: field ? f.field_chance : f.bye_chance, src: "facts." + (field ? "field_chance" : "bye_chance") } }, src: "facts.now" }];
    now.push({ tpl: f.left === 0 ? COPY.lNone : f.left === 1 ? COPY.lOne : COPY.lMany, vals: { left: { t: "int", v: f.left, src: "facts.left" } }, src: "facts.left" });
    var want = { "": ["now", "usual", "rec", "stage"], Min: ["now", "usual", "rec"], Loss: ["now", "usual"], Help: ["now", "usual", "rec", "stage"], Key: ["now", "games"] }[fk];
    function has(x) { return want.indexOf(x) >= 0; }
    groups.push({ heading: COPY.hNow, items: now, empty: COPY.eGames });
    var usedMin = false, usedSeasons = false;
    if (has("usual") && f.tables) {
      var items = [];
      if (f.cross) {
        V.cross = { t: "rec", v: [f.cross.rec.w, f.cross.rec.l], src: "facts.cross.rec" }; V.half = { t: "pct", v: f.half, src: "facts.half" };
        items.push({ tpl: COPY.uUsual, vals: { rec: V.cross, half: V.half }, src: "facts.cross" });
        if (fk === "Loss" || fk === "Min" || fk === "") items.push({ tpl: COPY.uLoss, vals: { n: { t: "int", v: f.cross.losses, src: "facts.cross.losses" } }, src: "facts.cross.losses" });
      } else { V.half = { t: "pct", v: f.half, src: "facts.half" }; items.push({ tpl: COPY.uNone, vals: { half: V.half }, src: "facts.cross" }); }
      if (f.low_rec && (fk === "Min" || fk === "")) items.push({ tpl: COPY.uLow, vals: { rec: { t: "rec", v: [f.low_rec.rec.w, f.low_rec.rec.l], src: "facts.low_rec.rec" }, low: { t: "pct", v: f.low, src: "facts.low" } }, src: "facts.low_rec" });
      groups.push({ heading: COPY.hUsual, items: items, empty: COPY.eRec });
    }
    if (has("rec") && f.tables) {
      groups.push({ heading: field ? COPY.hRecField : COPY.hRecBye, items: f.by_record.map(function (r, k) { var b = "facts.by_record." + k + "."; return { tpl: COPY.itRec, vals: { rec: { t: "rec", v: [r.rec.w, r.rec.l], src: b + "rec" }, pct: { t: "pct", v: r[pk], src: b + pk }, share: { t: "pct", v: r.share, src: b + "share" } }, src: "facts.by_record." + k }; }), empty: COPY.eRec });
      V.minshare = { t: "pct", v: f.min_share, src: "facts.min_share" }; notes.push(COPY.nRec); usedMin = true;
    }
    if (has("stage") && f.chain && !f.ind) {      /* an independent has no stage chain: its chances are the "Right now" line */
      var it = [];
      if (f.game_chance !== null) it.push({ tpl: COPY.sGame, vals: { pct: { t: "pct", v: f.game_chance, src: "facts.game_chance" } }, src: "facts.game_chance" });
      if (f.win_it !== null) it.push({ tpl: COPY.sWinIt, vals: { pct: { t: "pct", v: f.win_it, src: "facts.win_it" } }, src: "facts.win_it" });
      f.chain.forEach(function (c, i) {
        var b = "facts.chain." + i + ".", vals = { team: tm(), field: { t: "pct", v: c.field, src: b + "field" }, bye: { t: "pct", v: c.bye, src: b + "bye" } };
        if (c.share !== null) vals.share = { t: "pct", v: c.share, src: b + "share" };
        it.push({ tpl: f.ind ? COPY.sNoGame : c.state === 0 ? COPY.sMiss : c.state === 1 ? COPY.sLose : COPY.sWinS, vals: vals, src: "facts.chain." + i });
      });
      groups.push({ heading: COPY.hStage, items: it, empty: COPY.eGames });
      V.seasons = { t: "int", v: f.chain_seasons, src: "facts.chain_seasons" }; usedSeasons = true; if (!usedMin) V.minshare = { t: "pct", v: f.min_share, src: "facts.min_share" }; usedMin = true; notes.push(COPY.nStage);
    }
    if (has("games") && f.tables) {
      groups.push({ heading: COPY.hGames, items: f.games.map(function (r, k) { var b = "facts.games." + k + "."; return { tpl: r.site === "home" ? COPY.itHome : r.site === "away" ? COPY.itAway : COPY.itNeutral, vals: { opp: { t: "text", v: r.opp_name, src: b + "opp_name" }, wk: { t: "int", v: r.week, src: b + "week" }, team: tm(), win: { t: "pct", v: r.win, src: b + "win" }, lose: { t: "pct", v: r.lose, src: b + "lose" } }, src: "facts.games." + k }; }), empty: COPY.eGames });
      if (!usedSeasons) V.seasons = { t: "int", v: f.seasons, src: "facts.seasons" }; notes.push(COPY.nGames);
    }
    if (!f.tables || (!f.chain && !f.ind)) notes.push(COPY.nDegraded);
    links.push({ label: COPY.lField, href: "/#field" });
  }
