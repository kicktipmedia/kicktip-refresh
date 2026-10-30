#!/usr/bin/env node
/* sensitivity.js: which in / out calls in data/tb/ccg-alive.json depend on a rule encoding the Analyst could not match to the published text?
   Source of the list of mismatches: /workspace/hub/kicktip-tb-verify-1026/RULES_CHECK.md (copied into tools/analyst_verdicts.json, field "mismatches").
   Method (everything re-runs the live engine assets/ccgsim.js through alive_core.js; the engine is never changed):
     variant "h2h_only"   : every step after head-to-head is replaced by a draw among all teams still tied (and the pre-step is dropped). Any ranking, rating, composite, coin toss or later record step is therefore one of the draw outcomes: a call that holds here holds under EVERY ranking / draw outcome and under any rewrite of the later steps.
     variant "reading_B"  : the second reading carried in rules[conf].alt (Pac-12 tie for second, Conference USA 3+ head-to-head) or, for the ACC, the equal-games reading; the base rules are reading A.
     variant "elim_flip"  : continue <-> restart after one team is seeded from a 3+ tie (the Big Ten Section B, American 10.6, Mountain West steps 3-5 mismatches).
     counting margin      : for out calls, how many rivals are strictly ahead on record in every outcome, minus the slots; >= 1 means the call survives one rival being ruled ineligible (the ineligible-team rules the data does not carry).
   usage: node sensitivity.js --root <tree> [--json out.json] [--conf x]   (default: prints a table) */
"use strict";
const fs = require("fs"), path = require("path");
const core = require("./alive_core.js");
const VERD = JSON.parse(fs.readFileSync(path.join(__dirname, "analyst_verdicts.json"), "utf8"));

function variantsOf(R) {
  const V = {}, strip = Object.assign({}, R); delete strip.alt;
  const h2h = (steps, keep) => { const k = (steps || []).filter(s => keep.indexOf(s.k) >= 0); return k.concat([{ k: "random", name: "any draw outcome", t: "Any later step: every tied team may advance." }]); };
  V.h2h_only = Object.assign({}, strip, { two: h2h(R.two, ["h2h"]), multi: h2h(R.multi, ["h2h_group"]), pre: undefined });
  if (R.two_second) V.h2h_only.two_second = h2h(R.two_second, ["h2h"]);
  delete V.h2h_only.pre; delete V.h2h_only.host;
  if (R.alt && R.alt.patch) { V.reading_A = strip; V.reading_B = Object.assign({}, R, R.alt.patch); delete V.reading_B.alt; }
  else if (R.tie_group === "acc_unequal") V.reading_B = Object.assign({}, R, { tie_group: "equal" });
  V.elim_flip = Object.assign({}, strip, { elim: R.elim === "restart" ? "continue" : "restart" });
  return V;
}

/* Global-wins counting argument (no tiebreaker involved). Every conference game gives exactly one win, so the final wins of all teams add up to the number of games T.
   X can be in the top `slots` only if at most slots-1 rivals finish strictly ahead of X's final pct. Give X wx final wins, every rival at or below X's pct gets at most floor(wx*fin_i/fin_x) wins (and at most its own maximum),
   and let k extra rivals (ineligible teams, which the data does not carry) and the slots-1 allowed rivals reach their own maximum. If the largest total is still below T for every wx, X cannot be in the top `slots`.
   Returns the largest k for which that still holds (-1 = the argument does not prove X out). Only for equal-length tie rules (the unequal-schedule tie rules can pull a team above its pct). */
function pigeonK(ctx, x) {
  if (ctx.tg !== "equal" || ctx.div) return -1;
  let T = 0; ctx.conf.games.forEach(() => { T++; });
  const n = ctx.n, mx = i => ctx.W0[i] + ctx.L0[i];
  const bound = (wx, k) => { let tot = wx; const gains = []; for (let i = 0; i < n; i++) { if (i === x) continue; const cap = Math.min(mx(i), Math.floor(wx * ctx.fin[i] / ctx.fin[x] + 1e-9)); tot += cap; gains.push(mx(i) - cap); } gains.sort((a, b) => b - a); for (let q = 0; q < ctx.slots - 1 + k && q < gains.length; q++) tot += gains[q]; return tot; };
  const out = k => { for (let wx = ctx.W0[x]; wx <= mx(x); wx++) if (bound(wx, k) >= T) return false; return true; };
  if (!out(0)) return -1; let k = 0; while (k < n && out(k + 1)) k++; return k;
}

function run(root, only) {
  const K = require(path.join(root, "assets/ccgsim.js")), S = JSON.parse(fs.readFileSync(path.join(root, "data/ccg-sim.json"), "utf8")), RJ = JSON.parse(fs.readFileSync(path.join(root, "data/ccg-rules.json"), "utf8")), card = JSON.parse(fs.readFileSync(path.join(root, "data/tb/ccg-alive.json"), "utf8"));
  const out = { asof: S.asof, confs: {} };
  Object.keys(S.confs).filter(c => !only || c === only).forEach(code => {
    const R = RJ.rules[code], conf = S.confs[code], base = {}; card.confs[code].teams.forEach(t => { base[t.s] = t; });
    const C = { analyst: (VERD.conferences[code] || {}).verdict || "none", mismatches: (VERD.conferences[code] || {}).mismatch_ids || [], variants: {}, calls: [] };
    const V = variantsOf(R), stat = {};
    Object.keys(V).forEach(name => {
      const A = core.analyzeConf(K, V[name], conf, { seed: 777 + name.length, samples: 120 }), ch = [];
      A.res.forEach((r, i) => { const s = conf.teams[i].slug, b = base[s], bs = b.st === "in" && b.sure === false ? "tie_only" : b.st, vs = r.st === "in" && r.sure === false ? "tie_only" : r.st; if (vs !== bs) ch.push({ team: s, base: bs, variant: vs }); });
      stat[name] = A; C.variants[name] = ch;
    });
    const ctx = core.makeCtx(K, R, conf, {}), st0 = { W: ctx.W0, left: ctx.L0 };
    card.confs[code].teams.forEach(t => {
      const cls = t.st === "in" && t.sure === false ? "tie_only" : t.st; if (cls === "in") return;     // calls that can depend on an encoding: out, and in-only-through-a-tiebreaker
      const x = conf.teams.findIndex(y => y.slug === t.s), pool = ctx.pool[x], mx = core.EPS && (ctx.fin[x] > 0 ? (ctx.W0[x] + ctx.L0[x]) / ctx.fin[x] : 0);
      let ahead = 0; pool.forEach(y => { if (y !== x && (ctx.fin[y] > 0 ? ctx.W0[y] / ctx.fin[y] : 0) > mx + core.EPS) ahead++; });
      const margin = cls === "out" ? ahead - ctx.slots : null, why = [];
      Object.keys(C.variants).forEach(name => { if (C.variants[name].some(c => c.team === t.s)) why.push(name); });
      const pk = cls === "out" ? pigeonK(ctx, x) : null, ruleInel = C.mismatches.indexOf("ineligible_teams_not_in_data") >= 0 || C.mismatches.indexOf("belt_ineligible_champion") >= 0;
      const inelig = cls === "out" && ruleInel && !(cls === "out" && (margin >= 1 || (pk !== null && pk >= 1)));
      C.calls.push({ team: t.s, name: t.n, call: cls, method: t.why || null, record: t.w + "-" + t.l, left: t.left, ahead_on_record: cls === "out" ? ahead : null, margin: margin, wins_total_proof_k: pk, changes_under: why, ineligibility_sensitive: inelig,
        tiebreak_encoding_sensitive: why.length > 0 || cls === "tie_only" });
    });
    out.confs[code] = C;
  });
  return out;
}
module.exports = { run, variantsOf, pigeonK };
if (require.main === module) {
  const a = process.argv.slice(2), o = {}; for (let i = 0; i < a.length; i++) if (a[i].startsWith("--")) o[a[i].slice(2)] = a[++i];
  if (!o.root) { console.error("usage: sensitivity.js --root <tree>"); process.exit(2); }
  const r = run(path.resolve(o.root), o.conf);
  if (o.json) fs.writeFileSync(o.json, JSON.stringify(r, null, 1));
  Object.keys(r.confs).forEach(c => { const C = r.confs[c]; console.log(c.padEnd(9), "analyst:", C.analyst.padEnd(13), "variant changes:", JSON.stringify(Object.keys(C.variants).reduce((m, k) => (m[k] = C.variants[k].map(x => x.team + ":" + x.base + ">" + x.variant), m), {})));
    C.calls.forEach(k => console.log("    ", k.team.padEnd(18), k.call.padEnd(9), k.method || "", "margin", k.margin, "pigeon_k", k.wins_total_proof_k, "changes_under", JSON.stringify(k.changes_under), "inelig_sens", k.ineligibility_sensitive, "tb_sens", k.tiebreak_encoding_sensitive)); });
}
