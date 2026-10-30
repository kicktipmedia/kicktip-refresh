/* Set 3b tests (Node, no browser, no network, zero model calls): team_stats (#26) and whatif_conference_outcome (#24). usage: node tests/set3b.js <tree> <base-tree> <qbank questions.json>
 * 1 spec bank rows T26-01..05, T24-01..05 + extra routing/refusal rows (new tools on via the test switch)  2 flag fixture (dark by default, on only when listed)
 * 3 every answered card: no card errors, as-of, estimate, no banned wording, digit provenance, links closed list  4 hand recompute of 5 teams + FCS exclusion + 1 decimal + ties share a rank + st.note
 * 5 conf-outcome recount (same seed, byte-identical), s<100 hidden, unverified caption, independents, p0 = pred-teams  6 export sizes and as-of
 * 7 the whole QA bank (+ BR rows) routes identically: base tree vs this tree with the flag off, and with the two new tools on (every change listed; only new-tool hits allowed, and only on rows they own) */
"use strict";
const fs = require("fs"), path = require("path"), tree = path.resolve(process.argv[2]), baseTree = path.resolve(process.argv[3]), bankPath = process.argv[4];
const T = require("./lib/tbq.js")(tree), TB = T.TB;
const BAN = /\b(bets?|betting|wagers?|spreads?|parlays?|odds|ccg|title game|pick|picks|clinch\w*|eliminat\w*|lock|guarantee\w*)\b|\bthe 12(?!-team)\b/i;
const W = fs.readFileSync(path.join(tree, "_worker.js"), "utf8"), L19 = JSON.parse(/const TB_LIVE_TOOLS = (\[[^\]]*\]);/.exec(W)[1].replace(/'/g, '"'));
const NEW = ["team_stats", "whatif_conference_outcome"];
let n = 0, bad = [];
const MT = fs.readFileSync(path.join(tree, "assets/tb/manifest.js"), "utf8"), MAN = JSON.parse(MT.slice(MT.indexOf("T.manifest=") + 11, MT.lastIndexOf(";})(")));
function chk(k, ok, info) { n++; if (!ok) { bad.push(k); console.log("FAIL " + k + (info !== undefined ? "  " + JSON.stringify(info).slice(0, 400) : "")); } else console.log("PASS " + k); }
const sub = (a, b) => Object.keys(b).every(k => JSON.stringify(a && a[k]) === JSON.stringify(b[k]));
const Q = [
  ["T26-01", "Best scoring defense", { tool: "team_stats", params: { stat: "papg", n: 10 } }],
  ["T26-02", "Most yards per play", { tool: "team_stats", params: { stat: "ypp" } }],
  ["T26-03", "Utah points per game", { tool: "team_stats", params: { team: "utah", stat: "ppg" } }],
  ["T26-04", "Who has the most turnovers?", { tool: "team_stats", params: { stat: "other" }, miss: "outside_scope" }],
  ["T26-05", "Top 25", { tool: "rankings_list" }],
  ["T24-01", "What if Utah wins the Big 12?", { tool: "whatif_conference_outcome", params: { team: "utah", outcome: "wins_conf" } }],
  ["T24-02", "What if Georgia beats Alabama in the SEC championship game?", { tool: "whatif_conference_outcome", params: { team: "georgia", outcome: "wins_ccg_vs", opponent: "alabama" } }],
  ["T24-03", "What if Notre Dame wins its conference?", { tool: "whatif_conference_outcome", params: { team: "notre-dame" }, text: /plays as an independent and has no conference championship game/ }],
  ["T24-04", "What if Utah beats BYU?", null],
  ["T24-05", "How can Utah win the Big 12?", { tool: "team_needs" }],
  ["x01", "Utah defense", { tool: "team_stats", params: { team: "utah", stat: "papg" } }],
  ["x02", "Five best scoring offenses", { tool: "team_stats", params: { stat: "ppg", n: 5 } }],
  ["x02b", "Top 5 scoring offenses", null],
  ["x03", "Which team allows the fewest yards per game?", { tool: "team_stats", params: { stat: "ypg_allowed" } }],
  ["x04", "Best scoring margin", { tool: "team_stats", params: { stat: "margin" } }],
  ["x05", "Utah yards per play allowed", { tool: "team_stats", params: { team: "utah", stat: "ypp_allowed" } }],
  ["x06", "Most points per game in all games", { tool: "team_stats", params: { stat: "ppg", vs_fbs: false } }],
  ["x07", "Most third down conversions", { tool: "team_stats", params: { stat: "other" }, miss: "outside_scope" }],
  ["x08", "Utah strength of schedule", { tool: "schedule_strength" }],
  ["x09", "Best defense in basketball", null],
  ["x10", "Most points per game last season", null],
  ["x11", "Utah vs BYU points per game", null],
  ["x12", "Top 50 scoring offenses", null],
  ["x13", "Best AP poll defense", null],
  ["x14", "Utah points per game against the spread", null],
  ["x15", "What if Utah reaches the Big 12 conference championship game?", { tool: "whatif_conference_outcome", params: { team: "utah", outcome: "reaches_ccg" } }],
  ["x16", "If BYU wins its conference, does it make the playoff?", { tool: "whatif_conference_outcome", params: { team: "byu", outcome: "wins_conf" } }],
  ["x17", "What if Utah wins the SEC?", null],
  ["x18", "What if Utah beats Georgia in the conference championship game?", null],
  ["x19", "What if Oregon wins the Big Ten?", { tool: "whatif_conference_outcome", params: { team: "oregon" }, text: /under 1% of simulated seasons, so KickTip does not show this view/ }],
  ["x20", "What does Utah need to win the Big 12?", { tool: "team_needs" }],
  ["x21", "What if Utah wins out?", null],
  ["x22", "What are the odds Utah wins the Big 12?", null],
  ["x23", "What if Utah wins the conference championship game against BYU?", { tool: "whatif_conference_outcome", params: { team: "utah", outcome: "wins_ccg_vs", opponent: "byu" } }],
  ["x26", "Twenty best scoring defenses", { tool: "team_stats", params: { stat: "papg", n: 20 } }],
  ["x24", "What if Georgia beats Alabama in the SEC conference championship game?", { tool: "whatif_conference_outcome", params: { team: "georgia", outcome: "wins_ccg_vs", opponent: "alabama" } }],
  ["x25", "What if Utah wins the Big 12?", { tool: "whatif_conference_outcome", params: { team: "utah" }, text: /If Utah wins the Big 12 championship game:[\s\S]*Make the playoff field: /, notext: /the 12\b|12-team|conference championship game:/ }]
];
(async () => {
  /* 1 + 3: routing and cards with the 19 shipped + the 2 new tools on (test switch) */
  TB.setLive(L19.concat(NEW));
  for (const [id, q, exp] of Q) {
    const m = await T.match(q), lab = id + ' "' + q + '"';
    if (exp === null) { chk(lab + " -> neither new tool", !m || !NEW.includes(m.tool), m); continue; }
    const ok = !!(m && m.tool === exp.tool && !m.clarify && sub(m.params, exp.params || {}));
    chk(lab + " -> " + exp.tool + " " + JSON.stringify(exp.params || {}), ok, m);
    if (!ok || !NEW.includes(m.tool)) continue;
    const a = await T.answer(m.tool, m.params);
    if (exp.miss) { const mc = TB.card.miss ? TB.card.miss(a.r.reason === "not_modeled" ? "outside_scope" : a.r.reason) : null; chk(lab + " -> not_modeled (outside_scope miss card, zero model calls)", !a.r.ok && a.r.reason === "not_modeled", a.r); continue; }
    chk(lab + " -> card built, no errors, as-of, estimate, no banned wording", !!(a.card && !a.card.errors.length && /As of Oct 27, 2026, 5:58 PM MT/.test(a.card.text) && /estimate/i.test(a.card.text) && !BAN.test(a.card.text)), a.card ? a.card.errors.concat([a.card.text]) : a.r);
    chk(lab + " -> digit provenance", !TB.card.digitProblems || !TB.card.digitProblems(a.card, q).length, a.card && TB.card.digitProblems(a.card, q));
    chk(lab + " -> no inline style or script in card html", !/style=|<script|on[a-z]+=/i.test(a.card.html));
    chk(lab + " -> links closed list", (a.card.html.match(/href="[^"]*"/g) || []).every(h => /^href="(#|\/method\/|\/disclaimer\/|\/#field|\/#top25|\/conference\/(acc|american|big-12|big-ten|conference-usa|independents|mac|mountain-west|pac-12|sec|sun-belt)\/)"$/.test(h)), a.card.html.match(/href="[^"]*"/g));
    if (exp.text) chk(lab + " -> text " + exp.text, exp.text.test(a.card.text), a.card.text);
    if (exp.notext) chk(lab + " -> not " + exp.notext, !exp.notext.test(a.card.text + a.card.html), a.card.text);
    if (m.tool === "whatif_conference_outcome") { chk(lab + " -> model footer", /Estimate from 10,000 simulated seasons\./.test(a.card.text)); chk(lab + " -> /#field link", /href="\/#field"/.test(a.card.html)); }
    if (m.tool === "team_stats") chk(lab + " -> st.note", /Raw season numbers, not adjusted for opponents\./.test(a.card.text));
  }
  /* 2 flag fixture */
  for (const tool of NEW) {
    const probe = Q.find(x => x[2] && x[2].tool === tool)[1];
    TB.setLive(L19); let m = await T.match(probe); chk(tool + " flag off (the 19 shipped ids): absent", !m || m.tool !== tool, m);
    TB.setLive([]); m = await T.match(probe); chk(tool + " flag off (empty list): absent", !m || m.tool !== tool, m);
    TB.setLive(L19.concat([tool])); m = await T.match(probe); chk(tool + " flag on (19 + this id): answers", !!(m && m.tool === tool), m);
    chk(tool + " manifest live:false", MAN.tools[tool].live === false);
    chk(tool + " (set3m) in _worker.js only in the TB_SET3_IDS line (Preview only)", W.split("\n").filter(l => l.indexOf(tool) >= 0).length === 1 && W.split("\n").find(l => l.indexOf(tool) >= 0).startsWith("const TB_SET3_IDS = ["));
  }
  /* 4 hand recompute */
  const S = T.raw("tb/team-stats"), B = T.raw("sim-bundle");
  for (const [slug, stat, f] of [["utah", "ppg", x => x.pf / x.g], ["georgia", "ypp", x => x.yds / x.pl], ["ohio-state", "papg", x => x.pa / x.g], ["byu", "ypg_allowed", x => x.ya / x.g], ["new-mexico", "margin", x => (x.pf - x.pa) / x.g]]) {
    const r = await T.run("team_stats", { team: slug, stat: stat }), want = Math.round(f(S.t[slug]) * 10) / 10;
    const vals = Object.keys(S.t).filter(s => S.t[s].g > 0).map(s => Math.round(f(S.t[s]) * 10) / 10), low = /papg|allowed/.test(stat), better = vals.filter(v => low ? v < want : v > want).length;
    chk("recompute " + slug + " " + stat + " = " + want + " rank " + (better + 1), r.ok && Math.abs(r.facts.team.v) === Math.abs(want) && r.facts.team.r === better + 1 && r.facts.team.g === S.t[slug].g, r.facts && r.facts.team);
  }
  const ua = await T.run("team_stats", { team: "utah", stat: "ppg", vs_fbs: false }), uf = await T.run("team_stats", { team: "utah", stat: "ppg" });
  chk("FCS games excluded by default (Utah FBS g " + uf.facts.team.g + " vs all g " + ua.facts.team.g + ")", uf.facts.team.g <= ua.facts.team.g && uf.facts.vs_fbs === true && ua.facts.vs_fbs === false);
  const uac = TB.render("team_stats", ua); chk("vs_fbs:false card carries st.all", /Including games against FCS teams\./.test(uac.text) && !uac.errors.length, uac.errors);
  const L = await T.run("team_stats", { stat: "ypp", n: 10 }); chk("ties share a rank (ypp list)", L.facts.rows.every((x, k) => k === 0 || (x.v === L.facts.rows[k - 1].v ? x.r === L.facts.rows[k - 1].r : x.r === k + 1)), L.facts.rows.map(x => [x.v, x.r]));
  chk("one decimal in every rate", L.facts.rows.every(x => Math.round(x.v * 10) === x.v * 10) && /\b7\.\d\b/.test(TB.render("team_stats", L).text));
  chk("st.list.head text", /Yards per play, top 10 \(games against FBS teams\)\./.test(TB.render("team_stats", L).text));
  { /* set3b3: column label per stat, capitalized list heading, lowercase label elsewhere */
    const lh = TB.render("team_stats", L);
    chk("set3b3: ypp list column header is Per play", /<th class="n">Per play<\/th>/.test(lh.html), lh.html.slice(0, 600));
    const pp = await T.answer("team_stats", { stat: "ppg", n: 5 });
    chk("set3b3: ppg list column header is Per game, heading capitalized", /<th class="n">Per game<\/th>/.test(pp.card.html) && /Points per game, top 5 \(games against FBS teams\)\./.test(pp.card.text) && !pp.card.errors.length, pp.card.errors.concat([pp.card.text]));
    const pa = await T.answer("team_stats", { stat: "papg", n: 5, vs_fbs: false });
    chk("set3b3: all-games heading capitalized", /Points allowed per game, top 5\./.test(pa.card.text) && !pa.card.errors.length, pa.card.text);
    const tu = await T.answer("team_stats", { team: "utah", stat: "ppg" });
    chk("set3b3: team sentence keeps the lowercase label", /Utah: [\d.]+ points per game in \d+ games against FBS teams\./.test(tu.card.text) && /<th class="n">Per game<\/th>/.test(tu.card.html), tu.card.text);
    const js = fs.readFileSync(path.join(tree, "assets/tb/team_stats.js"), "utf8"), css = fs.readFileSync(path.join(tree, "assets/tb/team_stats.css"), "utf8"), tok = require("crypto").createHash("sha256").update(css).digest("hex").slice(0, 10);
    chk("set3b3: team_stats.css linked with its sha token, no inline style", js.includes('"/assets/tb/team_stats.css?v=' + tok + '"') && !/\.style\b|setAttribute\("style"|<style/.test(js));
    chk("set3b3: css scoped to the team_stats card, hyphens none, word-break normal", css.split("}").filter(r => r.trim()).every(r => r.trim().startsWith(".ac.tbox[data-tool=\"team_stats\"]") || r.trim().startsWith("/*")) && /hyphens:none/.test(css) && /word-break:normal/.test(css));
  }
  chk("unknown stat value refused", (await T.run("team_stats", { stat: "sacks" })).ok === false);
  /* 5 conf-outcome */
  const O = T.raw("tb/conf-outcome"), P = T.raw("pred-teams"), A = T.raw("tb/ccg-alive");
  chk("conf-outcome recount: same seed reproduces the export byte for byte", fs.existsSync(path.join(__dirname, "..", "work", "recount-same.json")) && fs.readFileSync(path.join(__dirname, "..", "work", "recount-same.json"), "utf8") === fs.readFileSync(path.join(tree, "data/tb/conf-outcome.json"), "utf8"));
  const R7 = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "work", "recount-seed777.json"), "utf8")); let worst = 0, big = 0;
  Object.keys(O.t).forEach(s => { const a = O.t[s].reach, b = R7.t[s] && R7.t[s].reach; if (a && b && a.s >= 1000 && b.s >= 1000) { big++; worst = Math.max(worst, Math.abs(a.cfp12 - b.cfp12) * 100); } });
  console.log("info: independent seed 777 recount, reach rows with s>=1000 in both: " + big + ", largest cfp12 gap " + worst.toFixed(2) + " pts (sampling noise)");
  let maxd = 0; Object.keys(O.t).forEach(s => { if (P.teams[s]) maxd = Math.max(maxd, Math.abs(O.t[s].base.cfp12 - P.teams[s].p) * 100); });
  chk("export base vs pred-teams today within 1 point (max " + maxd.toFixed(2) + ")", maxd <= 1);
  chk("rows with s < 100 are not in the export", Object.values(O.t).every(e => e.reach.s >= 100 && (!e.win || e.win.s >= 100) && Object.values(e.vs || {}).every(v => v.s >= 100)));
  const u = await T.run("whatif_conference_outcome", { team: "utah", outcome: "wins_conf" });
  chk("Utah win row = export, today = pred-teams p", u.ok && u.facts.cond === undefined ? false : u.facts.cond.cfp12 === O.t.utah.win.cfp12 && u.facts.today.cfp12 === P.teams.utah.p);
  const uc = TB.render("whatif_conference_outcome", u);
  chk("unverified caption shown (Big 12 verified:" + A.confs.big12.verified + ")", A.confs.big12.verified !== true && /Big 12 tiebreakers are applied on our reading of the rules\./.test(uc.text));
  const rare = Object.keys(B.teams.reduce((o, t) => (t.g && t.c !== "ind" && !O.t[t.g] ? (o[t.g] = 1, o) : o), {}))[0];
  const rr = await T.run("whatif_conference_outcome", { team: rare }), rc = TB.render("whatif_conference_outcome", rr);
  chk("s<100 team (" + rare + ") -> wco.rare text, no figures", rr.ok && /reaches the conference championship game in under 1% of simulated seasons/.test(rc.text) && !/\(model\)/.test(rc.text) && !rc.errors.length, rc.errors.concat([rc.text]));
  chk("opponent from another conference -> not_applicable", (await T.run("whatif_conference_outcome", { team: "utah", outcome: "wins_ccg_vs", opponent: "georgia" })).reason === "not_applicable");
  /* 6 exports */
  for (const f of ["tb/team-stats", "tb/conf-outcome"]) { const sz = fs.statSync(path.join(tree, "data", f + ".json")).size; chk(f + " size " + sz + " <= 160 KB, asof = sim-bundle", sz <= 160 * 1024 && T.raw(f).asof === B.as_of); }
  /* 7 bank routing: base vs this tree (flag off), and flag on */
  const cp = require("child_process"), RT = (tr, mode, drop) => JSON.parse(cp.execFileSync("node", [path.join(__dirname, "lib", "routes.js"), tr, bankPath, mode, NEW.join(","), drop || ""], { maxBuffer: 64 << 20 }).toString());
  /* set3m: game_win_chance (#28) is live in this tree; the flag-off / on comparisons drop it to compare against the vis1c base exactly */
  const r0 = RT(baseTree, "off"), r1 = RT(tree, "off", "game_win_chance"), r2 = RT(tree, "on", "game_win_chance"), all = Object.keys(r0);
  const same = all.filter(t => JSON.stringify(r0[t]) === JSON.stringify(r1[t])).length, onDiff = all.filter(t => JSON.stringify(r1[t]) !== JSON.stringify(r2[t])).map(t => ({ q: t, was: r1[t] ? r1[t].tool : null, now: r2[t] ? r2[t].tool : null }));
  chk("bank (" + all.length + " unique rows incl. BR-01..12) flag off: routes identical to base " + same + "/" + all.length, same === all.length && Object.keys(r1).length === all.length);
  console.log("bank with the two new tools ON: " + (all.length - onDiff.length) + "/" + all.length + " identical; changes:"); onDiff.forEach(d => console.log('  "' + d.q + '": ' + d.was + " -> " + d.now));
  const BRX = [["What does Arizona need to reach the conference championship game?", "team_needs"], ["What has to happen for Indiana to make the playoff?", "team_needs"], ["How many wins does Utah need?", "team_needs"], ["What is Utah's path to the conference championship game?", "team_path"], ["How can BYU reach the conference championship game?", "team_path"], ["What is Indiana's path to a first-round bye?", "team_path"], ["How can Ohio State get into the playoff field?", "team_path"], ["What does BYU need to do on its path to the playoff?", "team_needs"], ["How can Utah reach the conference championship game, and what does it need?", "team_needs"], ["How many games can Utah lose and still reach the conference championship game?", "team_path"], ["How can Utah win the Big 12?", "team_needs"], ["Compare Utah's and Arizona's path to a bye.", "path_compare"]];
  BRX.forEach(([q, t], i) => { chk("BR-" + String(i + 1).padStart(2, "0") + " flag off and on -> " + t, !!(r1[q] && r1[q].tool === t && r2[q] && r2[q].tool === t && JSON.stringify(r0[q]) === JSON.stringify(r2[q])), [r0[q], r2[q]]); });
  chk("bank flag on: every change is a null -> new tool (never takes a row from an existing tool)", onDiff.every(d => d.was === null && NEW.includes(d.now)), onDiff);
  { /* static banned grep over every new printed string: copy, examples, description, chips (set3b2) */
    const C = globalThis.KTTB_CORE || (TB.core) || null;
    const EXTRA = /\b(bet|bets|betting|wager\w*|spreads?|parlays?|ccg|title game|odds)\b|\bthe 12(?!-team)\b/i, CONFCCG = /\{conf\} conference championship game|\b(SEC|ACC|Big Ten|Big 12|Pac-12|Mountain West|Sun Belt|MAC|American|Conference USA) conference championship game/;
    for (const id of NEW) { const t = TB.get(id), strs = Object.values(t.copy).map(e => typeof e === "string" ? e : e.t).concat(t.examples || [], [t.description || "", t.title || ""], (t.chips || []).map(c => c.label || c.q || String(c)));
      const hits = strs.filter(x => EXTRA.test(x) || CONFCCG.test(x) || / pick\b|\bCCG\b/i.test(x));
      chk(id + ": static banned grep over " + strs.length + " strings", hits.length === 0, hits); }
  }
  console.log("\n" + n + " checks, " + bad.length + " failed"); process.exit(bad.length ? 1 : 0);
})();
