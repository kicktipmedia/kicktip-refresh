/* Builds tests/eval_facts.json: 25 real scenario fact objects (from the A1 card builder on the shipped data) used by tests/eval_models.js and the validator tests.
   usage: node tests/gen_eval_facts.js TREE   (TREE = the A2 site tree)  -- deterministic; ten of them carry a synthetic "playoff chance (model)" pair so the percent checks are exercised. */
"use strict";
const fs = require("fs"), path = require("path"); const tree = path.resolve(process.argv[2] || "work/outb3");
const H = require("./lib/scn_harness.js")(tree), itemText = require("./lib/itemtext.js")(H.B); const S = require(path.join(tree, "assets/ks/scnai.js"));
const QS = ["If BYU wins out", "What if Arizona loses out?", "what if Texas Tech loses out and Arizona wins out", "Colorado wins out", "Tennessee wins 3 of their remaining 4", "Texas A&M wins out", "What if BYU and Texas Tech both end with just one loss?", "what if BYU wins out and Texas Tech loses to Arizona",
  "What if BYU ends with 3 losses?", "What if Utah finishes with no losses?", "what if Utah and Texas Tech win out", "what if Arizona State and Houston win out", "what if New Mexico State and Western Kentucky win out", "what if Miami (OH) and Toledo win out", "what if Ohio State and Indiana both win out", "what if Ohio State ends with 2 losses",
  "what if Alabama and Ole Miss win out", "what if Vanderbilt wins out", "what if Wake Forest ends with 2 losses", "what if SMU ends with 2 losses", "what if Boise State ends with 2 losses", "what if James Madison ends with 2 losses", "what if Duke loses out", "What if Utah loses only one more game?", "what if Georgia wins out", "what if Texas wins out", "what if Tulane wins out", "What if BYU loses 1 of the remaining games?"];
const out = []; let k = 0;
for (const q of QS) {
  const r = H.run(q, { itemText }); if (r.stage !== "build" || !r.f || r.f.ok === false) { console.log("no card: " + q); continue; }
  const f = JSON.parse(JSON.stringify(r.f)); k++;
  if (k % 3 === 1 && f.branches[0].teams.length) { const t = f.branches[0].teams[0].team; f.sim = [{ team: t, ccg: null, playoff: { before: 0.123, after: 0.456, before_text: "12.3%", after_text: "45.6%" } }]; }
  const c = S.compact(f); if (!c) { console.log("compact() null: " + q); continue; }
  out.push({ id: "f" + String(out.length + 1).padStart(2, "0"), q, status: f.status, branches: f.branches.length, facts: f, compact: c });
}
out.length = Math.min(out.length, 25); out.forEach((o, i) => { o.id = "f" + String(i + 1).padStart(2, "0"); });
fs.writeFileSync(path.join(__dirname, "eval_facts.json"), JSON.stringify({ about: "scn_a2 eval fixtures: real scenario fact objects (full = for the validator, compact = what the Worker receives).", tree: path.basename(tree), items: out }, null, 1) + "\n");
console.log("wrote " + out.length + " fixtures; compact sizes (chars): " + out.map((o) => JSON.stringify(o.compact).length).join(","));
