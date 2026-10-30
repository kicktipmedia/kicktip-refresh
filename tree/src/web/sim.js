/* KickTip season simulator (browser + Node), a port of src/sim.py + src/tiebreak.py + src/cfp.py.
 * Classic script, no inline use, no network, no eval. Browser: <script src="/js/sim.js"> -> window.KTSim. Node or a worker: require() / a classic worker script load.
 * KTSim.simulate(bundle, {seasons:2000, seed:1, forced:{gameId:1|0}, constraints:[{games:[ids], wins:n}]}) -> per-team chances (fractions 0..1).
 *   forced: 1 = home team wins, 0 = away team wins.  constraints: exactly `wins` home-or-away wins by `team` among `games` (team = team index) - see resolveConstraint.
 * Simulation analysis only (KickTip model). Model data comes from data/out/web/bundle.json (src/export_web.py). */
(function (root) {
  "use strict";

  // ---------- seeded RNG (sfc32 seeded through splitmix32) ----------
  function makeRng(seed) {
    var a = seed >>> 0;
    function sm() { a = (a + 0x9e3779b9) >>> 0; var z = a; z = Math.imul(z ^ (z >>> 16), 0x85ebca6b) >>> 0; z = Math.imul(z ^ (z >>> 13), 0xc2b2ae35) >>> 0; return (z ^ (z >>> 16)) >>> 0; }
    var s0 = sm(), s1 = sm(), s2 = sm(), s3 = sm();
    function next() {
      var t = (s0 + s1) >>> 0; s0 = s1 ^ (s1 >>> 9); s1 = (s2 + (s2 << 3)) >>> 0; s2 = (s2 << 21) | (s2 >>> 11); s3 = (s3 + 1) >>> 0; t = (t + s3) >>> 0; s2 = (s2 + t) >>> 0;
      return t / 4294967296;
    }
    for (var i = 0; i < 12; i++) next();
    return next;
  }
  function sig(x) { return 1 / (1 + Math.exp(-x)); }

  // ---------- tiebreak engine (table-driven; step names come from the bundle) ----------
  function mkCtx(H, rating, draw, ovp, wins12, fbsp, div) {
    var m = H.length, W = new Array(m), P = new Array(m), G = new Array(m), pct = new Array(m), i, j;
    for (i = 0; i < m; i++) { P[i] = new Array(m); }
    for (i = 0; i < m; i++) { var w = 0; for (j = 0; j < m; j++) { w += H[i][j]; P[i][j] = H[i][j] + H[j][i]; } W[i] = w; }
    for (i = 0; i < m; i++) { var g = 0; for (j = 0; j < m; j++) g += P[i][j]; G[i] = g; pct[i] = g ? W[i] / g : 0; }
    return { H: H, m: m, rating: rating, draw: draw, ovp: ovp, wins12: wins12, fbsp: fbsp, div: div, W: W, P: P, G: G, pct: pct };
  }
  function groups(c, pool) {
    var map = {}, keys = [], k, i;
    for (i = 0; i < pool.length; i++) { k = Math.round(c.pct[pool[i]] * 1e9) / 1e9; if (!(k in map)) { map[k] = []; keys.push(k); } map[k].push(pool[i]); }
    keys.sort(function (a, b) { return b - a; });
    return keys.map(function (x) { return map[x]; });
  }
  function wp(w, g) { return g ? w / g : null; }
  function allNonNull(a) { for (var i = 0; i < a.length; i++) if (a[i] === null) return null; return a; }
  function notIn(x, t) { return t.indexOf(x) < 0; }
  function sumH(c, a, list) { var s = 0; for (var i = 0; i < list.length; i++) s += c.H[a][list[i]]; return s; }
  function sumP(c, a, list) { var s = 0; for (var i = 0; i < list.length; i++) s += c.P[a][list[i]]; return s; }
  function allPlayedAmong(c, t) { for (var i = 0; i < t.length; i++) for (var j = i + 1; j < t.length; j++) if (!c.P[t[i]][t[j]]) return false; return true; }

  function mini(c, t, mode) {
    var n = t.length, w = [], g = [], k, x, y, b;
    var ap = allPlayedAmong(c, t);
    for (k = 0; k < n; k++) { var ws = 0, gs = 0; for (b = 0; b < n; b++) if (b !== k) { ws += c.H[t[k]][t[b]]; gs += c.P[t[k]][t[b]]; } w.push(ws); g.push(gs); }
    if (mode === "rr_equal") { for (k = 1; k < n; k++) if (g[k] !== g[0]) return null; return g[0] ? w.map(function (v, i) { return v / g[i]; }) : null; }   // collective record vs the tied group; null if unequal games played
    if (mode === "rr_only_pct") return w.map(function (v, i) { return g[i] ? v / g[i] : 0; });
    if (ap && (mode === "rr_beat_lost" || mode === "rr_beat" || mode === "rr_only")) return w.map(function (v, i) { return v / g[i]; });
    if (mode === "rr_only") return null;
    var sc = new Array(n).fill(0), any = false;
    for (k = 0; k < n; k++) {
      var a = t[k], beatAll = true, lostAll = true;
      for (b = 0; b < n; b++) { if (b === k) continue; if (!(c.H[a][t[b]] > 0)) beatAll = false; if (!(c.H[t[b]][a] > 0)) lostAll = false; }
      if (beatAll) { sc[k] = 1; any = true; } else if (mode === "rr_beat_lost" && lostAll) { sc[k] = -1; any = true; }
    }
    return any ? sc : null;
  }
  function commonOpps(c, t) { var out = []; for (var o = 0; o < c.m; o++) { if (!notIn(o, t)) continue; var ok = true; for (var i = 0; i < t.length; i++) if (!c.P[t[i]][o]) { ok = false; break; } if (ok) out.push(o); } return out; }
  function ordered(c, t, filt, pool) {
    if (!pool) { pool = []; for (var i = 0; i < c.m; i++) if (notIn(i, t)) pool.push(i); }
    var gs = groups(c, pool);
    for (var gi = 0; gi < gs.length; gi++) {
      var grp = gs[gi].filter(function (o) { return notIn(o, t); });
      if (!grp.length) continue;
      if (!filt(grp, t)) continue;
      var sc = t.map(function (a) { return wp(sumH(c, a, grp), sumP(c, a, grp)); });
      var distinct = false; for (var q = 1; q < sc.length; q++) if (sc[q] !== sc[0]) distinct = true;
      if (distinct) return sc;
    }
    return null;
  }
  var STEPS = {
    h2h2: function (c, t) { var a = t[0], b = t[1]; return c.P[a][b] ? [c.H[a][b], c.H[b][a]] : null; },
    common_pct: function (c, t) { var co = commonOpps(c, t); if (!co.length) return null; return t.map(function (a) { return wp(sumH(c, a, co), sumP(c, a, co)); }); },
    common_ordered: function (c, t) { return ordered(c, t, function (grp, tt) { for (var i = 0; i < tt.length; i++) for (var j = 0; j < grp.length; j++) if (!c.P[tt[i]][grp[j]]) return false; return true; }); },
    ordered_any: function (c, t) { return ordered(c, t, function (grp, tt) { for (var i = 0; i < tt.length; i++) if (!(sumP(c, tt[i], grp) > 0)) return false; return true; }); },
    ordered_div: function (c, t) {
      var pool = []; for (var i = 0; i < c.m; i++) if (c.div[i] === c.div[t[0]] && notIn(i, t)) pool.push(i);
      return ordered(c, t, function (grp, tt) { for (var k = 0; k < tt.length; k++) if (!(sumP(c, tt[k], grp) > 0)) return false; return true; }, pool);
    },
    opp_conf_pct: function (c, t) {
      return allNonNull(t.map(function (a) { var w = 0, g = 0; for (var o = 0; o < c.m; o++) if (c.P[a][o]) { w += c.W[o]; g += c.G[o]; } return wp(w, g); }));
    },
    div_pct: function (c, t) {
      return allNonNull(t.map(function (a) { var w = 0, g = 0; for (var o = 0; o < c.m; o++) if (c.div[o] === c.div[a] && o !== a) { w += c.H[a][o]; g += c.P[a][o]; } return wp(w, g); }));
    },
    common_nondiv: function (c, t) {
      var co = []; for (var o = 0; o < c.m; o++) { if (c.div[o] === c.div[t[0]]) continue; var ok = true; for (var i = 0; i < t.length; i++) if (!c.P[t[i]][o]) { ok = false; break; } if (ok) co.push(o); }
      if (!co.length) return null; return t.map(function (a) { return wp(sumH(c, a, co), sumP(c, a, co)); });
    },
    rating: function (c, t) { return t.map(function (a) { return c.rating[a]; }); },
    overall_pct: function (c, t) { return c.ovp ? t.map(function (a) { return c.ovp[a]; }) : null; },
    wins12: function (c, t) { return c.wins12 ? t.map(function (a) { return c.wins12[a]; }) : null; },
    fbs_pct: function (c, t) { return c.fbsp ? t.map(function (a) { return c.fbsp[a]; }) : null; },
    apr: function () { return null; },
    draw: function (c, t) { return t.map(function (a) { return c.draw[a]; }); }
  };
  STEPS.margin_proxy = STEPS.rating;
  function runStep(c, name, t) { if (name.indexOf("h2h:") === 0) return mini(c, t, name.slice(4)); return STEPS[name](c, t); }

  function resolve(c, tied, spots, rl) {
    tied = tied.slice(); var chosen = [];
    for (;;) {
      if (tied.length <= spots) return chosen.concat(tied);
      var proc = tied.length === 2 ? rl.two : rl.multi, reverted = false;
      for (var pi = 0; pi < proc.length; pi++) {
        var sc = runStep(c, proc[pi], tied);
        if (sc === null) continue;
        var best = Math.max.apply(null, sc), grp = [];
        for (var k = 0; k < tied.length; k++) if (sc[k] === best) grp.push(tied[k]);
        if (grp.length === tied.length) continue;
        if (grp.length <= spots) {
          chosen = chosen.concat(grp); spots -= grp.length; tied = tied.filter(function (a) { return notIn(a, grp); });
          reverted = true; break;
        }
        tied = grp;
        if (tied.length === 2) { reverted = true; break; }
      }
      if (!reverted && tied.length > spots) { tied = tied.slice().sort(function (a, b) { return c.draw[b] - c.draw[a]; }).slice(0, spots); }
      if (spots <= 0) return chosen;
    }
  }
  function orderPair(c, pair, rl) {
    var a = pair[0], b = pair[1];
    if (c.pct[a] !== c.pct[b]) return c.pct[a] > c.pct[b] ? [a, b] : [b, a];
    var first = resolve(c, [a, b], 1, rl)[0];
    return [first, first === a ? b : a];
  }
  function extended(c, pool, top) {
    var t1 = pool.filter(function (i) { return c.pct[i] === top; }), ext = t1.slice();
    for (var p = 0; p < pool.length; p++) {
      var i = pool[p]; if (t1.indexOf(i) >= 0) continue;
      for (var q = 0; q < t1.length; q++) { var j = t1[q]; if (c.G[i] !== c.G[j] && (c.W[i] === c.W[j] || c.G[i] - c.W[i] === c.G[j] - c.W[j])) { ext.push(i); break; } }
    }
    return ext;
  }
  function selectCcg(c, rl) {
    var fmt = rl.fmt, i;
    if (fmt === "none") return [];
    if (fmt === "div") {
      var champs = [], divs = [];
      for (i = 0; i < c.m; i++) if (divs.indexOf(c.div[i]) < 0) divs.push(c.div[i]);
      divs.sort(function (a, b) { return a - b; });
      divs.forEach(function (d) {
        var pool = [], top = -1; for (i = 0; i < c.m; i++) if (c.div[i] === d) { pool.push(i); if (c.pct[i] > top) top = c.pct[i]; }
        var tied = pool.filter(function (x) { return c.pct[x] === top; });
        champs.push(resolve(c, tied, 1, rl)[0]);
      });
      var a = champs[0], b = champs[1];
      if (c.pct[a] !== c.pct[b]) return c.pct[a] > c.pct[b] ? [a, b] : [b, a];
      var host = resolve(c, [a, b], 1, { two: rl.host, multi: rl.host })[0];
      return [host, host === a ? b : a];
    }
    var pool2 = []; for (i = 0; i < c.m; i++) pool2.push(i);
    var spots = 2, chosen = [];
    while (spots > 0 && pool2.length) {
      var top2 = -1; for (i = 0; i < pool2.length; i++) if (c.pct[pool2[i]] > top2) top2 = c.pct[pool2[i]];
      var tier = rl.ext ? extended(c, pool2, top2) : pool2.filter(function (x) { return c.pct[x] === top2; });
      if (tier.length <= spots) chosen = chosen.concat(tier.length === 2 ? orderPair(c, tier, rl) : tier);
      else chosen = chosen.concat(resolve(c, tier, spots, rl));
      spots = 2 - chosen.length; pool2 = pool2.filter(function (x) { return notIn(x, chosen); });
    }
    if (chosen.length === 2) chosen = orderPair(c, chosen, rl);
    return chosen;
  }

  // ---------- CFP field (src/cfp.py)  ** SWAPPABLE SECTION **  ----------
  // Everything that depends on the CFP field rule lives in this block: P4, G6, finish(), field().
  // Contract: field(rank, champs, order, nd, g6) -> array of team indexes (field order, auto-bids outside the top 12 last);
  //   rank[t] = final ranking position (1 = best), champs = {confCode: championTeam|null}, order = teams sorted best first, nd = Notre Dame index.
  // When src/cfp.py changes, edit only this block (and nothing else in this file), then run: python3 tests/web_test.py --rebuild
  var P4 = ["acc", "big10", "big12", "sec"], G6 = ["American", "usa", "midam", "mwest", "pac12", "belt"];
  function finish(rank, auto, order) {
    var F = order.filter(function (t) { return auto.indexOf(t) >= 0; }), i;
    for (i = 0; i < order.length; i++) { var t = order[i]; if (F.length < 12 && auto.indexOf(t) < 0) F.push(t); }
    F.sort(function (a, b) { return rank[a] - rank[b]; });
    return F.filter(function (t) { return rank[t] <= 12 || auto.indexOf(t) < 0; }).concat(F.filter(function (t) { return rank[t] > 12 && auto.indexOf(t) >= 0; }));
  }
  // g6 = all FBS team indexes in the six Group of 6 conferences (built once per simulate() call from bundle.teams[].c)
  function field(rank, champs, order, nd, g6) {
    var auto = [], i;
    P4.forEach(function (c) { if (champs[c] !== null && champs[c] !== undefined && auto.indexOf(champs[c]) < 0) auto.push(champs[c]); });
    if (g6.length) { var b = g6[0]; for (i = 1; i < g6.length; i++) if (rank[g6[i]] < rank[b]) b = g6[i]; if (auto.indexOf(b) < 0) auto.push(b); }
    if (nd !== null && nd !== undefined && rank[nd] <= 12 && auto.indexOf(nd) < 0) auto.push(nd);
    return finish(rank, auto, order);
  }

  // ---------- conditional sampling for "exactly n wins of these games" ----------
  // q[i][j] = P(exactly j wins among games i..M-1), by DP; then sequential exact conditional sampling per season.
  function makeConstraint(bundle, cons, gindex) {
    var team = cons.team, gs = [], ps = [], M = cons.games.length, k;
    cons = { team: cons.team, wins: cons.wins, games: cons.games.slice().sort(function (x, y) { return gindex[x] - gindex[y]; }) };   // DP runs in global game order
    var mdl = bundle.model, GS = mdl.gs || mdl.s, GH = mdl.gs ? mdl.ghfa : mdl.hfa, sg = mdl.gs ? mdl.gsigma : mdl.sigma;   // game win probabilities: calibrated model when the bundle carries one
    for (k = 0; k < M; k++) {
      var gi = gindex[cons.games[k]], g = bundle.games[gi];
      var ph = sig((GS[g.h] - GS[g.a] + (g.neu ? 0 : GH)) / sg);
      gs.push(gi); ps.push({ pt: g.h === team ? ph : 1 - ph, teamHome: g.h === team });   // pt = P(team wins)
    }
    var q = []; for (k = 0; k <= M; k++) q.push(new Array(M + 2).fill(0)); q[M][0] = 1;
    for (k = M - 1; k >= 0; k--) for (var j = 0; j <= M - k; j++) q[k][j] = ps[k].pt * (j > 0 ? q[k + 1][j - 1] : 0) + (1 - ps[k].pt) * q[k + 1][j];
    return { gs: gs, ps: ps, q: q, need: cons.wins, M: M };
  }

  // ---------- main entry ----------
  function simulate(bundle, opts) {
    opts = opts || {};
    var N = opts.seasons || 2000, rng = makeRng(opts.seed === undefined ? 1 : opts.seed), n = bundle.n, FCS = bundle.fcs;
    var mod = bundle.model, now = bundle.now, games = bundle.games, G = games.length, confs = bundle.confs;
    var s = mod.s, hfa = mod.hfa, SG = mod.sigma, GS = mod.gs || mod.s, GH = mod.gs ? mod.ghfa : mod.hfa, GG = mod.gs ? mod.gsigma : mod.sigma, bench = mod.bench, col = mod.colley, cg = mod.colley_games;
    var gindex = {}; games.forEach(function (g, k) { gindex[g.id] = k; });
    var forced = new Int8Array(G).fill(-1), fk;
    if (opts.forced) for (fk in opts.forced) { if (!(fk in gindex)) throw new Error("unknown game id " + fk); forced[gindex[fk]] = opts.forced[fk] ? 1 : 0; }
    var cons = (opts.constraints || []).map(function (c) { return makeConstraint(bundle, c, gindex); });
    var consOf = new Int16Array(G).fill(-1), consPos = new Int16Array(G);
    cons.forEach(function (c, ci) { c.gs.forEach(function (gi, p) { consOf[gi] = ci; consPos[gi] = p; }); });
    // per-game constants: P(home wins), and the SOR / Colley increments for each side win or loss
    var ph = new Float64Array(G), sorW = new Float64Array(G * 2), sorL = new Float64Array(G * 2), colW = new Float64Array(G * 2), colL = new Float64Array(G * 2);
    games.forEach(function (g, k) {
      ph[k] = sig((GS[g.h] - GS[g.a] + (g.neu ? 0 : GH)) / GG);
      [[g.h, g.a, 1], [g.a, g.h, -1]].forEach(function (x, side) {
        var t = x[0], o = x[1], sd = x[2], pb = sig((bench - s[o] + (g.neu ? 0 : sd * hfa)) / SG);
        sorW[k * 2 + side] = 1 - pb; sorL[k * 2 + side] = -pb;
        colW[k * 2 + side] = (0.5 + col[o] - col[t]) / (3 + cg[t]); colL[k * 2 + side] = (-0.5 + col[o] - col[t]) / (3 + cg[t]);
      });
    });
    var RK = 10 * 0.6 / mod.resume_sd, A = 0.7 / mod.sor_sd, B = 0.3 / mod.colley_sd;
    var F = []; for (var t0 = 0; t0 < n; t0++) if (t0 !== FCS) F.push(t0);
    var g6 = F.filter(function (t) { return G6.indexOf(bundle.teams[t].c) >= 0; });
    var members = confs.map(function (c) { return c.members; });
    // per-team result counters
    var cCcg = new Float64Array(n), cTitle = new Float64Array(n), cCfp = new Float64Array(n), cBye = new Float64Array(n), cTop4 = new Float64Array(n), cWins = new Float64Array(n);
    var wins = new Float64Array(n), fcsw = new Float64Array(n), fbsw = new Float64Array(n), dsor = new Float64Array(n), dcol = new Float64Array(n);
    var rReg = new Float64Array(n), draw = new Float64Array(n), rFin = new Float64Array(n), dsor2 = new Float64Array(n), dcol2 = new Float64Array(n);
    var hw = new Uint8Array(G), U2 = new Float64Array(confs.length);
    var capw = new Float64Array(n), ovp = new Float64Array(n), fbsp = new Float64Array(n), rank = new Int32Array(n);
    var consWins = new Int16Array(cons.length);
    var nd = bundle.nd;

    for (var sidx = 0; sidx < N; sidx++) {
      // 1. games (uniforms are always consumed, in a fixed order, so forced runs are common-random-number twins of the base run)
      var ci2;
      for (ci2 = 0; ci2 < cons.length; ci2++) consWins[ci2] = cons[ci2].need;
      for (var k = 0; k < G; k++) {
        var u = rng(), r;
        if (forced[k] >= 0) r = forced[k];
        else if (consOf[k] >= 0) {
          var cc = cons[consOf[k]], pos = consPos[k], pt = cc.ps[pos].pt, j = consWins[consOf[k]], pw;
          pw = j <= 0 ? 0 : (cc.q[pos][j] > 0 ? pt * cc.q[pos + 1][j - 1] / cc.q[pos][j] : 0);   // P(team wins this game | need j wins among the rest incl. this)
          var teamWins = u < pw; if (teamWins) consWins[consOf[k]]--;
          r = teamWins === cc.ps[pos].teamHome ? 1 : 0;
        } else r = u < ph[k] ? 1 : 0;
        hw[k] = r;
      }
      for (var tt = 0; tt < n; tt++) draw[tt] = rng();
      for (var cj = 0; cj < confs.length; cj++) U2[cj] = rng();
      // 2. season-to-date totals
      for (tt = 0; tt < n; tt++) { wins[tt] = now.w[tt]; fcsw[tt] = now.fcsw[tt]; fbsw[tt] = now.fbsw[tt]; dsor[tt] = 0; dcol[tt] = 0; }
      for (k = 0; k < G; k++) {
        var g = games[k], h = g.h, a = g.a, w = hw[k];
        if (h !== FCS) {
          if (w) { wins[h] += 1; if (a === FCS) fcsw[h] += 1; else fbsw[h] += 1; dsor[h] += sorW[k * 2]; dcol[h] += colW[k * 2]; } else { dsor[h] += sorL[k * 2]; dcol[h] += colL[k * 2]; }
        }
        if (a !== FCS) {
          if (!w) { wins[a] += 1; if (h === FCS) fcsw[a] += 1; else fbsw[a] += 1; dsor[a] += sorW[k * 2 + 1]; dcol[a] += colW[k * 2 + 1]; } else { dsor[a] += sorL[k * 2 + 1]; dcol[a] += colL[k * 2 + 1]; }
        }
      }
      for (var fi = 0; fi < F.length; fi++) {
        tt = F[fi];
        rReg[tt] = mod.rating[tt] + RK * (A * dsor[tt] + B * dcol[tt]);
        var extraFcs = Math.max(0, fcsw[tt] - 1);
        capw[tt] = wins[tt] - extraFcs;
        var capg = now.gtot[tt] - Math.max(0, now.fcsg[tt] - 1) * (fcsw[tt] >= 1 ? 1 : 0);
        ovp[tt] = capw[tt] / Math.max(capg, 1);
        fbsp[tt] = fbsw[tt] / Math.max(now.fbsg[tt], 1);
        dsor2[tt] = dsor[tt]; dcol2[tt] = dcol[tt]; cWins[tt] += wins[tt];
      }
      // 3. conferences -> conference championship game teams -> champions
      var champs = {};
      for (cj = 0; cj < confs.length; cj++) {
        var C = confs[cj]; champs[C.code] = null;
        if (C.fmt === "none") continue;
        var mem = C.members, kk = mem.length, H = new Array(kk), i, jj;
        for (i = 0; i < kk; i++) { H[i] = C.base[i].slice(); }
        for (var q = 0; q < C.games.length; q++) { var cgm = C.games[q]; if (hw[cgm[0]]) H[cgm[1]][cgm[2]] += 1; else H[cgm[2]][cgm[1]] += 1; }
        var rt = new Array(kk), dr = new Array(kk), ov = new Array(kk), w12 = new Array(kk), fb = new Array(kk);
        for (i = 0; i < kk; i++) { var mt = mem[i]; rt[i] = rReg[mt]; dr[i] = draw[mt]; ov[i] = ovp[mt]; w12[i] = capw[mt]; fb[i] = fbsp[mt]; }
        var ctx = mkCtx(H, rt, dr, ov, w12, fb, C.div || null);
        var top = selectCcg(ctx, C), g1 = mem[top[0]], g2 = mem[top[1]];
        var neu = C.neutral, pw1 = sig((GS[g1] - GS[g2] + (neu ? 0 : GH)) / GG), w1 = U2[cj] < pw1, ch = w1 ? g1 : g2;
        champs[C.code] = ch; cCcg[g1] += 1; cCcg[g2] += 1; cTitle[ch] += 1;
        var sides = [[g1, g2, w1, 1], [g2, g1, !w1, -1]];
        for (var sd = 0; sd < 2; sd++) {
          var x = sides[sd], pb = sig((bench - s[x[1]] + (neu ? 0 : x[3] * hfa)) / SG), wf = x[2] ? 1 : 0;
          dsor2[x[0]] += wf - pb; dcol2[x[0]] += ((wf - 0.5) + col[x[1]] - col[x[0]]) / (3 + cg[x[0]]);
        }
      }
      // 4. final ratings, ranking, CFP field
      for (fi = 0; fi < F.length; fi++) { tt = F[fi]; rFin[tt] = mod.rating[tt] + RK * (A * dsor2[tt] + B * dcol2[tt]); }
      var order = F.slice().sort(function (x, y) { return rFin[y] - rFin[x]; });
      for (i = 0; i < order.length; i++) rank[order[i]] = i + 1;
      var f1 = field(rank, champs, order, nd, g6);
      for (i = 0; i < f1.length; i++) { cCfp[f1[i]] += 1; if (i < 4) cBye[f1[i]] += 1; }
      for (i = 0; i < 4; i++) cTop4[order[i]] += 1;
    }
    var inv = 1 / N, out = { seasons: N, seed: opts.seed === undefined ? 1 : opts.seed, ccg: new Float64Array(n), title: new Float64Array(n), cfp12: new Float64Array(n), bye: new Float64Array(n), top4: new Float64Array(n), exp_wins: new Float64Array(n) };
    for (var z = 0; z < n; z++) { out.ccg[z] = cCcg[z] * inv; out.title[z] = cTitle[z] * inv; out.cfp12[z] = cCfp[z] * inv; out.bye[z] = cBye[z] * inv; out.top4[z] = cTop4[z] * inv; out.exp_wins[z] = cWins[z] * inv; }
    return out;
  }

  var API = { simulate: simulate, makeRng: makeRng, version: 1 };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.KTSim = API;
})(typeof self !== "undefined" ? self : this);
