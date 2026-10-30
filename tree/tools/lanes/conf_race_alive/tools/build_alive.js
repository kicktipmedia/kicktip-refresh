#!/usr/bin/env node
/* build_alive.js: precompute data/tb/ccg-alive.json (+ <root>/../<rootname>.ccg-alive-proof.json, not shipped) = who is still in the race for each conference's championship game.
   Usage:  node tools/build_alive.js --root <site root with assets/ccgsim.js and data/ccg-sim.json, data/ccg-rules.json>  [--out data/tb/ccg-alive.json] [--proof <path>]
                                    [--conf big12] [--check [--card-only]] [--quiet]
   --check : rebuild in memory and compare with the files on disk (exit 1 on any difference, or if ccg-sim.json / the engine changed since the file was built). Used as the refresh gate and by QA.
   Deterministic: same inputs -> byte-identical files (seeded sampling, node caps, no clock in the output). Wording in the file avoids the abbreviation and the other banned words. */
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const core = require("./alive_core.js");

const args = process.argv.slice(2), opt = {};
for (let i = 0; i < args.length; i++) { const a = args[i]; if (a === "--check" || a === "--quiet" || a === "--card-only") opt[a.slice(2)] = true; else if (a.startsWith("--")) opt[a.slice(2)] = args[++i]; }
if (!opt.root) { console.error("usage: build_alive.js --root <tree root with assets/ and data/>"); process.exit(2); }
const ROOT = path.resolve(opt.root);
const OUT = path.resolve(ROOT, opt.out || "data/tb/ccg-alive.json"), PROOF = path.resolve(ROOT, opt.proof || path.join("..", path.basename(ROOT) + ".ccg-alive-proof.json"));   // the proof file is NOT shipped: it lives next to the tree, never inside it
const sha = s => crypto.createHash("sha256").update(s).digest("hex").slice(0, 16);
const read = p => fs.readFileSync(path.join(ROOT, p), "utf8");

/* Auto-derived, user-safe "limits" per conference: what the rules text leaves to a step this tool cannot compute or to a reading. These go into the card footer, never a number. */
function limitsOf(R) {
  const L = [], steps = [].concat(R.two || [], R.multi || [], R.two_second || [], R.host || [], R.pre || []);
  if (steps.some(s => s.k === "external")) L.push("ranking_step");
  if (steps.some(s => s.k === "random")) L.push("draw_step");
  if ((R.pre || []).length) L.push("immunity_step");
  if (R.alt) L.push("two_readings");
  if (R.tie_group && R.tie_group !== "equal") L.push("unequal_schedules");
  if (R.fmt === "div") L.push("divisions");
  const v = (R.doc && R.doc.version || "") + " " + (R.doc && R.doc.title || "");
  if (/2024|2025|not republished|latest edition|no 2026|2018/i.test(v)) L.push("rules_text_not_2026");
  return L;
}

function build() {
  const simTxt = read("data/ccg-sim.json"), rulesTxt = read("data/ccg-rules.json"), engTxt = read("assets/ccgsim.js");
  const K = require(path.join(ROOT, "assets/ccgsim.js")), S = JSON.parse(simTxt), RJ = JSON.parse(rulesTxt);
  let vf = {}; try { vf = JSON.parse(read("data/ccg-rules-verified.json")); } catch (e) {}
  /* Analyst verdicts (tools/analyst_verdicts.json, copied from the Analyst's verdicts.json): valid only for the exact ccg-rules.json bytes the Analyst checked; otherwise every conference is "none". */
  let av = { conferences: {} }; try { const a = JSON.parse(fs.readFileSync(path.join(__dirname, "analyst_verdicts.json"), "utf8")); if (crypto.createHash("sha256").update(rulesTxt).digest("hex") === (a.checked_against || {})["ccg-rules.json_sha256"]) av = a; } catch (e) {}
  let pg = null; try { pg = JSON.parse(read("data/pred-games.json")).g; } catch (e) {}      // only used as a sampling bias (never shown, never a number in the output)
  const card = { v: 2, kind: "conf_race_alive", words: "in_race", asof: S.asof, src: { sim: sha(simTxt), rules: sha(rulesTxt), engine: sha(engTxt) }, confs: {} };
  const proof = { v: 1, src: card.src, note: "Witness = one complete set of results (bit i = 1 when the home team of remaining game i wins; games listed in rem[conf] order) after which the team is in the championship game under the rules in ccg-rules.json. w = in the race, nw = not clinched, sw = in under every unresolved tie step.", rem: {}, teams: {} };
  const stats = {};
  const codes = opt.conf ? [opt.conf] : Object.keys(S.confs);
  codes.forEach(code => {
    const conf = S.confs[code], R = RJ.rules[code];
    const bias = pg ? conf.games.filter(g => g.w === null || g.w === undefined).map(g => { const e = pg[g.k]; return e && typeof e[0] === "number" ? e[0] : 0.5; }) : null;
    const A = core.analyzeConf(K, R, conf, { bias, seed: 12345 + code.length });
    const ctx = A.ctx, n = ctx.n, order = [...Array(n).keys()].sort((a, b) => (ctx.W0[b] / Math.max(1, ctx.G0[b])) - (ctx.W0[a] / Math.max(1, ctx.G0[a])) || ctx.W0[b] - ctx.W0[a] || (ctx.names[a] < ctx.names[b] ? -1 : 1));
    const rows = order.map(i => {
      const r = A.res[i], t = conf.teams[i], l = ctx.G0[i] - ctx.W0[i];
      const row = { n: t.short, s: t.slug, w: ctx.W0[i], l, left: ctx.L0[i], best: { w: ctx.W0[i] + ctx.L0[i], l }, st: r.st, cl: r.clinched, sure: r.sure };
      if (r.st === "out") row.why = r.proof.method === "record" ? "record" : "search";
      if (r.out_by && r.out_by.length) row.by = r.out_by.map(y => ctx.names[y]);
      return row;
    });
    const pick = f => rows.filter(f).map(r => r.n);
    const rem = ctx.games.map(g => g.id);
    card.confs[code] = {
      name: R.name, fmt: R.fmt, analyst: (av.conferences[code] || {}).verdict || "none", verified: false, verified_by: null, verified_on: null,
      rules: { title: R.doc.title, version: R.doc.version, checked: R.doc.checked, hash: sha(JSON.stringify(R)) },
      limits: limitsOf(R), remaining: rem.length, weeks: [...new Set(ctx.games.map(g => g.wk))].sort((a, b) => a - b),
      counts: { teams: n, in_race: rows.filter(r => r.st === "in").length, out: rows.filter(r => r.st === "out").length, clinched: rows.filter(r => r.cl === true).length, unknown: rows.filter(r => r.st === "unk").length },
      in_race: pick(r => r.st === "in"), out_race: pick(r => r.st === "out"), clinched: pick(r => r.cl === true), tie_only: pick(r => r.st === "in" && r.sure === false), unknown: pick(r => r.st === "unk"),
      teams: rows
    };
    const v = vf[code]; if (v && v.verified === true && v.rules_hash === card.confs[code].rules.hash && card.confs[code].analyst === "verified") {   /* stronger wording needs BOTH: the CEO-approved flag with a matching rules hash AND an Analyst verdict of VERIFIED MATCH for these bytes */ Object.assign(card.confs[code], { verified: true, verified_by: v.by || null, verified_on: v.date || null }); }
    proof.rem[code] = rem; proof.notes = proof.notes || {}; proof.notes[code] = R.notes || []; proof.teams[code] = {};
    order.forEach(i => { const r = A.res[i], p = {}; if (ctx.wit.any[i]) p.w = core.toHex(ctx.wit.any[i]); if (ctx.wit.notAll[i]) p.nw = core.toHex(ctx.wit.notAll[i]); if (ctx.wit.all[i]) p.sw = core.toHex(ctx.wit.all[i]); if (r.proof && r.st !== "in") p.out = r.proof; if (r.cproof) p.cl = r.cproof; proof.teams[code][ctx.names[i]] = p; });
    stats[code] = { ms: A.ms, leaves: ctx.stats.leaves, nodes: ctx.stats.nodes, tooMany: ctx.stats.tooMany, games: rem.length };
  });
  return { card, proof, stats };
}

const BAN = /\bCCG\b|title game/i;
function lint(card) { const s = JSON.stringify(card); const m = BAN.exec(s); if (m) throw new Error("banned word in output: " + m[0]); }

const t0 = Date.now(), B = build(); lint(B.card);
const cardTxt = JSON.stringify(B.card), proofTxt = JSON.stringify(B.proof);
if (opt.check) {
  let bad = [];
  try { if (fs.readFileSync(OUT, "utf8") !== cardTxt) bad.push(OUT); } catch (e) { bad.push(OUT + " (missing)"); }
  if (!opt["card-only"]) { try { if (fs.readFileSync(PROOF, "utf8") !== proofTxt) bad.push(PROOF); } catch (e) { bad.push(PROOF + " (missing)"); } }
  if (bad.length) { console.error("STALE or different: " + bad.join(", ")); process.exit(1); }
  console.log("ccg-alive up to date (sim " + B.card.src.sim + ", engine " + B.card.src.engine + ", asof " + B.card.asof + ")");
} else {
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, cardTxt); fs.writeFileSync(PROOF, proofTxt);
  if (!opt.quiet) {
    Object.keys(B.stats).forEach(c => { const k = B.card.confs[c].counts, s = B.stats[c]; console.log(c.padEnd(9), "games", String(s.games).padStart(2), "in", k.in_race, "out", k.out, "clinched", k.clinched, "unknown", k.unknown, "| leaves", s.leaves, "nodes", s.nodes, "tooMany", s.tooMany, "|", s.ms + " ms"); });
    console.log("wrote", OUT, cardTxt.length, "bytes;", PROOF, proofTxt.length, "bytes; total", Date.now() - t0, "ms");
  }
}
