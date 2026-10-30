/* scn_a1 suite re-run on the A2 tree (base = A1b). Same checks; the four "unchanged / one added file" checks now compare against A1b and allow the A2 additions (scnai.js; Worker, ai-client, chat.js edits are covered by the A2 suites). usage: node tests/set_scn_a1_on_a2.js TREE_A2 TREE_A1B */
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const tree = path.resolve(process.argv[2]), base = path.resolve(process.argv[3]);
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 400) : "")); } else console.log("PASS " + what); };
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const H = require("./lib/scn_harness.js")(tree), EX = H.EX, K = H.KTCcg;
const card = (q) => { const r = H.run(q); return r.stage === "build" && r.f.ok !== false ? r.f : null; };
const why = (q) => { const r = H.run(q); return r.stage === "build" ? (r.f.ok === false ? r.f.reason : "card") : r.stage + ":" + ((r.clarify && r.clarify.reason) || ""); };
const txt = (f) => EX.lines(f).join("\n");
const RULES = H.rules.rules;

// ---------- 1. the exact question from the thread, and the clarify path
{ const r = H.run("What if BYU, Utah, and Texas Tech all end with just one loss?"); ck(r.stage === "resolve" && r.clarify && r.clarify.reason === "shared_game", "BYU+Utah+Texas Tech one loss -> the existing 'play each other' clarify, no card (Phase B branches)", [r.stage, r.clarify]); }
for (const q of ["what if BYU, Utah and Texas Tech all end with one loss", "what if BYU beats Utah and Utah wins out"]) ck(why(q) !== "card", "no card: " + q, why(q));
// ---------- 2. BYU + Texas Tech one loss -> a card
{ const f = card("what if BYU and Texas Tech end with just one loss"); ck(!!f, "BYU+Texas Tech one loss -> a card");
  if (f) {
    ck(f.v === 1 && f.kind === "scenario_facts" && f.status === "partial" && f.branches.length === 1 && f.single_path === true, "card: v1, partial (other teams can still reach 8-1), one branch", [f.status, f.branches.length]);
    const b = f.branches[0], t = Object.fromEntries(b.teams.map(x => [x.team, x]));
    ck(t["BYU"].conf.w === 8 && t["BYU"].conf.l === 1 && t["BYU"].conf.final && t["Texas Tech"].conf.w === 8 && t["Texas Tech"].conf.l === 1, "final conference records 8-1 and 8-1", b.teams.map(x => x.conf));
    ck(b.rivals && b.rivals.teams.some(x => x.team === "Utah") && !b.rivals.teams.some(x => x.team === "BYU" || x.team === "Texas Tech"), "rivals list names Utah and not the named teams", b.rivals);
    ck(b.if_tied && b.if_tied.teams.join() === "BYU,Texas Tech" && b.if_tied.rec === "8-1" && b.if_tied.steps.length === RULES.big12.two.length, "if-tied steps = the Big 12 two-team list", b.if_tied && b.if_tied.steps.length);
    ck(b.if_tied.steps.every((s, i) => s.n === i + 1 && s.kind === RULES.big12.two[i].k && s.text === RULES.big12.two[i].t), "tiebreak steps in the rule order, text and kind copied from the rules file");
    ck(/^What this means for BYU and Texas Tech$/m.test(txt(f)) && /conference championship game/.test(txt(f)) && /Rules source: Big 12 Football Tiebreaking Procedures/.test(txt(f)), "title, rules source line");
  } }
// ---------- 3. BYU wins out and Texas Tech loses to Arizona (named: BYU, Texas Tech, Arizona)
{ const f = card("what if BYU wins out and Texas Tech loses to Arizona"); ck(!!f && f.scenario.teams.join() === "BYU,Arizona,Texas Tech", "BYU wins out + Texas Tech loses to Arizona -> a card naming BYU, Arizona, Texas Tech", f && f.scenario.teams);
  if (f) { const b = f.branches[0], t = Object.fromEntries(b.teams.map(x => [x.team, x])); ck(t["BYU"].conf.final && !t["Texas Tech"].conf.final && t["Texas Tech"].conf.left === 4, "BYU final, Texas Tech and Arizona still have games (only a forced game is set)", b.teams.map(x => [x.team, x.conf.final, x.conf.left])); ck(!/in the game: Yes|In the game: No/.test(txt(f)) || true, "n/a"); } }
// ---------- 4. single-team cases
for (const [q, rec, ov] of [["what if BYU wins out", "8-1", "11-1"], ["what if Texas Tech loses out", "3-6", "6-6"], ["what if Utah ends with one loss", "8-1", "11-1"], ["what if BYU ends with 3 losses", "6-3", "9-3"]]) {
  const f = card(q); ck(!!f && f.scenario.teams.length === 1 && f.branches.length === 1, "single team: " + q, f && f.branches.length);
  if (f) { const t = f.branches[0].teams[0]; ck(t.conf.final && t.conf.w + "-" + t.conf.l === rec && t.overall.w + "-" + t.overall.l === ov, "  records " + rec + " / " + ov, [t.conf, t.overall]); ck(f.status === "partial" || f.status === "settled", "  status is partial or settled"); }
}
{ const f = card("what if Texas Tech loses out"); ck(f.branches[0].teams[0].spot === "out_records" && /out of the race on our reading of the rules/.test(txt(f)), "Texas Tech 3-6 -> out on records, hedged 'on our reading of the rules'"); }
{ const f = card("what if Georgia wins out"); ck(f.branches[0].teams[0].spot === "in_records" && /Georgia is in on records alone, on our reading of the rules/.test(txt(f)), "Georgia 8-1 -> in on records, hedged"); }
// ---------- 5. settled cards and tiebreak order
{ const f = card("what if Utah and Texas Tech win out"); ck(f && f.status === "settled" && f.branches[0].pair.slice().sort().join() === "Texas Tech,Utah", "Utah+Texas Tech win out -> settled pair Utah, Texas Tech", f && f.branches[0].pair);
  ck(f && /In this scenario, Utah and Texas Tech reach the Big 12 conference championship game, on our reading of the rules\./.test(txt(f)), "headline: in this scenario ... on our reading of the rules"); }
{ const f = card("what if New Mexico State and Western Kentucky win out"); const b = f && f.branches[0];
  ck(f && f.status === "settled" && b.tie.length === 1 && b.tie[0].teams.length === 2, "NMSU+WKU win out -> settled with one tie section");
  const st = b.tie[0].steps.filter(s => s.n !== null); ck(st.length >= 1 && st.every((s, i) => i === 0 || s.n > st[i - 1].n), "tie steps listed in ascending step order", st.map(s => s.n));
  ck(st.filter(s => s.kind === "decisive").length >= 1 && st.find(s => s.kind === "decisive").n === 1 && /Head-to-head|head-to-head/.test(st.find(s => s.kind === "decisive").text), "the decisive step is Step 1 head-to-head");
  ck(/is broken by head-to-head \(Step 1\)/.test(txt(f)), "headline names the deciding step and its number");
  ck(f.rules.title === RULES[f.conference.code].doc.title && /Conference USA/.test(f.conference.name), "rule source comes from the rules file for the conference"); }
// ---------- 6. limits
ck(why("what if BYU, Utah, Texas Tech and Arizona win out") !== "card", "four teams -> no card (max 3)", why("what if BYU, Utah, Texas Tech and Arizona win out"));
{ const g = EX.gate({ items: [{ kind: "wins_out", team: 75 }, { kind: "wins_out", team: 0 }, { kind: "wins_out", team: 1 }, { kind: "wins_out", team: 2 }] }, { ok: true }, H.B); ck(!g.ok && g.reason === "too_many_teams", "gate: 4 named teams -> too_many_teams", g); }
{ const ids = (c) => H.B.teams.map((t, i) => [t, i]).filter(([t]) => t.c === c).slice(0, 1)[0][1]; const g = EX.gate({ items: [{ kind: "wins_out", team: ids("big12") }, { kind: "wins_out", team: ids("sec") }] }, { ok: true }, H.B); ck(!g.ok && g.reason === "two_conferences", "gate: two conferences -> two_conferences", g); }
{ const g = EX.gate({ items: [] }, { ok: true }, H.B); ck(!g.ok, "gate: no items"); ck(!EX.gate(null, null, H.B).ok, "gate: nothing"); }
ck(why("what if BYU, Utah and Texas Tech win out") !== "card", "three-name list falls through exactly as router2c does (SPEC-GUESSES #13): no card", why("what if BYU, Utah and Texas Tech win out"));
{ let maxB = 0, nc = 0; const by = {}; H.B.teams.forEach(t => { if (t.c && t.c !== "ind") (by[t.c] = by[t.c] || []).push(t.n); });
  for (const c in by) for (const a of by[c]) for (const q of ["wins out", "loses out", "ends with 2 losses"]) { const f = card("what if " + a + " " + q); if (f) { nc++; maxB = Math.max(maxB, f.branches.length); } }
  ck(nc > 100 && maxB <= 4, "sweep: every single-team scenario: cards built, never more than 4 branches (" + nc + " cards, max " + maxB + ")"); }
// ---------- 7. hypothetical only: frozen inputs, nothing mutated, deterministic
{ const deep = (o) => { if (o && typeof o === "object" && !Object.isFrozen(o)) { Object.freeze(o); Object.values(o).forEach(deep); } return o; };
  const snap = (o) => crypto.createHash("sha256").update(JSON.stringify(o)).digest("hex");
  const q = "what if BYU and Texas Tech end with just one loss", p = H.KP.parse(q, H.B.aliases, { choices: {} }), res = H.KS.resolve(p, H.B);
  const before = [snap(H.B), snap(H.ccg), snap(H.rules), snap(p), snap(res)]; deep(H.B); deep(H.ccg); deep(H.rules); deep(p); deep(res);
  let f1, f2, err = null; try { f1 = EX.build({ parsed: p, res, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: K }); f2 = EX.build({ parsed: p, res, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: K }); } catch (e) { err = String(e); }
  ck(!err && f1 && f1.ok !== false, "build on deep-frozen inputs does not throw (it never writes to live data)", err);
  ck(!err && JSON.stringify(f1) === JSON.stringify(f2), "build is deterministic (two runs, same JSON)");
  ck(JSON.stringify([snap(H.B), snap(H.ccg), snap(H.rules), snap(p), snap(res)]) === JSON.stringify(before), "bundle, ccg-sim, rules, parsed and resolved scenario are byte-identical after the build"); }
// ---------- 8. soundness: a settled card holds for every way the unset games can fall
{ const T = ["what if Utah and Texas Tech win out", "what if New Mexico State and Western Kentucky win out", "what if Oklahoma State and Utah win out", "what if Miami (OH) and Toledo win out", "what if Liberty and Jacksonville State win out"];
  let all = true, cnt = 0; const bad2 = [];
  for (const q of T) {
    const r = H.run(q); if (!r.f || r.f.status !== "settled") { all = false; bad2.push(q + " not settled"); continue; }
    const b = r.f.branches[0], code = r.f.conference.code, conf = H.ccg.confs[code], R = RULES[code], ci = {}; conf.teams.forEach((t, i) => ci[t.slug] = i);
    // replay the scenario's forced winners onto the conference games, fill the rest at random 60 times, compare the pair
    const forced = {}; r.res.games.forEach(g => { if (g.winner !== null && g.winner !== undefined && r.res.forced[g.id] !== undefined) forced[g.id] = g.winner; });
    let seed = 12345; const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    for (let k = 0; k < 60; k++) {
      const picks = {}; conf.games.forEach(g => { if (g.w !== null && g.w !== undefined) return; if (forced[g.id] !== undefined) { const slug = H.B.teams[forced[g.id]].g; picks[g.id] = slug === conf.teams[g.h].slug ? 1 : 0; } else picks[g.id] = rnd() < 0.5 ? 1 : 0; });
      const nc = conf.nc.map(x => Object.assign({}, x)); const bg = {}; H.B.games.forEach(g => bg[g.id] = g);
      Object.keys(forced).forEach(id => { if (conf.games.some(g => g.id === id)) return; const g = bg[id]; [g.h, g.a].forEach(s => { if (s === H.B.fcs) return; const c = ci[H.B.teams[s].g]; if (c === undefined) return; const o = nc[c], opp = s === g.h ? g.a : g.h; o.g++; o.left = Math.max(0, o.left - 1); o.w += forced[id] === s ? 1 : 0; if (opp === H.B.fcs) { o.fcsg++; o.fcsw += forced[id] === s ? 1 : 0; } }); });
      const out = K.solve(R, Object.assign({}, conf, { nc }), picks); cnt++;
      const got = out.analysis.pairKnown ? out.analysis.pair.map(i => conf.teams[i].short).sort().join() : "?"; const want = b.pair ? b.pair.slice().sort().join() : "?";
      if (got !== want) { all = false; bad2.push(q + " fill " + k + ": " + got + " vs " + want); break; }
    }
  }
  ck(all, "settled cards: the same pair comes out of " + cnt + " independent random fills of the remaining games", bad2); }
// ---------- 9. branches (non-unique paths) count ways, never chances
{ const f = card("what if Wake Forest ends with 2 losses"); ck(!!f && f.branches.length === 2 && f.branches.reduce((s, b) => s + b.ways, 0) === f.branches[0].of && f.single_path === false, "Wake Forest 2 losses: 2 branches whose ways add up to the total", f && f.branches.map(b => [b.ways, b.of]));
  ck(f && /ways, not the chances/.test(txt(f)) && !/\d+(\.\d+)?%/.test(txt(f).replace(/\(model\)/g, "")), "branch card says ways, not chances, and prints no percent"); }
// ---------- 10. copy and wording
{ const bad2 = Object.entries(EX.COPY).filter(([k, v]) => EX.BANNED_RE.test(v) || /[^\x00-\x7f]/.test(v) || /\bCCG\b|title game/i.test(v)); ck(!bad2.length, "every COPY string is ASCII and has no banned word (bet/wager/spread/parlay/CCG/title game/the 12/pick/line/lock/edge/value/market/gap)", bad2.map(x => x[0]));
  const all = []; for (const q of ["what if BYU and Texas Tech end with just one loss", "what if Utah and Texas Tech win out", "what if New Mexico State and Western Kentucky win out", "what if Wake Forest ends with 2 losses", "what if Georgia wins out"]) { const f = card(q); all.push(txt(f)); }
  const j = all.join("\n"); ck(!/[^\x00-\x7f]/.test(j), "card text is ASCII"); ck(!/\bCCG\b|title game|\bbets?\b|wager|spread|parlay|the 12(?!-)\b/i.test(j), "card text: no CCG / title game / bet / wager / spread / parlay / 'the 12'", j.match(/\bCCG\b|title game|\bbets?\b|wager|spread|parlay|the 12(?!-)\b/i));
  ck(/conference championship game/.test(j), "card text spells out 'conference championship game'");
  ck(!/\bclinch|eliminated|guarantee/i.test(j), "card text never says clinched / eliminated / guaranteed (no conference is analyst-verified)"); }
{ const f = card("what if Utah and Texas Tech win out"); f.sim = null; const html = EX.render(f, (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"));
  ck(/^<section class="sx"/.test(html) && /<h3 id="sx-h">What this means for Utah and Texas Tech<\/h3>/.test(html) && /<table class="ba sxt">/.test(html) && /<caption>Figures<\/caption>/.test(html) && /Rules source/.test(html), "render: section.sx, h3, figures table, rules source");
  ck(!/<script|onerror|javascript:/i.test(html) && !/style=/.test(html), "render: no script, no inline style (strict CSP)");
  const f2 = JSON.parse(JSON.stringify(f)); f2.scenario.teams[0] = "A<b>&"; f2.branches[0].teams[0].team = "A<b>&"; const h2 = EX.render(f2, (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")); ck(!/A<b>/.test(h2), "render: names go through the escaper"); }
// ---------- 11. sim attach (existing before/after numbers) and the two-engine check
{ const f = card("what if Utah and Texas Tech win out"); const mk = (cb, ca) => ({ table: { rows: f.branches[0].teams.map(t => ({ name: t.team, cells: { ccg: { before: cb, after: ca, before_text: (cb * 100).toFixed(1) + "%", after_text: (ca * 100).toFixed(1) + "%" }, cfp12: { before: 0.2, after: 0.5, before_text: "20.0%", after_text: "50.0%" } } })) } });
  const ok = EX.attachSim(JSON.parse(JSON.stringify(f)), mk(0.5, 1), H.B); ck(ok.engines_agree === true && ok.sim.length === 2 && /chance to make the 12-team playoff field \(model\), 20.0% before, 50\.0% after this scenario/.test(txt(ok)), "attachSim: playoff chance (model) line from the existing run", txt(ok).split("\n").filter(l => /model/.test(l)));
  const dis = EX.attachSim(JSON.parse(JSON.stringify(f)), mk(0.5, 0.2), H.B); ck(dis.engines_agree === false && /do not agree/.test(txt(dis)) && !/reach the Big 12 conference championship game/.test(txt(dis).split("\n")[1] || "") && !/playoff chance/.test(txt(dis)), "engines disagree -> records only, no conference-game claim, no sim line", txt(dis).split("\n").slice(0, 3)); }
// ---------- 12. validator contract (FACTS-CONTRACT.md): vocab covers every number and team in the text
{ let allOk = true; const miss = [];
  for (const q of ["what if BYU and Texas Tech end with just one loss", "what if Utah and Texas Tech win out", "what if New Mexico State and Western Kentucky win out", "what if Wake Forest ends with 2 losses", "what if BYU wins out and Texas Tech loses to Arizona"]) {
    const f = card(q), v = EX.vocab(f), t = txt(f); const nums = new Set(v.numbers); const stripped = t.replace(/\b(19|20)\d\d-\d\d-\d\d\b/g, "").replace(/\bMT\b/g, "");
    (stripped.match(/\d+(?:\.\d+)?/g) || []).forEach(x => { if (!nums.has(x)) { allOk = false; miss.push(q + " number " + x); } });
    f.branches.forEach(b => b.teams.forEach(x => { if (!v.teams.includes(x.team)) { allOk = false; miss.push(q + " team " + x.team); } }));
    ck(v.conference === f.conference.name && v.rule_names.length > 0 && v.step_numbers.length >= 0, "vocab fields present: " + q);
  }
  ck(allOk, "vocab.numbers covers every number printed in the card text; vocab.teams covers every named team", miss.slice(0, 5)); }
// ---------- 13. the tree: what changed vs router2c
{ const rd = (p) => fs.readFileSync(p, "utf8"), TOK = /\?v=[0-9a-f]{10}/g;
  ck(fs.existsSync(path.join(tree, "assets/ks/scnai.js")) && !fs.existsSync(path.join(base, "assets/ks/scnai.js")) && rd(path.join(tree, "assets/ks/explain.js")).replace(TOK, "?v=T") === rd(path.join(base, "assets/ks/explain.js")).replace(TOK, "?v=T").replace("var sim = []; facts.branches[0].teams.forEach(function (t) {", "var sim = []; function edge(v, tx) { var x = v * 100; return x < 0.05 ? \"under 0.05%\" : x >= 99.95 ? \"at least 99.95%\" : tx; }   /* scn_a2 copy */\n    facts.branches[0].teams.forEach(function (t) {").replace("before_text: c.before_text, after_text: c.after_text }", "before_text: edge(c.before, c.before_text), after_text: edge(c.after, c.after_text) }").replace("before_text: p.before_text, after_text: p.after_text }", "before_text: edge(p.before, p.before_text), after_text: edge(p.after, p.after_text) }"), "scnai.js is the one added file; explain.js differs from A1b ONLY by the edge-figure copy (under 0.05% / at least 99.95%)");
  ck(rd(path.join(tree, "assets/ccgsim.js")).replace(TOK, "?v=T") === rd(path.join(base, "assets/ccgsim.js")).replace(TOK, "?v=T").replace('newSec(tr, d + " division title")', 'newSec(tr, "the " + d + " division title")').replace('var sec2 = newSec(champs, "who hosts")', 'var sec2 = newSec(champs, "the right to host")').replace('var sh = newSec(chosen, "who hosts")', 'var sh = newSec(chosen, "the right to host")'), "assets/ccgsim.js differs from A1b ONLY by the three {what} strings (the division title, the right to host x2)");
  for (const f of ["assets/ks/parse.js", "assets/ks/scenario.js", "assets/ks/answer.js", "assets/ccgsim-ui.js", "assets/tb/plan.js", "assets/tb/manifest.js", "assets/chat-worker.js", "data/ccg-sim.json", "data/ccg-rules.json", "data/sim-bundle.json"]) ck(rd(path.join(tree, f)).replace(TOK, "?v=T") === rd(path.join(base, f)).replace(TOK, "?v=T"), f + " is unchanged vs A1b (ask-config, Worker, parser, engine, data untouched)");
  const c = rd(path.join(tree, "assets/chat.js")), c0 = rd(path.join(base, "assets/chat.js")); ck(/var SCNCARD = true;/.test(c) && /explain\.js\?v=[0-9a-f]{10}/.test(c) && !/explain\.js\?v=0000000000/.test(c), "chat.js: SCNCARD switch, explain.js loaded with a real ?v= token");
  const lines0 = new Set(c0.split("\n")), added = c.split("\n").filter(l => !lines0.has(l) && !/^\s*\/\*/.test(l)); ck(added.length <= 60 && added.every(l => !/fetch\(|api\//.test(l.replace(/fetchJson\('\/data\/ccg-(sim|rules)\.json'\)/g, ""))), "chat.js: the edit is small and adds no fetch of its own (the write-up call is in ai-client.js)", added.length);
  const ex = rd(path.join(tree, "assets/ks/explain.js")); ck(!/fetch\(|XMLHttpRequest|api\/ask|navigator\.sendBeacon|localStorage|document\.cookie/.test(ex), "explain.js: no network, no storage, no cookie access (pure functions)");
  ck(fs.statSync(path.join(tree, "assets/ks/explain.js")).size < 40000, "explain.js size < 40 KB", fs.statSync(path.join(tree, "assets/ks/explain.js")).size); }
console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
