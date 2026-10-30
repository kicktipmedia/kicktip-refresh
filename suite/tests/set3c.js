/* Set 3c tests (Node, no browser, no network, zero model calls): team_history (#25) and game_win_chance (#28). usage: node tests/set3c.js <tree> <base-tree> <qbank questions.json>
 * 1 spec bank rows T25-01..05, T28-01 + extra routing rows (new tools on via the test switch)  2 flag fixture (dark by default; dark keeps the single_game / past_seasons rows off the new tools)
 * 3 every answered card: no card errors, as-of, no banned wording, digit provenance, no inline style, links closed list  4 history: 10 records recomputed from the prior files, 5 realigned teams,
 * range sentence on every series card, dark conference rows when conf_ok/champ_ok false (fixture)  5 game_win_chance: pairs sum to 100, note always shown, played / no game / FCS
 * 6 history.json size and as-of  7 the whole QA bank routes identically with the flag off; with both tools on every change is listed (only null -> new tool allowed) */
"use strict";
const fs = require("fs"), path = require("path"), tree = path.resolve(process.argv[2]), baseTree = path.resolve(process.argv[3]), bankPath = process.argv[4];
const T = require("./lib/tbq.js")(tree), TB = T.TB, PRIOR = "/workspace/kicktip-bracketfit/data/store/prior";
const BAN = /\b(bets?|betting|wagers?|spreads?|parlays?|ccg|title game|pick|picks|favou?rites?|underdogs?|lines?|clinch\w*|eliminat\w*|lock|guarantee\w*)\b|\bthe 12(?!-team)\b/i;
const W = fs.readFileSync(path.join(tree, "_worker.js"), "utf8"), L22 = JSON.parse(/const TB_LIVE_TOOLS = (\[[^\]]*\]);/.exec(W)[1].replace(/'/g, '"')), L19 = L22.filter(x => x !== "game_win_chance");   /* set3m: L19 = the vis1c live list (21 ids) without #28, the flag-off baseline */
const NEW = ["team_history", "game_win_chance"];
let n = 0, bad = [];
const MT = fs.readFileSync(path.join(tree, "assets/tb/manifest.js"), "utf8"), MAN = JSON.parse(MT.slice(MT.indexOf("T.manifest=") + 11, MT.lastIndexOf(";})(")));
function chk(k, ok, info) { n++; if (!ok) { bad.push(k); console.log("FAIL " + k + (info !== undefined ? "  " + JSON.stringify(info).slice(0, 500) : "")); } else console.log("PASS " + k); }
const sub = (a, b) => Object.keys(b).every(k => JSON.stringify(a && a[k]) === JSON.stringify(b[k]));
const APPROVED = "KickTip is not a betting site.", strip = t => t.split(APPROVED).join(" ");   /* exact sentence allow-listed in the lane lint only (set3c2) */
const RANGE = /KickTip's history covers 2021 to 2025\. Older seasons are not covered yet\./, NOTE = /A model estimate for information only\. KickTip is not a betting site\./;
const Q = [
  ["T25-01", "When did Utah last make the playoff?", { tool: "team_history", params: { team: "utah", view: "last_cfp" }, text: /Utah did not make the College Football Playoff in 2024 or 2025, on KickTip's records\./ }],
  ["T25-02", "Texas record 2024", { tool: "team_history", params: { team: "texas", view: "record", season: 2024 }, text: /Texas went 11-2 in 2024, in the SEC\./ }],
  ["T25-03", "BYU all-time vs Utah", { tool: "team_history", params: { team: "byu", opponent: "utah", view: "series" }, text: /BYU vs Utah, from 2021: BYU 3, Utah 0\.[\s\S]*2021: BYU 26-17[\s\S]*2024: BYU 22-21[\s\S]*2025: BYU 24-21[\s\S]*All-time here means from 2021\.[\s\S]*KickTip's history covers/ }],
  ["T25-04", "Who won the SEC in 2019?", null],
  ["T25-05", "Did Indiana beat Ohio State?", { tool: "head_to_head" }],
  ["T28-01", "Will Utah beat BYU?", { tool: "game_win_chance", params: { teams: ["utah", "byu"] }, text: /Utah wins \d+\.\d% of simulated games and BYU wins \d+\.\d%\.[\s\S]*Understood as: how often Utah and BYU each win this game in KickTip's simulations\.|Understood as: how often Utah and BYU each win this game in KickTip's simulations\.[\s\S]*Utah wins \d+\.\d% of simulated games and BYU wins \d+\.\d%\./ }],
  ["h01", "What was Texas's record in 2024?", { tool: "team_history", params: { team: "texas", season: 2024, view: "record" } }],
  ["h02", "BYU vs Utah the last five years", { tool: "team_history", params: { team: "byu", opponent: "utah", view: "series" } }],
  ["h03", "Who won the Big 12 last year?", { tool: "team_history", params: { conference: "big12", season: 2025, view: "conf_champ" }, text: /Big 12 champion in 2025: Texas Tech\./ }],
  ["h04", "Who won the SEC in 2023?", { tool: "team_history", params: { conference: "sec", season: 2023, view: "conf_champ" }, text: /SEC champion in 2023: Alabama\./ }],
  ["h05", "Utah record by season", { tool: "team_history", params: { team: "utah", view: "record" }, text: /2023: 8-4, Pac-12[\s\S]*2024: 5-7, Big 12/ }],
  ["h06", "When did Indiana last make the playoff?", { tool: "team_history", params: { team: "indiana", view: "last_cfp" }, text: /Indiana's most recent College Football Playoff trip on KickTip's records: 2025\./ }],
  ["h07", "Utah vs Georgia history", { tool: "team_history", params: { view: "series" }, text: /did not play each other from 2021 to 2025[\s\S]*KickTip's history covers/ }],
  ["h08", "How did BYU do in 2021?", { tool: "team_history", params: { team: "byu", season: 2021 }, text: /BYU went 10-2 in 2021, as an independent\./ }],
  ["h09", "Pac-12 champions", { tool: "team_history", params: { conference: "pac12", view: "conf_champ" }, text: /2023: Washington The Pac-12 had no championship game in 2024\./ }],
  ["h10", "Utah record in 2018", null],
  ["h11", "Utah record", null],
  ["h12", "Will Utah make the playoff?", null],
  ["h13", "Utah vs BYU", null],
  ["h14", "When do Utah and BYU play?", null],
  ["g01", "Who wins Georgia vs Florida?", { tool: "game_win_chance", params: { teams: ["georgia", "florida"] }, text: /Neutral site\./ }],
  ["g02", "What if Utah beats BYU?", null],
  ["g03", "Did Indiana beat Ohio State?", null],
  ["g04", "Will Indiana beat Ohio State?", { tool: "game_win_chance", text: /This game has been played\. Ohio State won 19-15\./ }],
  ["g05", "Will Utah beat Georgia?", { tool: "game_win_chance", text: /Utah and Georgia do not play this regular season\./ }],
  ["g06", "Who is the favorite, Utah or BYU?", null],
  ["g07", "Will Utah cover the spread against BYU?", null],
  ["g08", "Will Utah beat BYU in basketball?", null]
];
(async () => {
  TB.setLive(L19.concat(NEW));
  for (const [id, q, exp] of Q) {
    const m = await T.match(q), lab = id + ' "' + q + '"';
    if (exp === null) { chk(lab + " -> neither new tool", !m || !NEW.includes(m.tool), m); continue; }
    const ok = !!(m && m.tool === exp.tool && !m.clarify && sub(m.params, exp.params || {}));
    chk(lab + " -> " + exp.tool + " " + JSON.stringify(exp.params || {}), ok, m);
    if (!ok || !NEW.includes(m.tool)) continue;
    const a = await T.answer(m.tool, m.params);
    chk(lab + " -> card built, no errors, as-of, no banned wording", !!(a.card && !a.card.errors.length && /As of Oct 27, 2026, 5:58 PM MT/.test(a.card.text) && !BAN.test(strip(a.card.text))), a.card ? a.card.errors.concat([a.card.text]) : a.r);
    chk(lab + " -> digit provenance", !TB.card.digitProblems || !TB.card.digitProblems(a.card, q).length, a.card && TB.card.digitProblems(a.card, q));
    chk(lab + " -> no inline style or script in card html", !/style=|<script|on[a-z]+=/i.test(a.card.html));
    chk(lab + " -> links closed list", (a.card.html.match(/href="[^"]*"/g) || []).every(h => /^href="(#|\/method\/|\/disclaimer\/|\/#field|\/#top25)"$/.test(h)), a.card.html.match(/href="[^"]*"/g));
    chk(lab + " -> no game dates", !/\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]* \d/i.test(a.card.text.replace(/As of Oct 27, 2026, 5:58 PM MT/g, "")), a.card.text);
    if (exp.text) chk(lab + " -> text " + exp.text, exp.text.test(a.card.text), a.card.text);
    if (m.tool === "game_win_chance") { chk(lab + " -> gw.note shown", NOTE.test(a.card.text)); chk(lab + " -> model footer, 6,000", /6,000 simulated seasons/.test(a.card.text), a.card.text); }
    if (m.tool === "team_history" && m.params.view === "series") chk(lab + " -> th.range on the series card", RANGE.test(a.card.text));
  }
  /* 2 flag fixture: dark = the 19 shipped ids */
  for (const [tool, probe] of [["team_history", "When did Utah last make the playoff?"], ["game_win_chance", "Will Utah beat BYU?"]]) {
    TB.setLive(L19); let m = await T.match(probe); chk(tool + " flag off (the 19 shipped ids): absent, so the model's miss stands", !m || m.tool !== tool, m);
    TB.setLive([]); m = await T.match(probe); chk(tool + " flag off (empty list): absent", !m || m.tool !== tool, m);
    TB.setLive(L19.concat([tool])); m = await T.match(probe); chk(tool + " flag on (19 + this id): answers", !!(m && m.tool === tool), m);
    chk(tool + " manifest live:false", MAN.tools[tool].live === false);
    if (tool === "game_win_chance") { const LST = (k) => JSON.parse(new RegExp("const " + k + " = (\\[[^\\]]*\\]);").exec(W)[1].replace(/'/g, '"')); chk(tool + " (set3m, live #28) in TB_LIVE_TOOLS and TB_TOOL_IDS, not in ROUTER_TOOLS (matcher-only), not in TB_SET3_IDS", LST("TB_LIVE_TOOLS").includes(tool) && LST("TB_TOOL_IDS").includes(tool) && !Object.keys(JSON.parse(/^const ROUTER_TOOLS = (\{.*\});$/m.exec(W)[1])).includes(tool) && !LST("TB_SET3_IDS").includes(tool)); }
    else chk(tool + " (set3m) in _worker.js only in the TB_SET3_IDS line (Preview only)", W.split("\n").filter(l => l.indexOf(tool) >= 0).length === 1 && W.split("\n").find(l => l.indexOf(tool) >= 0).startsWith("const TB_SET3_IDS = ["));
  }
  TB.setLive(L19.concat(NEW));
  /* 4 history recompute from the prior files */
  const H = T.raw("tb/history"), B = T.raw("sim-bundle");
  const rd = f => JSON.parse(fs.readFileSync(path.join(PRIOR, f), "utf8"));
  for (const [slug, yr] of [["utah", 2021], ["texas", 2024], ["byu", 2022], ["ohio-state", 2025], ["indiana", 2024], ["georgia", 2023], ["alabama", 2021], ["smu", 2024], ["boise-state", 2025], ["new-mexico", 2023]]) {
    const G = rd("games_" + yr + ".json"), TM = rd("teams_" + yr + ".json");
    const nm = B.teams.find(t => t.g === slug).n, id = Object.keys(TM).find(k => TM[k].name === nm); let w = 0, l = 0;
    G.forEach(g => { const hs = String(g.home), as = String(g.away); if (hs !== id && as !== id) return;
      const ph = +g.hs, pa = +g.as_; if (!isFinite(ph) || !isFinite(pa)) return;
      const mine = hs === id ? ph : pa, oth = hs === id ? pa : ph; if (mine > oth) w++; else l++; });
    const want = H.t[slug] && H.t[slug].rec[String(yr)];
    chk("record " + slug + " " + yr + " from the prior file " + w + "-" + l + " = export " + JSON.stringify(want), !!(id && want && want[0] === w && want[1] === l), { id, w, l, want });
  }
  for (const [slug, exp] of [["utah", ["pac12", "pac12", "pac12", "big12", "big12"]], ["texas", ["big12", "big12", "big12", "sec", "sec"]], ["byu", ["ind", "ind", "big12", "big12", "big12"]], ["smu", ["American", "American", "American", "acc", "acc"]], ["ucla", ["pac12", "pac12", "pac12", "big10", "big10"]]])
    chk("realigned " + slug + " conference by season " + exp.join(","), JSON.stringify(H.seasons.map(y => H.t[slug].conf[String(y)])) === JSON.stringify(exp), H.t[slug].conf);
  chk("seasons 2021-2025, conf_ok all true (membership from teams_{yr})", JSON.stringify(H.seasons) === "[2021,2022,2023,2024,2025]" && H.seasons.every(y => H.conf_ok[String(y)] === true));
  { /* dark fixture: a season without verified membership / champions shows no conference rows (never guessed) */
    const real = JSON.parse(JSON.stringify(H)); T.DATA["tb/history"] = Object.assign(JSON.parse(JSON.stringify(H)), { conf_ok: Object.assign({}, H.conf_ok, { "2023": false }), champ_ok: Object.assign({}, H.champ_ok, { "2023": false }) }); TB.clearData();
    const r1 = await T.run("team_history", { team: "utah", view: "record" }), c1 = TB.render("team_history", r1);
    chk("dark fixture: conf_ok false 2023 -> Utah 2023 row has no conference, 2024 keeps Big 12", /2023: 8-4(?!,)/.test(c1.text) && !/2023: 8-4, /.test(c1.text) && /2024: 5-7, Big 12/.test(c1.text) && !c1.errors.length, c1.text);
    const r2 = await T.run("team_history", { conference: "sec", season: 2023, view: "conf_champ" });
    chk("dark fixture: champ_ok false 2023 -> SEC 2023 champion not shown (not_modeled)", r2.ok === false && r2.reason === "not_modeled", r2);
    const r3 = await T.run("team_history", { conference: "sec", view: "conf_champ" }), c3 = TB.render("team_history", r3);
    chk("dark fixture: SEC champions list skips 2023", r3.ok && !/2023/.test(c3.text.replace(/As of[^.]*\./, "")) && /2024: Georgia/.test(c3.text), c3.text);
    T.DATA["tb/history"] = real; TB.clearData();
  }
  chk("season 2019 refused by the tool (not_applicable)", (await T.run("team_history", { team: "utah", season: 2019 })).ok === false);
  chk("series card for teams that never met carries th.range", RANGE.test(TB.render("team_history", await T.run("team_history", { team: "utah", opponent: "georgia", view: "series" })).text));
  /* 5 game_win_chance over every remaining game */
  const IDX = T.raw("whatif/index"); let sums = 0, cards = 0, errs = [];
  for (const g of IDX.games) { const a = B.teams[g.h].g, b = B.teams[g.a].g; if (!a || !b) continue; const r = await T.run("game_win_chance", { teams: [a, b] }); if (!r.ok || r.facts.kind !== "game") { errs.push([a, b, r.reason || r.facts.kind]); continue; }
    if (r.facts.pa_pm + r.facts.pb_pm === 1000 && (parseFloat(r.facts.pa) + parseFloat(r.facts.pb)).toFixed(1) === "100.0") sums++; const c = TB.render("game_win_chance", r); cards++; if (c.errors.length || !NOTE.test(c.text) || BAN.test(strip(c.text)) || !/ is at home\.| Neutral site\./.test(c.text)) errs.push([a, b, c.errors, c.text.slice(0, 200)]); }
  chk("every remaining game (" + cards + "): percents sum to 100, note shown, no card errors, no banned words", sums === cards && cards >= 300 && !errs.length, errs.slice(0, 5));
  const ub = await T.run("game_win_chance", { teams: ["utah", "byu"] }), g0 = IDX.games.find(g => [g.h, g.a].map(i => B.teams[i].g).sort().join() === "byu,utah");
  chk("Utah-BYU percents = round(p_home/10) from whatif/index", ub.ok && (B.teams[g0.h].g === "utah" ? ub.facts.pa : ub.facts.pb) === (g0.p_home / 10).toFixed(1) + "%", [ub.facts, g0]);
  { /* set3c2 edge forms: fixture p_home 0 and 1000 */
    const real = JSON.parse(JSON.stringify(IDX)), fx = JSON.parse(JSON.stringify(IDX)), gi = fx.games.indexOf(fx.games.find(g => g === fx.games.find(x => [x.h, x.a].map(i => B.teams[i].g).sort().join() === "byu,utah")));
    for (const [pm, want] of [[0, /Utah wins (under 0\.05%|at least 99\.95%) of simulated games and BYU wins (under 0\.05%|at least 99\.95%)\./], [1000, /wins at least 99\.95% of simulated games and \w+ wins under 0\.05%\.|wins under 0\.05% of simulated games and \w+ wins at least 99\.95%\./]]) {
      fx.games[gi].p_home = pm; T.DATA["whatif/index"] = fx; TB.clearData(); const r = await T.run("game_win_chance", { teams: ["utah", "byu"] }), c = TB.render("game_win_chance", r);
      chk("edge p_home " + pm + " -> under 0.05% / at least 99.95%, no (model) label, no 0.0/100.0", want.test(c.text) && !/\b(0\.0|100\.0)%/.test(c.text) && !c.errors.length, c.errors.concat([c.text])); }
    T.DATA["whatif/index"] = real; TB.clearData();
    const r = await T.run("game_win_chance", { teams: ["utah", "byu"] }), c = TB.render("game_win_chance", r);
    chk("note exact: A model estimate for information only. KickTip is not a betting site.", c.text.includes("A model estimate for information only. KickTip is not a betting site.") && !c.errors.length);
    chk("home line: {home} is at home.", / is at home\./.test(c.text), c.text);
  }
  { const r = await T.run("game_win_chance", { teams: ["utah", "byu"] }), c = TB.render("game_win_chance", r);
    chk("set3c3 row form: Utah wins N.N% of simulated games and BYU wins N.N%.", new RegExp("Utah wins " + r.facts.pa.replace(".", "\\.") + " of simulated games and BYU wins " + r.facts.pb.replace(".", "\\.") + "\\.").test(c.text) && !/; BYU in /.test(c.text), c.text); }
  /* 6 export */
  const sz = fs.statSync(path.join(tree, "data/tb/history.json")).size; chk("tb/history size " + sz + " < 160 KB (160,000 bytes), asof = sim-bundle", sz < 160000 && H.asof === B.as_of);
  /* 7 bank routing */
  const cp = require("child_process"), RT = (tr, mode, drop) => JSON.parse(cp.execFileSync("node", [path.join(__dirname, "lib", "routes.js"), tr, bankPath, mode, NEW.join(","), drop || ""], { maxBuffer: 64 << 20 }).toString());
  /* set3m: game_win_chance (#28) is live in this tree; the flag-off / on comparisons drop it to compare against the vis1c base exactly */
  const r0 = RT(baseTree, "off"), r1 = RT(tree, "off", "game_win_chance"), r2 = RT(tree, "on", "game_win_chance"), all = Object.keys(r0);
  { const r3 = RT(tree, "off"), d3 = all.filter(t => JSON.stringify(r0[t]) !== JSON.stringify(r3[t])).map(t => ({ q: t, was: r0[t] ? r0[t].tool : null, now: r3[t] ? r3[t].tool : null }));
    console.log("set3m shipped state (22 live ids) vs vis1c: " + d3.length + " changes"); d3.forEach(d => console.log('  "' + d.q + '": ' + d.was + " -> " + d.now));
    chk("set3m shipped (22 live, Set 3 dark): every bank change vs vis1c is null -> game_win_chance", d3.every(d => d.was === null && d.now === "game_win_chance"), d3); }
  const same = all.filter(t => JSON.stringify(r0[t]) === JSON.stringify(r1[t])).length, onDiff = all.filter(t => JSON.stringify(r1[t]) !== JSON.stringify(r2[t])).map(t => ({ q: t, was: r1[t] ? r1[t].tool : null, now: r2[t] ? r2[t].tool : null }));
  chk("bank (" + all.length + " unique rows) flag off: routes identical to base " + same + "/" + all.length, same === all.length && Object.keys(r1).length === all.length);
  console.log("bank with the two new tools ON: " + (all.length - onDiff.length) + "/" + all.length + " identical; changes:"); onDiff.forEach(d => console.log('  "' + d.q + '": ' + d.was + " -> " + d.now));
  const PASTQ = /\b(20(1\d|2[0-5])|last (year|season)|history|all time|series|last (\d|two|three|four|five) (years|seasons)|record)\b/i;
  chk("bank flag on: every change goes to a new tool, and only from null or (team_history) on a past-season / history question", onDiff.every(d => NEW.includes(d.now) && (d.was === null || (d.now === "team_history" && PASTQ.test(d.q)))), onDiff);
  { const EXTRA = /\b(bet|bets|betting|wager\w*|spreads?|parlays?|ccg|title game|favou?rites?|underdogs?|lines?)\b|\bthe 12(?!-team)\b/i, CONFCCG = /\{conf\} conference championship game|\b(SEC|ACC|Big Ten|Big 12|Pac-12|Mountain West|Sun Belt|MAC|American|Conference USA) conference championship game/;
    for (const id of NEW) { const t = TB.get(id), strs = Object.values(t.copy).map(e => typeof e === "string" ? e : e.t).concat(t.examples || [], [t.description || ""]);
      const hits = strs.map(strip).filter(x => EXTRA.test(x) || CONFCCG.test(x) || /\bpicks?\b|\bCCG\b/i.test(x) || (TB.core.BANNED && TB.core.BANNED.test(x)));
      chk(id + ": static banned grep (incl. core C.BANNED) over " + strs.length + " strings", hits.length === 0, hits); } }
  console.log("\n" + n + " checks, " + bad.length + " failed"); process.exit(bad.length ? 1 : 0);
})();
