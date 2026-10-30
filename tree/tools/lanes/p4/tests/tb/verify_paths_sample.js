#!/usr/bin/env node
/* Soundness spot check of data/tb/ccg-paths.json by random sampling, judged by the same shipped rules engine (alive_core.judge -> KTCcg.solve).  node verify_paths_sample.js <root with data/ccg-sim.json, ccg-rules.json, assets/ccgsim.js> <ccg-paths.json> [samples-per-cell=40]
 * For every team and every own-win total k: N at k -> no sampled completion with exactly k own wins puts the team in; A -> every sampled completion has it in under every result; T -> none has it in under every result.
 * Every "cannot lose" game: losing it never puts the team in.  Every "help" set: with the team winning out and the set's results fixed, the team is in under every result.  Prints counts; exit 1 on any violation. */
"use strict";
const fs = require("fs"), path = require("path");
const core = require("../../../conf_race_alive/tools/alive_core.js");
const ROOT = path.resolve(process.argv[2]), PATHS = JSON.parse(fs.readFileSync(process.argv[3], "utf8")), PER = parseInt(process.argv[4] || "40", 10);
const S = JSON.parse(fs.readFileSync(path.join(ROOT, "data/ccg-sim.json"), "utf8")), RJ = JSON.parse(fs.readFileSync(path.join(ROOT, "data/ccg-rules.json"), "utf8")), SIM = require(path.join(ROOT, "assets/ccgsim.js"));
const rnd = core.mulberry(4242); let checks = 0, bad = 0, solves = 0;
function fail(m) { bad++; if (bad <= 20) console.log("VIOLATION " + m); }
Object.keys(PATHS.confs).forEach(code => {
  const conf = S.confs[code], ctx = core.makeCtx(SIM, RJ.rules[code], conf, {}), N = ctx.games.length, slugOf = i => conf.teams[i].slug;
  const gidx = {}; ctx.games.forEach((g, i) => { gidx[g.id] = i; });
  const wins = (g, bit, x) => (g.h === x && bit === 1) || (g.a === x && bit === 0);
  for (let x = 0; x < ctx.n; x++) {
    const e = PATHS.confs[code][slugOf(x)]; if (!e) { fail(code + " missing " + slugOf(x)); continue; }
    const own = e.o.map(id => gidx[id]); if (own.some(i => i === undefined)) { fail(code + "/" + slugOf(x) + " unknown own game id"); continue; }
    const complete = (fix) => { const bits = new Array(N); for (let i = 0; i < N; i++) bits[i] = fix[i] !== undefined ? fix[i] : (rnd() < 0.5 ? 1 : 0); return bits; };
    for (let k = 0; k <= own.length; k++) {
      const c = e.t.charAt(k); if (c === "H" || c === "P" || c === "U") continue;
      for (let s = 0; s < PER; s++) {
        const idx = own.slice(); for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
        const fix = {}; idx.forEach((gi, p) => { const g = ctx.games[gi], win = p < k; fix[gi] = (g.h === x) === win ? 1 : 0; });
        const j = core.judge(ctx, complete(fix)); solves++; if (j.tooMany) continue; checks++;
        if (c === "N" && j.any[x]) fail(code + "/" + slugOf(x) + " k=" + k + " N but sampled in");
        if (c === "A" && !j.all[x]) fail(code + "/" + slugOf(x) + " k=" + k + " A but a sample is not in under every result");
        if (c === "T" && j.all[x]) fail(code + "/" + slugOf(x) + " k=" + k + " T but a sample is in under every result");
      }
    }
    (e.k || []).forEach(id => { const gi = gidx[id], g = ctx.games[gi];
      for (let s = 0; s < PER; s++) { const fix = {}; fix[gi] = (g.h === x) ? 0 : 1; const j = core.judge(ctx, complete(fix)); solves++; if (j.tooMany) continue; checks++; if (j.any[x]) fail(code + "/" + slugOf(x) + " 'cannot lose' game " + id + " lost yet sampled in"); } });
    if (e.h) for (let s = 0; s < PER; s++) {
      const fix = {}; own.forEach(gi => { fix[gi] = (ctx.games[gi].h === x) ? 1 : 0; });
      e.h.forEach(([id, winner]) => { const gi = gidx[id], g = ctx.games[gi]; fix[gi] = slugOf(g.h) === winner ? 1 : 0; });
      const j = core.judge(ctx, complete(fix)); solves++; if (j.tooMany) continue; checks++; if (!j.all[x]) fail(code + "/" + slugOf(x) + " help set does not put the team in under every result");
    }
  }
});
console.log("verify_paths_sample: %d checks (%d solves), %d violations", checks, solves, bad); process.exit(bad ? 1 : 0);
