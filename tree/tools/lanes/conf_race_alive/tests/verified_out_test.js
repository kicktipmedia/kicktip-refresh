#!/usr/bin/env node
/* verified_out_test.js: for the conferences the Analyst marked VERIFIED MATCH (tools/analyst_verdicts.json, valid only for the ccg-rules.json bytes it names), every "out" call must hold
   (1) under every ranking / draw outcome: re-judged with the engine's branch list (every tied team may advance at a ranking, rating or draw step) on sampled and adversarial completions, and
       again with every step after head-to-head replaced by a draw (the most permissive tie rule there is);
   (2) under BOTH readings carried for the conference (Pac-12 tie for second place; MAC, SEC, Big 12 and American have one reading);
   (3) with a counting proof that uses no tiebreaker (global wins, tools/sensitivity.js pigeonK).
   It also checks the test has teeth: every verified conference's tie-only team is found IN by a sampled completion (so a wrong "out" would be caught).
   usage: node verified_out_test.js --root <built tree> */
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const core = require("../tools/alive_core.js"), sens = require("../tools/sensitivity.js");
const a = process.argv.slice(2); const root = path.resolve(a[a.indexOf("--root") + 1] || "");
if (!fs.existsSync(root)) { console.error("usage: verified_out_test.js --root <tree>"); process.exit(2); }
const K = require(path.join(root, "assets/ccgsim.js")), S = JSON.parse(fs.readFileSync(path.join(root, "data/ccg-sim.json"), "utf8")), rulesTxt = fs.readFileSync(path.join(root, "data/ccg-rules.json"), "utf8"), RJ = JSON.parse(rulesTxt);
const card = JSON.parse(fs.readFileSync(path.join(root, "data/tb/ccg-alive.json"), "utf8")), VER = JSON.parse(fs.readFileSync(path.join(__dirname, "../tools/analyst_verdicts.json"), "utf8"));
let pass = 0, fail = 0; const ok = (c, m) => { if (c) pass++; else { fail++; console.log("FAIL", m); } };
const sameBytes = crypto.createHash("sha256").update(rulesTxt).digest("hex") === VER.checked_against["ccg-rules.json_sha256"];
if (!sameBytes) console.log("note: ccg-rules.json differs from the bytes the Analyst checked: no conference counts as verified, the test only checks the snapshot guard");
const verified = Object.keys(VER.conferences).filter(c => sameBytes && VER.conferences[c].verdict === "verified");
ok(sameBytes ? verified.sort().join() === "American,big12,midam,pac12,sec" : verified.length === 0, "verified set is the five the Analyst named (got " + verified + ")");
const S2 = sens.run(root);
function rng(seed) { return core.mulberry(seed); }
let branched = 0;
verified.forEach(code => {
  const R = RJ.rules[code], conf = S.confs[code], X = card.confs[code], ctx = core.makeCtx(K, R, conf, {}), V = sens.variantsOf(R);
  const readings = [R]; if (R.alt && R.alt.patch) { readings.length = 0; readings.push(V.reading_A, V.reading_B); }
  ok(R.alt ? readings.length === 2 : readings.length === 1, code + " readings carried: " + readings.length);
  ok(X.analyst === "verified", code + " card carries the analyst verdict");
  const outs = X.teams.filter(t => t.st === "out"), ties = X.teams.filter(t => t.st === "in" && t.sure === false);
  const variants = [{ name: "base", R: R }].concat(readings.length === 2 ? [{ name: "A", R: readings[0] }, { name: "B", R: readings[1] }] : []).concat([{ name: "h2h_only", R: V.h2h_only }]);
  const N = ctx.games.length;
  outs.forEach(t => {
    const x = conf.teams.findIndex(y => y.slug === t.s);
    // (3) counting proof without any tiebreaker
    const pk = sens.pigeonK(ctx, x); ok(pk >= 0, code + "/" + t.s + " out: global-wins proof holds (k=" + pk + ")");
    // (1)+(2) every variant, adversarial and random completions
    const rnd = rng(9000 + x);
    variants.forEach(v => {
      const sets = [];
      sets.push(ctx.games.map(g => (g.h === x ? 1 : g.a === x ? 0 : 1)));   // X wins all its games, home teams win the rest
      sets.push(ctx.games.map(g => (g.h === x ? 1 : g.a === x ? 0 : 0)));   // X wins all, away teams win the rest
      for (let c = 0; c < 400; c++) sets.push(ctx.games.map(g => (g.h === x ? 1 : g.a === x ? 0 : (rnd() < 0.5 ? 1 : 0))));   // X wins all its games, others random
      for (let c = 0; c < 150; c++) sets.push(ctx.games.map(() => (rnd() < 0.5 ? 1 : 0)));
      let inAny = false, noTooMany = true;
      sets.forEach(bits => { const picks = {}; ctx.games.forEach((g, i) => { picks[g.id] = bits[i]; }); const r = K.solve(v.R, conf, picks), an = r.analysis; if (an.leafList.length > 1) branched++; if (an.tooMany) noTooMany = false; if (an.leafList.some(l => l.order.indexOf(x) >= 0)) inAny = true; });
      ok(!inAny, code + "/" + t.s + " out holds under reading/variant " + v.name + " (" + sets.length + " completions, all ranking/draw branches)");
      ok(noTooMany, code + "/" + t.s + " " + v.name + ": branch lists complete");
    });
    // the sensitivity run agrees (full search under each variant)
    const C = S2.confs[code]; Object.keys(C.variants).forEach(k => ok(!C.variants[k].some(c => c.team === t.s), code + "/" + t.s + " status unchanged under search variant " + k));
  });
  // teeth: a tie-only team is found IN by some completion (so "out" would be reported as wrong if it were)
  ties.forEach(t => { const x = conf.teams.findIndex(y => y.slug === t.s); const A = core.analyzeConf(K, R, conf, { seed: 5, samples: 200 }); ok(A.res[x].st === "in" && A.ctx.wit.any[x], code + "/" + t.s + " tie-only team has an in witness"); });
  // both readings agree on every team's call (the Pac-12 case): no status flips between readings
  if (readings.length === 2) ["reading_A", "reading_B"].forEach(k => ok(S2.confs[code].variants[k].length === 0, code + " every team keeps its call under " + k));
});
ok(branched > 0, "the engine branched over ranking / draw outcomes on sampled completions (" + branched + " branch lists with more than one leaf)");
console.log((fail ? "FAILED" : "PASSED") + ": verified-out test " + pass + " checks, " + fail + " failures; verified conferences: " + verified.join(", "));
process.exit(fail ? 1 : 0);
