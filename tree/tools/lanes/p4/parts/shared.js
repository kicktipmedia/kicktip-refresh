  /* ---- shared by team_path and path_compare (one source: lanes/p4/parts/shared.js, pasted into both modules by tools/compose_p4.js; a test asserts the two copies are identical) ---- */
  var KEY = { championship_game: "c", playoff: "p", bye: "b" };
  var MIN_SHARE = 0.01, HALF = 0.5, LOW = 0.05;
  function optionalData(names, optional) {   /* optional files that fail to load resolve to null and run() decides (same wrapper as team_needs) */
    Object.defineProperty(names, "map", { value: function (fn) {
      return Array.prototype.map.call(this, function (n) { var p; try { p = fn(n); } catch (e) { p = Promise.reject(e); } return optional.indexOf(n) >= 0 ? Promise.resolve(p).then(null, function () { return null; }) : p; });
    }, enumerable: false });
    return names;
  }
  var OPTIONAL = ["tb/ccg-alive", "tb/ccg-paths", "tb/path-by-stage", "tb/needs-by-record"];
  function gameInfo(B, id, i) {      /* a remaining game of team index i: opponent name, site, week */
    var g = null; B.games.forEach(function (x) { if (x.id === id) g = x; }); if (!g) return null;
    var k = g.h === i ? g.a : g.h; return { id: id, opp_name: k === B.fcs ? "FCS opponent" : B.teams[k].s, site: g.neu ? "neutral" : g.h === i ? "home" : "away", week: g.wk };
  }
  /* everything one team's path needs, for one goal. Returns null when the team is not in the model. Pure: only reads the loaded data. */
  function teamFacts(slug, goal, data, ctx) {
    var B = data["sim-bundle"], P = data["pred-teams"].teams, p = P[slug], i = ctx.idx[slug];
    if (i === undefined || !p || typeof p.p !== "number" || typeof p.b !== "number") return null;
    var confId = ctx.teamConf[slug], ind = confId === "ind", AL = data["tb/ccg-alive"], CP = data["tb/ccg-paths"], N = data["tb/needs-by-record"], S = data["tb/path-by-stage"];
    var f = { team: { slug: slug, name: B.teams[i].s }, conf: ind ? null : { id: confId, name: p.cn }, ind: ind, game_chance: !ind && typeof p.c === "number" ? p.c : null, field_chance: p.p, bye_chance: p.b, min_share: MIN_SHARE, half: HALF, low: LOW,
      now: goal === "championship_game" ? (!ind && typeof p.c === "number" ? p.c : null) : goal === "playoff" ? p.p : p.b,
      cg: null, chain: null, win_it: null, by_record: [], cross: null, low_rec: null, tables: false, games: [], left: 0, total: 0, seasons: null, chain_seasons: null };
    var left = B.games.filter(function (g) { return g.h === i || g.a === i; }), played = B.played.filter(function (g) { return g[0] === i || g[1] === i; }).length;
    f.left = left.length; f.total = played + left.length;
    /* conference stage: record-based path, from ccg-alive (race status) and ccg-paths (own-win totals) */
    var X = !ind && AL && AL.asof === B.as_of && AL.confs && AL.confs[confId];
    var row = X ? X.teams.filter(function (t) { return t.s === slug; })[0] : null;
    if (row) {
      var verified = X.verified === true && X.analyst === "verified", pe = CP && CP.asof === B.as_of && CP.rules && CP.rules[confId] === X.rules.hash && CP.confs && CP.confs[confId] && CP.confs[confId][slug];
      if (pe && pe.o.length !== row.left) pe = null;
      var cg = { rec: { w: row.w, l: row.l }, left: row.left, best: { w: row.best.w, l: row.best.l }, status: row.st === "out" ? "out" : row.st === "in" ? (row.sure === false ? "tie" : "in") : "unknown", verified: verified, analyst: X.analyst || "none", limits: (X.limits || []).slice(), remaining: X.remaining, paths: !!pe, tab: [], minw: null, losses_allowed: null, must: [], help: null, exh: false };
      if (pe) {
        for (var k = 0; k <= row.left; k++) cg.tab.push({ wins: k, code: pe.t.charAt(k), rec: { w: row.w + k, l: row.l + row.left - k } });
        cg.minw = pe.m; cg.losses_allowed = pe.m === null ? null : row.left - pe.m; cg.exh = pe.e === 1;
        cg.must = pe.k.map(function (id) { return gameInfo(B, id, i); }).filter(function (x) { return x; });
        if (pe.h) cg.help = pe.h.map(function (e) { var g = null; B.games.forEach(function (x) { if (x.id === e[0]) g = x; }); if (!g) return null; var w = ctx.idx[e[1]], l = g.h === w ? g.a : g.h; return { id: e[0], winner_name: B.teams[w].s, loser_name: B.teams[l].s, week: g.wk }; }).filter(function (x) { return x; });
        if (cg.help && !cg.help.length) cg.help = null;
      }
      f.cg = cg;
    }
    /* simulation stage: by final record (needs-by-record) and by conference-game state (path-by-stage), both stamped with the sim-bundle as-of */
    var nf = N && N.asof === B.as_of && N.byrec && N.games && N.byrec[slug] && N.games[slug];
    if (nf) {
      f.tables = true; f.seasons = N.whatif_seasons;
      var byg = {}; N.games[slug].forEach(function (g) { byg[g.id] = g; });
      var IDX = { championship_game: 0, playoff: 2, bye: 3 };
      left.forEach(function (g) {
        var e = byg[g.id]; if (!e) return; var o = g.h === i ? g.a : g.h, w = e.w[IDX[goal]], l = e.l[IDX[goal]];
        f.games.push({ id: g.id, opp_name: o === B.fcs ? "FCS opponent" : B.teams[o].s, site: g.neu ? "neutral" : g.h === i ? "home" : "away", week: g.wk, win: w / 1000, lose: l / 1000, pm: w - l });
      });
      f.games.sort(function (a, b) { return b.pm - a.pm || a.week - b.week || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); }); f.games.forEach(function (g) { delete g.pm; });
      var R = N.byrec[slug], arrP = R.p, arrB = R.b, recs = [];
      R.n.forEach(function (n, k) { if (n >= N.seasons * MIN_SHARE) recs.push({ wins: R.w0 + k, rec: { w: R.w0 + k, l: f.total - (R.w0 + k) }, field: arrP[k] / n, bye: arrB[k] / n, share: n / N.seasons }); });
      recs.sort(function (a, b) { return b.wins - a.wins; }); f.by_record = recs;
      var asc = recs.slice().sort(function (a, b) { return a.wins - b.wins; }), ck = goal === "bye" ? "bye" : "field";
      var hit = asc.filter(function (r) { return r[ck] >= HALF; })[0], lo = asc.filter(function (r) { return r[ck] >= LOW; })[0];
      f.cross = hit ? { rec: { w: hit.rec.w, l: hit.rec.l }, wins: hit.wins, losses: hit.rec.l } : null; f.low_rec = lo ? { rec: { w: lo.rec.w, l: lo.rec.l }, wins: lo.wins, losses: lo.rec.l } : null;
    }
    var sf = S && S.asof === B.as_of && S.t && S.t[slug];
    if (sf) {
      f.chain_seasons = S.seasons; f.chain = []; f.win_it = !ind && sf.n[1] + sf.n[2] >= S.seasons * MIN_SHARE ? sf.n[2] / (sf.n[1] + sf.n[2]) : null;
      [0, 1, 2].forEach(function (z) { if (sf.n[z] >= S.seasons * MIN_SHARE && (!ind || z === 0)) f.chain.push({ state: z, share: ind ? null : sf.n[z] / S.seasons, field: sf.p[z] / sf.n[z], bye: sf.b[z] / sf.n[z] }); });
    }
    return f;
  }
