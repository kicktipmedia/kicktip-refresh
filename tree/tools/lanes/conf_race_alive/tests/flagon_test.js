#!/usr/bin/env node
/* flagon_test.js: the verified-wording path END TO END through the page's own TB.render (not tool.render).
   Builds a scratch copy of the built tree, writes a data/ccg-rules-verified.json flag file with the REAL rules hashes, re-runs tools/build_alive.js on the scratch copy, then renders every view and every team.
   Flag file: the five conferences the Analyst verified get {verified:true, rules_hash:<real>}; every other conference ALSO claims verified:true with its real hash (must stay neutral: no Analyst verdict);
   pac12 is given a WRONG hash (must stay neutral). Asserts: no render errors, gated wording only where both keys match, never "all alive" wording (QA checks.json patterns), out-team sentences keep the full phrase.
   usage: node flagon_test.js --root <built tree> */
"use strict";
const fs = require("fs"), os = require("os"), path = require("path"), cp = require("child_process");
const a = process.argv.slice(2), root = path.resolve(a[a.indexOf("--root") + 1] || "");
if (!fs.existsSync(root)) { console.error("usage: flagon_test.js --root <tree>"); process.exit(2); }
let pass = 0, fail = 0; const ok = (c, m) => { if (c) pass++; else { fail++; console.log("FAIL", m); } };
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "flagon_")), T = path.join(tmp, "t");
fs.cpSync(root, T, { recursive: true });
const base = JSON.parse(fs.readFileSync(path.join(root, "data/tb/ccg-alive.json"), "utf8")), flag = {};
Object.keys(base.confs).forEach(c => { flag[c] = { verified: true, rules_hash: c === "pac12" ? "0000000000000000" : base.confs[c].rules.hash, by: "flagon_test", date: "2026-10-26" }; });
fs.writeFileSync(path.join(T, "data/ccg-rules-verified.json"), JSON.stringify(flag));
cp.execFileSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", T, "--quiet"], { stdio: "pipe" });
const A = JSON.parse(fs.readFileSync(path.join(T, "data/tb/ccg-alive.json"), "utf8")), pt = JSON.parse(fs.readFileSync(path.join(T, "data/pred-teams.json"), "utf8"));
const { TB } = require(path.join(__dirname, "../../../core/tools/tbnode.js"))(T), tool = TB.tool("conf_race_alive");
const VERIFIED = ["American", "big12", "midam", "sec"];   /* verified by the Analyst AND flag with the right hash (pac12: right verdict, wrong hash) */
Object.keys(A.confs).forEach(c => ok(A.confs[c].verified === (VERIFIED.indexOf(c) >= 0), c + ": card verified flag is " + A.confs[c].verified + " (want " + (VERIFIED.indexOf(c) >= 0) + ")"));
let qa = null; try { qa = JSON.parse(fs.readFileSync("/workspace/hub/kicktip-toolbox-1026/qbank/checks.json", "utf8")).conf_race.all_alive_forbidden.map(p => new RegExp(p, "i")); } catch (e) { qa = [/\ball (?:\d+ |of the )?teams? (?:are |is )?(?:still )?(?:alive|in the race|in the hunt|in contention)\b/i, /\bno (?:team|one) has been eliminated\b/i, /\bevery(?:one| team)(?: is| are)? (?:still )?(?:alive|in the race|in the hunt|in contention)\b/i]; }
const GATED = /\b(clinch\w*|eliminated|locked)\b/i;
function card(p) {
  const r = tool.run(p, { "tb/ccg-alive": A, "pred-teams": pt }, {}); if (!r.ok) return { r };
  const b = TB.render("conf_race_alive", r);
  ok(b && b.html && !/tbox-miss/.test(b.html) && !(b.errors && b.errors.length), "TB.render builds " + JSON.stringify(p) + (b && b.errors ? ": " + b.errors.join("; ") : ""));
  qa.forEach(re => ok(!re.test(b.text || ""), "all-alive wording in " + JSON.stringify(p) + ": " + re));
  return { r, b, t: b.text || "" };
}
Object.keys(A.confs).forEach(c => {
  const v = VERIFIED.indexOf(c) >= 0, X = A.confs[c], outs = X.teams.filter(t => t.st === "out");
  ["", "in", "out"].forEach(st => {
    const g = card(st ? { conference: c, status: st } : { conference: c }); ok(g.r.ok && g.r.facts.verified === v && g.r.facts.wording === (v ? "verified" : "neutral"), c + " " + st + ": wording " + (g.r.facts || {}).wording);
    if (!g.t) return;
    if (st !== "in") {
      if (outs.length) ok(g.t.indexOf("Out of the race (" + outs.length + ")") >= 0, c + " " + st + ": heading is \"Out of the race (n)\" in both modes");
      ok(!/Eliminated/.test(g.t), c + " " + st + ": no Eliminated heading in either mode");
      if (!outs.length) ok(g.t.indexOf("Out of the race (0)") >= 0 && g.t.indexOf("None yet.") >= 0, c + " " + st + ": empty out-state wording (both modes)");
      if (!v) ok(!GATED.test(g.t), c + " " + st + ": neutral card has no gated word");
    }
    if (st === "in") ok(!/Eliminated \(/.test(g.t), c + " in: no Eliminated heading in the in-view");
  });
  X.teams.forEach(t => {
    const g = card({ conference: c, team: t.s }); if (!g.t) return;
    if (v && t.st === "out") { ok(g.t.indexOf(t.n + " is eliminated from the race for the conference championship game.") >= 0, c + "/" + t.s + ": verified out sentence"); ok(g.t.indexOf("Understood as: whether " + t.n + " is out of the race on our reading of the rules.") >= 0, c + "/" + t.s + ": verified understood line says out (the bank reads title + understood as one sentence)"); ok(/^[^.!?;]*out of the race/.test(g.t), c + "/" + t.s + ": first sentence of the card already says out of the race"); ok(!/whether [^.]* is in the race/.test(g.t), c + "/" + t.s + ": no in-the-race understood line on an out team"); ok(g.t.indexOf("This conference's tiebreaker text has been checked by a person against its source.") >= 0, c + ": verified note"); }
    if (!v) ok(!GATED.test(g.t), c + "/" + t.s + ": neutral team card has no gated word");
    if (!v && t.st === "out") ok(g.t.indexOf(t.n + " is out of the race on our reading of the rules.") >= 0, c + "/" + t.s + ": neutral out sentence");
    if (t.st === "in") ok(!/out of the race/i.test(g.t), c + "/" + t.s + ": in-team card never says out of the race");
  });
});
fs.rmSync(tmp, { recursive: true, force: true });
console.log((fail ? "FAILED" : "PASSED") + ": flag-on test " + pass + " checks, " + fail + " failures"); process.exit(fail ? 1 : 0);
