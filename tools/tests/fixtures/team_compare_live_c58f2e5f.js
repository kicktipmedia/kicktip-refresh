/* Tool: team_compare (Set 2b, wave 1). Two teams' measures side by side. No verdict: every row is a number from the data files, in the same order for both teams.
 * Data: data/pred-teams.json (chances), data/sim-bundle.json (records, ratings, games left, this season's meeting), data/polls.json (AP and Coaches ranks), data/ccg-sim.json (conference record).
 * The schedule rows use schedule_strength's definition: scheduleTable below is copied word for word from schedule_strength.js (a test proves the text and the results equal on every team).
 * The meeting date rule is copied from head_to_head / team_schedule (04:00Z and 05:00Z kickoffs are ESPN's "time not set" placeholder: UTC calendar date plus "time TBD", exception game 401864537; every other kickoff is its Mountain Time day). */
(function (root) {
  "use strict";
  var TB = root.KTTB || (typeof require !== "undefined" ? require("./registry.js") : null), C = TB.core;

  var COPY = {
    title: "{a} and {b}",
    uAll: "{a} and {b} side by side",
    uChances: "the chances of {a} and {b} side by side",
    uRecord: "the records of {a} and {b} side by side",
    uRank: "the ranks of {a} and {b} side by side",
    uSched: "the games left for {a} and {b} side by side",
    caption: "{a} and {b}, measure by measure",
    colMeasure: "Measure",
    colA: "{a}",
    colB: "{b}",
    lRecord: "Record",
    lConfRecord: "Conference record",
    lKtRank: "KickTip rank (computer rating, not a poll)",
    lAp: "AP rank",
    lCoaches: "Coaches rank",
    lGame: "Chance to reach the conference championship game",
    lTitle: "Chance to win the conference",
    lPlayoff: "Chance to make the 12-team playoff field",
    lBye: "Chance of a first-round bye",
    lLeft: "Games left",
    lOpp: "Remaining opponents' average KickTip rating",
    cX: "{x}",
    cY: "{y}",
    cNa: "Not applicable (independent)",
    cNotRanked: "Not ranked",
    cNone: "None",
    nVerdict: "Each row is a measure, not a verdict.",
    nRating: "KickTip rank is a computer rating, not a poll and not the committee's order.",
    nPolls: "AP and Coaches ranks are from the polls released {pollasof}.",
    nSched: "The average counts FBS opponents only.",
    nIndepA: "{a} is an independent, so it has no conference record or conference chances.",
    nIndepB: "{b} is an independent, so it has no conference record or conference chances.",
    mResult: "This season's meeting: {winner} beat {loser} {score}, week {wk}",
    mNeutral: "This season's meeting: {a} and {b} play {when} (neutral site)",
    mHome: "This season's meeting: {a} and {b} play {when} (at {host})",
    mNone: "No meeting this season.",
    nDates: "Dates are Mountain Time.",
    nTba: "Games marked time TBD do not have a kickoff time yet."
  };

  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function isMDT(ms) {   /* America/Denver: daylight time from the 2nd Sunday of March 2:00 (09:00Z) to the 1st Sunday of November 2:00 (08:00Z) */
    var y = new Date(ms).getUTCFullYear(), d1 = new Date(Date.UTC(y, 2, 1)).getUTCDay(), second = 1 + ((7 - d1) % 7) + 7, n1 = new Date(Date.UTC(y, 10, 1)).getUTCDay(), first = 1 + ((7 - n1) % 7);
    return ms >= Date.UTC(y, 2, second, 9, 0) && ms < Date.UTC(y, 10, first, 8, 0);
  }
  function when(iso, id) {   /* -> {label:"Sat Oct 31", tba:bool}  (identical to team_schedule's when) */
    var m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(iso || ""); if (!m) return { label: String(iso || ""), tba: true };
    var y = +m[1], mo = +m[2] - 1, d = +m[3], hh = +m[4], mm = +m[5], ph = (hh === 4 || hh === 5) && mm === 0 && id !== "401864537", ms = Date.UTC(y, mo, d, hh, mm);
    var t = ph ? new Date(ms) : new Date(ms + (isMDT(ms) ? -6 : -7) * 3600000);
    return { label: DOW[t.getUTCDay()] + " " + MON[t.getUTCMonth()] + " " + t.getUTCDate(), tba: ph };
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
  var MOD = TB.register({
    id: "team_compare",
    set: 2, priority: "P1", live: false,
    kind: "model", card: "table",                        /* the footer is set per card in render: model when a chance row shows, lookup otherwise */
    description: "Two teams side by side: record, conference record, KickTip rank, AP and Coaches ranks, chances, games left and this season's meeting. No verdict.",
    modes: ["home", "conference", "team"],
    params: {
      teams: { type: "teams", max: 2, required: true },
      aspect: { type: "enum", values: ["all", "chances", "record", "rank", "schedule"], default: "all" }
    },
    data: ["pred-teams", "sim-bundle", "polls", "ccg-sim"],
    examples: ["Utah vs BYU", "Compare Arizona and BYU", "Indiana vs Ohio State"],
    consts: ["12"],
    gates: [],
    copy: COPY,

    run: function (params, data, ctx) {
      var P = data["pred-teams"], B = data["sim-bundle"], POL = data["polls"] && data["polls"].polls, S = data["ccg-sim"], teams = params.teams || [], aspect = params.aspect || "all";
      if (teams.length !== 2 || teams[0] === teams[1]) return { ok: false, reason: "bad_param" };
      if (!P || !P.teams || !B || !B.as_of || !S || S.asof !== B.as_of || String(P.model_asof).indexOf(C.asofLabel(B.as_of)) < 0) return { ok: false, reason: "no_data" };   /* every file must carry the same as-of as the simulation bundle, else the two columns would mix dates */
      var ids = teams.map(function (t) { return ctx.idx[t]; });
      if (ids.some(function (i) { return i === undefined; }) || teams.some(function (t) { return !P.teams[t]; })) return { ok: false, reason: "not_modeled" };
      var st = scheduleTable(B), kr = ktRanks(B), nFbs = 0;
      kr.forEach(function (x) { if (x !== null) nFbs++; });
      function pollRank(k, slug) { var r = POL && POL[k] && POL[k].ranks.filter(function (x) { return x[1] === slug; })[0]; return r ? r[0] : null; }
      function confRecord(slug, conf) {
        var c = S && S.confs && S.confs[conf]; if (!c) return null;
        var rec = { w: 0, l: 0 }, ti = c.teams.filter(function (t) { return t.slug === slug; })[0]; if (!ti) return null;
        c.games.forEach(function (g) { if (g.w === null || g.w === undefined || (g.h !== ti.i && g.a !== ti.i)) return; var won = (g.w === 1) === (g.h === ti.i); if (won) rec.w++; else rec.l++; });
        return rec;
      }
      var out = teams.map(function (slug, k) {
        var i = ids[k], w = 0, l = 0, left = 0, p = P.teams[slug], s = st[i];
        B.played.forEach(function (g) { if (g[0] === i) { if (g[2] > g[3]) w++; else l++; } else if (g[1] === i) { if (g[3] > g[2]) w++; else l++; } });
        B.games.forEach(function (g) { if (g.h === i || g.a === i) left++; });
        var indep = p.c === null || p.w === null;
        return {
          slug: slug, name: slug === "miami" && teams.indexOf("miami-oh") >= 0 ? "Miami (FL)" : B.teams[i].s,   /* never a bare "Miami" next to Miami (OH) */
           conf: B.teams[i].c, independent: indep, record: { w: w, l: l }, conf_record: indep ? null : confRecord(slug, B.teams[i].c),
          kt_rank: kr[i], kt_of: nFbs, ap: pollRank("ap", slug), coaches: pollRank("coaches", slug),
          chances: { game: indep ? null : p.c, title: indep ? null : p.w, playoff: p.p, bye: p.b },
          games_left: left, sched: { games: s.remaining.n, fcs: s.remaining.fcs, mean: s.remaining.mean, rank: s.remaining.rank === undefined ? null : s.remaining.rank, of: s.remaining.of === undefined ? null : s.remaining.of }
        };
      });
      var a = ids[0], b = ids[1], results = [], upcoming = [];
      function nm(i) { return out[0].slug && ids[0] === i ? out[0].name : ids[1] === i ? out[1].name : B.teams[i].s; }
      B.played.forEach(function (g, n) {
        if (!((g[0] === a && g[1] === b) || (g[0] === b && g[1] === a))) return;
        var aw = g[0] === a ? g[2] : g[3], bw = g[0] === a ? g[3] : g[2], wn = aw > bw ? a : b, ls = aw > bw ? b : a;
        results.push({ n: n, week: g[4], winner: nm(wn), loser: nm(ls), score: Math.max(aw, bw) + "-" + Math.min(aw, bw) });
      });
      results.sort(function (x, y) { return x.week - y.week || x.n - y.n; }); results.forEach(function (r) { delete r.n; });
      B.games.forEach(function (g) {
        if (!((g.h === a && g.a === b) || (g.h === b && g.a === a))) return;
        var w = when(g.date, g.id);
        upcoming.push({ id: g.id, week: g.wk, date: w.label, tba: w.tba, when: w.tba ? w.label + ", time TBD" : w.label, neutral: !!g.neu, host: g.neu ? null : nm(g.h) });
      });
      upcoming.sort(function (x, y) { return x.week - y.week || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0); });
      var asof = { label: C.asofLabel(B.as_of), files: [{ file: "sim-bundle", label: C.asofLabel(B.as_of) }, { file: "pred-teams", label: P.model_asof || null }, { file: "polls", label: POL && POL.ap ? POL.ap.asof : null }, { file: "ccg-sim", label: S && S.asof ? C.asofLabel(S.asof) : null }] };
      return { ok: true, tool: "team_compare", params: params, n_seasons: P.seasons, asof: asof, facts: { aspect: aspect, teams: out, meeting: { result: results.length ? results[0] : null, upcoming: upcoming.length ? upcoming[0] : null, has_tba: upcoming.some(function (u) { return u.tba; }) }, poll_asof: POL && POL.ap ? POL.ap.asof : null } };
    },

    render: function (r) {
      var F = r.facts, T = F.teams, V = {}, rows = [], notes = [], asp = F.aspect, ranksShown = false, pollsShown = false, chShown = false, schedShown = false;
      V.a = { t: "text", v: T[0].name, src: "facts.teams.0.name" }; V.b = { t: "text", v: T[1].name, src: "facts.teams.1.name" };
      function two(label, type, p, g0, g1, na0, na1) {   /* one measure row: value for each team, or a fixed cell when a value does not apply */
        var vals = {}, c0 = COPY.cX, c1 = COPY.cY;
        if (g0 === null || g0 === undefined) c0 = na0; else vals.x = { t: type, v: type === "rec" ? [g0.w, g0.l] : g0, src: "facts.teams.0." + p };
        if (g1 === null || g1 === undefined) c1 = na1; else vals.y = { t: type, v: type === "rec" ? [g1.w, g1.l] : g1, src: "facts.teams.1." + p };
        rows.push({ cells: [label, c0, c1], src: "facts.teams", vals: vals });
      }
      var showRecord = asp === "all" || asp === "record", showRank = asp === "all" || asp === "rank", showCh = asp === "all" || asp === "chances", showSched = asp === "all" || asp === "schedule";
      if (showRecord) {
        two(COPY.lRecord, "rec", "record", T[0].record, T[1].record, COPY.cNone, COPY.cNone);
        two(COPY.lConfRecord, "rec", "conf_record", T[0].conf_record, T[1].conf_record, COPY.cNa, COPY.cNa);
      }
      if (showRank) {
        ranksShown = true;
        two(COPY.lKtRank, "rank", "kt_rank", T[0].kt_rank, T[1].kt_rank, COPY.cNone, COPY.cNone);
        if (T[0].ap !== null || T[1].ap !== null || T[0].coaches !== null || T[1].coaches !== null) {
          pollsShown = true;
          two(COPY.lAp, "rank", "ap", T[0].ap, T[1].ap, COPY.cNotRanked, COPY.cNotRanked);
          two(COPY.lCoaches, "rank", "coaches", T[0].coaches, T[1].coaches, COPY.cNotRanked, COPY.cNotRanked);
        }
      }
      if (showCh) {
        chShown = true;
        two(COPY.lGame, "pct", "chances.game", T[0].chances.game, T[1].chances.game, COPY.cNa, COPY.cNa);
        two(COPY.lTitle, "pct", "chances.title", T[0].chances.title, T[1].chances.title, COPY.cNa, COPY.cNa);
        two(COPY.lPlayoff, "pct", "chances.playoff", T[0].chances.playoff, T[1].chances.playoff, COPY.cNone, COPY.cNone);
        two(COPY.lBye, "pct", "chances.bye", T[0].chances.bye, T[1].chances.bye, COPY.cNone, COPY.cNone);
      }
      if (showSched) {
        schedShown = true;
        two(COPY.lLeft, "int", "games_left", T[0].games_left, T[1].games_left, COPY.cNone, COPY.cNone);
        two(COPY.lOpp, "num1", "sched.mean", T[0].sched.mean, T[1].sched.mean, COPY.cNone, COPY.cNone);
      }
      notes.push(COPY.nVerdict);
      if (showRecord || showCh) { if (T[0].independent) notes.push(COPY.nIndepA); if (T[1].independent) notes.push(COPY.nIndepB); }
      if (ranksShown) notes.push(COPY.nRating);
      if (pollsShown) { V.pollasof = { t: "text", v: F.poll_asof, src: "facts.poll_asof" }; notes.push(COPY.nPolls); }
      if (schedShown) notes.push(COPY.nSched);
      if (asp === "all" || asp === "record") {
        var M = F.meeting;
        if (M.result) {
          V.winner = { t: "text", v: M.result.winner, src: "facts.meeting.result.winner" }; V.loser = { t: "text", v: M.result.loser, src: "facts.meeting.result.loser" };
          V.score = { t: "text", v: M.result.score, src: "facts.meeting.result.score" }; V.wk = { t: "int", v: M.result.week, src: "facts.meeting.result.week" };
          notes.push(COPY.mResult);
        }
        if (M.upcoming) {
          V.when = { t: "text", v: M.upcoming.when, src: "facts.meeting.upcoming.when" };
          if (M.upcoming.neutral) notes.push(COPY.mNeutral); else { V.host = { t: "text", v: M.upcoming.host, src: "facts.meeting.upcoming.host" }; notes.push(COPY.mHome); }
          notes.push(COPY.nDates); if (M.has_tba) notes.push(COPY.nTba);
        }
        if (!M.result && !M.upcoming) notes.push(COPY.mNone);
      }
      MOD.kind = chShown ? "model" : "lookup";
      var und = asp === "chances" ? COPY.uChances : asp === "record" ? COPY.uRecord : asp === "rank" ? COPY.uRank : asp === "schedule" ? COPY.uSched : COPY.uAll;
      return { type: "table", title: COPY.title, understood: und, vals: V, caption: COPY.caption, cols: [COPY.colMeasure, COPY.colA, COPY.colB], rows: rows, notes: notes, chips: [] };
    }
  });
  if (typeof module !== "undefined" && module.exports) module.exports = TB;
})(typeof self !== "undefined" ? self : globalThis);
