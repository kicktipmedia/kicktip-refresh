/* Set 2b tests (Node, no network, zero model calls): strength_of_record + conf_vs_conf and their exports, built DARK. usage: node tests/set2b_sor_cvc.js <tree> [<pipeline dir>]
 * 1 dark state: manifest live:false, ids not in _worker.js, 21 live ids never route to them, test switch turns them on
 * 2 matcher tables (positives with params, refusals, boundaries) with the 21 shipped ids + the two new tools on
 * 3 resume.json: shape, ranks 1..n, as-of, recompute of z / rk from the pipeline's colley + sor (when the pipeline is given), and the card's numbers
 * 4 conf-bids.json: rows sum to seasons, mean bids within 1.4 of the sum of p per conference, card numbers recomputed; nonconf / top25 / strength recomputed independently
 * 5 failure codes (stale as-of, bad params) and every card: no errors, as-of, lint, digit provenance, banned words, no accents, no rating names */
"use strict";
const path = require("path"), fs = require("fs"), cp = require("child_process");
const tree = path.resolve(process.argv[2]), PIPE = process.argv[3] || "/workspace/kicktip-bracketfit", T = require("./lib/tbq.js")(tree), TB = T.TB, C = TB.core;
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? "  " + String(typeof x === "string" ? x : JSON.stringify(x)).slice(0, 300) : "")); } else console.log("PASS " + what); };
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const L21 = L19.concat(["ccg_matchup", "team_trend"]), NEWT = ["strength_of_record", "conf_vs_conf"], L23 = L21.concat(NEWT);
const BAN = new RegExp(C.BANNED.source + "|\\b(odds? (of|on) winning|sp\\+|fpi|espn|title game|ccg|strength of record|the 12(?!-team)|wager\\w*|parlay\\w*|bets?)\\b|:\\/\\/|\\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \\d", "i");
const sub = (a, b) => Object.keys(b).every(k => JSON.stringify(a && a[k]) === JSON.stringify(b[k]));
const using = async (ov, f) => { const saved = {}; Object.keys(ov).forEach(k => { saved[k] = T.DATA[k]; T.DATA[k] = ov[k]; }); TB.clearData(); TB.setLive(L23); try { return await f(); } finally { Object.keys(ov).forEach(k => { T.DATA[k] = saved[k]; }); TB.clearData(); } };
function cardOk(label, a) {
  if (!a.card) return ck(false, label + ": no card", a.r);
  const c = a.card, t = c.text || "", body = t.replace(/As of [^.]*?\d{4}, [^.]*?MT\./, "");
  ck(!(c.errors && c.errors.length), label + ": card errors", c.errors);
  ck(/As of /.test(t) && /estimate/i.test(t), label + ": as-of + estimate footer");
  ck(!BAN.test(body), label + ": banned wording / dates in copy", (body.match(BAN) || [])[0]);
  ck(!/[^\x20-\x7E\u2212]/.test(t) && !/resum\u00e9/i.test(t), label + ": ASCII only, no accent");
  ck(!/\bundefined\b|\bNaN\b|\bnull\b|\[object|\{[a-z0-9_]+\}/i.test(t), label + ": no unfilled slot");
  const dp = TB.card.digitProblems(c, ""); ck(!dp.length, label + ": digit provenance", dp);
}
(async () => {
  const B = T.raw("sim-bundle"), P = T.raw("pred-teams"), R = T.raw("tb/resume"), K = T.raw("tb/conf-bids"), POL = T.raw("polls");
  const mtxt = fs.readFileSync(path.join(tree, "assets/tb/manifest.js"), "utf8"), M = JSON.parse(mtxt.slice(mtxt.indexOf("T.manifest=") + 11, mtxt.lastIndexOf(";})(")));
  /* 1 dark */
  NEWT.forEach(id => { ck(M.tools[id] && M.tools[id].live === false, id + ": manifest live:false"); ck(TB.get(id) && TB.get(id).live === false, id + ": registered live:false"); });
  const worker = fs.readFileSync(path.join(tree, "_worker.js"), "utf8"); const V1 = require("./lib/vis1_expect.cjs"), LST = (nm) => JSON.parse(worker.match(new RegExp("^const " + nm + " = (\\[.*\\]);$", "m"))[1].replace(/'/g, '"')), RT = JSON.parse(worker.match(/^const ROUTER_TOOLS = (\{.*\});$/m)[1]);
  NEWT.forEach(id => ck(LST("TB_LIVE_TOOLS").includes(id) && LST("TB_TOOL_IDS").includes(id) && !!RT[id], id + ": live in _worker.js (vis1: TB_LIVE_TOOLS, TB_TOOL_IDS, ROUTER_TOOLS)"));
  ck(JSON.stringify(LST("TB_LIVE_TOOLS")) === JSON.stringify(V1.ALL22) && JSON.stringify(LST("TB_TOOL_IDS")) === JSON.stringify(V1.ALL22), "set3m: both Worker lists are exactly the 22 ids (vis1 21 + game_win_chance)");
  ck(M.data["tb/resume"] && M.data["tb/conf-bids"], "manifest lists both new data files");
  const DQ = ["What is Utah's resume rank?", "Who has the best resume?", "How many playoff teams will the SEC get?", "Big Ten vs SEC", "Non-conference record by conference"];
  TB.setLive(L21); for (const q of DQ) { const m = await T.match(q); ck(!m || NEWT.indexOf(m.tool) < 0, "dark (21 live): '" + q + "' does not route to a new tool", m); }
  TB.setLive(L19); for (const q of DQ) { const m = await T.match(q); ck(!m || NEWT.indexOf(m.tool) < 0, "dark (19 live): '" + q + "'", m); }
  TB.setLive(L21); const dk = await T.match("Who has the best resume?", { dark: true }); ck(dk && dk.tool === "strength_of_record", "opts.dark turns the new rules on", dk);
  /* 2 matcher tables */
  TB.setLive(L23);
  const TAB = [
    ["What is Utah's resume rank?", "strength_of_record", { team: "utah" }], ["Utah resume", "strength_of_record", { team: "utah" }], ["How good is Indiana's resume?", "strength_of_record", { team: "indiana" }],
    ["What is BYU's strength of record?", "strength_of_record", { team: "byu" }], ["Ohio State SOR", "strength_of_record", { team: "ohio-state" }], ["Who has the best resume?", "strength_of_record", {}],
    ["Résumé rankings", "strength_of_record", {}], ["strength of record rankings", "strength_of_record", {}], ["Resume ranking top 5", "strength_of_record", { n: 5 }], ["top 25 resumes", "strength_of_record", { n: 25 }],
    ["ESPN strength of record", null], ["Utah resume according to ESPN", null], ["Will the committee like Utah's resume?", null], ["Utah vs BYU resume", null], ["Utah resume last year", null], ["Kentucky basketball resume", null], ["top 40 resumes", null], ["Help me write a resume for a job", null],
    ["How many playoff teams will the SEC get?", "conf_vs_conf", { metric: "bids", conference: "sec" }], ["How many teams will the Big Ten get in the playoff?", "conf_vs_conf", { metric: "bids", conference: "big10" }],
    ["Will the Big 12 get at least 2 teams in the playoff?", "conf_vs_conf", { metric: "bids", conference: "big12", at_least: 2 }], ["Playoff bids by conference", "conf_vs_conf", { metric: "bids" }],
    ["ACC vs Big 12 playoff bids", "conf_vs_conf", { metric: "bids", conference: "acc", conference2: "big12" }], ["Big Ten vs SEC", "conf_vs_conf", { metric: "strength", conference: "big10", conference2: "sec" }],
    ["Is the SEC better than the Big Ten?", "conf_vs_conf", { metric: "strength", conference: "sec", conference2: "big10" }], ["Compare the ACC, Big 12 and Pac-12", "conf_vs_conf", { metric: "strength", conference: "acc", conference2: "big12", conference3: "pac12" }],
    ["What is the best conference?", "conf_vs_conf", { metric: "strength" }], ["Which conference has the most top 25 teams?", "conf_vs_conf", { metric: "top25_count" }], ["SEC vs Big Ten ranked teams", "conf_vs_conf", { metric: "top25_count", conference: "sec", conference2: "big10" }],
    ["Non-conference record by conference", "conf_vs_conf", { metric: "nonconf_record" }], ["SEC non-conference record", "conf_vs_conf", { metric: "nonconf_record", conference: "sec" }],
    ["SEC standings", "conf_standings"], ["Utah vs BYU", null, null, "conf_vs_conf"], ["Will Utah make the playoff?", null, null, "conf_vs_conf"], ["SEC vs Big Ten basketball", null], ["SEC vs Big Ten all time", null], ["Who will play in the SEC championship game?", "ccg_matchup"]
  ];
  for (const [q, tool, p, notTool] of TAB) {
    const m = await T.match(q);
    if (notTool) ck(!m || m.tool !== notTool, "matcher: '" + q + "' not " + notTool, m);
    else if (tool === null) ck(!m || NEWT.indexOf(m.tool) < 0, "matcher refuses: '" + q + "'", m);
    else ck(m && m.tool === tool && (!p || (sub(m.params, p) && Object.keys(m.params).length === Object.keys(p).length)), "matcher: '" + q + "' -> " + tool + " " + JSON.stringify(p || ""), m && { t: m.tool, p: m.params });
  }
  /* 3 resume */
  const slugs = Object.keys(R.t);
  ck(R.v === 1 && R.asof === B.as_of && R.n === 138 && slugs.length === 138, "resume.json: v1, as-of = sim-bundle, 138 FBS teams");
  ck(JSON.stringify(slugs.map(s => R.t[s].rk).sort((a, b) => a - b)) === JSON.stringify(Array.from({ length: 138 }, (_, i) => i + 1)), "resume.json: ranks are 1..138, no ties");
  ck(slugs.every(s => B.teams.some(t => t.g === s)), "resume.json: every slug is an FBS team in sim-bundle");
  ck(Math.abs(R.w_sor + R.w_colley - 1) < 1e-12, "resume.json: weights sum to 1");
  const ord = slugs.slice().sort((a, b) => R.t[b].z - R.t[a].z || (a < b ? -1 : 1)); ck(ord.every((s, i) => R.t[s].rk === i + 1), "resume.json: rk is the order of z (ties by slug)");
  if (fs.existsSync(path.join(PIPE, "src/ratings.py"))) {
    const out = cp.spawnSync("python3", [path.join(__dirname, "..", "tools", "gen_resume.py"), "--pipeline", PIPE, "--bundle", path.join(tree, "data/sim-bundle.json"), "--out", "/tmp/set2b_resume_check.json"], { encoding: "utf8" });
    ck(out.status === 0, "gen_resume.py re-runs from the pipeline (fails closed on colley / sd mismatch)", out.stderr && out.stderr.slice(-300));
    if (out.status === 0) ck(fs.readFileSync("/tmp/set2b_resume_check.json", "utf8") === fs.readFileSync(path.join(tree, "data/tb/resume.json"), "utf8"), "resume.json byte-identical to a fresh pipeline recompute");
  } else ck(true, "pipeline not present: recompute skipped");
  TB.setLive(L23);
  let a = await T.answer("strength_of_record", { team: "utah" }); ck(a.r.ok && a.r.facts.team.rk === R.t.utah.rk && a.r.facts.of === 138, "team card rank = export", a.r);
  const ui = B.teams.findIndex(t => t.g === "utah"); let w = 0, l = 0; B.played.forEach(g => { if (g[0] === ui) (g[2] > g[3] ? w++ : l++); if (g[1] === ui) (g[3] > g[2] ? w++ : l++); });
  ck(a.r.facts.team.record.w === w && a.r.facts.team.record.l === l, "team card record recomputed from played");
  ck(a.card.text.indexOf("KickTip resume rank #" + R.t.utah.rk + " of 138") >= 0, "team card prints 'KickTip resume rank #N of 138'"); cardOk("sor team", a);
  a = await T.answer("strength_of_record", {}); ck(a.r.ok && a.r.facts.rows.length === 10 && a.r.facts.rows.every((x, i) => x.rk === i + 1), "list default 10, ranks 1..10"); cardOk("sor list", a);
  a = await T.answer("strength_of_record", { n: 25 }); ck(a.r.ok && a.r.facts.rows.length === 25, "list n=25"); cardOk("sor list 25", a);
  ck(/same opponents, home and away as played\./.test(a.card.text) && !/same stadiums/.test(a.card.text) && /not a poll/.test(a.card.text), "list card: the /method/ definition (Creative edit 2) and 'not a poll'");
  { const src = fs.readFileSync(path.join(tree, "assets/tb/conf_vs_conf.js"), "utf8"), sor = fs.readFileSync(path.join(tree, "assets/tb/strength_of_record.js"), "utf8");
    ck(src.indexOf('"Expected playoff teams by conference"') > 0 && src.indexOf("How many playoff teams will the SEC get?") < 0, "Creative edit 1: conf_vs_conf chip is 'Expected playoff teams by conference'");
    ck(src.indexOf('nAtLeast: "The \\"At least\\" columns show the chance that the conference has that many teams or more in the 12-team playoff field."') > 0, "Creative edit 3: nAtLeast");
    ck(src.indexOf('nExp: "Expected teams and the \\"At least\\" chances come from {seasons} simulated seasons."') > 0, "Creative edit 4: nExp");
    ck(sor.indexOf("same stadiums") < 0, "Creative edit 2: no 'same stadiums' left"); }
  a = await T.answer("strength_of_record", { n: 26 }); ck(!a.r.ok && a.r.reason === "bad_param", "n=26 -> bad_param", a.r);
  a = await using({ "tb/resume": Object.assign({}, R, { asof: "2026-10-20 17:58 MT" }) }, () => T.answer("strength_of_record", { team: "utah" })); ck(!a.r.ok && a.r.reason === "no_data", "stale resume.json -> no_data", a.r);
  a = await using({ "tb/resume": { v: 1 } }, () => T.answer("strength_of_record", {})); ck(!a.r.ok && a.r.reason === "no_data", "empty resume.json -> no_data", a.r);
  /* 4 conf-bids */
  const confOf = {}; B.teams.forEach(t => { if (t.g) confOf[t.g] = t.c; });
  ck(K.v === 1 && K.asof === B.as_of && K.seasons === 10000, "conf-bids.json: v1, as-of, 10000 seasons");
  C.CONFS.forEach(([c]) => {
    const row = K.c[c]; ck(Array.isArray(row) && row.reduce((x, y) => x + y, 0) === K.seasons && row.every(v => v >= 0 && Number.isInteger(v)), "conf-bids " + c + ": non-negative integers, sum = seasons");
    const mean = row.reduce((s, v, k) => s + k * v, 0) / K.seasons, sp = Object.keys(P.teams).filter(g => confOf[g] === c).reduce((s, g) => s + P.teams[g].p, 0);
    ck(Math.abs(mean - sp) * 100 <= 1.4, "conf-bids " + c + ": mean bids within 1.4 points of the sum of p (" + mean.toFixed(3) + " vs " + sp.toFixed(3) + ")");
  });
  a = await T.answer("conf_vs_conf", {}); ck(a.r.ok && a.r.facts.rows.length === 11 && a.r.facts.rows[10].id === "ind", "bids: 11 rows, Independents last"); cardOk("cvc bids all", a);
  const sec = a.r.facts.rows.find(r => r.id === "sec"), sp = Object.keys(P.teams).filter(g => confOf[g] === "sec").reduce((s, g) => s + P.teams[g].p, 0);
  ck(Math.abs(sec.expected - sp) < 1e-9, "bids: SEC expected = sum of p");
  ck(Math.abs(sec.atleast[2] - K.c.sec.slice(3).reduce((x, y) => x + y, 0) / K.seasons) < 1e-12, "bids: SEC at least 3 from the distribution");
  a = await T.answer("conf_vs_conf", { conference: "sec", conference2: "big10", at_least: 3 }); ck(a.r.ok && a.r.facts.rows.length === 2 && a.r.facts.ks.length === 1, "bids: two conferences, at_least 3"); cardOk("cvc bids k", a);
  a = await T.answer("conf_vs_conf", { metric: "strength" }); ck(a.r.ok && a.r.facts.rows.filter(r => r.rank).map(r => r.rank).join() === "1,2,3,4,5,6,7,8,9,10" && a.r.facts.rows[10].rank === null, "strength: ranks 1..10, Independents not ranked"); cardOk("cvc strength", a);
  const mm = c => { const xs = B.teams.map((t, i) => [t, i]).filter(([t, i]) => t.g && i !== B.fcs && t.c === c).map(([t, i]) => B.model.rating[i]); return xs.reduce((s, v) => s + v, 0) / xs.length; };
  ck(a.r.facts.rows.every(r => Math.abs(r.mean - mm(r.id)) < 1e-9), "strength: means recomputed");
  a = await T.answer("conf_vs_conf", { metric: "top25_count" }); cardOk("cvc top25", a);
  ck(a.r.facts.rows.reduce((s, r) => s + r.kt25, 0) === 25, "top25: KickTip counts sum to 25");
  const ap25 = POL.polls.ap.ranks.filter(r => r[0] <= 25 && confOf[r[1]]).length; ck(a.r.facts.rows.reduce((s, r) => s + r.ap25, 0) === ap25, "top25: AP counts sum to the AP top 25 FBS entries");
  a = await T.answer("conf_vs_conf", { metric: "nonconf_record" }); cardOk("cvc nonconf", a);
  let cross = 0; B.played.forEach(g => { if (g[0] !== B.fcs && g[1] !== B.fcs && (B.teams[g[0]].c !== B.teams[g[1]].c || B.teams[g[0]].c === "ind")) cross++; });
  const tot = a.r.facts.rows.reduce((s, r) => s + r.fbs.w + r.fbs.l, 0), wins = a.r.facts.rows.reduce((s, r) => s + r.fbs.w, 0), losses = a.r.facts.rows.reduce((s, r) => s + r.fbs.l, 0);
  const indInd = B.played.filter(g => g[0] !== B.fcs && g[1] !== B.fcs && B.teams[g[0]].c === "ind" && B.teams[g[1]].c === "ind").length;
  ck(tot === 2 * cross - 2 * indInd + 2 * indInd && wins === losses, "nonconf: every FBS cross-conference game counted once per side (wins = losses)", { tot, cross, wins, losses });
  a = await T.answer("conf_vs_conf", { conference: "ind" }); ck(a.r.ok, "bids: Independents alone answers"); cardOk("cvc ind", a);
  a = await T.answer("conf_vs_conf", { metric: "strength", conference: "ind" }); ck(!a.r.ok && a.r.reason === "not_applicable", "strength: Independents alone -> not_applicable");
  a = await T.answer("conf_vs_conf", { conference: "sec", conference2: "sec" }); ck(!a.r.ok && a.r.reason === "bad_param", "repeated conference -> bad_param");
  a = await T.answer("conf_vs_conf", { metric: "strength", at_least: 2 }); ck(!a.r.ok && a.r.reason === "bad_param", "at_least outside bids -> bad_param");
  a = await using({ "tb/conf-bids": Object.assign({}, K, { asof: "2026-10-20 17:58 MT" }) }, () => T.answer("conf_vs_conf", {})); ck(!a.r.ok && a.r.reason === "no_data", "stale conf-bids -> no_data", a.r);
  const Kb = JSON.parse(JSON.stringify(K)); Kb.c.sec[0] += 1; a = await using({ "tb/conf-bids": Kb }, () => T.answer("conf_vs_conf", {})); ck(!a.r.ok && a.r.reason === "no_data", "row not summing to seasons -> no_data", a.r);
  console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})().catch(e => { console.log("CRASH " + e.stack); process.exit(1); });
