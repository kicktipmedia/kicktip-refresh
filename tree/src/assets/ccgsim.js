/* KickTip official-rules conference championship game engine (browser + Node). Official published tiebreaker rules ONLY: no rating, model number, line or prediction is used here.
   KTCcg.solve(rules, conf, picks, opts) -> result (shape documented in SCHEMA.md). Rules are data (src/ccg_rules_step*.py -> data/ccg-rules.json).
   A step the tool cannot compute (committee/computer ranking, coin toss, draw) is `external` / `random`: the engine BRANCHES over every tied team and reports
   "tie not resolvable by this tool" with every possible outcome unless all branches give the same result. It never guesses.
   picks: {gameId: 1 (home team wins) | 0 (away team wins)}; a game with no entry is "not set". */
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(); else root.KTCcg = factory(); })(typeof self !== "undefined" ? self : this, function () {
"use strict";
var EPS = 1e-9, DAY = 86400, MAXLEAVES = 3000;
var KINDS = ["h2h", "h2h_group", "common_pct", "common_ordered", "ordered_any", "opp_conf_pct", "wins12", "overall_pct", "fbs_pct", "div_pct", "ordered_div", "common_nondiv", "external", "random"];
var LABEL = { h2h: "head-to-head", h2h_group: "head-to-head among the tied teams", common_pct: "record against common opponents", common_ordered: "record against the best-placed common opponents",
  ordered_any: "record against the best-placed opponents", opp_conf_pct: "opponents' combined conference record", wins12: "total wins in the 12-game season", overall_pct: "overall record",
  fbs_pct: "record against FBS opponents", div_pct: "record against division opponents", ordered_div: "record against division opponents in order of finish", common_nondiv: "record against common opponents outside the division" };
function eq(a, b) { return Math.abs(a - b) < EPS; }
function pc(w, g) { return g > 0 ? w / g : 0; }
function p3(x) { var s = x.toFixed(3); return x >= 1 ? "1.000" : s.slice(1); }
function list(a) { return a.length < 3 ? a.join(" and ") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]; }
function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

/* ---------- state ---------- */
function build(conf, picks, useUnset) {
  var n = conf.teams.length, i, j;
  var S = { n: n, names: conf.teams.map(function (t) { return t.short; }), div: conf.div || null, nc: conf.nc || [], H: [], P: [], W: [], G: [], left: [], unset: [], total: conf.games.length, played: 0 };
  for (i = 0; i < n; i++) { S.H.push(new Array(n).fill(0)); S.P.push(new Array(n).fill(0)); S.W.push(0); S.G.push(0); S.left.push(0); }
  conf.games.forEach(function (g) {
    var w = g.w; if (w === null || w === undefined) { w = picks && picks[g.id] !== undefined && picks[g.id] !== null ? picks[g.id] : null; } else S.played++;
    if (w === null) { S.unset.push(g); S.left[g.h]++; S.left[g.a]++; return; }
    var win = w ? g.h : g.a, lose = w ? g.a : g.h;
    S.H[win][lose]++; S.P[win][lose]++; S.P[lose][win]++; S.W[win]++; S.G[win]++; S.G[lose]++;
  });
  S.pct = S.W.map(function (w, k) { return pc(w, S.G[k]); });
  S.ready = S.unset.length === 0;
  var order = []; for (i = 0; i < n; i++) order.push(i);
  order.sort(function (a, b) { return !eq(S.pct[a], S.pct[b]) ? S.pct[b] - S.pct[a] : S.W[b] - S.W[a] || (S.names[a] < S.names[b] ? -1 : 1); });
  S.groups = []; order.forEach(function (t) { var L = S.groups[S.groups.length - 1]; if (L && eq(S.pct[L[0]], S.pct[t])) L.push(t); else S.groups.push([t]); });
  return S;
}
function rec(S, t) { return S.W[t] + "-" + (S.G[t] - S.W[t]); }
function nm(S, a) { return a.map(function (t) { return S.names[t]; }); }
function ovW(S, t) { var x = S.nc[t] || { w: 0, fcsw: 0 }; return S.W[t] + x.w - Math.max(0, x.fcsw - 1); }

/* ---------- steps: return null (does not apply / no data), {unres} or {scores, text} ---------- */
function bestScores(scores) { var m = Math.max.apply(null, scores); return scores.map(function (v) { return eq(v, m); }); }
function pairRecText(S, tied, rs) { return tied.map(function (t, k) { return S.names[t] + " " + rs[k].w + "-" + (rs[k].g - rs[k].w); }).join(", "); }
function h2hGroup(S, tied, mode) {
  var w = tied.map(function (t) { var s = 0; tied.forEach(function (o) { if (o !== t) s += S.H[t][o]; }); return s; });
  var g = tied.map(function (t) { var s = 0; tied.forEach(function (o) { if (o !== t) s += S.P[t][o]; }); return s; });
  var all = tied.every(function (t) { return tied.every(function (o) { return o === t || S.P[t][o] > 0; }); });
  var rs = tied.map(function (t, k) { return { w: w[k], g: g[k] }; });
  if (mode === "beat_or_lost") {   // Mountain West: no win-percentage step, only "beat every other tied team" (placed first) and "lost to every other tied team" (dropped)
    var bw = tied.map(function (t) { return tied.every(function (o) { return o === t || S.H[t][o] > 0; }); }), bwi = bw.indexOf(true);
    if (bwi >= 0) return { scores: tied.map(function (t, k) { return k === bwi ? 1 : 0; }), text: S.names[tied[bwi]] + " beat every other tied team." };
    var lw = tied.map(function (t) { return tied.every(function (o) { return o === t || S.H[o][t] > 0; }); }), lwi = lw.indexOf(true);
    if (lwi >= 0) return { scores: tied.map(function (t, k) { return k === lwi ? -1 : 0; }), text: S.names[tied[lwi]] + " lost to every other tied team and is dropped." };
    return null;
  }
  if (all && mode !== "beat_all") return { scores: rs.map(function (r) { return pc(r.w, r.g); }), text: pairRecText(S, tied, rs) + "." };
  if (mode === "pct_only") return null;
  var beat = tied.map(function (t) { return tied.every(function (o) { return o === t || S.H[t][o] > 0; }); });
  var bi = beat.indexOf(true);
  if (bi >= 0) return { scores: tied.map(function (t, k) { return k === bi ? 1 : 0; }), text: S.names[tied[bi]] + " beat every other tied team." };
  if (mode === "pct_else_beat_lost") {
    var lost = tied.map(function (t) { return tied.every(function (o) { return o === t || S.H[o][t] > 0; }); }), li = lost.indexOf(true);
    if (li >= 0) return { scores: tied.map(function (t, k) { return k === li ? -1 : 0; }), text: S.names[tied[li]] + " lost to every other tied team and is dropped." };
  }
  return null;
}
function splitByH2H(S, grp) {
  if (grp.length === 1) return [grp];
  if (grp.length === 2) { var a = grp[0], b = grp[1]; if (S.P[a][b] && S.H[a][b] !== S.H[b][a]) return S.H[a][b] > S.H[b][a] ? [[a], [b]] : [[b], [a]]; return [grp]; }
  var r = h2hGroup(S, grp, "pct_else_beat_all"); if (!r) return [grp];
  var best = bestScores(r.scores), top = grp.filter(function (t, k) { return best[k]; }), rest = grp.filter(function (t, k) { return !best[k]; });
  if (!rest.length) return [grp];
  // a beat-all result only separates the winner; a pct result sorts everyone
  var sc = {}; grp.forEach(function (t, k) { sc[t] = r.scores[k]; });
  var parts = [], sorted = grp.slice().sort(function (x, y) { return sc[y] - sc[x]; });
  sorted.forEach(function (t) { var L = parts[parts.length - 1]; if (L && eq(sc[L[0]], sc[t])) L.push(t); else parts.push([t]); });
  return parts;
}
function commonOpps(S, tied) { var o = []; for (var k = 0; k < S.n; k++) if (tied.indexOf(k) < 0 && tied.every(function (t) { return S.P[t][k] > 0; })) o.push(k); return o; }
function recAgainst(S, tied, opps) {
  return tied.map(function (t) { var w = 0, g = 0; opps.forEach(function (o) { w += S.H[t][o]; g += S.P[t][o]; }); return { w: w, g: g }; });
}
function ordered(S, step, tied, common, pool) {   // walk the standings groups from the top
  var strict = step.opp_ties === "collective_strict";
  for (var gi = 0; gi < S.groups.length; gi++) {
    var grp = S.groups[gi].filter(function (o) { return tied.indexOf(o) < 0 && (!pool || pool.indexOf(o) >= 0); });
    if (!grp.length) continue;
    var opp = grp;
    if (common && !strict) opp = grp.filter(function (o) { return tied.every(function (t) { return S.P[t][o] > 0; }); });
    else if (!common) opp = grp.filter(function (o) { return tied.some(function (t) { return S.P[t][o] > 0; }); });
    if (!opp.length) continue;
    var parts = [opp];
    if (opp.length > 1 && step.opp_ties === "h2h_then_combine") parts = splitByH2H(S, opp);
    for (var pi = 0; pi < parts.length; pi++) {
      var part = parts[pi], rs = recAgainst(S, tied, part);
      if (!common && rs.some(function (r) { return r.g === 0; })) continue;
      if (common && rs.some(function (r) { return r.g === 0; })) continue;
      if (strict && rs.some(function (r) { return r.g !== rs[0].g; })) continue;
      var sc = rs.map(function (r) { return pc(r.w, r.g); });
      if (sc.every(function (v) { return eq(v, sc[0]); })) continue;
      var place = gi + 1, who = part.length > 1 ? list(nm(S, part)) + " as a group" : S.names[part[0]];
      return { scores: sc, text: "against " + who + " (" + (grp.length > 1 ? "tied in the standings" : "placed " + ordinal(S, part[0])) + "): " + pairRecText(S, tied, rs) + "." };
    }
  }
  return null;
}
function ordinal(S, t) { var r = 1; S.groups.some(function (g) { if (g.indexOf(t) >= 0) return true; r += g.length; return false; }); return "No. " + r; }
function pendingNc(S, tied) { return tied.some(function (t) { return (S.nc[t] || { left: 0 }).left > 0; }); }
function evalStep(S, step, tied) {
  var k = step.k, r;
  if (k === "external" || k === "random") return { unres: true, name: step.short || step.name, kind: k };
  if (k === "h2h") {
    var a = tied[0], b = tied[1]; if (tied.length !== 2 || !S.P[a][b] || S.H[a][b] === S.H[b][a]) return null;
    var aw = S.H[a][b] > S.H[b][a]; return { scores: [aw ? 1 : 0, aw ? 0 : 1], text: S.names[aw ? a : b] + " beat " + S.names[aw ? b : a] + "." };
  }
  if (k === "h2h_group") return h2hGroup(S, tied, step.mode);
  if (k === "common_pct") {
    var c = commonOpps(S, tied); if (!c.length) return null; var rs = recAgainst(S, tied, c);
    return { scores: rs.map(function (x) { return pc(x.w, x.g); }), text: "against " + list(nm(S, c)) + ": " + pairRecText(S, tied, rs) + "." };
  }
  if (k === "common_ordered") return ordered(S, step, tied, true);
  if (k === "ordered_any") return ordered(S, step, tied, false);
  if (k === "opp_conf_pct") {
    var rs2 = tied.map(function (t) { var w = 0, g = 0; for (var o = 0; o < S.n; o++) if (S.P[t][o]) { w += S.P[t][o] * S.W[o]; g += S.P[t][o] * S.G[o]; } return { w: w, g: g }; });
    if (rs2.some(function (x) { return x.g === 0; })) return null;
    return { scores: rs2.map(function (x) { return pc(x.w, x.g); }), text: tied.map(function (t, i) { return S.names[t] + " " + p3(pc(rs2[i].w, rs2[i].g)); }).join(", ") + "." };
  }
  if (k === "wins12") {
    if (pendingNc(S, tied)) return { unres: true, pending: true, name: "total wins in the 12-game season (not every non-conference game is played yet)", kind: "pending" };
    var wv = tied.map(function (t) { return ovW(S, t); }); return { scores: wv, text: tied.map(function (t, i) { return S.names[t] + " " + wv[i] + (wv[i] === 1 ? " win" : " wins"); }).join(", ") + "." };
  }
  if (k === "overall_pct" || k === "fbs_pct") {
    if (pendingNc(S, tied)) return { unres: true, pending: true, name: LABEL[k] + " (not every non-conference game is played yet)", kind: "pending" };
    var vals = tied.map(function (t) { var x = S.nc[t] || { w: 0, fcsw: 0, fcsg: 0, g: 0 }, w, g;
      if (k === "overall_pct") { var ex = Math.max(0, x.fcsw - 1); w = S.W[t] + x.w - ex; g = S.G[t] + x.g - ex; } else { w = S.W[t] + x.w - x.fcsw; g = S.G[t] + x.g - x.fcsg; }
      return { w: w, g: g }; });
    return { scores: vals.map(function (x) { return pc(x.w, x.g); }), text: tied.map(function (t, i) { return S.names[t] + " " + vals[i].w + "-" + (vals[i].g - vals[i].w); }).join(", ") + "." };
  }
  if (!S.div) return null;
  if (k === "div_pct") {
    var rs3 = tied.map(function (t) { var w = 0, g = 0; for (var o = 0; o < S.n; o++) if (o !== t && S.div[o] === S.div[t]) { w += S.H[t][o]; g += S.P[t][o]; } return { w: w, g: g }; });
    if (rs3.some(function (x) { return x.g === 0; })) return null;
    return { scores: rs3.map(function (x) { return pc(x.w, x.g); }), text: pairRecText(S, tied, rs3) + "." };
  }
  if (k === "ordered_div") { var pool = []; for (var o2 = 0; o2 < S.n; o2++) if (S.div[o2] === S.div[tied[0]]) pool.push(o2); return ordered(S, step, tied, false, pool); }
  if (k === "common_nondiv") {
    var c2 = commonOpps(S, tied).filter(function (o) { return S.div[o] !== S.div[tied[0]]; }); if (!c2.length) return null; var rs4 = recAgainst(S, tied, c2);
    return { scores: rs4.map(function (x) { return pc(x.w, x.g); }), text: "against " + list(nm(S, c2)) + ": " + pairRecText(S, tied, rs4) + "." };
  }
  throw new Error("unknown step kind " + k);
}
function skipText(S, step, tied, res) {
  var k = step.k;
  if (k === "h2h") return S.P[tied[0]][tied[1]] ? "they split their games" : "they did not play each other";
  if (k === "h2h_group") return "they did not all play each other and no team beat all the others";
  if (k === "common_pct") return commonOpps(S, tied).length ? "level" : "no common opponents";
  if (k === "common_ordered" || k === "ordered_any" || k === "ordered_div") return "no opponent in the standings separates them";
  return res === null ? "not available" : "level";
}

/* ---------- selection ---------- */
function ctxMake(choices) {
  return { ci: 0, choices: choices, assumptions: [], conds: [], assumed: 0, sections: [], imm: {}, ordered: false,
    choose: function (n, assumeFn, cond) { if (this.ci >= this.choices.length) { var e = { need: n }; throw e; } var b = this.choices[this.ci++]; this.assumptions.push(assumeFn(b)); if (cond) this.conds.push(cond(b)); this.assumed++; return b; } };
}
function combos(arr, k) {
  var out = [];
  (function rec(start, cur) { if (cur.length === k) { out.push(cur.slice()); return; } for (var i = start; i < arr.length; i++) { cur.push(arr[i]); rec(i + 1, cur); cur.pop(); } })(0, []);
  return out;
}
/* Record text for a tied tier. Tier members can have DIFFERENT records at the same win percentage (4-0 and 3-0 are both 100%; ACC / Conference USA tiers mix games played), so one team's record is never printed for all of them.
   rec = a key (the shared record, "unbeaten" or the distinct records); desc = the fragment that goes after "tied": " at 3-0", " (both unbeaten)" or " on win percentage (4-2 and 2-1)". */
function recOfTier(S, tier) { return tierRec(S, tier).rec; }
function tierRec(S, tier) {
  var recs = [], zero = true; tier.forEach(function (t) { var r = rec(S, t); if (recs.indexOf(r) < 0) recs.push(r); if (S.G[t] !== S.W[t]) zero = false; });
  if (recs.length === 1) return { rec: recs[0], desc: " at " + recs[0] };
  if (zero) return { rec: "unbeaten", desc: " (" + (tier.length === 2 ? "both" : "all") + " unbeaten)" };
  return { rec: recs.join("/"), desc: " on win percentage (" + (recs.length === 2 ? recs.join(" and ") : recs.slice(0, -1).join(", ") + " and " + recs[recs.length - 1]) + ")" };
}
function immKey(S, t) { return String(Math.round(S.pct[t] * 1e6)); }
function resolveGroup(S, R, tied, spots, ctx, sec, listOverride, seeding) {
  tied = tied.slice(); var chosen = [], guard = 0;
  var preAll = R.pre || [], optPre = preAll.filter(function (s) { return s.optional; }), fixedPre = preAll.filter(function (s) { return !s.optional; });
  for (;;) {
    if (spots <= 0) return chosen;
    if (tied.length <= spots) return chosen.concat(tied);
    if (++guard > 40) throw new Error("tie loop");
    if (guard > 1) sec.lines.push({ text: "Still to place: " + list(nm(S, tied)) + (spots === 1 ? " (one spot open)." : " (" + spots + " spots open)."), branch: ctx.assumed > 0, head: true });
    /* optional "immunity" step (Mountain West): one fact per tie group, asked once before any other step */
    var ik = immKey(S, tied[0]);
    if (optPre.length && ctx.imm[ik] === undefined) {
      var ps = optPre[0], psn = ps.short || ps.name, TI = tied.slice(), nameI = nm(S, TI);
      var bi = ctx.choose(TI.length + 1, function (b) { return b < TI.length ? nameI[b] + " gets the " + psn + " (the highest-ranked tied team in the Nov 24 CFP ranking, if it also wins its final game)" : "no tied team gets the " + psn; },
        function (b) { return { step: psn, picked: b < TI.length ? [TI[b]] : [], tied: TI.slice() }; });
      sec.unresolved = true;
      if (bi < TI.length) {
        ctx.imm[ik] = TI[bi];
        sec.lines.push({ text: "Before any other step: " + cap(psn) + ". This tool cannot work this out. Tie not resolvable by this tool.", branch: ctx.assumed > 1, unres: true, step: psn });
        sec.lines.push({ text: nameI[bi] + " is in" + (spots > 1 || tied.length === 2 ? " (and hosts if tied for the best record)" : "") + ".", branch: true, head: true });
        chosen = chosen.concat([TI[bi]]); tied = tied.filter(function (t) { return t !== TI[bi]; }); spots -= 1; continue;
      }
      ctx.imm[ik] = -1;
      sec.lines.push({ text: "Before any other step: " + cap(psn) + ". This tool cannot work this out. Tie not resolvable by this tool.", branch: ctx.assumed > 1, unres: true, step: psn });
    }
    var steps = [].concat(fixedPre, listOverride || (tied.length === 2 ? (R.two_second && !seeding && spots === 1 && guard === 1 ? R.two_second : R.two) : R.multi)), restart = false;
    for (var si = 0; si < steps.length; si++) {
      var step = steps[si], res = evalStep(S, step, tied), scores, num = "Step " + (si + 1 - fixedPre.length) + ", ";
      if (res === null) { sec.lines.push({ text: num + LABEL[step.k] + ": " + skipText(S, step, tied, res) + ".", branch: ctx.assumed > 0, skip: true }); continue; }
      var text;
      if (res.unres) {
        var T = tied.slice(), nameS = nm(S, T), stepName = res.name, kk = (step.take === "all" && spots > 1 && T.length > spots) ? spots : 1, CB = combos(T.map(function (t, q) { return q; }), kk);
        var b = ctx.choose(CB.length, function (b) {
          var pk = CB[b].map(function (q) { return nameS[q]; });
          if (res.kind === "random") return "the " + stepName + " goes to " + list(pk);
          return "the " + stepName + " puts " + list(pk) + (kk > 1 ? " in the top " + kk + " of " + list(nameS) : (T.length === 2 ? " above " + nameS[1 - CB[b][0]] : " highest of " + list(nameS)));
        }, function (b) { return { step: stepName, picked: CB[b].map(function (q) { return T[q]; }), tied: T.slice() }; });
        scores = T.map(function (t, q) { return CB[b].indexOf(q) >= 0 ? 1 : 0; });
        sec.unresolved = true;
        text = num + cap(stepName) + ": this tool cannot work this out. Tie not resolvable by this tool.";
        sec.lines.push({ text: text, branch: ctx.assumed > 1, unres: true, step: stepName });
      } else {
        scores = res.scores;
        var best0 = bestScores(scores);
        if (best0.every(Boolean)) { sec.lines.push({ text: num + LABEL[step.k] + ": all level" + (res.text ? " (" + res.text.replace(/\.$/, "") + ")" : "") + ".", branch: ctx.assumed > 0, skip: true }); continue; }
        sec.lines.push({ text: num + LABEL[step.k] + ": " + res.text, branch: ctx.assumed > 0, decisive: true, lab: LABEL[step.k] });
      }
      var best = bestScores(scores), grp = tied.filter(function (t, k) { return best[k]; });
      if (grp.length === tied.length) continue;
      if (grp.length <= spots) {
        var put = grp;
        if (grp.length === 2 && spots >= 2) put = orderPair(S, R, grp, ctx, sec);
        sec.lines.push({ text: list(nm(S, grp)) + (grp.length > 1 ? " are" : " is") + " in.", branch: ctx.assumed > 0, head: true });
        chosen = chosen.concat(put); spots -= grp.length; tied = tied.filter(function (t) { return grp.indexOf(t) < 0; }); restart = true; break;
      }
      tied = grp; sec.lines.push({ text: list(nm(S, grp)) + " stay in the tie; the others drop out.", branch: ctx.assumed > 0, head: true });
      if (tied.length === 2 || R.elim === "restart") { restart = true; break; }
    }
    if (!restart) {   // every listed step used and still tied (the lists end in a draw, so this is defensive)
      var T2 = tied.slice(), nameS2 = nm(S, T2);
      var b2 = ctx.choose(T2.length, function (b) { return "the rules' remaining steps favor " + nameS2[b]; }, function (b) { return { step: "remaining steps", picked: [T2[b]], tied: T2.slice() }; });
      sec.unresolved = true; sec.lines.push({ text: "The listed steps do not separate them. Tie not resolvable by this tool.", branch: ctx.assumed > 1, unres: true, step: "remaining steps" });
      chosen = chosen.concat([T2[b2]]); tied = tied.filter(function (t) { return t !== T2[b2]; }); spots -= 1;
    }
  }
}
function orderPair(S, R, pair, ctx, sec) {
  ctx.ordered = true;
  var a = pair[0], b = pair[1];
  if (!(R.ccg && R.ccg.host && R.ccg.host !== "neutral")) return [a, b];   // neutral site: the order of the two does not matter
  if (!eq(S.pct[a], S.pct[b])) return S.pct[a] > S.pct[b] ? [a, b] : [b, a];
  var iv = ctx.imm[immKey(S, a)];
  if (iv !== undefined && iv >= 0 && (iv === a || iv === b)) { sec.lines.push({ text: S.names[iv] + " has the tiebreaker immunity, so it hosts.", branch: true, head: true }); return [iv, iv === a ? b : a]; }
  sec.lines.push({ text: "Both are in. To order the two (seeding and host), the two-team steps apply:", branch: ctx.assumed > 0, head: true });
  var first = resolveGroup(S, R, [a, b], 1, ctx, sec, R.host || null, true)[0];
  return [first, first === a ? b : a];
}
function tier(S, pool, top, R) {
  var lead = pool.filter(function (t) { return eq(S.pct[t], top); });
  if (R.tie_group === "equal" || !R.tie_group) return lead;
  var ext = lead.slice();
  pool.forEach(function (t) {
    if (lead.indexOf(t) >= 0) return;
    lead.forEach(function (j) {
      if (S.G[t] === S.G[j]) return;
      var lt = S.G[t] - S.W[t], lj = S.G[j] - S.W[j];
      var ok = R.tie_group === "unequal_one_win" ? (lt === lj && S.W[j] - S.W[t] === 1) : (S.W[t] === S.W[j] || lt === lj);
      if (ok && ext.indexOf(t) < 0) ext.push(t);
    });
  });
  return ext;
}
function select(S, R, ctx) {
  var chosen = [], sections = ctx.sections;
  function newSec(tr, what) { var tr0 = tierRec(S, tr), s = { teams: tr, rec: tr0.rec, desc: tr0.desc, what: what, lines: [], unresolved: false }; sections.push(s); return s; }
  if (R.fmt === "div") {
    var champs = [], ds = []; S.div.forEach(function (d) { if (ds.indexOf(d) < 0) ds.push(d); }); ds.sort();
    ds.forEach(function (d) {
      var pool = []; for (var i = 0; i < S.n; i++) if (S.div[i] === d) pool.push(i);
      var top = Math.max.apply(null, pool.map(function (t) { return S.pct[t]; })), tr = tier(S, pool, top, R), sec = newSec(tr, d + " division title");
      champs.push(resolveGroup(S, R, tr, 1, ctx, sec)[0]);
    });
    var sec2 = newSec(champs, "who hosts"), p = orderPair(S, R, champs, ctx, sec2); if (!sec2.lines.length) sections.pop();
    return p;
  }
  var pool2 = []; for (var q = 0; q < S.n; q++) pool2.push(q); var spots = 2;
  while (spots > 0 && pool2.length) {
    var top2 = Math.max.apply(null, pool2.map(function (t) { return S.pct[t]; })), tr2 = tier(S, pool2, top2, R), got;
    var place = chosen.length === 0 ? "first place" : "the next spot";
    if (tr2.length <= spots) {
      got = tr2;
      if (tr2.length === 2 && spots === 2) { var sc = newSec(tr2, "first place"); got = orderPair(S, R, tr2, ctx, sc); if (!sc.lines.length) sections.pop(); }
    } else {
      var sec3 = newSec(tr2, spots === 2 ? "the two conference championship game spots" : (chosen.length ? "the last conference championship game spot" : "first place"));
      got = resolveGroup(S, R, tr2, spots, ctx, sec3);
    }
    chosen = chosen.concat(got); spots = 2 - chosen.length; pool2 = pool2.filter(function (t) { return chosen.indexOf(t) < 0; });
  }
  if (!ctx.ordered && chosen.length === 2 && R.ccg && R.ccg.host && R.ccg.host !== "neutral") {   // hosted game: who hosts (record first, then the host steps)
    var sh = newSec(chosen, "who hosts"); chosen = orderPair(S, R, chosen, ctx, sh); if (!sh.lines.length) sections.pop();
  }
  return chosen;
}
function enumerate(S, R) {
  var leaves = [], stack = [[]], cnt = 0, over = false;
  while (stack.length) {
    var ch = stack.pop(), ctx = ctxMake(ch);
    try { var order = select(S, R, ctx); leaves.push({ order: order, sections: ctx.sections, assumptions: ctx.assumptions, conds: ctx.conds }); }
    catch (e) { if (e && typeof e.need === "number") { for (var b = e.need - 1; b >= 0; b--) stack.push(ch.concat([b])); } else throw e; }
    if (++cnt > MAXLEAVES) { over = true; break; }
  }
  return { leaves: leaves, over: over };
}
function key(a) { return a.slice().sort(function (x, y) { return x - y; }).join(","); }

/* ---------- record-only clinch analysis ---------- */
function clinch(S, R) {
  var n = S.n, minP = [], maxP = [], fin = [];
  for (var t = 0; t < n; t++) { var g = S.G[t] + S.left[t]; fin.push(g); minP.push(pc(S.W[t], g)); maxP.push(pc(S.W[t] + S.left[t], g)); }
  var st = [], inN = 0, alive = 0;
  for (var x = 0; x < n; x++) {
    var rivals = []; for (var y = 0; y < n; y++) if (y !== x && (R.fmt !== "div" || S.div[y] === S.div[x])) rivals.push(y);
    var slots = R.fmt === "div" ? 1 : 2, ahead = rivals.filter(function (y) { return minP[y] > maxP[x] + EPS; }).length, maybe = rivals.filter(function (y) { return maxP[y] >= minP[x] - EPS; }).length;
    var s = ""; if (ahead >= slots) s = "out"; else if (maybe < slots) s = "in"; if (s !== "out") alive++; if (s === "in") inN++;
    st.push(s);
  }
  return { status: st, alive: alive, inCount: inN, minP: minP, maxP: maxP };
}

/* ---------- public ---------- */
var READ_TXT = { whole: "the ACC reads its extended-group wording as sending the whole extended group through the three-or-more-team steps", pct: "the ACC reads its extended-group wording as taking teams in win-percentage order" };
function enumerateBoth(S, R) {   // ACC: the policy wording on the extended group has two readings; both are carried and shown when they give different pairings for the conference championship game
  var E = enumerate(S, R);
  var alt = null, ta, tb, idA, idB, stp = "reading";
  if (R.tie_group === "acc_unequal") { alt = Object.assign({}, R, { tie_group: "equal" }); ta = READ_TXT.whole; tb = READ_TXT.pct; idA = "whole"; idB = "pct"; stp = "acc_reading"; }
  else if (R.alt && R.alt.patch) { alt = Object.assign({}, R, R.alt.patch); delete alt.alt; ta = R.alt.a; tb = R.alt.b; idA = "a"; idB = "b"; }   // a rule sentence with two readings (rules[code].alt): both are carried
  if (!alt) return E;
  var E2 = enumerate(S, alt), k1 = {}, k2 = {}, hm = !!(R.ccg && R.ccg.host && R.ccg.host !== "neutral");
  function kf(l) { return hm ? l.order.join(",") : key(l.order); }
  E.leaves.forEach(function (l) { k1[kf(l)] = 1; }); E2.leaves.forEach(function (l) { k2[kf(l)] = 1; });
  var a = Object.keys(k1).sort().join("|"), b = Object.keys(k2).sort().join("|");
  if (a === b) return E;
  E.leaves.forEach(function (l) { l.assumptions = [ta].concat(l.assumptions); l.conds = [{ step: stp, picked: [idA], tied: [] }].concat(l.conds); });
  E2.leaves.forEach(function (l) { l.assumptions = [tb].concat(l.assumptions); l.conds = [{ step: stp, picked: [idB], tied: [] }].concat(l.conds); });
  return { leaves: E.leaves.concat(E2.leaves), over: E.over || E2.over, readings: true };
}
function analyze(S, R) {
  var E = enumerateBoth(S, R), leaves = E.leaves, outs = {}, sets = {}, ords = {};
  leaves.forEach(function (lf) {
    var ks = key(lf.order), ko = lf.order.join(",");
    (sets[ks] = sets[ks] || []).push(lf); (ords[ko] = ords[ko] || []).push(lf);
  });
  var setKeys = Object.keys(sets), ordKeys = Object.keys(ords);
  var hostMatters = !!(R.ccg && R.ccg.host && R.ccg.host !== "neutral");   // at a neutral site the order of the two teams does not matter
  var res = { tooMany: E.over, pairKnown: setKeys.length === 1, orderKnown: ordKeys.length === 1 || (setKeys.length === 1 && !hostMatters), leaves: leaves.length, outcomes: [], readings: !!E.readings, ordKeys: ordKeys, setKeys: setKeys, leafList: leaves.map(function (l) { return { order: l.order.slice(), conds: l.conds }; }) };
  var first = leaves[0];
  res.pair = res.pairKnown ? (res.orderKnown ? first.order.slice() : sets[setKeys[0]][0].order.slice()) : null;
  res.sections = first.sections.map(function (s) { return { teams: s.teams, rec: s.rec, desc: s.desc, what: s.what, unresolved: s.unresolved, lines: s.lines.filter(function (l) { return !l.branch; }) }; });
  var groupsBy = hostMatters ? ords : sets, kk = Object.keys(groupsBy);
  if (kk.length > 1) {
    res.outcomes = kk.map(function (k) {
      var ls = groupsBy[k], conds = [], seen = {};
      ls.forEach(function (lf) { var c = lf.assumptions.join(", and "); if (!seen[c]) { seen[c] = 1; conds.push(c); } });
      return { teams: ls[0].order.slice(), conds: conds, why: ls[0].sections.reduce(function (a, s) { return a.concat(s.lines.filter(function (l) { return l.branch; }).map(function (l) { return l.text; })); }, []) };
    });
  }
  res.tieIrrelevant = res.pairKnown && res.orderKnown && leaves.length > 1;
  res.hostMatters = hostMatters;
  return res;
}
function tableOf(S, R, cl, final) {
  var rows = [], rank = 1;
  S.groups.forEach(function (g) {
    g.forEach(function (t) { rows.push({ i: t, name: S.names[t], w: S.W[t], l: S.G[t] - S.W[t], g: S.G[t], left: S.left[t], pct: S.pct[t], rank: rank, tied: g.length > 1, clinch: cl.status[t] }); });
    rank += g.length;
  });
  return rows;
}
function solve(R, conf, picks, opts) {
  picks = picks || {};
  var S = build(conf, picks), cl = clinch(S, R), out = { ready: S.ready, left: S.unset.length, total: S.total, played: S.played, clinch: cl, names: S.names };
  out.table = tableOf(S, R, cl);
  out.sure = cl.inCount === 2 && R.fmt !== "div" ? cl.status.map(function (s, i) { return s === "in" ? i : -1; }).filter(function (i) { return i >= 0; }) : [];
  out.inRace = cl.alive;
  var cur = S.ready ? analyze(S, R) : null;
  if (!S.ready) { var snow = S; out.now = analyze(snow, R); }
  var a = cur || out.now;
  out.analysis = a;
  var N = S.names, box = {};
  if (S.ready) {
    out.pair = a.pair; out.pairKnown = a.pairKnown; out.orderKnown = a.orderKnown; out.unresolvable = !a.pairKnown || !a.orderKnown; out.outcomes = a.outcomes;
    out.sections = a.sections;
    var lines = [];
    var secs = a.sections.filter(function (s) { return s.lines.length; });
    if (a.pairKnown) {
      var p = a.pair;
      if (!secs.length) lines.push(N[p[0]] + " and " + N[p[1]] + " finish first and second on conference record.");
      else lines.push(N[p[0]] + " and " + N[p[1]] + " are the two teams in the conference championship game" + (a.orderKnown ? "." : "; the order of the two cannot be settled by this tool."));
      secs.forEach(function (s) { lines.push("Tied" + s.desc + " for " + s.what + ": " + list(nm(S, s.teams)) + "."); s.lines.forEach(function (l) { lines.push(l.text); }); });
      if (a.tieIrrelevant) lines.push("A tie step this tool cannot work out is involved, but every way it could go gives the same two teams" + (a.orderKnown ? " in the same order" : "") + ".");
    } else {
      secs.forEach(function (s) { lines.push("Tied" + s.desc + " for " + s.what + ": " + list(nm(S, s.teams)) + "."); s.lines.forEach(function (l) { lines.push(l.text); }); });
    }
    out.why = lines;
    box.kind = a.pairKnown && a.orderKnown ? "decided" : (a.pairKnown ? "order-open" : "unresolvable");
  } else {
    var nowTxt;
    if (out.sure.length === 2) nowTxt = nm(S, out.sure).join(" and ") + " have clinched the two conference championship game spots on record alone.";
    else nowTxt = a.pairKnown ? "Top two right now: " + list(nm(S, a.pair)) + ", using final results and the results shown." : "Right now the top two spots are tied in a way this tool cannot settle with the games set so far.";
    out.why = [nowTxt, "Still in the race on record: " + (cl.alive === S.n ? "all " + S.n : cl.alive + " of " + S.n) + " teams."];
    box.kind = "open";
  }
  var inAll = null, inAny = {};
  if (S.ready && a.pairKnown) inAll = a.pair.slice();
  else if (S.ready) { (a.outcomes || []).forEach(function (o, k) { o.teams.forEach(function (t) { inAny[t] = 1; }); inAll = (inAll === null ? o.teams.slice() : inAll.filter(function (t) { return o.teams.indexOf(t) >= 0; })); }); }
  out.table.forEach(function (r) { r.spot = S.ready ? (inAll && inAll.indexOf(r.i) >= 0 ? "in" : (inAny[r.i] ? "possible" : "")) : (r.clinch === "in" ? "in" : ""); });
  out.box = box;
  return out;
}

/* ---------- starting results: ESPN favorites, then better record (numbers are never shown; only which side is used) ----------
   FAV_COPY = EVERY visible word about the pre-game favorite (tags, legend, counts, hints). The page label sits in src/build.py (SIM_FAV_LABEL). Edit here to reword; rebuild. */
var FAV_COPY = {
  fav: "ESPN's pre-game favorite", legendFav: "ESPN's pre-game favorite",
  rec: "Better record", legendRec: "Better record or home team", countRec: "from record or home team",
  home: "Records level: home team", homeNote: "No ESPN favorite listed yet; the two teams' records are level, so starting with the home team",
  recNote: "No ESPN favorite listed yet; starting with the team with the better record",
  nol: "No favorite listed yet", legendNol: "No favorite listed", countNol: "with no favorite listed", set: "Set by you (no favorite listed yet)",
  unavailable: "ESPN's pre-game favorites are not available right now, so every game starts with the team with the better record (or the home team when records are level). Tap a team to flip a game.",
  some: function (n) { return n + (n === 1 ? " game starts" : " games start") + " with the team with the better record (or the home team when records are level) because ESPN has not listed a favorite yet."; },
  how: "Games start from ESPN's pre-game favorite, or the team with the better record (the home team if records are level) where none is listed yet. Tap a team to flip a game."
};
/* Starting side for a game with no usable ESPN favorite: the team with the better overall record (conference games counted in the standings + non-conference results), then the better conference record, then the home team.
   Uses only results already in ccg-sim.json (no rating, no number shown, nothing fetched). 1 = home team, 0 = away team. */
function recordInfo(conf, g) {
  var rec = function (t) {
    var w = 0, n = 0; conf.games.forEach(function (x) { if (x.w === null || x.w === undefined || (x.h !== t && x.a !== t)) return; n++; if ((x.w && x.h === t) || (!x.w && x.a === t)) w++; });
    var nc = (conf.nc && conf.nc[t]) || { w: 0, g: 0 }; return { cw: w, cg: n, ow: w + nc.w, og: n + nc.g };
  };
  var h = rec(g.h), a = rec(g.a), ph = pc(h.ow, h.og), pa = pc(a.ow, a.og);
  if (!eq(ph, pa)) return { side: ph > pa ? 1 : 0, level: false };
  ph = pc(h.cw, h.cg); pa = pc(a.cw, a.cg); if (!eq(ph, pa)) return { side: ph > pa ? 1 : 0, level: false };
  return { side: 1, level: true };   // overall and conference records level: the home team (a different label in the UI)
}
function recordSide(conf, g) { return recordInfo(conf, g).side; }
/* Every remaining game gets a starting side. ESPN's pre-game favorite wins when this load has a valid fresh line for that game (same 24 h rule as /games/); otherwise recordSide(). Computed on every load, so when ESPN lists a favorite the game switches to it by itself.
   out.picks/out.defaults = every remaining game; out.src[id] = "espn" | "rec" | "home" ("home" = records level, home team); out.withLine = ESPN games; out.noLine = record games (noRec better record + noHome records level). */
function favorites(conf, lines, now, st) {
  var remaining = conf.games.filter(function (g) { return g.w === null || g.w === undefined; }), l = lines && lines.l && typeof lines.l === "object" ? lines.l : null;
  var out = { picks: {}, defaults: {}, src: {}, withLine: 0, noLine: 0, noRec: 0, noHome: 0, status: "ok", note: "" };
  if (!l || !Object.keys(l).length) out.status = l ? "empty" : "missing";
  var expired = 0;
  remaining.forEach(function (g) {
    var e = l ? l[g.k] : null;
    if (e) {
      var spread = e[0], read = e[1], ko = e[2];
      var stale = !(now - read <= DAY && now - read > -3600) || (ko > 0 && now >= ko);
      if (!stale && typeof spread === "number" && spread !== 0 && !isNaN(spread)) { out.picks[g.id] = spread < 0 ? 1 : 0; out.src[g.id] = "espn"; out.withLine++; return; }
      if (stale) expired++;
    }
    var ri = recordInfo(conf, g); out.picks[g.id] = ri.side; out.src[g.id] = ri.level ? "home" : "rec"; out.noLine++; if (ri.level) out.noHome++; else out.noRec++;
  });
  if (out.status === "ok" && !out.withLine && expired) out.status = "stale";
  for (var k in out.picks) out.defaults[k] = out.picks[k];
  if (out.status !== "ok") out.note = FAV_COPY.unavailable;
  else if (out.noLine) out.note = FAV_COPY.some(out.noLine);
  return out;
}
function changedCount(conf, picks, defaults) {
  var c = 0; conf.games.forEach(function (g) { if (g.w !== null && g.w !== undefined) return; var a = picks[g.id], b = defaults[g.id]; if ((a === undefined ? null : a) !== (b === undefined ? null : b)) c++; });
  return c;
}
function randomFill(conf, picks, rnd) {   // fills only the games that are not set
  var p = Object.assign({}, picks); conf.games.forEach(function (g) { if ((g.w === null || g.w === undefined) && (p[g.id] === undefined || p[g.id] === null)) p[g.id] = rnd() < 0.5 ? 1 : 0; }); return p;
}
function flip(conf, picks, id, side) {   // side: 1 = home, 0 = away. One tap on a team makes it the winner (so one tap on the other team flips the game); tapping the team that already wins changes nothing
  var p = Object.assign({}, picks); p[id] = side; return p;
}
function unset(picks, id) { var p = Object.assign({}, picks); delete p[id]; return p; }
function resetGame(picks, id, defaults) { var p = Object.assign({}, picks); if (defaults[id] === undefined) delete p[id]; else p[id] = defaults[id]; return p; }
/* "decided early": with few games unset, try every way they can end; if all give the same two teams the conference championship game is already settled. Returns the pair (sorted by engine order of the first completion) or null. */
function early(R, conf, picks, limit) {
  var un = conf.games.filter(function (g) { return (g.w === null || g.w === undefined) && (picks[g.id] === undefined || picks[g.id] === null); });
  if (!un.length || un.length > (limit || 10)) return null;
  var p = Object.assign({}, picks), k = null, pair = null;
  for (var m = 0; m < (1 << un.length); m++) {
    un.forEach(function (g, j) { p[g.id] = (m >> j) & 1; });
    var r = solve(R, conf, p); if (!r.pairKnown || !r.orderKnown) return null;
    var kk = (r.analysis && r.analysis.hostMatters) ? r.pair.join(",") : key(r.pair); if (k === null) { k = kk; pair = r.pair.slice(); } else if (k !== kk) return null;
  }
  return pair;
}
return { solve: solve, favorites: favorites, recordSide: recordSide, recordInfo: recordInfo, changedCount: changedCount, randomFill: randomFill, flip: flip, unset: unset, resetGame: resetGame, early: early, KINDS: KINDS, build: build, DAY: DAY, FAV_COPY: FAV_COPY };
});
