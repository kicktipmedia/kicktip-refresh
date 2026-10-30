#!/usr/bin/env node
/* Lane P4 builder for data/tb/ccg-paths.json: per team, what each own-win total (0..games left) means for reaching the conference championship game, plus the fewest wins that keeps a path,
 * the own games it cannot lose, and one proven sufficient set of outside results for the wins-out case. Built on lane B's alive_core.js (every leaf is judged by the shipped rules engine KTCcg).
 *   node build_ccg_paths.js --root <tree with assets/ccgsim.js + data/ccg-sim.json + data/ccg-rules.json> --alive <ccg-alive.json> --out <file> [--check]
 * Letters per (team, k own wins in its remaining conference games), proven only by an exhausted search (never by a capped one):
 *   A reaches the game under every result of the other games (search for a counter-example exhausted: none)   H reaches it only if the other results help (a result that gets it in under every
 *   unresolved tie step exists, and another result leaves it out)   T reaches it only if a tie step the tool cannot read goes its way (some result leaves it in on one reading, none on every reading)
 *   N does not reach it under any result (exhausted)   P a result that gets it in exists but whether it needs help is not worked out (capped)   U not worked out (capped, nothing found).
 * Deterministic: seeded sampling, leaf/node caps (no wall-clock decisions). Nothing here is shipped. */
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const core = require("../../conf_race_alive/tools/alive_core.js");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const ROOT = path.resolve(arg("root") || "."), _r = arg("root"), ALIVE = arg("alive"), OUT = arg("out"), ONLY = arg("conf");
if (!_r || !ALIVE || !OUT) { console.error("usage: see header"); process.exit(2); }
const read = f => fs.readFileSync(path.join(ROOT, f), "utf8"), sha = s => crypto.createHash("sha256").update(s).digest("hex").slice(0, 16);
const CAP = { leafCap: 8000, nodeCap: 400000 }, SAMPLES = 60, MAXHELP = 5;

/* constrained search: own wins exactly k (k = null: free), `fixed` = {gameIndex: bit}. mode any | all | notAll as in alive_core.dfs. */
function dfsK(ctx, x, mode, o) {
  const N = ctx.games.length, k = o.k === undefined ? null : o.k, fixed = o.fixed || {};
  const st = { W: ctx.W0.slice(), left: ctx.L0.slice() }, bits = new Array(N).fill(0);
  const isOwn = g => g.h === x || g.a === x;
  const rank = g => (isOwn(g) ? 0 : (ctx.pool[x].indexOf(g.h) >= 0 || ctx.pool[x].indexOf(g.a) >= 0 ? 1 : 2));
  const order = ctx.games.map((g, i) => i).sort((p, q) => rank(ctx.games[p]) - rank(ctx.games[q]) || ctx.games[p].wk - ctx.games[q].wk || p - q);
  const ownLeft0 = ctx.games.filter(isOwn).length;
  let leaves = 0, nodes = 0, capped = false, tooMany = false, found = null, ownWins = 0, ownLeft = ownLeft0;
  const wantIn = mode !== "notAll";
  const prune = () => wantIn ? core.deadX(ctx, st, x) : core.certainX(ctx, st, x);
  function rec(d) {
    if (found || capped) return;
    if (++nodes > o.nodeCap) { capped = true; return; }
    if (prune()) return;
    if (d === N) {
      if (++leaves > o.leafCap) { capped = true; return; }
      const j = core.judge(ctx, bits);
      if (j.tooMany) { tooMany = true; return; }
      if (mode === "any" ? j.any[x] : mode === "all" ? j.all[x] : !j.all[x]) found = bits.slice();
      return;
    }
    const gi = order[d], g = ctx.games[gi], own = isOwn(g);
    let vals;
    if (fixed[gi] !== undefined) vals = [fixed[gi]];
    else if (own) { const win = g.h === x ? 1 : 0; vals = wantIn ? [win, 1 - win] : [1 - win, win]; }
    else { const ph = st.W[g.h] / Math.max(1, ctx.fin[g.h]), pa = st.W[g.a] / Math.max(1, ctx.fin[g.a]), f = (wantIn ? ph <= pa : ph >= pa) ? 1 : 0; vals = [f, 1 - f]; }
    for (const v of vals) {
      const wn = v ? g.h : g.a; let dw = 0;
      if (own) { dw = (wn === x) ? 1 : 0; if (k !== null) { const nw = ownWins + dw, nl = ownLeft - 1; if (nw > k || nw + nl < k) continue; } }
      bits[gi] = v; st.W[wn]++; st.left[g.h]--; st.left[g.a]--; if (own) { ownWins += dw; ownLeft--; }
      rec(d + 1);
      st.W[wn]--; st.left[g.h]++; st.left[g.a]++; if (own) { ownWins -= dw; ownLeft++; }
      if (found || capped) return;
    }
  }
  rec(0);
  return { found, exhausted: !found && !capped && !tooMany, capped: capped || tooMany };
}
const R = o => dfsK.bind(null, o.ctx);

function buildConf(code, conf, Rules, alive) {
  const ctx = core.makeCtx(require(path.join(ROOT, "assets/ccgsim.js")), Rules, conf, {}), n = ctx.n, N = ctx.games.length;
  const slugOf = i => conf.teams[i].slug, teams = {};
  const rnd = core.mulberry(777 + code.length * 31 + N);
  for (let x = 0; x < n; x++) {
    const own = []; ctx.games.forEach((g, i) => { if (g.h === x || g.a === x) own.push(i); });
    const L = own.length, row = alive.teams.filter(r => r.s === slugOf(x))[0];
    if (!row) throw new Error("no ccg-alive row for " + slugOf(x));
    let tab = "", firstBits = null;
    const hit = {};      // per k: {any, all, notAll} witnesses from sampling
    for (let k = 0; k <= L; k++) {
      let anyW = null, allW = null, notAllW = null;
      if (row.st !== "out") {
        for (let s = 0; s < SAMPLES && !(allW && notAllW); s++) {
          const bits = new Array(N); for (let i = 0; i < N; i++) bits[i] = rnd() < 0.5 ? 1 : 0;
          const idx = own.slice(); for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = idx[i]; idx[i] = idx[j]; idx[j] = t; }
          idx.forEach((gi, p) => { const g = ctx.games[gi], win = g.h === x ? 1 : 0; bits[gi] = p < k ? win : 1 - win; });
          const j = core.judge(ctx, bits); if (j.tooMany) continue;
          if (j.any[x] && !anyW) anyW = bits;
          if (j.all[x] && !allW) allW = bits;
          if (!j.all[x] && !notAllW) notAllW = bits;
        }
      }
      let ch;
      if (row.st === "out") ch = "N";
      else {
        if (!anyW) { const d = dfsK(ctx, x, "any", Object.assign({ k }, CAP)); if (d.found) { anyW = d.found; } else ch = d.exhausted ? "N" : "U"; }
        if (!ch) {
          if (allW) {
            if (notAllW) ch = "H"; else { const d = dfsK(ctx, x, "notAll", Object.assign({ k }, CAP)); ch = d.found ? "H" : (d.exhausted ? "A" : "P"); }
          } else { const d = dfsK(ctx, x, "all", Object.assign({ k }, CAP)); ch = d.found ? "H" : (d.exhausted ? "T" : "P"); if (d.found) allW = d.found; }
        }
      }
      if (ch === "H" && k === L) hit.wins = allW;
      tab += ch;
    }
    let minw = null; for (let k = 0; k <= L; k++) { if (tab[k] === "N") continue; if ("AHTP".indexOf(tab[k]) >= 0) minw = k; break; }
    /* games it cannot lose: counting proof (must win out), else one exhausted search per own game */
    const must = [];
    if (minw !== null && minw === L && L > 0) own.forEach(gi => must.push(ctx.games[gi].id));
    else if (minw !== null && L > 0 && L <= 8 && row.st !== "out") {
      own.forEach(gi => { const g = ctx.games[gi], d = dfsK(ctx, x, "any", Object.assign({ fixed: { [gi]: g.h === x ? 0 : 1 } }, CAP)); if (d.exhausted) must.push(g.id); });
    }
    /* one proven sufficient set of other results for "wins out" when that case is H */
    let help = null;
    if (L > 0 && tab[L] === "H" && hit.wins) {
      const fixed = {}; ctx.games.forEach((g, gi) => { fixed[gi] = hit.wins[gi]; });
      const outside = ctx.games.map((g, gi) => gi).filter(gi => own.indexOf(gi) < 0);
      /* free the games that do not touch the team's own race first: far from X in the pool, then the rest by week */
      outside.sort((a, b) => { const ga = ctx.games[a], gb = ctx.games[b], ra = (ctx.pool[x].indexOf(ga.h) >= 0 ? 0 : 1) + (ctx.pool[x].indexOf(ga.a) >= 0 ? 0 : 1), rb = (ctx.pool[x].indexOf(gb.h) >= 0 ? 0 : 1) + (ctx.pool[x].indexOf(gb.a) >= 0 ? 0 : 1); return rb - ra || ga.wk - gb.wk || a - b; });
      outside.forEach(gi => { const keep = fixed[gi]; delete fixed[gi]; const d = dfsK(ctx, x, "notAll", Object.assign({ fixed }, CAP)); if (!(d.exhausted && !d.found)) fixed[gi] = keep; });
      const left = outside.filter(gi => fixed[gi] !== undefined);
      if (left.length > 0 && left.length <= MAXHELP) help = left.map(gi => { const g = ctx.games[gi]; return [g.id, slugOf(fixed[gi] ? g.h : g.a)]; });
    }
    teams[slugOf(x)] = { o: own.map(gi => ctx.games[gi].id), t: tab, m: minw, k: must, h: help, e: /[UP]/.test(tab) ? 0 : 1 };
    /* consistency with ccg-alive: out = all N; in = some path */
    if (row.st === "out" && !/^N+$/.test(tab)) throw new Error(code + " " + slugOf(x) + ": alive says out, tab " + tab);
    if (row.st === "in" && /^N*$/.test(tab) && tab.indexOf("U") < 0) throw new Error(code + " " + slugOf(x) + ": alive says in, tab " + tab);
    if (row.st === "in" && L === 0 && tab !== "N" && !/[AHTP]/.test(tab)) throw new Error(code + " " + slugOf(x) + ": alive in, no letters " + tab);
  }
  return teams;
}

const S = JSON.parse(read("data/ccg-sim.json")), RJ = JSON.parse(read("data/ccg-rules.json")), AL = JSON.parse(fs.readFileSync(ALIVE, "utf8"));
const out = { v: 1, asof: AL.asof, doc: "Lane P4 ccg-paths. Per conference, per team slug: o = own remaining conference game ids, t = one letter per own-win total 0..len(o) (A reaches the game under every result; H only if other results help; T only if an unreadable tie step goes its way; N does not reach it; P a path exists, whether it needs help is not worked out; U not worked out), m = fewest wins that keeps a path (null if not proven), k = own games it cannot lose, h = a set of other results that gets it in if it wins out (null if none shown), e = 1 when no letter is P or U.", rules: {}, confs: {} };
const codes = ONLY ? [ONLY] : Object.keys(AL.confs);
const t0 = Date.now();
codes.forEach(code => {
  const t1 = Date.now(), tm = buildConf(code, S.confs[code], RJ.rules[code], AL.confs[code]);
  out.confs[code] = tm; out.rules[code] = AL.confs[code].rules.hash;
  const cnt = {}; Object.keys(tm).forEach(s => tm[s].t.split("").forEach(c => { cnt[c] = (cnt[c] || 0) + 1; }));
  console.log(code.padEnd(9), JSON.stringify(cnt), (Date.now() - t1) + " ms");
});
fs.writeFileSync(OUT, JSON.stringify(out));
console.log("wrote " + OUT + " " + fs.statSync(OUT).size + " bytes, " + (Date.now() - t0) + " ms");
