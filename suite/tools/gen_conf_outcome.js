#!/usr/bin/env node
/* Exporter for data/tb/conf-outcome.json (Set 3b, tool #24 whatif_conference_outcome). Run in the refresh step after sim-bundle.json is written (same place, seed and season count as gen_conf_bids.js).
 *   node gen_conf_outcome.js --sim <assets/ks/sim.js> --bundle <data/sim-bundle.json> --out <file> [--seasons 10000] [--seed 20261] [--min 100] [--vs 3]
 * Runs the SHIPPED KTSim unchanged except for anchored in-memory insertions that, per simulated season, note each conference championship game (both teams, the winner) and the 12-team playoff field (first four = first-round byes).
 * No new sim runs beyond the refresh's own seasons: the counts are a filter over those seasons. For every team that reaches its conference championship game in at least --min seasons (1% of 10,000):
 *   t[slug] = {base:{cfp12,bye}, reach:{s,cfp12,bye}, win:{s,cfp12,bye}?, vs:{opp:{s,win_cfp12,win_bye}}?}
 *   s = seasons in the condition; the rest are shares of those seasons. win / vs rows only when s >= --min; vs keeps the --vs opponents with the most such seasons.
 * Nothing here ships. No network. */
"use strict";
const fs = require("fs"), vm = require("vm");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const simPath = arg("sim"), bundlePath = arg("bundle"), outPath = arg("out"), SEASONS = parseInt(arg("seasons", "10000"), 10), SEED = parseInt(arg("seed", "20261"), 10), MIN = parseInt(arg("min", "100"), 10), NVS = parseInt(arg("vs", "3"), 10);
if (!simPath || !bundlePath || !outPath) { console.error("usage: see header"); process.exit(2); }
let src = fs.readFileSync(simPath, "utf8");
function patch(find, repl) { const c = src.split(find).length - 1; if (c !== 1) throw new Error("anchor count " + c + " (expected 1): " + find.slice(0, 60)); src = src.replace(find, () => repl); }
patch("var nd = bundle.nd;", "var nd = bundle.nd; var CO = { games: [], n: 0, rs: {}, vs: {}, base: {} }; function coAdd(o, k, inF, bye) { var e = o[k] || (o[k] = [0, 0, 0]); e[0] += 1; if (inF) e[1] += 1; if (bye) e[2] += 1; }");
patch("champs[C.code] = ch; cCcg[g1] += 1; cCcg[g2] += 1; cTitle[ch] += 1;", "champs[C.code] = ch; cCcg[g1] += 1; cCcg[g2] += 1; cTitle[ch] += 1; CO.games.push([g1, g2, ch]);");
patch("for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }",
  "for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; } CO.n += 1; var fpos = {}; for (i = 0; i < f1.length; i++) fpos[f1[i]] = i; CO.games.forEach(function (gm) { [0, 1].forEach(function (sd) { var me = gm[sd], op = gm[1 - sd], inF = fpos[me] !== undefined, bye = inF && fpos[me] < 4; coAdd(CO.rs, me + ':reach', inF, bye); if (gm[2] === me) { coAdd(CO.rs, me + ':win', inF, bye); coAdd(CO.vs, me + ':' + op, inF, bye); } }); }); CO.games = [];");
patch("return out;\n  }\n\n  var API", "out.co = CO; out.cfpN = cCfp; out.byeN = cBye; return out;\n  }\n\n  var API");
const mod = { exports: {} }; vm.runInNewContext(src, { module: mod, exports: mod.exports, Math, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Array, Object, Error, String, Number, Date }, { filename: "sim.patched.js" });
const KTSim = mod.exports, B = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const res = KTSim.simulate(B, { seasons: SEASONS, seed: SEED }), CO = res.co;
if (CO.n !== SEASONS) throw new Error("season count " + CO.n);
const r4 = x => Math.round(x * 1e4) / 1e4, slug = i => B.teams[i].g, t = {};
const ids = Object.keys(CO.rs).filter(k => /:reach$/.test(k)).map(k => +k.split(":")[0]).sort((a, b) => slug(a) < slug(b) ? -1 : 1);
ids.forEach(i => {
  const R = CO.rs[i + ":reach"]; if (R[0] < MIN) return;
  const row = { base: { cfp12: r4(res.cfpN[i] / SEASONS), bye: r4(res.byeN[i] / SEASONS) }, reach: { s: R[0], cfp12: r4(R[1] / R[0]), bye: r4(R[2] / R[0]) } };
  const W = CO.rs[i + ":win"]; if (W && W[0] >= MIN) row.win = { s: W[0], cfp12: r4(W[1] / W[0]), bye: r4(W[2] / W[0]) };
  const vs = Object.keys(CO.vs).filter(k => +k.split(":")[0] === i).map(k => ({ o: +k.split(":")[1], e: CO.vs[k] })).filter(x => x.e[0] >= MIN).sort((a, b) => b.e[0] - a.e[0] || (slug(a.o) < slug(b.o) ? -1 : 1)).slice(0, NVS);
  if (vs.length) { row.vs = {}; vs.forEach(x => { row.vs[slug(x.o)] = { s: x.e[0], win_cfp12: r4(x.e[1] / x.e[0]), win_bye: r4(x.e[2] / x.e[0]) }; }); }
  t[slug(i)] = row;
});
const out = { v: 1, asof: B.as_of, n: SEASONS, seed: SEED, min_s: MIN, doc: "Set 3b conf-outcome. Filtered from the simulated seasons of the shipped simulator (seed above). t[slug]: base = share of all seasons in the 12-team playoff field (cfp12) and with a first-round bye (bye); reach = seasons the team plays in its conference championship game (s) and those shares within them; win = seasons it wins that game; vs[opp] = seasons it beats that opponent there. Rows only when s >= min_s.", t };
fs.writeFileSync(outPath, JSON.stringify(out));
console.log("wrote " + outPath + " bytes " + fs.statSync(outPath).size + " teams " + Object.keys(t).length);
