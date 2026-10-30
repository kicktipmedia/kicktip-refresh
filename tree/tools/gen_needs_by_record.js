#!/usr/bin/env node
/* Reference exporter for data/tb/needs-by-record.json (Lane C). Run from the refresh step after sim-bundle.json and the whatif shards are written.
 *   node gen_needs_by_record.js --sim <ks/sim.js> --bundle <sim-bundle.json> --whatif <dir with index.json + w*.json> --out <file> [--seasons 10000] [--seed 20261]
 * Section byrec: runs the SHIPPED KTSim (assets/ks/sim.js) unchanged except for four anchored in-memory insertions that count, per team and per final regular-season
 *   win total, how many simulated seasons the team (a) finished with that many wins, (b) made the 12-team playoff field, (c) earned a first-round bye (field seeds 1 to 4).
 * Section games: a plain re-pack of the published what-if shards: per team and remaining game, chances (per mille) if the team wins and if it loses; a team missing from a shard
 *   list means "no move of 0.3 points or more was stored", so the chance is the baseline from index.json (same rule the site uses).
 * Nothing here is shipped to visitors (tools/ is never copied into a build). */
"use strict";
const fs = require("fs"), vm = require("vm"), path = require("path");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const simPath = arg("sim"), bundlePath = arg("bundle"), wiDir = arg("whatif"), outPath = arg("out"), SEASONS = parseInt(arg("seasons", "10000"), 10), SEED = parseInt(arg("seed", "20261"), 10);
if (!simPath || !bundlePath || !wiDir || !outPath) { console.error("usage: see header"); process.exit(2); }
let src = fs.readFileSync(simPath, "utf8");
function patch(find, repl) { const c = src.split(find).length - 1; if (c !== 1) throw new Error("anchor count " + c + " (expected 1): " + find.slice(0, 60)); src = src.replace(find, () => repl); }
patch("var nd = bundle.nd;", "var nd = bundle.nd; var BW = { n: [], p: [], b: [] }; for (var bt = 0; bt < n; bt++) { BW.n.push({}); BW.p.push({}); BW.b.push({}); }");
patch("for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }",
  "for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }\n      for (fi = 0; fi < F.length; fi++) { var bq = F[fi], bw = wins[bq]; BW.n[bq][bw] = (BW.n[bq][bw] || 0) + 1; }\n      for (i = 0; i < f1.length; i++) { var bw2 = wins[f1[i]]; BW.p[f1[i]][bw2] = (BW.p[f1[i]][bw2] || 0) + 1; if (i < 4) BW.b[f1[i]][bw2] = (BW.b[f1[i]][bw2] || 0) + 1; }");
patch("return out;\n  }\n\n  var API", "out.byw = BW; return out;\n  }\n\n  var API");
const mod = { exports: {} }; vm.runInNewContext(src, { module: mod, exports: mod.exports, Math, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Array, Object, Error, String, Number, Date }, { filename: "sim.patched.js" });
const KTSim = mod.exports, B = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const res = KTSim.simulate(B, { seasons: SEASONS, seed: SEED });
const byrec = {};
B.teams.forEach((t, i) => {
  if (!t.g || i === B.fcs) return;
  const n = res.byw.n[i], ws = Object.keys(n).map(Number).sort((a, b) => a - b); if (!ws.length) return;
  const w0 = ws[0], w1 = ws[ws.length - 1], arr = (o) => { const a = []; for (let w = w0; w <= w1; w++) a.push(o[w] || 0); return a; };
  byrec[t.g] = { w0, n: arr(res.byw.n[i]), p: arr(res.byw.p[i]), b: arr(res.byw.b[i]) };
});
/* games: re-pack of the what-if shards */
const WI = JSON.parse(fs.readFileSync(path.join(wiDir, "index.json"), "utf8")), shards = {};
Object.keys(WI.shards).forEach(wk => { const f = path.join(wiDir, WI.shards[wk]); if (fs.existsSync(f)) shards[wk] = JSON.parse(fs.readFileSync(f, "utf8")); });
const games = {};
B.games.forEach(g => {
  const sh = shards[String(g.wk)], e = sh && sh[g.id]; if (!e) return;
  [[g.h, "h", "a"], [g.a, "a", "h"]].forEach(([ti, win, lose]) => {
    if (ti === B.fcs) return;
    const slug = B.teams[ti].g, base = WI.baseline[ti], pick = (side) => { const r = (e[side] || []).filter(x => x[0] === ti)[0]; return r ? r.slice(1, 5) : base.slice(0, 4); };
    (games[slug] = games[slug] || []).push({ id: g.id, w: pick(win), l: pick(lose) });
  });
});
const out = { asof: B.as_of, seasons: SEASONS, seed: SEED, doc: "Lane C needs-by-record. byrec[team]: w0 = lowest final regular-season win total seen; n[k], p[k], b[k] = simulated seasons in which the team finished with w0+k wins / made the 12-team playoff field / earned a first-round bye. games[team]: remaining games with chances in per mille [reach the conference championship game, win the conference, make the field, bye] if the team wins (w) and if it loses (l), from the what-if shards (" + (WI.seasons || "?") + " seasons).", whatif_seasons: WI.seasons, byrec, games };
fs.writeFileSync(outPath, JSON.stringify(out));
console.log("wrote " + outPath + " bytes " + fs.statSync(outPath).size + " teams " + Object.keys(byrec).length + " game-teams " + Object.keys(games).length);
