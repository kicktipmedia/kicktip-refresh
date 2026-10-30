// Unit + property tests for src/assets/ccgsim.js (official-rules engine) and the ESPN-line favorites helpers. Run: node tests/ccg_engine_test.js
const fs = require("fs"), path = require("path"), K = require("../src/assets/ccgsim.js");
const root = path.join(__dirname, ".."); let fails = 0, n = 0;
const ok = (c, m) => { n++; if (!c) { fails++; console.log("FAIL", m); } };
const eq = (a, b, m) => ok(JSON.stringify(a) === JSON.stringify(b), m + " expected " + JSON.stringify(b) + " got " + JSON.stringify(a));
const HOSTR = Object.assign({}, { fmt: "top2" }, {});
const H2H = { k: "h2h", t: "head-to-head" }, RAND = { k: "random", name: "coin toss", t: "coin toss" }, EXT = { k: "external", name: "ranking X", t: "x" };
const R0 = { fmt: "top2", tie_group: "equal", elim: "continue", ccg: { host: "neutral" }, two: [H2H, { k: "common_pct" }, EXT, RAND], multi: [{ k: "h2h_group", mode: "pct_else_beat_all" }, { k: "common_pct" }, EXT, RAND] };
function mk(names, results, remaining, nc) {
  const ix = Object.fromEntries(names.map((x, i) => [x, i])); let id = 0; const games = [];
  results.forEach(r => { const [a, b] = r.split(">"); games.push({ id: "g" + id++, h: ix[a], a: ix[b], w: 1, wk: 1, k: a.toLowerCase() + "~" + b.toLowerCase() }); });
  (remaining || []).forEach(r => { const [a, b] = r.split("-"); games.push({ id: "g" + id++, h: ix[a], a: ix[b], w: null, wk: 9, k: a.toLowerCase() + "~" + b.toLowerCase() }); });
  return { teams: names.map(s => ({ short: s })), div: null, games, nc: nc || names.map(() => ({ w: 0, fcsw: 0, fcsg: 0, g: 0, left: 0 })) };
}
const nm = (r, a) => a.map(i => r.names[i]);
// 1. no tie
let c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>C", "B>D", "C>D"]), r = K.solve(R0, c, {});
eq(nm(r, r.pair), ["A", "B"], "no tie pair"); ok(/first and second on conference record/.test(r.why[0]), "no-tie why"); ok(r.ready && !r.unresolvable, "ready");
// 2. three-way cycle for second place: nothing in the 'two'/'multi' lists is computable -> not resolvable, three outcomes, each with a condition
c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>D", "D>C", "C>B"]); r = K.solve(R0, c, {});
ok(r.unresolvable && !r.pairKnown && r.pair === null, "cycle unresolvable"); eq(r.outcomes.length, 3, "cycle has three outcomes");
ok(r.outcomes.every(o => o.teams.includes(0) && o.conds.length >= 1 && /ranking X puts/.test(o.conds[0])), "outcome conditions name the step");
ok(r.why.some(l => /Tie not resolvable by this tool/.test(l)), "says tie not resolvable by this tool");
eq(r.table.filter(t => t.spot === "possible").length, 3, "possible spots flagged"); eq(r.table.find(t => t.name === "A").spot, "in", "A in");
// 3. order-open: A and B both in for sure, tied at the top, never played; the two-team list ends in the unresolvable step
c = mk(["A", "B", "C", "D"], ["A>C", "A>D", "B>C", "B>D", "C>D"]); r = K.solve(R0, c, {});
ok(r.pairKnown && r.orderKnown && !r.unresolvable && r.box.kind === "decided", "neutral site: order of the two does not matter");
const RH = Object.assign({}, R0, { ccg: { host: "higher_seed" } }); r = K.solve(RH, c, {});
ok(r.pairKnown && !r.orderKnown && r.unresolvable, "order open when the higher seed hosts"); eq(r.outcomes.length, 2, "two orderings"); eq(r.box.kind, "order-open", "box kind order-open");
// 4. two-team tie for second decided by head-to-head
c = mk(["A", "B", "C", "D", "E"], ["A>B", "A>C", "A>D", "A>E", "B>C", "D>B", "C>D", "B>E", "C>E", "D>E"]); r = K.solve(R0, c, {});
// B: lost A,D beat C,E 2-2; C: lost A,B beat D,E 2-2; D: lost A,C beat B,E 2-2 -> three-way cycle among B,C,D: not resolvable except common opponents A,E level -> unresolvable
ok(!r.pairKnown && r.outcomes.length === 3, "5-team cycle unresolvable");
c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>C", "D>B", "C>D", "B>D"]); // B: lost A,D? give B two wins
r = K.solve(R0, c, {}); ok(r.ready, "ready 4"); // sanity: just runs
// 5. h2h decides a two-team tie for the last spot
c = mk(["A", "B", "C", "D", "E"], ["A>B", "A>C", "A>D", "A>E", "B>C", "C>E", "E>B", "D>E", "D>C", "B>D"]);
// A 4-0; B: beat C, D; lost A, E => 2-2; C: beat E; lost A,B,D => 1-3; D: beat E,C; lost A,B => 2-2; E: beat B; lost A,C,D => 1-3? (C>E) E lost to C -> E 1-3
r = K.solve(R0, c, {}); eq(nm(r, r.pair)[0], "A", "A first"); eq(nm(r, r.pair)[1], "B", "B beat D head-to-head"); ok(r.why.some(l => /B beat D/.test(l)), "why names h2h winner");
// 6. wins12 pending when a non-conference game is unplayed
const RW = Object.assign({}, R0, { two: [{ k: "wins12", t: "wins" }, RAND], multi: [{ k: "wins12", t: "wins" }, RAND] });
c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>D", "D>C", "C>B"]); c.nc[1].left = 1; r = K.solve(RW, c, {});
ok(r.unresolvable && r.outcomes.length === 3, "pending wins12 unresolvable"); c.nc[1].left = 0; c.nc[1].w = 3; c.nc[2].w = 2; c.nc[3].w = 2; r = K.solve(RW, c, {});
eq(nm(r, r.pair), ["A", "B"], "wins12 decides"); ok(r.why.some(l => /B 4 wins/.test(l)), "wins12 text");
// 6b. one FCS win only
c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>D", "D>C", "C>B"]); c.nc[1].w = 3; c.nc[1].fcsw = 3; c.nc[2].w = 3; c.nc[3].w = 3; r = K.solve(RW, c, {});
ok(!r.pairKnown && r.outcomes.length === 2 && !r.outcomes.some(o => o.teams.includes(1)), "extra FCS wins ignored: B (3 FCS wins = 1) drops out; C and D tie -> two outcomes");
// 7. partial picks: clinch / out logic, no pairing shown until every game is set
c = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>C", "B>D"], ["C-D"]); r = K.solve(R0, c, {});
ok(!r.ready && r.left === 1 && !r.pair, "partial: not ready, no pair"); eq(r.sure.map(i => r.names[i]), ["A", "B"], "A and B sure on record"); eq(r.clinch.status[2] + "/" + r.clinch.status[3], "out/out", "C, D out");
r = K.solve(R0, c, { g5: 1 }); ok(r.ready && r.pairKnown, "all set -> ready");
// 8. restart vs continue only matters with 4+ tied; both must still return a valid pair on random data
// 9. tie_group unequal_one_win (CUSA): a team with fewer games and same losses within one win counts as tied
const RU = Object.assign({}, R0, { tie_group: "unequal_one_win" });
c = mk(["A", "B", "C", "D"], ["A>C", "A>D", "B>C", "B>D"], []); c.games.push({ id: "gx", h: 2, a: 3, w: 1, wk: 3, k: "x" });
r = K.solve(RU, c, {}); ok(r.ready, "unequal ok");
// 10. data-driven property test on the real data
const data = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs, rules = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules;
let s = 12345; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
let leaves = 0, unres = 0, cases = 0;
for (const code of Object.keys(rules)) for (let t = 0; t < 120; t++) {
  const cf = data[code], p = K.randomFill(cf, {}, rnd), res = K.solve(rules[code], cf, p); cases++;
  ok(res.ready, code + " ready after full fill");
  const top = res.table.reduce((a, x) => a + x.w, 0), tot = res.table.reduce((a, x) => a + x.l, 0); eq(top, tot, code + " wins == losses");
  if (res.pairKnown) { ok(res.pair.length === 2 && res.pair[0] !== res.pair[1], code + " distinct pair"); const w = res.table.filter(x => x.spot === "in").length; eq(w, 2, code + " two spots marked"); }
  else { unres++; ok(res.outcomes.length >= 2 && res.outcomes.every(o => o.teams.length === 2 && o.conds.length), code + " unresolved lists outcomes with conditions"); ok(res.why.some(l => /not resolvable by this tool/.test(l)) || res.analysis.readings, code + " says not resolvable (or carries the two ACC readings)"); }
  // top two by record are always among the pair unless a tie is involved
  const g = res.table.filter(x => x.rank === 1);
  if (rules[code].fmt !== "div" && g.length === 1 && res.table.filter(x => x.rank === 2).length === 1 && res.pairKnown) eq(res.pair.map(i => res.names[i]).sort(), [g[0].name, res.table.find(x => x.rank === 2).name].sort(), code + " untied top two");
  // determinism
  eq(K.solve(rules[code], cf, p).pair, res.pair, code + " deterministic");
  // monotone: changing a game leaves a ready table
  const id = cf.games.find(x => x.w === null).id, p2 = Object.assign({}, p, { [id]: 1 - p[id] }); ok(K.solve(rules[code], cf, p2).ready, code + " flip ready");
}
// 11. favorites from ESPN (pre-game favorite wording)
const cf = data.big12, rem = cf.games.filter(x => x.w === null), now = 1792913600;
const lines = { l: {} }; rem.forEach((g, i) => { lines.l[g.k] = [i % 2 ? 3.5 : -3.5, now - 3600, now + 86400]; });
let f = K.favorites(cf, lines, now);
eq(f.status, "ok", "fav ok"); eq(f.withLine, rem.length, "all have lines"); eq(f.noLine, 0, "none missing");
ok(rem.every((g, i) => f.picks[g.id] === (i % 2 ? 0 : 1)), "negative line = home favored, positive = away favored"); ok(!/\d/.test(f.note), "note has no numbers when ok");
// no line for one game -> unset; zero (even) -> unset
delete lines.l[rem[0].k]; lines.l[rem[1].k][0] = 0; f = K.favorites(cf, lines, now);
ok(f.picks[rem[0].id] === undefined && f.picks[rem[1].id] === undefined, "missing and even lines stay unset"); eq(f.noLine, 2, "noLine count"); ok(f.note === "2 games have no ESPN favorite listed yet, so they start unset and highlighted.", "note names the unset count (F3 wording)");
// stale (>24h) per game and for the whole file
lines.l[rem[2].k][1] = now - 86400 - 5; f = K.favorites(cf, lines, now); ok(f.picks[rem[2].id] === undefined, "line older than 24h is not used");
const old = { l: {} }; rem.forEach(g => { old.l[g.k] = [-3, now - 90000, now + 5000]; }); f = K.favorites(cf, old, now);
eq(f.status, "stale", "all stale"); eq(Object.keys(f.picks).length, 0, "stale -> all unset"); ok(/not available right now/.test(f.note) && f.note.length < 140, "short plain note on stale");
// started game: not used
const st = { l: {} }; rem.forEach(g => { st.l[g.k] = [-3, now - 100, now - 50]; }); f = K.favorites(cf, st, now); eq(Object.keys(f.picks).length, 0, "started games get no pre-fill");
// missing / empty / malformed never throw
for (const bad of [null, undefined, {}, { l: {} }, { l: null }, [], "x", { l: { "a~b": "oops" } }]) { let thrown = false, q; try { q = K.favorites(cf, bad, now); } catch (e) { thrown = true; } ok(!thrown && Object.keys(q.picks).length === 0 && q.note.length > 0, "bad lines " + JSON.stringify(bad)); }
// early decision: with 3 games unset a clear leader is locked
{ const cc = mk(["A", "B", "C", "D"], ["A>B", "A>C", "A>D", "B>C", "B>D"], ["C-D"]); eq(K.early(R0, cc, {}, 10).map(i => i).sort(), [0, 1], "decided early: A and B however C-D goes"); const c3 = mk(["A", "B", "C", "D"], ["A>B", "B>C", "C>D"], ["A-C", "B-D", "A-D"]); ok(K.early(R0, c3, {}, 10) === null, "not decided early"); ok(K.early(R0, c3, {}, 1) === null, "early skipped above the limit"); }
// 12. flip / counters / reset / clear / random
lines.l[rem[0].k] = [-5, now - 10, now + 10000]; lines.l[rem[1].k] = [-5, now - 10, now + 10000]; lines.l[rem[2].k] = [-5, now - 10, now + 10000];
delete lines.l[rem[4].k]; f = K.favorites(cf, lines, now); let p = Object.assign({}, f.picks);
eq(K.changedCount(cf, p, f.defaults), 0, "fresh = 0 changed");
const gid = rem[3].id, side = p[gid]; p = K.flip(cf, p, gid, 1 - side); eq(p[gid], 1 - side, "one tap on the other team flips"); eq(K.changedCount(cf, p, f.defaults), 1, "changed = 1");
p = K.flip(cf, p, gid, side); eq(p[gid], side, "flip back"); eq(K.changedCount(cf, p, f.defaults), 0, "flipping back is not a change");
p = K.flip(cf, p, gid, side); eq(p[gid], side, "tapping the team that already wins changes nothing"); p = K.unset(p, gid); ok(p[gid] === undefined, "unset"); eq(K.changedCount(cf, p, f.defaults), 1, "cleared favorite counts as changed");
p = K.resetGame(p, gid, f.defaults); eq(p[gid], side, "reset one game to its favorite"); eq(K.changedCount(cf, p, f.defaults), 0, "reset one game -> 0 changed"); const u0 = rem.find(g => f.defaults[g.id] === undefined); p = K.flip(cf, p, u0.id, 0); p = K.resetGame(p, u0.id, f.defaults); ok(p[u0.id] === undefined, "no favorite -> reset unsets");
const reset = Object.assign({}, f.defaults); eq(K.changedCount(cf, reset, f.defaults), 0, "Reset to favorites -> 0 changed"); eq(Object.keys(reset).length, f.withLine, "reset restores favorites only");
const clear = {}; eq(K.changedCount(cf, clear, f.defaults), f.withLine, "Clear all counts every favorite as changed"); eq(K.solve(rules.big12, cf, clear).left, rem.length, "Clear all -> all games left, none set");
const un = rem.find(g => f.defaults[g.id] === undefined); const q1 = K.flip(cf, {}, un.id, 1); eq(K.changedCount(cf, q1, f.defaults) - K.changedCount(cf, {}, f.defaults), 1, "setting an unset game counts as changed");
let s2 = 7; const r2 = () => { s2 = (s2 * 1664525 + 1013904223) % 4294967296; return s2 / 4294967296; };
const rp = K.randomFill(cf, { [rem[0].id]: 1 }, r2); eq(rp[rem[0].id], 1, "random keeps existing picks"); eq(Object.keys(rp).length, rem.length, "random fills every unset game"); ok(K.solve(rules.big12, cf, rp).ready, "random -> ready");
// games that are final are never changed or counted
ok(!Object.keys(K.randomFill(cf, {}, r2)).some(id => !rem.find(g => g.id === id)), "random touches only games left");
// step 2 semantics on hand-built fills
(function () {
  const mk = (names, wins, div) => { const games = []; let id = 1; wins.forEach(([a, b]) => games.push({ id: id++, h: a, a: b, w: 1, wk: 1, date: "", neu: false, k: "" })); return { teams: names.map(n => ({ short: n })), div: div || null, games, nc: [] }; };
  // Sun Belt: division champions play, even if a team in the other division has a better record
  const sb = mk(["E1", "E2", "W1", "W2"], [[0, 1], [2, 3], [0, 2], [1, 3]], ["East", "West", "East", "West"].map((x, i) => [ "East", "East", "West", "West"][i]));
  const r = K.solve(rules.belt, sb, {}); ok(r.pairKnown && r.orderKnown, "sun belt hand case decided");
  eq(r.pair.slice().sort((a, b) => a - b), [0, 2], "sun belt: one champion per division (E1 4-.. and W1), host is the better record: E1 2-1 hosts"); eq(r.pair[0], 0, "sun belt host = better conference record");
  // MW: three teams tied for the best record -> immunity branches: each could host, plus nobody-immune
  const mw = mk(["A", "B", "C", "D"], [[0, 1], [1, 2], [2, 0], [0, 3], [1, 3], [2, 3]]);
  const rm = K.solve(rules.mwest, mw, {}); ok(!rm.pairKnown && rm.outcomes.length >= 3, "mw three-way tie: several outcomes (immunity)"); ok(rm.outcomes.every(o => o.conds.length), "mw outcomes carry conditions");
  ok(rm.analysis.leafList.some(l => l.conds.some(c => c.picked.length === 0)), "mw has a nobody-immune branch");
  // ACC readings
})();
// data sanity: no team has more conference games than the rules' schedule length (Mountain West once had NDSU and SJSU at 9: a non-conference game ESPN flags as conference)
{
  const RUL = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules, DAT = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs;
  for (const code of Object.keys(DAT)) { const c = {}; DAT[code].games.forEach(g => { c[g.h] = (c[g.h] || 0) + 1; c[g.a] = (c[g.a] || 0) + 1; }); ok(Object.values(c).every(v => v <= RUL[code].games_per_team), code + ": no team has more conference games than games_per_team " + JSON.stringify(c)); }
  ok(DAT.mwest.games.length === 40 && !DAT.mwest.games.some(g => g.id === "401864549"), "mwest: 40 conference games, the NDSU at SJSU non-conference game is not counted");
}
// rules with two readings of one sentence (rules[code].alt: pac12, usa) and ACC: every reading is its own flagged outcome, never silently picked
{
  const RUL = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules, DAT = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs;
  for (const code of ["pac12", "usa", "acc"]) {
    let s = 11; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; }; let nr = 0, bad = 0;
    for (let i = 0; i < 1500; i++) {
      const p = K.randomFill(DAT[code], {}, rnd), r = K.solve(RUL[code], DAT[code], p);
      if (!(r.analysis && r.analysis.readings)) continue; nr++;
      const steps = new Set(r.analysis.leafList.flatMap(l => l.conds.filter(c => c.step === "acc_reading" || c.step === "reading").map(c => c.picked[0])));
      if (!(r.ready && !r.pairKnown && r.outcomes.length >= 2 && steps.size === 2 && r.outcomes.every(o => o.conds.length && o.teams.length === 2))) bad++;
      if (code !== "acc") { const A = RUL[code].alt; if (!r.outcomes.some(o => o.conds.some(c => c.includes(A.a))) || !r.outcomes.some(o => o.conds.some(c => c.includes(A.b)))) bad++; }
    }
    ok(nr > 0, code + ": some fills give two readings with different conference championship game pairings (" + nr + ")"); ok(bad === 0, code + ": every two-reading fill lists both readings as flagged outcomes with plain-words conditions (" + bad + " bad)");
  }
  ok(!/\bpicks?\b/i.test(fs.readFileSync(root + "/src/assets/ccgsim.js", "utf8").replace(/\/\*[\s\S]*?\*\//g, "").split("\n").filter(l => /"[^"]*\bpicks? [a-z]/.test(l) || /"[^"]*\bpicks\b[^"]*"/.test(l)).join("\n")), "no 'picks' wording in engine text strings");
}
// F4: a tied tier never prints one team's record for all members (4-0 and 3-0 are both 100%; ACC / Conference USA mix games played)
{
  const RUL = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules, DAT = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs;
  // hand case, Pac-12-like (7 conference games, equal win percentage): O 4-0, B 3-0, C 1-2, D 0-3 -> O and B are both unbeaten, not "tied at 3-0"
  const g = []; let id = 1; [[0, 2], [0, 3], [0, 2], [0, 3], [1, 2], [1, 3], [1, 3], [2, 3]].forEach(([a, b], i) => g.push({ id: id++, h: a, a: b, w: 1, wk: 1, date: "", neu: false, k: "x" + i }));
  const hand = { teams: ["O", "B", "C", "D"].map(n => ({ short: n })), div: null, games: g, nc: [] }, RP = Object.assign({}, RUL.pac12);
  const rr = K.solve(RP, hand, {}), sec = (rr.analysis && rr.analysis.sections || rr.sections || []).concat(rr.sections || []);
  ok(!sec.some(x => / at \d+-\d+/.test(x.desc || "") && x.teams.length > 1 && new Set(x.teams.map(t => rr.table.find(q => q.i === t).w + "-" + rr.table.find(q => q.i === t).l)).size > 1), "F4 hand case: no shared record printed for teams with different records");
  ok((rr.sections || []).some(x => x.desc === " (both unbeaten)") && rr.why.some(l => l === "Tied (both unbeaten) for first place: O and B."), "F4 hand case: says both unbeaten, never \"tied at 3-0\"" + JSON.stringify(rr.why));
  let s7 = 5; const r7 = () => { s7 = (s7 * 1664525 + 1013904223) % 4294967296; return s7 / 4294967296; };
  for (const code of Object.keys(DAT)) {
    const rem = DAT[code].games.filter(x => x.w === null); let bad = 0, tot = 0, unb = 0;
    for (let i = 0; i < 600; i++) {
      const p = K.randomFill(DAT[code], {}, r7); if (i % 2) for (const x of rem) if (r7() < 0.6) delete p[x.id];
      const r = K.solve(RUL[code], DAT[code], p);
      for (const sc of (r.sections || []).concat((r.analysis && r.analysis.sections) || [])) {
        tot++; const recs = new Set(sc.teams.map(t => { const T = r.table.find(q => q.i === t); return T.w + "-" + T.l; }));
        if (typeof sc.desc !== "string") { bad++; continue; }
        if (recs.size === 1) { if (sc.desc !== " at " + [...recs][0]) bad++; }
        else { unb++; if (/ at \d+-\d+/.test(sc.desc)) bad++; if (!/^ \((both|all) unbeaten\)$|^ on win percentage \(/.test(sc.desc)) bad++; }
      }
    }
    ok(tot > 0 && bad === 0, "F4 " + code + ": " + tot + " tied tiers over 600 fills, " + unb + " with differing records, " + bad + " printed a wrong shared record");
  }
}
console.log(`ccg engine test: ${n} checks, ${fails} failed (${cases} data cases, ${unres} unresolvable)`); process.exit(fails ? 1 : 0);

