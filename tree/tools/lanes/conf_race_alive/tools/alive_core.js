/* KickTip "who is still in the race" search core (Node). Pure functions on top of the live rules engine assets/ccgsim.js (KTCcg); nothing is reimplemented
   about tiebreakers: every leaf of the search is judged by KTCcg.solve() (all branches of steps the tool cannot compute are kept).
   Exact method and limits: see NOTES.md. Deterministic: seeded RNG, node caps (no wall-clock decisions). */
"use strict";
const EPS = 1e-9;

function mulberry(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

/* Context for one conference + its rules. K = KTCcg. */
function makeCtx(K, R, conf, opts) {
  opts = opts || {};
  const base = K.build(conf, {});
  const n = base.n;
  const unset = conf.games.filter(g => g.w === null || g.w === undefined);
  const div = R.fmt === "div" ? base.div : null;
  const ctx = {
    K, R, conf, n, base, unset, div, names: base.names,
    W0: base.W.slice(), G0: base.G.slice(), L0: base.left.slice(),
    fin: base.G.map((g, i) => g + base.left[i]),
    slots: R.fmt === "div" ? 1 : 2,
    tg: R.tie_group || "equal",
    leafCap: opts.leafCap || 200000, nodeCap: opts.nodeCap || 4000000,
    small: { leafCap: opts.smallLeafCap || 4000, nodeCap: opts.smallNodeCap || 120000 },   // clinched / "sure" searches: bounded, an unfinished one is reported as unknown (null), never guessed
    stats: { leaves: 0, nodes: 0, tooMany: 0 },
    wit: { any: new Array(n).fill(null), notAll: new Array(n).fill(null), all: new Array(n).fill(null) },   // best-known witnesses per team (bit arrays over `unset`)
    games: unset
  };
  ctx.idx = {}; unset.forEach((g, i) => { ctx.idx[g.id] = i; });
  ctx.pool = []; for (let x = 0; x < n; x++) ctx.pool.push(div ? Array.from({ length: n }, (_, y) => y).filter(y => div[y] === div[x]) : Array.from({ length: n }, (_, y) => y));
  return ctx;
}

/* ---- sound record-only bounds (see NOTES.md section 3). state = {W, left}. fin[] (final conference games) is fixed. ---- */
function minP(ctx, st, y) { return ctx.fin[y] > 0 ? st.W[y] / ctx.fin[y] : 0; }
function maxP(ctx, st, y) { return ctx.fin[y] > 0 ? (st.W[y] + st.left[y]) / ctx.fin[y] : 0; }
/* Can X, at the end, be pulled into a tie tier with a lead team j that played a different number of games (ACC / Conference USA rules)? Conservative. */
function extPossible(ctx, st, x, M) {
  if (ctx.tg === "equal") return false;
  for (let j = 0; j < ctx.n; j++) {
    if (j === x || ctx.fin[j] === ctx.fin[x]) continue;
    if (ctx.div && ctx.div[j] !== ctx.div[x]) continue;
    for (let wx = st.W[x]; wx <= st.W[x] + st.left[x]; wx++) for (let wj = st.W[j]; wj <= st.W[j] + st.left[j]; wj++) {
      if (wj / ctx.fin[j] < M - EPS) continue;       // j must be able to be a lead team (pct >= second-best guaranteed pct)
      const lx = ctx.fin[x] - wx, lj = ctx.fin[j] - wj;
      if (ctx.tg === "acc_unequal" ? (wx === wj || lx === lj) : (lx === lj && wj - wx === 1)) return true;
    }
  }
  return false;
}
/* X is provably out: at least `slots` rivals (same division in a division format) finish strictly ahead of X in every outcome, and no unequal-schedule tie rule can pull X back in. */
function deadX(ctx, st, x, who) {
  const pool = ctx.pool[x], mx = maxP(ctx, st, x); let ahead = 0, ms = [];
  for (let k = 0; k < pool.length; k++) { const y = pool[k]; if (y === x) continue; const m = minP(ctx, st, y); if (m > mx + EPS) { ahead++; ms.push(y); } }
  if (ahead < ctx.slots) return false;
  if (ctx.tg !== "equal") {
    const mins = pool.filter(y => y !== x).map(y => minP(ctx, st, y)).sort((a, b) => b - a), M = mins[ctx.slots - 1];
    if (extPossible(ctx, st, x, M)) return false;
  }
  if (who) who.push.apply(who, ms);
  return true;
}
/* X is provably in on record alone (fewer than `slots` rivals can reach X's pct); only for equal-length-tie conferences. */
function certainX(ctx, st, x) {
  if (ctx.tg !== "equal") return false;
  const pool = ctx.pool[x], mn = minP(ctx, st, x); let may = 0;
  for (let k = 0; k < pool.length; k++) { const y = pool[k]; if (y !== x && maxP(ctx, st, y) >= mn - EPS) may++; }
  return may < ctx.slots;
}

/* ---- leaf judging ---- */
function judge(ctx, bits) {    // bits[i] = 1 home wins game i. returns {inAny:Set-like array, inAll, tooMany}
  const picks = {}; for (let i = 0; i < ctx.games.length; i++) picks[ctx.games[i].id] = bits[i];
  const r = ctx.K.solve(ctx.R, ctx.conf, picks), a = r.analysis, n = ctx.n;
  const any = new Array(n).fill(false), all = new Array(n).fill(true);
  const lv = a.leafList;
  lv.forEach(l => { const s = new Array(n).fill(false); l.order.forEach(t => { s[t] = true; any[t] = true; }); for (let t = 0; t < n; t++) if (!s[t]) all[t] = false; });
  ctx.stats.leaves++;
  if (a.tooMany) ctx.stats.tooMany++;
  return { any, all, tooMany: !!a.tooMany, leaves: lv.length, pairKnown: a.pairKnown };
}
function record(ctx, bits, j) {      // store witnesses for every team this completion proves something about
  if (j.tooMany) return;           // an incomplete branch list proves nothing
  let b = null;
  for (let t = 0; t < ctx.n; t++) {
    if (j.any[t] && !ctx.wit.any[t]) ctx.wit.any[t] = b = b || bits.slice();
    if (!j.all[t] && !ctx.wit.notAll[t]) ctx.wit.notAll[t] = b = b || bits.slice();
    if (j.all[t] && !ctx.wit.all[t]) ctx.wit.all[t] = b = b || bits.slice();
  }
}

/* ---- random sampling phase (cheap witnesses for most teams) ---- */
function sample(ctx, count, seed, bias) {
  const rnd = mulberry(seed), N = ctx.games.length;
  const pw = bias || null;                // optional per-game home-win probability
  for (let c = 0; c < count; c++) {
    const bits = new Array(N);
    for (let i = 0; i < N; i++) bits[i] = rnd() < (pw ? pw[i] : 0.5) ? 1 : 0;
    record(ctx, bits, judge(ctx, bits));
  }
}

/* ---- targeted exhaustive/pruned DFS. mode: "any" (find completion where X can be in), "all" (X in under every branch), "notAll" (X missing from some branch).
   Returns {found:bits|null, exhausted:bool, capped:bool, leaves, nodes}. exhausted && !found == proof that no completion exists (sound prune only). ---- */
function dfs(ctx, x, mode, opts) {
  opts = opts || {};
  const N = ctx.games.length, leafCap = opts.leafCap || ctx.leafCap, nodeCap = opts.nodeCap || ctx.nodeCap;
  const st = { W: ctx.W0.slice(), left: ctx.L0.slice() }, bits = new Array(N).fill(0);
  // order: games with X first, then games between X's pool members by week
  const rank = g => ((g.h === x || g.a === x) ? 0 : (ctx.pool[x].indexOf(g.h) >= 0 || ctx.pool[x].indexOf(g.a) >= 0 ? 1 : 2));
  const order = ctx.games.map((g, i) => i).sort((p, q) => rank(ctx.games[p]) - rank(ctx.games[q]) || ctx.games[p].wk - ctx.games[q].wk || p - q);
  let leaves = 0, nodes = 0, capped = false, tooMany = false, found = null;
  const wantIn = mode !== "notAll";
  function prune() { return wantIn ? deadX(ctx, st, x) : certainX(ctx, st, x); }
  function rec(d) {
    if (found || capped) return;
    if (++nodes > nodeCap) { capped = true; return; }
    if (prune()) return;
    if (d === N) {
      if (++leaves > leafCap) { capped = true; return; }
      const j = judge(ctx, bits); record(ctx, bits, j);
      if (j.tooMany) { tooMany = true; return; }
      if (mode === "any" ? j.any[x] : mode === "all" ? j.all[x] : !j.all[x]) found = bits.slice();
      return;
    }
    const gi = order[d], g = ctx.games[gi];
    let first;
    if (g.h === x || g.a === x) first = (g.h === x) === wantIn ? 1 : 0;       // wantIn: X wins; notAll: X loses
    else { const ph = st.W[g.h] / Math.max(1, ctx.fin[g.h]), pa = st.W[g.a] / Math.max(1, ctx.fin[g.a]); first = (wantIn ? ph <= pa : ph >= pa) ? 1 : 0; }
    for (let t = 0; t < 2; t++) {
      const v = t === 0 ? first : 1 - first, wn = v ? g.h : g.a;
      bits[gi] = v; st.W[wn]++; st.left[g.h]--; st.left[g.a]--;
      rec(d + 1);
      st.W[wn]--; st.left[g.h]++; st.left[g.a]++;
      if (found || capped) return;
    }
  }
  rec(0);
  ctx.stats.nodes += nodes;
  const exhausted = !found && !capped && !tooMany;
  return { found, exhausted, capped: capped || tooMany, leaves, nodes };
}

/* ---- full analysis of one conference ---- */
function analyzeConf(K, R, conf, opts) {
  opts = opts || {};
  const ctx = makeCtx(K, R, conf, opts), n = ctx.n, N = ctx.games.length, t0 = Date.now();
  const res = ctx.names.map(() => ({ st: null, clinched: null, sure: null, out_by: null, proof: null }));
  if (N === 0) { const j = judge(ctx, []); record(ctx, [], j); }
  else {
    // cheap sampling first: fair coins, plus all-home / all-away / model-free "favorite = better current record" completions
    sample(ctx, opts.samples === undefined ? Math.min(400, 40 + N * 8) : opts.samples, opts.seed || 12345);
    if (opts.bias) sample(ctx, opts.samples === undefined ? 200 : opts.samples, (opts.seed || 12345) + 1, opts.bias);
  }
  for (let x = 0; x < n; x++) {
    const r = res[x];
    // in the race?
    if (ctx.wit.any[x]) r.st = "in";
    else {
      const who = []; if (deadX(ctx, { W: ctx.W0, left: ctx.L0 }, x, who)) { r.st = "out"; r.out_by = who; r.proof = { method: "record", leaves: 0, nodes: 0 }; }
      else {
        const d = dfs(ctx, x, "any");
        if (d.found) r.st = "in"; else if (d.exhausted) { r.st = "out"; r.proof = { method: "search", leaves: d.leaves, nodes: d.nodes }; } else { r.st = "unk"; r.proof = { method: "cap", leaves: d.leaves, nodes: d.nodes }; }
      }
    }
    if (r.st === "out") { r.clinched = false; r.sure = false; continue; }
    if (r.st === "unk") continue;
    // clinched: in under every completion and every branch. false has a witness (notAll); true needs an exhausted search for notAll
    if (ctx.wit.notAll[x]) r.clinched = false;
    else { const d = dfs(ctx, x, "notAll", ctx.small); r.clinched = d.found ? false : (d.exhausted ? true : null); if (r.clinched === true) r.cproof = { leaves: d.leaves, nodes: d.nodes }; }
    // sure: some completion puts X in whatever a ranking/coin step does ("in" on the rules the tool can read)
    if (ctx.wit.all[x]) r.sure = true;
    else { const d = dfs(ctx, x, "all", ctx.small); r.sure = d.found ? true : (d.exhausted ? false : null); }
  }
  return { ctx, res, ms: Date.now() - t0 };
}

const toHex = bits => { let s = ""; for (let i = 0; i < bits.length; i += 4) { let v = 0; for (let k = 0; k < 4; k++) v = v * 2 + (bits[i + k] || 0); s += v.toString(16); } return s; };
const fromHex = (hex, N) => { const b = []; for (let i = 0; i < N; i++) b.push((parseInt(hex[Math.floor(i / 4)], 16) >> (3 - (i % 4))) & 1); return b; };

module.exports = { makeCtx, deadX, certainX, judge, sample, dfs, analyzeConf, toHex, fromHex, mulberry, EPS };
