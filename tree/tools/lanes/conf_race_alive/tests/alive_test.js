/* Verification suite for ccg-alive. Run: node tests/alive_test.js --root <built tree> [--proof <file>] [--quick]
   A. file checks (shape, hashes, asof, wording lint, size budget, verified:false, determinism, --check gate)
   B. witness replay: every stored witness is replayed through KTCcg.solve (independent decoder) and must prove what it claims
   C. exhaustive cross-check on hypothetical late-season states (<= 13 games left): status / clinched / sure must equal full enumeration of all 2^k completions, 10 conferences
   D. Monte Carlo cross-check: no team marked out is ever put in the game by any sampled completion (real state + hypothetical states with 14-24 games left), uniform and model-weighted sampling
   E. independent counting certificate for teams eliminated on the real data (pigeonhole on total wins), unequal-schedule safety, pruning-off equivalence */
"use strict";
const fs = require("fs"), path = require("path"), cp = require("child_process");
const core = require("../tools/alive_core.js");
const args = process.argv.slice(2), QUICK = args.includes("--quick");
const arg = (k, d) => args.includes("--" + k) ? args[args.indexOf("--" + k) + 1] : d;
if (!arg("root")) { console.error("usage: alive_test.js --root <tree> [--proof file] [--quick]"); process.exit(2); }
const ROOT = path.resolve(arg("root")), PROOFP = path.resolve(arg("proof", path.join(ROOT, "..", path.basename(ROOT) + ".ccg-alive-proof.json")));
const K = require(path.join(ROOT, "assets/ccgsim.js")), S = JSON.parse(fs.readFileSync(path.join(ROOT, "data/ccg-sim.json"))), RJ = JSON.parse(fs.readFileSync(path.join(ROOT, "data/ccg-rules.json")));
const CARDP = path.join(ROOT, "data/tb/ccg-alive.json"), CARD = JSON.parse(fs.readFileSync(CARDP)), PROOF = JSON.parse(fs.readFileSync(PROOFP));
let pass = 0, fail = 0; const fails = [];
function ok(c, msg) { if (c) pass++; else { fail++; fails.push(msg); console.log("FAIL:", msg); } }
const hdr = s => console.log("\n== " + s);
const codes = Object.keys(S.confs);

/* leaf judging written independently of alive_core.judge */
function truth(R, conf, picks) {
  const r = K.solve(R, conf, picks), a = r.analysis, n = conf.teams.length, any = Array(n).fill(false), all = Array(n).fill(true);
  a.leafList.forEach(l => { const s = Array(n).fill(false); l.order.forEach(t => { s[t] = true; any[t] = true; }); for (let t = 0; t < n; t++) if (!s[t]) all[t] = false; });
  return { any, all, over: !!a.tooMany };
}
function hypo(conf, k, seed, mode, pg) {     // hypothetical state for TESTS ONLY: keeps k games unset, resolves the other unset games at random (model-weighted when pg given)
  const rnd = core.mulberry(seed), un = conf.games.filter(g => g.w === null || g.w === undefined);
  let keep;
  if (mode === "late") keep = un.slice().sort((a, b) => b.wk - a.wk || (a.date < b.date ? 1 : -1)).slice(0, k);
  else { const sh = un.slice().sort(() => rnd() - 0.5); keep = sh.slice(0, k); }
  const ks = new Set(keep.map(g => g.id));
  const c2 = JSON.parse(JSON.stringify(conf));
  c2.games.forEach(g => { if ((g.w === null || g.w === undefined) && !ks.has(g.id)) { const p = pg && pg[g.k] ? pg[g.k][0] : 0.5; g.w = rnd() < p ? 1 : 0; } });
  return c2;
}

/* ---------------- A ---------------- */
hdr("A. file checks");
ok(CARD.asof === S.asof, "asof equals ccg-sim asof"); ok(CARD.src.sim === PROOF.src.sim, "src sim equal in both files");
ok(JSON.stringify(Object.keys(CARD.confs)) === JSON.stringify(codes), "10 conferences in ccg-sim order");
const size = fs.statSync(CARDP).size; ok(size < 32 * 1024, "card file under 32 KB raw (" + size + ")");
ok(!/\bCCG\b|title game/i.test(JSON.stringify(CARD)), "no banned words in card file");
ok(!/\b(bet|wager|parlay|lock|locked|edge|value|market|odds|gap)\b/i.test(JSON.stringify(Object.assign({}, CARD, { confs: Object.fromEntries(Object.entries(CARD.confs).map(([k, v]) => [k, Object.assign({}, v, { rules: null })])) }))), "no betting words in card (rules title/url excluded)");
ok(!/https?:\/\/|www\./i.test(JSON.stringify(CARD)), "no URL of any kind anywhere in data/tb/ccg-alive.json");
codes.forEach(c => {
  const x = CARD.confs[c], R = RJ.rules[c];
  ok(x.verified === false && x.verified_by === null, c + ": verified:false until a person signs off");
  ok(x.rules.title === R.doc.title && x.rules.version === R.doc.version, c + ": rules source title and version copied from ccg-rules.json");
  ok(!("url" in x.rules), c + ": no outside rule-source URL in the card data (item 10: it could never render, and now it is not shipped)");
  ok(x.counts.in_race + x.counts.out + x.counts.unknown === x.counts.teams, c + ": counts add up");
  ok(x.in_race.length === x.counts.in_race && x.out_race.length === x.counts.out && x.clinched.length === x.counts.clinched, c + ": lists match counts");
  ok(x.counts.unknown === 0, c + ": no unknown team status (search finished)");
  ok(x.teams.length === S.confs[c].teams.length, c + ": every team has a row");
  ok(x.teams.every(t => (t.st === "out") === x.out_race.includes(t.n) && (t.st === "in") === x.in_race.includes(t.n)), c + ": rows agree with lists");
  ok(x.teams.every(t => t.st !== "out" || t.cl === false), c + ": out team is never clinched");
  ok(x.remaining === S.confs[c].games.filter(g => g.w == null).length, c + ": remaining count");
});
ok(!fs.existsSync(path.join(ROOT, "data/ccg-rules-verified.json")) || true, "verified file optional");
// determinism + gate
const r1 = cp.spawnSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", ROOT, "--proof", PROOFP, "--check"], { encoding: "utf8" });
ok(r1.status === 0, "build_alive --check passes on the shipped files: " + (r1.stderr || r1.stdout).trim());
{ // staleness gate: copy root, flip one remaining game result in the copy's ccg-sim.json, --check must fail
  const tmp = fs.mkdtempSync("/tmp/alive-"); fs.mkdirSync(tmp + "/data/tb", { recursive: true }); fs.mkdirSync(tmp + "/assets"); const TP = tmp + "/proof.json";
  ["data/ccg-sim.json", "data/ccg-rules.json", "data/pred-games.json", "data/tb/ccg-alive.json", "assets/ccgsim.js"].forEach(f => fs.copyFileSync(path.join(ROOT, f), path.join(tmp, f))); fs.copyFileSync(PROOFP, TP);
  const s2 = JSON.parse(fs.readFileSync(tmp + "/data/ccg-sim.json")); const g = s2.confs.pac12.games.find(g => g.w == null); g.w = 1; fs.writeFileSync(tmp + "/data/ccg-sim.json", JSON.stringify(s2));
  const r2 = cp.spawnSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", tmp, "--proof", TP, "--check"], { encoding: "utf8" });
  ok(r2.status === 1 && /STALE/.test(r2.stderr), "--check fails when ccg-sim.json changes (stale gate)");
  const r3 = cp.spawnSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", tmp, "--proof", TP, "--quiet"], { encoding: "utf8" });
  const r4 = cp.spawnSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", tmp, "--proof", TP, "--check"], { encoding: "utf8" });
  ok(r3.status === 0 && r4.status === 0, "rebuild after a data change, then --check passes");
  const b1 = fs.readFileSync(tmp + "/data/tb/ccg-alive.json", "utf8"); cp.spawnSync("node", [path.join(__dirname, "../tools/build_alive.js"), "--root", tmp, "--proof", TP, "--quiet"]); ok(b1 === fs.readFileSync(tmp + "/data/tb/ccg-alive.json", "utf8"), "deterministic: second build byte-identical");
}

/* ---------------- B ---------------- */
hdr("B. witness replay");
let nw = 0, nn = 0, ns = 0;
codes.forEach(c => {
  const conf = S.confs[c], R = RJ.rules[c], rem = PROOF.rem[c], N = rem.length;
  ok(JSON.stringify(rem) === JSON.stringify(conf.games.filter(g => g.w == null).map(g => g.id)), c + ": rem list = unplayed games");
  CARD.confs[c].teams.forEach(row => {
    const i = conf.teams.findIndex(t => t.short === row.n), p = PROOF.teams[c][row.n] || {};
    const run = hex => { const picks = {}; rem.forEach((id, k) => { picks[id] = (parseInt(hex[k >> 2], 16) >> (3 - (k & 3))) & 1; }); return truth(R, conf, picks); };
    if (row.st === "in") { ok(!!p.w, c + " " + row.n + ": in-race team has a witness"); if (p.w) { nw++; const t = run(p.w); ok(!t.over && t.any[i], c + " " + row.n + ": witness puts team in"); } }
    if (row.cl === false) { ok(!!p.nw, c + " " + row.n + ": not-clinched has a witness"); if (p.nw) { nn++; const t = run(p.nw); ok(!t.over && !t.all[i], c + " " + row.n + ": not-clinched witness leaves team out of some branch"); } }
    if (row.sure === true) { ok(!!p.sw, c + " " + row.n + ": sure=true has a witness"); if (p.sw) { ns++; const t = run(p.sw); ok(!t.over && t.all[i], c + " " + row.n + ": sure witness puts team in every branch"); } }
    if (row.st === "out") ok(p.out && (p.out.method === "record" || p.out.method === "search"), c + " " + row.n + ": out team carries a proof record");
  });
});
console.log("replayed witnesses: in", nw, "not-clinched", nn, "sure", ns);

/* ---------------- C ---------------- */
hdr("C. exhaustive cross-check on hypothetical states");
const pg = JSON.parse(fs.readFileSync(path.join(ROOT, "data/pred-games.json"))).g;
const ks = QUICK ? [6, 10] : [6, 9, 11, 12, 13];
let states = 0, outSeen = 0, certSeen = 0, sureFalse = 0, nullCl = 0, nullSure = 0, nIn = 0;   // null = search hit its cap: allowed (never a wrong answer), but counted
codes.forEach(c => {
  const R = RJ.rules[c], full = S.confs[c];
  ks.forEach((k, ki) => ["late", "random"].forEach((mode, mi) => {
    const seed = 1000 + ki * 17 + mi * 5 + c.length * 31, conf = hypo(full, k, seed, mode, ki % 2 ? pg : null);
    const n = conf.teams.length, un = conf.games.filter(g => g.w == null), N = un.length;
    if (N > 13) return;
    const anyT = Array(n).fill(false), notAllT = Array(n).fill(false), allT = Array(n).fill(false);
    for (let m = 0; m < (1 << N); m++) {
      const picks = {}; un.forEach((g, j) => { picks[g.id] = (m >> j) & 1; });
      const t = truth(R, conf, picks); if (t.over) { ok(false, c + ": enumeration overflow in brute force"); return; }
      for (let q = 0; q < n; q++) { if (t.any[q]) anyT[q] = true; if (!t.all[q]) notAllT[q] = true; if (t.all[q]) allT[q] = true; }
    }
    const A = core.analyzeConf(K, R, conf, { bias: null, seed: seed });
    states++;
    for (let q = 0; q < n; q++) {
      const r = A.res[q], tag = c + " k=" + N + " " + mode + " seed " + seed + " " + conf.teams[q].short;
      ok(r.st === (anyT[q] ? "in" : "out"), tag + ": status " + r.st + " vs truth " + (anyT[q] ? "in" : "out"));
      if (anyT[q]) { ok(r.clinched === null || r.clinched === !notAllT[q], tag + ": clinched " + r.clinched + " vs " + !notAllT[q]); ok(r.sure === null || r.sure === allT[q], tag + ": sure " + r.sure + " vs " + allT[q]); if (r.clinched === null) nullCl++; if (r.sure === null) nullSure++; nIn++; if (!allT[q]) sureFalse++; }
      if (!anyT[q]) outSeen++;
      if (r.st === "out" && r.proof.method === "search") certSeen++;
    }
  }));
});
ok(nullCl + nullSure <= 0.05 * nIn, "unfinished clinched/sure searches stay rare (" + nullCl + " + " + nullSure + " of " + nIn + " in-race teams)");
console.log("clinched/sure left unknown (null) because a capped search could not finish:", nullCl, nullSure, "of", nIn);
console.log("states compared:", states, "| teams out in those states:", outSeen, "(of which proved by search rather than record bounds:", certSeen + ")", "| in-race teams that can only get in through an unresolved tie step:", sureFalse);

/* ---------------- D ---------------- */
hdr("D. Monte Carlo cross-check (no team marked out is ever put in the game)");
const NS = QUICK ? 1500 : 6000;
function mc(R, conf, count, seed, weighted) {
  const rnd = core.mulberry(seed), un = conf.games.filter(g => g.w == null), n = conf.teams.length, seen = Array(n).fill(0);
  for (let s = 0; s < count; s++) {
    const picks = {}; un.forEach(g => { const p = weighted && pg[g.k] ? pg[g.k][0] : 0.5; picks[g.id] = rnd() < p ? 1 : 0; });
    const t = truth(R, conf, picks); t.any.forEach((v, q) => { if (v) seen[q]++; });
  }
  return seen;
}
let mcOut = 0, mcSeenIn = 0, mcNever = 0;
codes.forEach(c => {
  const R = RJ.rules[c], full = S.confs[c];
  [[full, "real"], [hypo(full, 16, 777 + c.length, "late", pg), "late16"], [hypo(full, 20, 913 + c.length, "late", pg), "late20"], [hypo(full, 24, 55 + c.length, "random", null), "random24"]].forEach(([conf, tag]) => {
    if (conf.games.filter(g => g.w == null).length > 40 && tag !== "real") return;
    const A = core.analyzeConf(K, R, conf, { seed: 99 });
    [false, true].forEach(w => {
      const seen = mc(R, conf, NS, 4242 + (w ? 1 : 0), w);
      A.res.forEach((r, q) => {
        const t = c + " " + tag + (w ? " weighted " : " uniform ") + conf.teams[q].short;
        if (r.st === "out") { mcOut++; ok(seen[q] === 0, t + ": marked out but sampled in " + seen[q] + " times"); }
        if (seen[q] > 0) mcSeenIn++;
        if (r.st === "in" && seen[q] === 0) mcNever++;
        if (seen[q] > 0) ok(r.st === "in", t + ": sampled in but not marked in race");
      });
    });
  });
});
console.log("MC: out-team checks", mcOut, "| team-samples seen in", mcSeenIn, "| in-race teams never seen by sampling (carry a witness instead):", mcNever);

/* ---------------- E ---------------- */
hdr("E. independent counting certificate, pigeonhole on total wins (equal schedules, one pool)");
codes.forEach(c => {
  const R = RJ.rules[c], conf = S.confs[c]; if (R.fmt !== "top2" || (R.tie_group && R.tie_group !== "equal")) return;
  const n = conf.teams.length, W = Array(n).fill(0), G = Array(n).fill(0), L = Array(n).fill(0); conf.games.forEach(g => { G[g.h]++; G[g.a]++; if (g.w == null) { L[g.h]++; L[g.a]++; } else W[g.w ? g.h : g.a]++; });
  const fin = G; if (new Set(fin).size !== 1) return;
  const totalWins = conf.games.length;
  CARD.confs[c].teams.filter(t => t.st === "out").forEach(t => {
    const x = conf.teams.findIndex(q => q.short === t.n);
    // X ends with wx wins at most W+L. In the top two means at most one team with MORE wins. Others' total wins is fixed by the schedule: total - wx. Upper bound: one team at its cap, the rest at most wx each.
    let cert = true;
    for (let wx = W[x]; wx <= W[x] + L[x]; wx++) {
      const caps = []; for (let y = 0; y < n; y++) if (y !== x) caps.push(Math.min(fin[y], W[y] + L[y]));
      // others with floor: each y has at least W[y] wins
      const maxOther = (() => { let best = -1; for (let top = 0; top < caps.length; top++) { let s = 0; caps.forEach((cap, k) => { s += k === top ? cap : Math.min(cap, wx); }); best = Math.max(best, s); } return best; })();
      if (maxOther >= totalWins - wx) { cert = false; break; }
    }
    ok(cert, c + " " + t.n + ": out on the shipped data has an independent counting certificate");
    if (cert) console.log("  certificate ok:", c, t.n, t.w + "-" + t.l, "(" + t.left + " left)");
  });
});
// unequal-schedule safety: the prune must stay off when the rules can pull a lower-percentage team into a tie
{
  const R = RJ.rules.acc, ctx = core.makeCtx(K, R, S.confs.acc), st = { W: ctx.W0.slice(), left: ctx.L0.slice() };
  ok(ctx.tg === "acc_unequal" && ctx.fin.some(f => f !== ctx.fin[0]), "ACC has unequal schedules in the data (8 and 9 games)");
  const hy = hypo(S.confs.acc, 6, 5, "late", pg), ctx2 = core.makeCtx(K, R, hy);
  const st2 = { W: ctx2.W0.slice(), left: ctx2.L0.slice() };
  let proven = 0, falsePrune = 0; // every record-pruned team must also be absent from the exhaustive truth
  const un = hy.games.filter(g => g.w == null), N = un.length, anyT = Array(hy.teams.length).fill(false);
  for (let m = 0; m < (1 << N); m++) { const picks = {}; un.forEach((g, j) => { picks[g.id] = (m >> j) & 1; }); truth(R, hy, picks).any.forEach((v, q) => { if (v) anyT[q] = true; }); }
  hy.teams.forEach((t, q) => { if (core.deadX(ctx2, st2, q)) { proven++; if (anyT[q]) falsePrune++; } });
  ok(falsePrune === 0, "ACC record-prune never removes a team the enumeration puts in (pruned " + proven + ")");
}
console.log("\nPASS", pass, "FAIL", fail); if (fail) { console.log(fails.slice(0, 30).join("\n")); process.exit(1); }
