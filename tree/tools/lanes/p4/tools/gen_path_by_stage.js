#!/usr/bin/env node
/* Reference exporter for data/tb/path-by-stage.json (Lane P4). Same method as lane C gen_needs_by_record.js: runs the SHIPPED KTSim (assets/ks/sim.js) with three anchored in-memory
 * insertions (no extra random draws, so the totals equal needs-by-record). Per team and per conference-championship-game state (0 = does not play in the game, 1 = plays and loses,
 * 2 = plays and wins) it counts simulated seasons: n = seasons in that state, p = made the 12-team playoff field, b = earned a first-round bye.
 *   node gen_path_by_stage.js --sim <ks/sim.js> --bundle <sim-bundle.json> --out <file> [--seasons 10000] [--seed 20261] [--check <needs-by-record.json>]
 * Nothing here is shipped to visitors. */
"use strict";
const fs = require("fs"), vm = require("vm");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const simPath = arg("sim"), bundlePath = arg("bundle"), outPath = arg("out"), SEASONS = parseInt(arg("seasons", "10000"), 10), SEED = parseInt(arg("seed", "20261"), 10), checkPath = arg("check");
if (!simPath || !bundlePath || !outPath) { console.error("usage: see header"); process.exit(2); }
let src = fs.readFileSync(simPath, "utf8");
function patch(find, repl) { const c = src.split(find).length - 1; if (c !== 1) throw new Error("anchor count " + c + " (expected 1): " + find.slice(0, 60)); src = src.replace(find, () => repl); }
patch("var nd = bundle.nd;", "var nd = bundle.nd; var PB = [[], [], []], PP = [[], [], []], PQ = [[], [], []]; for (var pz = 0; pz < 3; pz++) for (var pt = 0; pt < n; pt++) { PB[pz].push(0); PP[pz].push(0); PQ[pz].push(0); }");
patch("var champs = {};", "var champs = {}; var PS = new Int8Array(n);");
patch("champs[C.code] = ch; cCcg[g1] += 1;", "champs[C.code] = ch; PS[g1] = w1 ? 2 : 1; PS[g2] = w1 ? 1 : 2; cCcg[g1] += 1;");
patch("for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }",
  "for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }\n      for (fi = 0; fi < F.length; fi++) PB[PS[F[fi]]][F[fi]] += 1;\n      for (i = 0; i < f1.length; i++) { PP[PS[f1[i]]][f1[i]] += 1; if (i < 4) PQ[PS[f1[i]]][f1[i]] += 1; }");
patch("return out;\n  }\n\n  var API", "out.ps = { n: PB, p: PP, b: PQ }; return out;\n  }\n\n  var API");
const mod = { exports: {} }; vm.runInNewContext(src, { module: mod, exports: mod.exports, Math, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Array, Object, Error, String, Number, Date }, { filename: "sim.patched.js" });
const KTSim = mod.exports, B = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const res = KTSim.simulate(B, { seasons: SEASONS, seed: SEED });
const t = {};
B.teams.forEach((tm, i) => {
  if (!tm.g || i === B.fcs) return;
  const n = [0, 1, 2].map(z => res.ps.n[z][i]); if (n[0] + n[1] + n[2] !== SEASONS) return;
  t[tm.g] = { n, p: [0, 1, 2].map(z => res.ps.p[z][i]), b: [0, 1, 2].map(z => res.ps.b[z][i]) };
});
Object.keys(t).forEach(k => { const e = t[k]; for (let z = 0; z < 3; z++) if (e.p[z] > e.n[z] || e.b[z] > e.p[z]) throw new Error("bad counts " + k); });
if (checkPath) { const NB = JSON.parse(fs.readFileSync(checkPath, "utf8")); Object.keys(NB.byrec).forEach(k => { const e = t[k], r = NB.byrec[k], sum = a => a.reduce((x, y) => x + y, 0); if (!e || sum(e.p) !== sum(r.p) || sum(e.b) !== sum(r.b)) throw new Error("totals differ from needs-by-record for " + k); }); console.log("totals match needs-by-record for " + Object.keys(NB.byrec).length + " teams"); }
fs.writeFileSync(outPath, JSON.stringify({ asof: B.as_of, seasons: SEASONS, seed: SEED, doc: "Lane P4 path-by-stage. t[team].n/p/b = [does not play in its conference championship game, plays and loses, plays and wins]: simulated seasons in that state / of those, seasons the team made the 12-team playoff field / earned a first-round bye. Same simulation run and seed as needs-by-record.", t }));
console.log("wrote " + outPath + " bytes " + fs.statSync(outPath).size + " teams " + Object.keys(t).length);
