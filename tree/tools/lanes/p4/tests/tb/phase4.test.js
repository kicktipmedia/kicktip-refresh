/* Phase 4 unit tests (toolbox3): team_path and path_compare. Node, offline, no model, no /api/ask.
 * node phase4.test.js --tree <built tree> --frozen <frozen dir> [--lane <lane p4 dir>] */
"use strict";
const fs = require("fs"), path = require("path"), cp = require("child_process");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const tree = path.resolve(arg("tree", "out")), frozen = path.resolve(arg("frozen", "")), lane = path.resolve(arg("lane", path.join(__dirname, "../..")));
const { TB } = require(path.resolve(__dirname, "../../../../core/tools/tbnode.js"))(tree, {}), C = TB.core;
TB.setLoader(n => JSON.parse(fs.readFileSync(n.startsWith("tb/") ? path.join(tree, "data", n + ".json") : path.join(frozen, n + ".json"), "utf8")));
let pass = 0; const fails = [];
const ok = (c, m) => { if (c) pass++; else if (fails.length < 40) fails.push(m); };
const BAN = /\b(bet|bets|betting|wager|wagers|parlay|ccg|title game|the 12(?!-team)|clinch(es|ed)?|eliminat\w*)\b/i, LINT_BAD = /\b(pick|lock|edge|value|gap|market|line|agree|differ|difference)\b/i;
const OLD_LINKS = /\/(playoff|top25|teams)\//;
(async () => {
  /* the shipped assets are exactly what compose_p4.js writes from the parts */
  const comp = cp.spawnSync("node", [path.join(lane, "tools/compose_p4.js"), "--check"], { encoding: "utf8" });
  ok(comp.status === 0, "compose_p4.js --check: " + (comp.stdout + comp.stderr).slice(0, 200));
  /* registration: dark, whichGoal, tool counts */
  const tp = TB.get("team_path"), pc = TB.get("path_compare");
  ok(tp && pc, "both registered"); ok(tp.live === false && pc.live === false, "both dark"); ok(tp.whichGoal === true && pc.whichGoal === true, "whichGoal on both");
  ok(TB.list({ dark: true }).length === 11 && TB.list({ dark: true }).filter(t => t.live).length === 0 && TB.list().length === 0, "11 tools, none live");
  ok(tp.examples.length >= 3 && pc.examples.length >= 3, "examples");
  [tp, pc].forEach(t => { const w = t.description.trim().split(/\s+/).length; ok(w >= 3 && w <= 25, t.id + " description words " + w); });
  /* shared snippet is byte-identical in both composed files */
  const A = fs.readFileSync(path.join(tree, "assets/tb/team_path.js"), "utf8"), B = fs.readFileSync(path.join(tree, "assets/tb/path_compare.js"), "utf8");
  const sh = fs.readFileSync(path.join(lane, "parts/shared.js"), "utf8").trim(); ok(A.includes(sh) && B.includes(sh), "shared snippet identical in both files");
  ok(Buffer.byteLength(A) < 160 * 1024 && Buffer.byteLength(B) < 160 * 1024, "per-file limit 160 KB");
  /* data files within caps and links */
  ["ccg-paths", "path-by-stage"].forEach(n => { const s = fs.readFileSync(path.join(tree, "data/tb", n + ".json"), "utf8"); ok(Buffer.byteLength(s) < 160 * 1024, n + " size"); ok(!OLD_LINKS.test(s), n + " no old links"); });
  /* every team x goal and a pair sample: renders clean, only approved links, no banned words, no bare 0.0%/100.0% */
  const B0 = await TB.data("sim-bundle"), teams = B0.teams.filter(t => t.g).map(t => t.g);
  const sweep = async (id, params) => {
    const r = await TB.run(id, params); if (!r.ok) return;
    const b = TB.render(id, r); ok(b.errors.length === 0, id + " " + JSON.stringify(params) + " render errors " + b.errors.slice(0, 2));
    const t = b.text + " " + b.html;
    ok(!OLD_LINKS.test(t), id + " old-style link " + JSON.stringify(params)); ok(!BAN.test(b.text), id + " banned word " + JSON.stringify(params) + " " + (BAN.exec(b.text) || [])[0]);
    ok(!LINT_BAD.test(b.text.replace(/\bas of\b[^.]*\./i, "")), id + " lint word " + JSON.stringify(params) + " " + (LINT_BAD.exec(b.text) || [])[0]);
    ok(!/(^|[ (])0\.0%|(^|[ (])100\.0%/.test(b.text), id + " bare edge percent " + JSON.stringify(params));
    ok(/^[\x20-\x7e\n\u2019\u2014]*$/.test(b.text.replace(/[^\x00-\x7f]/g, "")), id + " text ascii");
    (b.html.match(/href="([^"]*)"/g) || []).forEach(h => ok(/href="(#|\/method\/|\/disclaimer\/|\/#field|\/#top25)/.test(h), id + " link " + h));
    ok(!/\bResum\u00e9\b/.test(b.text), "plain ASCII Resume");
  };
  for (const g of ["championship_game", "playoff", "bye"]) for (const t of teams) await sweep("team_path", { team: t, goal: g });
  const pairs = [["utah", "arizona"], ["byu", "utah"], ["indiana", "ohio-state"], ["notre-dame", "utah"], ["washington-state", "toledo"], ["alabama", "georgia"]];
  for (const g of ["championship_game", "playoff", "bye"]) for (const [a, b] of pairs) await sweep("path_compare", { teams: [a, b], goal: g });
  /* bad params */
  for (const [id, p] of [["team_path", {}], ["team_path", { team: "utah", goal: "x" }], ["team_path", { team: "nope", goal: "bye" }], ["path_compare", { teams: ["utah"], goal: "bye" }], ["path_compare", { teams: ["utah", "utah"], goal: "bye" }], ["path_compare", { teams: ["utah", "byu", "arizona"], goal: "bye" }]]) { const r = await TB.run(id, p); ok(r.ok === false && r.reason === "bad_param", id + " bad_param " + JSON.stringify(p)); }
  /* the CEO edge wording shows up where a chance is below 0.05% or at least 99.95% and nowhere else */
  const r = await TB.run("team_path", { team: "washington", goal: "bye" }); if (r.ok) { const t = TB.render("team_path", r).text; ok(!/(^|[ (])0\.0%/.test(t), "edge text replaces 0.0% in a path card"); }
  /* routing unit checks (matcher only) */
  const data = { "sim-bundle": B0 }, hint = q => TB.match(q, { mode: "home" }, data, { dark: true });
  const h1 = hint("What is Utah's path to the conference championship game?"); ok(h1 && h1.tool === "team_path" && h1.params.goal === "championship_game", "path -> team_path");
  const h2 = hint("What does Utah need to reach the conference championship game?"); ok(h2 && h2.tool === "team_needs", "need -> team_needs");
  const h3 = hint("Compare Utah's and Arizona's path to a bye."); ok(h3 && h3.tool === "path_compare", "compare -> path_compare");
  const h4 = hint("What is Utah's path to win the Big 12?"); ok(!h4 || h4.tool !== "team_path", "win the conference is not team_path");
  const h5 = hint("What is the fewest wins Utah can have and still reach the conference championship game?"); ok(h5 && h5.tool === "team_path" && h5.params.focus === "min_record", "fewest wins -> team_path min_record");
  console.log("phase4 tests: " + pass + " passed, " + fails.length + " failed"); fails.forEach(f => console.log("  FAIL " + f)); process.exit(fails.length ? 1 : 0);
})();
