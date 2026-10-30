#!/usr/bin/env node
/* Reference exporter for data/tb/ccg-games.json (toolbox10, tool ccg_matchup). Run from the refresh step after sim-bundle.json is written (same place as gen_needs_by_record.js).
 *   node gen_ccg_games.js --sim <ks/sim.js> --bundle <sim-bundle.json> --slots <data/ccg.json (pipeline slot text)> --out <file> [--seasons 10000] [--seed 20261]
 * Runs the SHIPPED KTSim (assets/ks/sim.js) unchanged except for two anchored in-memory insertions that count, per conference, how often each pair of teams plays in the conference championship game.
 * Slot text (date, time, site) is parsed from the pipeline's ccg.json "slot" string: "Sat 2026-12-05, noon ET (10:00 AM MT), ABC, Charlotte". The TV network is dropped on purpose.
 * Nothing here is shipped to visitors (tools/ is never copied into a build). */
"use strict";
const fs = require("fs"), vm = require("vm");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const simPath = arg("sim"), bundlePath = arg("bundle"), slotsPath = arg("slots"), outPath = arg("out"), SEASONS = parseInt(arg("seasons", "10000"), 10), SEED = parseInt(arg("seed", "20261"), 10);
if (!simPath || !bundlePath || !slotsPath || !outPath) { console.error("usage: see header"); process.exit(2); }
let src = fs.readFileSync(simPath, "utf8");
function patch(find, repl) { const c = src.split(find).length - 1; if (c !== 1) throw new Error("anchor count " + c + " (expected 1): " + find.slice(0, 60)); src = src.replace(find, () => repl); }
patch("var nd = bundle.nd;", "var nd = bundle.nd; var PC = {};");
patch("champs[C.code] = ch; cCcg[g1] += 1; cCcg[g2] += 1; cTitle[ch] += 1;", "champs[C.code] = ch; cCcg[g1] += 1; cCcg[g2] += 1; cTitle[ch] += 1; var pk = Math.min(g1, g2) + \"~\" + Math.max(g1, g2), pm = PC[C.code] || (PC[C.code] = {}); pm[pk] = (pm[pk] || 0) + 1;");
patch("return out;\n  }\n\n  var API", "out.pairs = PC; return out;\n  }\n\n  var API");
const mod = { exports: {} }; vm.runInNewContext(src, { module: mod, exports: mod.exports, Math, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Array, Object, Error, String, Number, Date }, { filename: "sim.patched.js" });
const KTSim = mod.exports, B = JSON.parse(fs.readFileSync(bundlePath, "utf8")), SL = JSON.parse(fs.readFileSync(slotsPath, "utf8")).ccg;
const res = KTSim.simulate(B, { seasons: SEASONS, seed: SEED });
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const SLOT = /^(Sun|Mon|Tue|Wed|Thu|Fri|Sat) (\d{4})-(\d\d)-(\d\d), (.+? \([0-9:]+ [AP]M MT\)), [A-Z]{3,5}, (.+)$/;   /* day, date, time text (with its MT conversion), TV (dropped), site */
const confs = {};
Object.keys(SL).forEach(code => {
  const m = SLOT.exec(SL[code].slot || ""); if (!m) throw new Error("slot text did not parse for " + code + ": " + SL[code].slot);
  const pm = res.pairs[code] || {}, ks = Object.keys(pm), total = ks.reduce((a, k) => a + pm[k], 0);
  const rows = ks.map(k => { const [a, b] = k.split("~").map(Number), sa = B.teams[a].g, sb = B.teams[b].g; return [sa < sb ? sa : sb, sa < sb ? sb : sa, pm[k]]; }).sort((x, y) => y[2] - x[2] || (x[0] + x[1] < y[0] + y[1] ? -1 : 1));
  confs[code] = { fmt: SL[code].format, neutral: !!SL[code].neutral_site, dow: m[1], date: m[2] + "-" + m[3] + "-" + m[4], time_text: m[5], site_text: m[6], games: total, pairs: rows.slice(0, 5) };
});
const out = { v: 1, asof: B.as_of, seasons: SEASONS, seed: SEED, doc: "toolbox10 ccg-games. confs[code].pairs = the five most frequent pairs of teams in the conference championship game as [slugA, slugB, seasons], slugs in alphabetical order, from the shipped simulator (seed above); games = seasons in which the game is played (equals seasons). date / time_text / site_text come from the pipeline's conference slot text (as announced by each conference); the TV network is not kept.", confs };
fs.writeFileSync(outPath, JSON.stringify(out));
console.log("wrote " + outPath + " bytes " + fs.statSync(outPath).size + " confs " + Object.keys(confs).length);
