// Diff the JS engine against the step 2 reference engine's 125 fills (/workspace/kicktip-sim-step2/conformance_step2.json copy: tests/data/conformance_step2.json).
// For every case: status (resolved / unresolved), the set of pairings (host first when hosted), and, per pairing, the set of "ways" (ranking/draw/immunity/reading facts).
const fs = require("fs"), K = require("../src/assets/ccgsim.js"), root = __dirname + "/..";
const RULES = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules, C = JSON.parse(fs.readFileSync(root + "/tests/data/conformance_step2.json")).cases;
let bad = 0, checks = 0;
const norm = (conds) => conds.map(c => { const pk = Array.isArray(c[1]) ? c[1] : c.picked, td = Array.isArray(c[2]) ? c[2] : c.tied; return pk.map(String).sort().join("+") + "/" + td.map(String).sort().join("+"); }).sort().join(";");
C.forEach((c, n) => {
  const R = RULES[c.conf], names = c.names, games = []; let id = 1;
  c.H.forEach((row, i) => row.forEach((w, j) => { for (let q = 0; q < w; q++) games.push({ id: id++, h: i, a: j, w: 1, wk: 1, date: "", neu: false, k: "" }); }));
  const conf = { teams: names.map((x, i) => ({ i, name: x, short: x })), div: c.div ? c.div.map(String) : null, games, nc: [] };
  let res;
  try { res = K.solve(R, conf, {}); } catch (e) { bad++; console.log("CRASH", n, c.conf, e.message); return; }
  const a = res.analysis, hosted = a.hostMatters;
  const mine = {}; a.leafList.forEach(l => { const k = hosted ? l.order.join(",") : l.order.slice().sort((x, y) => x - y).join(","); (mine[k] = mine[k] || new Set()).add(norm(l.conds)); });
  const ref = {}; c.branches.forEach(b => { const k = hosted ? b.ccg.join(",") : b.ccg.slice().sort((x, y) => x - y).join(","); ref[k] = ref[k] || new Set(); b.ways.forEach(w => ref[k].add(norm(w.conds))); });
  const st = Object.keys(mine).length === 1 ? "resolved" : "unresolved";
  const probs = [];
  checks++; if (st !== c.status) probs.push("status " + st + " vs " + c.status);
  checks++; if (Object.keys(mine).sort().join("|") !== Object.keys(ref).sort().join("|")) probs.push("pairings mine=" + Object.keys(mine).sort().join("|") + " ref=" + Object.keys(ref).sort().join("|"));
  else Object.keys(ref).forEach(k => { checks++; const A = [...mine[k]].sort().join("|"), B = [...ref[k]].sort().join("|"); if (A !== B) probs.push("ways for " + k + ": mine " + A + " ref " + B); });
  if (probs.length) { bad++; console.log("DIFF case", n, c.conf, probs.join(" ; ").slice(0, 600)); }
});
console.log("ccg conformance step 2: " + C.length + " cases, " + checks + " checks, " + bad + " cases differ"); process.exit(bad ? 1 : 0);
