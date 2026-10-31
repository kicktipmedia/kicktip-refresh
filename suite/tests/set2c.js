/* Set 2c tests (Node, no network, zero model calls): team_trend + ccg_matchup, built DARK. usage: node tests/set2c.js <tree10> [<tree9>]
 * 1 dark state: manifest live:false, nothing answers with the 19 live ids, matcher does not hijack, the test-only switch turns them on
 * 2 matcher tables (positives with params, refusals, boundaries, ties) with the 19 shipped ids + the two new tools on (test switch)
 * 3 ccg_matchup data: recomputed from ccg-games.json + pred-teams + sim-bundle, card text, wording, failure codes
 * 4 team_trend: the shipped not-yet path, then the >=2-point path on FIXTURES generated with tools/gen_trend.js into a temp dir (never shipped), stale / model / season mismatch, ties at 0, independents
 * 5 every card: no card errors, 'estimate' + as-of, lint, digit provenance, no banned words */
"use strict";
const path = require("path"), fs = require("fs"), os = require("os"), cp = require("child_process");
const tree = path.resolve(process.argv[2]), T = require("./lib/tbq.js")(tree), TB = T.TB, C = TB.core;
/* one toolbox instance (modules load once per process); a "fixture" is a set of data-file overrides applied around each call, then restored */
const using = async (ov, f) => { const saved = {}; Object.keys(ov).forEach(k => { saved[k] = T.DATA[k]; T.DATA[k] = ov[k]; }); TB.clearData(); TB.setLive(L21); try { return await f(); } finally { Object.keys(ov).forEach(k => { if (saved[k] === undefined) delete T.DATA[k]; else T.DATA[k] = saved[k]; }); TB.clearData(); } };
const mk = () => { const ov = {}; return { DATA: ov, TB: { setLive: () => {}, card: TB.card, run: (id, p) => using(ov, () => TB.run(id, p)) }, answer: (id, p) => using(ov, () => T.answer(id, p)) }; };
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? "  " + String(typeof x === "string" ? x : JSON.stringify(x)).slice(0, 300) : "")); } else console.log("PASS " + what); };
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const NEWT = ["ccg_matchup", "team_trend"], L21 = L19.concat(NEWT);
const BAN = new RegExp(C.BANNED.source + "|\\b(odds? (of|on) winning|sp\\+|fpi|title game|ccg)\\b|:\\/\\/", "i");
const sub = (a, b) => Object.keys(b).every(k => JSON.stringify(a && a[k]) === JSON.stringify(b[k]));
function cardOk(label, a, extra) {
  if (!a.card) return ck(false, label + ": no card", a.r);
  const c = a.card, t = c.text || "";
  ck(!(c.errors && c.errors.length), label + ": card errors", c.errors);
  ck(/estimate/i.test(t) && /As of /.test(t), label + ": 'estimate' and as-of label");
  ck(!BAN.test(t) && !/Resum\u00e9/i.test(t) && !/[^\x20-\x7E\u2212]/.test(t), label + ": banned wording / non-ASCII (only the true minus U+2212 is allowed, Creative edit 3)", (t.match(BAN) || [])[0]);
  ck(!/\bundefined\b|\bNaN\b|\bnull\b|\[object|\{[a-z0-9_]+\}/i.test(t), label + ": undefined/NaN/unfilled slot");
  ck(!/under 0\.0[0-4]|0\.0[0-4]%|100\.0%/.test(t), label + ": raw edge percent");
  const dp = TB.card.digitProblems(c, ""); ck(!dp.length, label + ": digit provenance", dp);
  ck(!(c.links || []).some(l => !/^\/(method|disclaimer)\/|^\/#(field|top25)$/.test(l.href || "")), label + ": links limited", c.links);
  if (extra) extra(t);
}
const run = async (id, p) => T.answer(id, p);
(async () => {
  const B = T.raw("sim-bundle"), P = T.raw("pred-teams"), G = T.raw("tb/ccg-games"), TR = T.raw("tb/trend"), mtxt = fs.readFileSync(path.join(tree, "assets/tb/manifest.js"), "utf8"), M = JSON.parse(mtxt.slice(mtxt.indexOf("T.manifest=") + 11, mtxt.lastIndexOf(";})(")));
  /* ---------- 1. dark ---------- */
  NEWT.forEach(id => { ck(M.tools[id] && M.tools[id].live === false, id + ": manifest live:false"); ck(TB.get(id) && TB.get(id).live === false, id + ": registered live:false"); });
  const worker = fs.readFileSync(path.join(tree, "_worker.js"), "utf8");
  NEWT.forEach(id => ck(worker.indexOf(id) < 0, id + ": id not in _worker.js"));
  TB.setLive(L19);
  for (const q of ["Who will play in the SEC championship game?", "When is the ACC championship game?", "How has Utah's playoff chance changed?", "Who moved the most this week?"]) { const m = await T.match(q); ck(!m || NEWT.indexOf(m.tool) < 0, "dark (19 live): '" + q + "' does not route to a new tool", m); }
  TB.setLive(L19); const dk = await T.match("Who will play in the SEC championship game?", { dark: true }); ck(dk && dk.tool === "ccg_matchup", "test-only switch opts.dark turns the new rules on", dk);
  TB.setLive(L21); ck((await T.match("Who will play in the SEC championship game?")).tool === "ccg_matchup", "test switch setLive(21 ids) answers");
  for (const only of NEWT) { TB.setLive(L19.concat([only])); const o = NEWT.filter(x => x !== only)[0]; const q = only === "ccg_matchup" ? "When is the ACC championship game?" : "Who moved the most this week?"; const q2 = only === "ccg_matchup" ? "Who moved the most this week?" : "When is the ACC championship game?"; ck((await T.match(q)) && (await T.match(q)).tool === only, only + ": flag fixture, listed -> answers"); const m2 = await T.match(q2); ck(!m2 || m2.tool !== o, only + ": flag fixture, the other tool stays absent", m2); }
  TB.setLive([]); ck(!(await T.match("When is the ACC championship game?")), "list empty -> absent");

  /* ---------- 2. matcher tables (21 on) ---------- */
  TB.setLive(L21);
  const CM = [
    ["Who will play in the Big 12 championship game?", { conference: "big12", view: "all" }], ["Most likely Big 12 championship matchup", { conference: "big12", view: "pairs" }], ["Who is likely to play in the SEC championship game?", { conference: "sec", view: "pairs" }],
    ["Who plays in the ACC conference championship game?", { conference: "acc", view: "all" }], ["Which teams could be in the Big Ten championship game?", { conference: "big10" }], ["Who might play in the Pac-12 championship game?", { conference: "pac12" }],
    ["Sun Belt championship matchups", { conference: "belt" }], ["Mountain West championship game matchup", { conference: "mwest", view: "pairs" }], ["Who is in the MAC championship game?", { conference: "midam" }], ["Who will face Utah in the Big 12 championship game?", null],
    ["When is the SEC championship game?", { conference: "sec", view: "date" }], ["Where is the ACC championship game?", { conference: "acc", view: "place" }], ["Where and when is the Big Ten championship game?", { conference: "big10", view: "all" }],
    ["What time is the Big 12 championship game?", { conference: "big12", view: "date" }], ["What city hosts the Big 12 championship game?", { conference: "big12", view: "place" }], ["Sun Belt championship game date", { conference: "belt", view: "date" }],
    ["who plays in the Big 12 title game", { conference: "big12" }], ["what is the CCG date for the ACC", { conference: "acc", view: "date" }], ["Conference USA championship game location", { conference: "usa", view: "place" }], ["American conference championship game date", { conference: "American", view: "date" }],
    ["When is the championship game?", { conference: "sec", view: "date" }, { mode: "conference", conf: "sec", conference: "sec" }], ["Who will play in the championship game?", { conference: "acc", view: "all" }, { mode: "conference", conf: "acc", conference: "acc" }],
    ["Mid-American championship game date", { conference: "midam", view: "date" }],
    /* refusals: other tools or the AI path */
    ["Who will win the Big 12 championship game?", null], ["Who wins the SEC championship game?", null], ["Who is still in the race for the Big 12 championship game?", "conf_race_alive"], ["Is Utah in the Big 12 championship game?", null], ["Can Arizona State still reach the Big 12 championship game?", "conf_race_alive"],
    ["What does BYU need to reach the Big 12 championship game?", "team_needs"], ["What are Utah's chances to reach the Big 12 championship game?", null], ["When is the Independents championship game?", null], ["Notre Dame championship game", null], ["When is the national championship game?", null], ["Who plays in the national championship game?", null],
    ["What channel is the SEC championship game on?", null], ["Tickets to the SEC championship game", null], ["How does the Big 12 championship game work?", null], ["Who played in the SEC championship game last year?", null], ["Big 12 championship game history", null],
    ["Who will play in the Big 12 or SEC championship game?", null], ["Big 12 championship game vs SEC championship game", null], ["Who will play in the Big Ten championship game basketball?", null], ["Who plays in the Pac-12 championship game and who will win", null],
    ["What if Utah beats BYU, who plays in the Big 12 championship game?", null], ["Who plays in the Big 12 championship game, should I bet on it?", null], ["Predict the SEC championship game score", null], ["SEC championship game spread", null], ["Big 12 tiebreakers for the championship game", null],
    ["When is the championship game?", null], ["Who plays in the championship game?", null], ["When is the Big 12 game?", null], ["Who plays in the Big 12?", null], ["When does the Big 12 season end?", null]
  ];
  const TT = [
    ["How has Utah's playoff chance changed?", { team: "utah", metric: "playoff" }], ["Is BYU's chance going up or down?", { team: "byu" }], ["Is Utah's chance going up?", { team: "utah" }], ["Did Utah's rank drop this week?", { team: "utah", metric: "rank" }],
    ["How have Alabama's playoff odds changed since last week?", { team: "alabama", metric: "playoff" }], ["Has Indiana's bye chance gone up?", { team: "indiana", metric: "bye" }], ["Are Ohio State's chances rising or falling?", { team: "ohio-state" }], ["Is Texas Tech's chance of winning the conference trending up?", { team: "texas-tech", metric: "conference" }],
    ["How did Saturday change Arizona's chances?", { team: "arizona" }], ["Is Georgia's ranking going up?", { team: "georgia", metric: "rank" }], ["How has Miami's championship game chance changed?", { clar: true }], ["How has Miami (OH)'s championship game chance changed?", { team: "miami-oh", metric: "championship_game" }],
    ["Has Notre Dame's chance gone down since last week?", { team: "notre-dame" }], ["Utah's playoff chances week over week", { team: "utah", metric: "playoff" }], ["How has the Big 12 team Utah's chance changed?", { team: "utah" }], ["Is the Utes' chance moving?", { team: "utah" }],
    ["Who moved the most this week?", {}], ["Biggest risers this week", {}], ["Biggest fallers in playoff odds", { metric: "playoff" }], ["Top 5 risers", { n: 5 }], ["Top 3 fallers in the rankings", { n: 3, metric: "rank" }], ["Who moved up the most in the rankings?", { metric: "rank" }],
    ["Which teams are rising?", null], ["Who is rising the fastest?", {}], ["Who is trending up?", {}], ["Biggest movers in bye chances", { metric: "bye" }],
    /* refusals */
    ["Why did Utah's chance drop?", null], ["How do injuries change Utah's chances?", null], ["What if Utah beats BYU, does their chance go up?", null], ["How would a loss change Utah's chances?", null], ["How does Utah's chance compare with BYU's?", null], ["Utah's chance", null], ["What are Utah's playoff chances?", null],
    ["What is Utah's rank?", "team_snapshot"], ["Where is Utah ranked?", "team_snapshot"], ["Top 10 teams", "rankings_list"], ["Top 25 risers", "rankings_list"], ["Biggest movers in the Big 12", null], ["Biggest risers in the Top 25", null], ["Is Utah's chance of making the playoff going up and Utah vs BYU", null],
    ["How has Utah's chance changed since last year?", null], ["Has Utah's chance changed since 2024?", null], ["Is the over under going up?", null], ["Utah's stock is going up", null], ["Did Utah's basketball rank drop?", null], ["Should I bet on Utah going up?", null], ["Has Utah moved?", null],
    ["Who has the biggest games this week?", null], ["Which games matter the most?", "games_that_matter"], ["Is Tech's chance going up?", { clar: true }], ["Is the Bears' chance going up?", "team_trend"], ["Who moved the most, Utah or BYU?", null]
  ];
  const tableRun = async (name, tbl, tool) => {
    ck(tbl.length >= 40 && tbl.filter(x => x[1] === null).length >= 14, name + ": table size (>=40 rows, >=14 refusals)");
    for (const [q, exp, page] of tbl) {
      const m = await T.match(q, page ? { page } : undefined), lab = name + ' "' + q + '"';
      if (exp === null) { ck(!m || m.tool !== tool, lab + " -> not " + tool, m); continue; }
      if (typeof exp === "string") { ck(!!m && m.tool === exp, lab + " -> " + exp + " (boundary, other tool keeps it)", m); continue; }
      if (exp.clar) { ck(!!(m && m.tool === tool && m.clarify) || !m || m.tool !== tool, lab + " -> clarify or no hijack", m); continue; }
      const ok = !!(m && m.tool === tool && !m.clarify && sub(m.params, exp));
      ck(ok, lab + " -> " + tool + " " + JSON.stringify(exp), m);
    }
  };
  await tableRun("ccg_matchup", CM, "ccg_matchup"); await tableRun("team_trend", TT, "team_trend");
  /* ties: no phrase of either table gets two different tools within the band (null with both live) */
  { let bad2 = []; for (const [q, exp, page] of CM.concat(TT)) { if (exp && typeof exp === "object" && !exp.clar) { const m = await T.match(q, page ? { page } : undefined); if (!m) bad2.push(q); } } ck(!bad2.length, "every positive phrase routes (no tie to null with all 21 on)", bad2); }
  { const m = await T.match("Is Tech's chance going up?"); ck(!m || m.tool !== "team_trend" || (m.clarify && m.clarify.param === "team"), "bare 'Tech' never one team", m); }
  { const m = await T.match("Is Utah State's chance going up?"); ck(m && m.tool === "team_trend" && m.params.team === "utah-state", "Utah State by name", m); const m2 = await T.match("Is the Aggies' chance going up?"); ck(!m2 || m2.tool !== "team_trend" || !!m2.clarify, "bare Aggies is a chooser or no match", m2); }
  { const m = await T.match("Is the U's chance going up?"); ck(m && m.tool === "team_trend" && m.params.team === "utah", "'the U' = Utah", m); }
  for (const q of ["How has Utah's playoff chance changed?", "Who moved the most this week?"]) { const w = await T.match(q, { page: { mode: "home" } }); ck(w, "home page route: " + q); }

  /* ---------- 3. ccg_matchup ---------- */
  TB.setLive(L21);
  ck(G.asof === B.as_of && G.seasons === 10000 && /^[0-9-]+ [0-9:]+ MT$/.test(G.asof), "ccg-games.json: as-of equals sim-bundle, 10,000 seasons");
  const confs = Object.keys(G.confs).sort(); ck(JSON.stringify(confs) === JSON.stringify(C.CONF_IDS.filter(x => x !== "ind").sort()), "ccg-games.json: every conference but independents", confs);
  /* ccg.json not needed */
  const teamConf = {}, names = {}; B.teams.forEach(t => { if (t.g) { teamConf[t.g] = t.c; names[t.g] = t.s; } });
  for (const cf of confs) {
    const E = G.confs[cf], tot = E.pairs.reduce((s, p) => s + p[2], 0);
    ck(E.games === G.seasons && tot <= G.seasons && E.pairs.length === 5, cf + ": pair counts <= games");
    ck(E.pairs.every((p, i) => p[0] < p[1] && teamConf[p[0]] === cf && teamConf[p[1]] === cf && (i === 0 || E.pairs[i - 1][2] >= p[2])), cf + ": pairs sorted, in conference, slugs ordered");
    const by = {}; E.pairs.forEach(p => { by[p[0]] = (by[p[0]] || 0) + p[2]; by[p[1]] = (by[p[1]] || 0) + p[2]; });
    ck(Object.keys(by).every(g => by[g] / G.seasons <= (P.teams[g].c || 0) + 0.03), cf + ": a team's listed pairs never exceed its chance to reach the game by more than 3 points (different simulator run)", by);
    const a = await run("ccg_matchup", { conference: cf }); cardOk("ccg_matchup " + cf, a, t => { ck(/conference championship game/.test(t) && !/\bccg\b|title game/i.test(t), cf + ": says 'conference championship game', never CCG / title game"); ck(/\bchance\b/.test(t) && !/\(model\)/.test(t), cf + ": 'chance' wording, no (model) label (home6c ruling)"); });
    const f = a.r.facts, want = E.pairs.filter(p => p[2] / G.seasons >= 0.02).slice(0, 3);
    ck(f.pairs.length === want.length && f.pairs.every((p, i) => p.a.id === want[i][0] && p.b.id === want[i][1] && Math.abs(p.chance - want[i][2] / G.seasons) < 1e-12), cf + ": pairs recomputed from the export (top 3, >= 2%)");
    const tw = Object.keys(P.teams).filter(g => teamConf[g] === cf && P.teams[g].c > 0).sort((x, y) => P.teams[y].c - P.teams[x].c || (names[x] < names[y] ? -1 : 1)).slice(0, 4);
    ck(JSON.stringify(f.teams.map(t => t.id)) === JSON.stringify(tw) && f.teams.every(t => t.chance === P.teams[t.id].c), cf + ": teams recomputed from pred-teams (top 4 by chance to reach the game)");
    ck(want.every(p => a.card.text.indexOf(((p[2] / G.seasons) * 100).toFixed(1) + "%") >= 0), cf + ": every pair chance appears in the card text with one decimal");
    ck(!E.pairs.some(p => p.length !== 3) && !/tv/i.test(JSON.stringify(E).replace(/"time_text"[^,]*/g, "")), cf + ": no TV text in export");
  }
  { const a = await run("ccg_matchup", { conference: "big12", view: "date" }); cardOk("ccg_matchup date", a, t => ck(/Fri Dec 4, 7:00 PM CT/.test(t) && !/Most likely matchups/.test(t), "date view: date and time only")); const b = await run("ccg_matchup", { conference: "big12", view: "place" }); cardOk("ccg_matchup place", b, t => ck(/AT&T Stadium, Arlington/.test(t) && !/7:00 PM/.test(t), "place view: place only")); }
  { const r = await TB.run("ccg_matchup", { conference: "ind" }); ck(!r.ok && r.reason === "not_applicable", "independents -> not_applicable", r); }
  { const r = await TB.run("ccg_matchup", {}); ck(!r.ok && r.reason === "bad_param", "no conference -> bad_param", r); const r2 = await TB.run("ccg_matchup", { conference: "xx" }); ck(!r2.ok && r2.reason === "bad_param", "unknown conference -> bad_param", r2); }
  /* stale / broken data -> no_data, never a made-up card */
  for (const [lab, mut] of [["stale as-of", g => { g.asof = "2026-10-20 17:58 MT"; }], ["games != seasons", g => { g.confs.sec.games = 9000; }], ["team in wrong conference", g => { g.confs.sec.pairs[0][0] = "byu"; }], ["unknown team", g => { g.confs.sec.pairs[0][0] = "nowhere-u"; }], ["missing conference", g => { delete g.confs.sec; }]]) {
    const T2 = mk(); T2.DATA["tb/ccg-games"] = JSON.parse(JSON.stringify(G)); mut(T2.DATA["tb/ccg-games"]); T2.TB.setLive(L21); const r = await T2.TB.run("ccg_matchup", { conference: "sec" }); ck(!r.ok && r.reason === "no_data", "ccg_matchup " + lab + " -> no_data", r);
  }
  { const T2 = mk(); T2.DATA["tb/ccg-games"] = JSON.parse(JSON.stringify(G)); T2.DATA["tb/ccg-games"].confs.sec.pairs = [["alabama", "georgia", 100], ["georgia", "texas", 90]]; T2.TB.setLive(L21); const a = await T2.answer("ccg_matchup", { conference: "sec" }); ck(a.card && a.card.text.indexOf("No single matchup has a chance of 2% or more.") >= 0 && !a.card.errors.length, "no pair at 2% -> the empty line, no pair listed"); }

  /* toolbox10b (Creative's edits): headings, example, division note gating */
  { const cm = TB.get("ccg_matchup"); ck(cm.examples[0] === "Who is likely to play in the SEC championship game?" && M.tools.ccg_matchup.examples[0] === cm.examples[0] && JSON.stringify(M.tools).indexOf("Who will play in the SEC") < 0, "example reads 'Who is likely to play in the SEC championship game?' in tool and manifest", cm.examples);
    const sc = await run("ccg_matchup", { conference: "sec" }); cardOk("ccg sec headings", sc, t => ck(t.indexOf("Teams most likely to reach the conference championship game, chance") >= 0 && t.indexOf("(model)") < 0 && t.indexOf("reach the game,") < 0, "hTeams spells out the conference championship game", t));
    ck(cm.copy.eTeams === "No team has a listed chance of reaching the conference championship game." && cm.copy.ePairs.t === "No single matchup has a chance of 2% or more.", "eTeams new text, ePairs unchanged");
    const T2 = mk(); T2.DATA["tb/ccg-games"] = JSON.parse(JSON.stringify(G)); T2.TB.setLive(L21);
    const divs = Object.keys(G.confs).filter(k => G.confs[k].fmt === "div"); ck(divs.length === 1 && divs[0] === "belt", "data: only the Sun Belt has division format today", divs);
    const bl = await T2.answer("ccg_matchup", { conference: "belt" }); cardOk("ccg belt (divisions)", bl, t => ck(t.indexOf("The game is between the two division winners.") >= 0, "belt (divisions): nDiv shown", t));
    for (const c of Object.keys(G.confs).filter(k => k !== "belt")) { const a = await T2.answer("ccg_matchup", { conference: c }); cardOk("ccg " + c + " (no divisions)", a, t => ck(t.indexOf("division winners") < 0, c + ": nDiv not shown", t)); }
    for (const v of ["date", "place", "pairs"]) { const a = await T2.answer("ccg_matchup", { conference: "belt", view: v }); cardOk("ccg belt view " + v, a, t => ck(t.indexOf("division winners") < 0 || v === "pairs", "belt " + v + ": nDiv only on all/pairs views", t)); }
    const ng = JSON.parse(JSON.stringify(G)); ng.confs.belt.fmt = "top2"; const T3 = mk(); T3.DATA["tb/ccg-games"] = ng; T3.TB.setLive(L21); const b2 = await T3.answer("ccg_matchup", { conference: "belt" }); cardOk("ccg belt flipped to top2", b2, t => ck(t.indexOf("division winners") < 0, "gate follows the data: top-2 format never shows nDiv", t)); }
  /* ---------- 4. team_trend ---------- */
  ck(TR.prev_asof === null && Object.keys(TR.t).length === 0 && TR.asof === B.as_of, "trend.json: not-yet file (prev_asof null, empty t)");
  for (const p of [{}, { team: "utah" }, { team: "notre-dame" }, { metric: "rank", n: 3 }]) { const a = await run("team_trend", p); cardOk("team_trend not-yet " + JSON.stringify(p), a, t => { ck(t.indexOf("Trends start once KickTip has two weekly updates to compare. It needs one more weekly update before it can show movement.") >= 0 && !/snapshot/i.test(t) && !/[0-9]+\.[0-9]%|#\d+|\+\d/.test(t.replace(/Estimate from 10,000 simulated seasons\. As of [^.]*\./, "")), "not-yet card has no made-up numbers"); }); }
  { /* the not-yet card does not depend on the as-of: stale as-of still shows it (nothing to compare, nothing to go stale) */ const T2 = mk(); T2.DATA["tb/trend"] = Object.assign({}, TR, { asof: "2026-10-20 17:58 MT" }); T2.TB.setLive(L21); const r = await T2.TB.run("team_trend", {}); ck(r.ok && r.facts.not_yet === true, "not-yet card ignores a stale as-of"); }
  /* fixtures: two snapshots, generated by tools/gen_trend.js into a temp dir; never shipped */
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tb10trend_")), W = f => path.join(tmp, f), gen = args => cp.spawnSync("node", [path.join(__dirname, "..", "tools", "gen_trend.js")].concat(args), { encoding: "utf8" });
  const prevPred = JSON.parse(JSON.stringify(P)), prevB = JSON.parse(JSON.stringify(B)); prevB.as_of = "2026-10-20 17:58 MT";
  const mv = (g, k, d) => { prevPred.teams[g][k] = Math.max(0, Math.min(1, +(prevPred.teams[g][k] - d).toFixed(4))); };
  mv("utah", "p", 0.05); mv("byu", "p", -0.031); mv("alabama", "p", 0.0); mv("texas", "p", 0.004); mv("indiana", "p", 0.0123); mv("georgia", "p", -0.0123); mv("ohio-state", "p", 0.0099); mv("miami", "p", 0.011);
  mv("utah", "b", 0.02); mv("utah", "c", 0.04); mv("utah", "w", -0.01); mv("notre-dame", "p", 0.02); mv("notre-dame", "b", 0.01);
  /* rank fixtures: swap rating so ranks move: lower Utah's old rating below ten teams, raise BYU's by one place */
  const rk1 = (b, g) => { const r = b.model.rating.slice(0, b.fcs), i = b.teams.findIndex(t => t.g === g); let k = 1; for (let j = 0; j < r.length; j++) if (r[j] > r[i] || (r[j] === r[i] && j < i)) k++; return k; };
  const ix = g => prevB.teams.findIndex(t => t.g === g); prevB.model.rating[ix("utah")] -= 3.0;
  const uNow = rk1(B, "utah"), uPrev = rk1(prevB, "utah"); ck(uPrev > uNow, "fixture: Utah's old rank is worse than now", [uNow, uPrev]);
  fs.writeFileSync(W("prevPred.json"), JSON.stringify(prevPred)); fs.writeFileSync(W("prevB.json"), JSON.stringify(prevB));
  let g1 = gen(["--pred", W("prevPred.json"), "--bundle", W("prevB.json"), "--out", W("junk.json"), "--snap-out", W("prev-snap.json")]); ck(g1.status === 0 && fs.existsSync(W("prev-snap.json")), "gen_trend: writes the weekly snapshot", g1.stderr);
  let g2 = gen(["--pred", path.join(tree, "data/pred-teams.json"), "--bundle", path.join(tree, "data/sim-bundle.json"), "--out", W("trend.json"), "--prev", W("prev-snap.json")]); ck(g2.status === 0, "gen_trend: writes the two-point file", g2.stderr);
  const FX = JSON.parse(fs.readFileSync(W("trend.json"), "utf8"));
  ck(FX.prev_asof === "2026-10-20 17:58 MT" && FX.asof === B.as_of && Object.keys(FX.t).length === 138 && FX.t.utah.p.length === 2, "fixture trend.json: 138 teams, [now, prev] pairs", [FX.prev_asof, Object.keys(FX.t).length]);
  ck(FX.t.utah.rk[0] === uNow && FX.t.utah.rk[1] === uPrev && Math.abs(FX.t.utah.p[0] - P.teams.utah.p) < 1e-12 && Math.abs(FX.t.utah.p[1] - prevPred.teams.utah.p) < 1e-12, "fixture: values equal the two sources");
  { const wrong = JSON.parse(fs.readFileSync(W("prev-snap.json"), "utf8")); wrong.model = "elo"; fs.writeFileSync(W("wrong-model.json"), JSON.stringify(wrong)); const g = gen(["--pred", path.join(tree, "data/pred-teams.json"), "--bundle", path.join(tree, "data/sim-bundle.json"), "--out", W("x.json"), "--prev", W("wrong-model.json")]); ck(g.status === 3, "gen_trend refuses a previous snapshot from another model (exit 3)");
    wrong.model = B.model_id; wrong.seasons = 6000; fs.writeFileSync(W("wrong-n.json"), JSON.stringify(wrong)); ck(gen(["--pred", path.join(tree, "data/pred-teams.json"), "--bundle", path.join(tree, "data/sim-bundle.json"), "--out", W("x.json"), "--prev", W("wrong-n.json")]).status === 3, "gen_trend refuses another season count (exit 3)");
    wrong.seasons = 10000; wrong.asof = "2026-11-20 17:58 MT"; fs.writeFileSync(W("newer.json"), JSON.stringify(wrong)); ck(gen(["--pred", path.join(tree, "data/pred-teams.json"), "--bundle", path.join(tree, "data/sim-bundle.json"), "--out", W("x.json"), "--prev", W("newer.json")]).status === 3, "gen_trend refuses a previous snapshot that is not older (exit 3)"); }
  const withFx = async (fx, f) => { const T2 = mk(); T2.DATA["tb/trend"] = fx; await f(T2); };
  await withFx(FX, async T2 => {
    const u = await T2.answer("team_trend", { team: "utah" }); cardOk("team_trend utah (2 points)", u, t => {
      const dp = ((P.teams.utah.p - prevPred.teams.utah.p) * 100).toFixed(1);
      ck(t.indexOf("Make the 12-team playoff field: " + (P.teams.utah.p * 100).toFixed(1) + "%, +" + dp + " points from last week (" + (prevPred.teams.utah.p * 100).toFixed(1) + "%)") >= 0, "utah: playoff row recomputed", t);
      ck(t.indexOf("Win the conference:") >= 0 && t.indexOf("Make conference championship:") >= 0 && t.indexOf("Earn a first-round bye:") >= 0, "utah: all five rows present");
      ck(t.indexOf("KickTip rank: #" + uNow + ", up " + (uPrev - uNow) + " places from last week (was #" + uPrev + ")") >= 0, "utah: rank row says up N places", t);
      ck(!/ pts\b/.test(t) && /\+\d+\.\d points from last week/.test(t), "movement size reads points, not pts");
      ck(/Last week means the update of Oct 20, 2026, 5:58 PM MT/.test(t), "last-week as-of named");
    });
    const by = await T2.answer("team_trend", { team: "byu" }); cardOk("team_trend byu (falls)", by, t => ck(t.indexOf("\u22123.1 points from last week") >= 0 && t.indexOf("-3.1") < 0, "byu: a fall shows a true minus, \u22123.1 points", t));
    const al = await T2.answer("team_trend", { team: "alabama" }); cardOk("team_trend alabama (flat)", al, t => ck(/Make the 12-team playoff field: [0-9.]+%, 0\.0 points from last week/.test(t) && /KickTip rank: #\d+, unchanged from last week/.test(t), "alabama: 0.0 points and unchanged rank (a tie at zero)", t));
    const nd = await T2.answer("team_trend", { team: "notre-dame" }); cardOk("team_trend notre-dame (independent)", nd, t => ck(/plays as an independent, so it has no conference chances/.test(t) && !/Win the conference|conference championship game:/.test(t), "independent: no conference rows, explained", t));
    const L = await T2.answer("team_trend", { metric: "playoff", n: 5 }); cardOk("team_trend list playoff", L, t => {
      const f = L.r.facts; const all = Object.keys(FX.t).map(g => ({ g, d: FX.t[g].p[0] - FX.t[g].p[1], nm: B.teams.find(x => x.g === g).s })).filter(x => x.g);
      const rise = all.filter(x => x.d >= 0.01 - 1e-9).sort((a, b) => b.d - a.d || (a.nm < b.nm ? -1 : 1)).slice(0, 5).map(x => x.g), fall = all.filter(x => x.d <= -0.01 + 1e-9).sort((a, b) => a.d - b.d || (a.nm < b.nm ? -1 : 1)).slice(0, 5).map(x => x.g);
      ck(JSON.stringify(f.rise.map(x => x.id)) === JSON.stringify(rise) && JSON.stringify(f.fall.map(x => x.id)) === JSON.stringify(fall), "list: risers and fallers recomputed (>= 1 point, top 5)", [f.rise.map(x => x.id), rise]);
      ck(f.rise[0].id === "utah" && f.fall[0].id === "byu", "list: Utah first riser, BYU first faller");
      ck(!f.rise.concat(f.fall).some(x => ["alabama", "texas"].indexOf(x.id) >= 0), "list: moves under a point are not listed (Alabama 0, Texas 0.4)");
      ck(f.rise.concat(f.fall).every(x => Math.abs(x.delta) >= 0.0099), "list: every listed move is a point or more");
      ck(/Biggest movers: chance to make the 12-team playoff field/.test(t) && /Rising since last week/.test(t) && /Falling since last week/.test(t), "list: title and both headings");
    });
    const L1 = await T2.answer("team_trend", { metric: "playoff", n: 1 }); cardOk("team_trend list n=1", L1, () => ck(L1.r.facts.rise.length === 1 && L1.r.facts.fall.length === 1, "n=1 gives one riser and one faller"));
    const LR = await T2.answer("team_trend", { metric: "rank", n: 5 }); cardOk("team_trend list rank", LR, t => { const f = LR.r.facts; ck(f.rise[0].id === "utah" || f.fall.length > 0, "rank list: movers listed", f); ck(f.rise.concat(f.fall).every(x => x.k >= 1), "rank list: every mover moved at least one place"); ck(/places from last week \(was #\d+\)|one place from last week/.test(t), "rank list wording"); });
    for (const m of ["bye", "conference", "championship_game"]) { const a = await T2.answer("team_trend", { metric: m }); cardOk("team_trend list " + m, a); }
    /* ties at zero: two teams with the same delta sort by name */
    const TF = JSON.parse(JSON.stringify(FX)); TF.t["byu"].p = [0.5, 0.45]; TF.t["utah"].p = [0.5, 0.45]; TF.t["arizona"].p = [0.5, 0.45];
    const T3 = mk(); T3.DATA["tb/trend"] = TF; T3.TB.setLive(L21); const tl = await T3.TB.run("team_trend", { metric: "playoff", n: 10 }); const tied = tl.facts.rise.filter(x => Math.abs(x.delta - 0.05) < 1e-9).map(x => x.name);
    ck(JSON.stringify(tied) === JSON.stringify(tied.slice().sort()) && tied.length >= 3, "ties sort by team name", tied);
  });
  for (const [lab, mut] of [["stale as-of", f => { f.asof = "2026-10-26 17:58 MT"; }], ["model mismatch", f => { f.prev_model = "elo"; }], ["season mismatch", f => { f.prev_seasons = 6000; }], ["prev not older", f => { f.prev_asof = f.asof; }], ["empty t", f => { f.t = {}; }]]) {
    const F2 = JSON.parse(JSON.stringify(FX)); mut(F2); await withFx(F2, async T2 => { for (const p of [{ team: "utah" }, {}]) { const r = await T2.TB.run("team_trend", p); ck(!r.ok && r.reason === "no_data", "team_trend " + lab + " " + JSON.stringify(p) + " -> no_data", r); } });
  }
  await withFx(FX, async T2 => { const F2 = JSON.parse(JSON.stringify(FX)); delete F2.t.utah; T2.DATA["tb/trend"]; const T3 = mk(); T3.DATA["tb/trend"] = F2; T3.TB.setLive(L21); const r = await T3.TB.run("team_trend", { team: "utah" }); ck(!r.ok && r.reason === "no_data", "team_trend team missing from the file -> no_data"); const r2 = await T3.TB.run("team_trend", { team: "nowhere" }); ck(!r2.ok && r2.reason === "bad_param", "unknown team -> bad_param"); const r3 = await T3.TB.run("team_trend", { n: 11 }); ck(!r3.ok && r3.reason === "bad_param", "n=11 -> bad_param"); });
  fs.rmSync(tmp, { recursive: true, force: true });
  ck(!fs.existsSync(path.join(tree, "data/tb/trend-fixture.json")), "no fixture file inside the tree");
  console.log("\n" + n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})();
