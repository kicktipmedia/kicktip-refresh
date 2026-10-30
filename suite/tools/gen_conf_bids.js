#!/usr/bin/env node
/* Exporter for data/tb/conf-bids.json (Set 2b, tool conf_vs_conf). Run in the refresh step after sim-bundle.json is written (same place, seed and season count as gen_needs_by_record.js / gen_ccg_games.js).
 *   node gen_conf_bids.js --sim <assets/ks/sim.js> --bundle <data/sim-bundle.json> --out <file> [--seasons 10000] [--seed 20261]
 * Runs the SHIPPED KTSim unchanged except for anchored in-memory insertions that count, per season, how many teams of each conference (sim-bundle teams[].c, Independents = "ind") are in the 12-team playoff field.
 * c[conf][k] = seasons in which exactly k teams of that conference made the field (array length = max k seen + 1; sums to seasons). No network; nothing here ships. */
"use strict";
const fs = require("fs"), vm = require("vm");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const simPath = arg("sim"), bundlePath = arg("bundle"), outPath = arg("out"), SEASONS = parseInt(arg("seasons", "10000"), 10), SEED = parseInt(arg("seed", "20261"), 10);
if (!simPath || !bundlePath || !outPath) { console.error("usage: see header"); process.exit(2); }
let src = fs.readFileSync(simPath, "utf8");
function patch(find, repl) { const c = src.split(find).length - 1; if (c !== 1) throw new Error("anchor count " + c + " (expected 1): " + find.slice(0, 60)); src = src.replace(find, () => repl); }
patch("var nd = bundle.nd;", "var nd = bundle.nd; var BC = {}, BCODE = bundle.teams.map(function (t) { return t.c; }); BCODE.forEach(function (cc) { if (cc && cc !== 'fcs') BC[cc] = [0]; });");
patch("for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }",
  "for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; } var bk = {}; for (i = 0; i < f1.length; i++) bk[BCODE[f1[i]]] = (bk[BCODE[f1[i]]] || 0) + 1; Object.keys(BC).forEach(function (cc) { var a = BC[cc], k = bk[cc] || 0; while (a.length <= k) a.push(0); a[k] += 1; });");
patch("return out;\n  }\n\n  var API", "out.bids = BC; return out;\n  }\n\n  var API");
const mod = { exports: {} }; vm.runInNewContext(src, { module: mod, exports: mod.exports, Math, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Array, Object, Error, String, Number, Date }, { filename: "sim.patched.js" });
const KTSim = mod.exports, B = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const res = KTSim.simulate(B, { seasons: SEASONS, seed: SEED });
const codes = Array.from(new Set(B.teams.map(t => t.c).filter(c => c && c !== "fcs"))).sort();
const c = {};
codes.forEach(code => { const a = res.bids[code].slice(), s = a.reduce((x, y) => x + y, 0); if (s !== SEASONS) throw new Error("row " + code + " sums to " + s); c[code] = a; });
const out = { v: 1, asof: B.as_of, seasons: SEASONS, seed: SEED, doc: "Set 2b conf-bids. c[conf][k] = simulated seasons in which exactly k teams of that conference are in the 12-team playoff field (conference = sim-bundle teams[].c; ind = Independents), from the shipped simulator with the seed above. Each row sums to seasons.", c };
fs.writeFileSync(outPath, JSON.stringify(out));
console.log("wrote " + outPath + " bytes " + fs.statSync(outPath).size + " confs " + codes.length);
