/* Set 2b wave 1 matcher tests (Node, no browser, no network, zero model calls). usage: node tests/set2b_matcher.js <tree>
 * 1. per tool: routing tables (matches with params, refusals, ambiguity, boundaries) with only that tool live
 * 2. flag fixture: the tool answers when listed, is absent when not listed
 * 3. boundary table with all 19 tools live (the 16 in the shipped Worker + the 3 new ones, test harness only): each phrase lands on the named tool or on none (the existing path)
 * 4. every answered card: no card errors, as-of label, no banned wording */
"use strict";
const path = require("path"), tree = path.resolve(process.argv[2] || "/workspace/kicktip-toolbox8/work/out8");
const T = require("./lib/tbq.js")(tree), TB = T.TB;
const BAN = /\b(bets?|betting|wagers?|spreads?|parlays?|ccg|title game|the 12(?!-team))\b/i;
const NEW = ["schedule_strength", "quality_wins", "team_compare"];
const OLD16 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site"];
let n = 0, bad = [];
function chk(k, ok, info) { n++; if (!ok) { bad.push(k); console.log("FAIL " + k + (info !== undefined ? "  " + JSON.stringify(info).slice(0, 300) : "")); } else console.log("PASS " + k); }
const sub = (a, b) => Object.keys(b).every(k => JSON.stringify(a && a[k]) === JSON.stringify(b[k]));
/* expectation: null | {tool, params(subset), absent:[param names that must be absent]} | {clar: tool} ; page: optional page context */
const Q = {
  schedule_strength: [
    ["How hard is BYU's remaining schedule?", { tool: "schedule_strength", params: { team: "byu", view: "remaining" } }],
    ["Toughest schedule left in the Big 12", { tool: "schedule_strength", params: { conference: "big12", view: "remaining" } }],
    ["Alabama's schedule strength so far", { tool: "schedule_strength", params: { team: "alabama", view: "played" } }],
    ["Who has the easiest schedule left?", { tool: "schedule_strength", params: { view: "remaining", order: "easiest" }, absent: ["team", "conference"] }],
    ["Utah's strength of schedule", { tool: "schedule_strength", params: { team: "utah", view: "remaining" } }],
    ["What is Texas Tech's strength of schedule so far?", { tool: "schedule_strength", params: { team: "texas-tech", view: "played" } }],
    ["Top 5 toughest schedules left", { tool: "schedule_strength", params: { n: 5, order: "toughest" } }],
    ["Which team has the toughest schedule so far?", { tool: "schedule_strength", params: { view: "played", order: "toughest" }, absent: ["team"] }],
    ["Easiest schedule in the Big 12", { tool: "schedule_strength", params: { conference: "big12" } }],
    ["Is Georgia's schedule hard?", { tool: "schedule_strength", params: { team: "georgia" } }],
    ["How tough is Ohio State's remaining schedule?", { tool: "schedule_strength", params: { team: "ohio-state", view: "remaining" } }],
    ["How tough are the Bears' opponents left?", { clar: "schedule_strength" }],
    ["Strength of schedule for Miami", { clar: "schedule_strength" }],
    ["How hard is the schedule?", { tool: "schedule_strength", params: { team: "utah" }, page: { mode: "team", team: "utah" } }],
    ["Utah's strength of schedule according to ESPN", null],
    ["Utah's SP+ strength of schedule", null],
    ["What is FPI strength of schedule for Utah?", null],
    ["What does Utah need to do with its remaining schedule?", null],
    ["What is the easiest path to a bye for Utah?", null],
    ["Utah's remaining games", null],
    ["Utah's schedule", null],
    ["Best record against the toughest schedule", null],
    ["vegas line on Utah's best wins", null],
    ["Utah's strength of schedule and BYU's", null],
    ["Strength of schedule? Should I bet on Utah?", null],
    ["Toughest basketball schedule left", null],
    ["Top 50 toughest schedules", null],
    ["What was Utah's strength of schedule last year?", null],
    ["Does the committee count strength of schedule?", null]
  ],
  quality_wins: [
    ["Alabama's worst loss", { tool: "quality_wins", params: { team: "alabama", view: "losses" } }],
    ["Who has beaten a top 10 team?", { tool: "quality_wins", params: { view: "wins", top: 10 }, absent: ["team"] }],
    ["Does Utah have a quality win?", { tool: "quality_wins", params: { team: "utah", view: "wins" } }],
    ["Indiana's best win", { tool: "quality_wins", params: { team: "indiana", view: "wins", show: "best" } }],
    ["Best wins in the country", { tool: "quality_wins", params: { view: "wins" }, absent: ["team"] }],
    ["Alabama's best wins", { tool: "quality_wins", params: { team: "alabama", view: "wins" } }],
    ["Georgia's best and worst", null],
    ["Alabama's best wins and worst losses", { tool: "quality_wins", params: { team: "alabama", view: "both" } }],
    ["Alabama's best wins and worst loss", { tool: "quality_wins", params: { team: "alabama", view: "both" } }],
    ["Utah's best wins over top 10 teams", { tool: "quality_wins", params: { team: "utah", view: "wins", top: 10 } }],
    ["Which teams have beaten a ranked team?", { tool: "quality_wins", params: { view: "wins" }, absent: ["team", "top"] }],
    ["Most wins over top 25 teams", { tool: "quality_wins", params: { view: "wins", top: 25 } }],
    ["What is Texas Tech's biggest win?", { tool: "quality_wins", params: { team: "texas-tech" } }],
    ["Utah's worst loss", { tool: "quality_wins", params: { team: "utah", view: "losses" } }],
    ["Did the Bears have a quality win?", { clar: "quality_wins" }],
    ["Miami's best wins", { clar: "quality_wins" }],
    ["What is Utah's best win?", { tool: "quality_wins", params: { team: "utah" }, page: { mode: "team", team: "utah" } }],
    ["Who beat Alabama?", null],
    ["Alabama's resume", null],
    ["Alabama's strength of record", null],
    ["Did Utah beat BYU?", null],
    ["Who has beaten a top 40 team?", null],
    ["Who has beaten a top 0 team?", null],
    ["Alabama's best wins according to ESPN", null],
    ["Alabama's best win? Should I bet on them?", null],
    ["What if Alabama beats Georgia, does that count as a quality win?", null],
    ["Best wins in the SEC", null],
    ["Alabama's best basketball wins", null],
    ["Alabama's best wins last year", null]
  ],
  team_compare: [
    ["Utah vs BYU", { tool: "team_compare", params: { teams: ["utah", "byu"], aspect: "all" } }],
    ["Utah versus BYU", { tool: "team_compare", params: { teams: ["utah", "byu"] } }],
    ["Compare Arizona and BYU", { tool: "team_compare", params: { teams: ["arizona", "byu"], aspect: "all" } }],
    ["Compare Notre Dame and Utah", { tool: "team_compare", params: { teams: ["notre-dame", "utah"] } }],
    ["Indiana vs Ohio State", { tool: "team_compare", params: { teams: ["indiana", "ohio-state"] } }],
    ["What is the difference between Georgia and Alabama?", { tool: "team_compare", params: { teams: ["georgia", "alabama"] } }],
    ["Compare Georgia and Alabama chances", { tool: "team_compare", params: { teams: ["georgia", "alabama"], aspect: "chances" } }],
    ["Compare Georgia and Alabama records", { tool: "team_compare", params: { teams: ["georgia", "alabama"], aspect: "record" } }],
    ["Compare Georgia and Alabama rank", { tool: "team_compare", params: { teams: ["georgia", "alabama"], aspect: "rank" } }],
    ["Compare Georgia and Alabama records and chances", { tool: "team_compare", params: { teams: ["georgia", "alabama"], aspect: "all" } }],
    ["Texas vs Oklahoma", { tool: "team_compare", params: { teams: ["texas", "oklahoma"] } }],
    ["Compare Texas and Tech", { clar: "team_compare" }],
    ["Compare Miami and Utah", { clar: "team_compare" }],
    ["Compare Utah and Utah", null],
    ["Utah vs Washington State and Boise", null],
    ["Compare Utah, BYU and Arizona", null],
    ["Compare Utah", null],
    ["Who would win Utah vs BYU?", null],
    ["what's the vegas line on Utah vs BYU", null],
    ["compare BYU winning vs losing to Texas Tech", null],
    ["Utah vs BYU point spread pick", null],
    ["Who will win Utah versus BYU?", null],
    ["Utah vs BYU tonight", null],
    ["Did Utah beat BYU?", null],
    ["Compare Utah and BYU's path to the playoff", null],
    ["Compare Utah and BYU's schedules", null],
    ["What if Utah beats BYU?", null],
    ["Utah vs BYU odds of winning", null],
    ["Utah vs BYU bet", null],
    ["Compare Utah and BYU in basketball", null],
    ["Compare Utah and Montana", null],
    ["Compare Utah and BYU resume", null],
    ["Who has the better resume, Utah or BYU?", null]
  ]
};
/* boundary phrases with all 19 tools live: expected tool, or null = no tool (falls to the existing AI/miss path), or "any:a|b" */
const BOUNDARY = [
  ["Who beat Alabama?", "head_to_head"], ["Did Utah beat BYU?", "head_to_head"], ["Who has Georgia beaten?", "head_to_head"],
  ["When does Utah play BYU?", "team_schedule"], ["Utah's remaining games", "team_schedule"], ["Utah's schedule", "team_schedule"], ["Utah's remaining schedule", "team_schedule"],
  ["What is the easiest path to a bye for Utah?", "any:team_path|path_compare|team_needs"], ["Utah and BYU's path to the playoff", "path_compare"],
  ["What if Utah beats BYU?", null], ["Alabama's resume", null], ["Utah's strength of record", null], ["Does Utah have a good resume?", null],
  ["Utah's strength of schedule according to ESPN", null], ["Utah's SP+ rating", null], ["What is Alabama's FPI?", null],
  ["Who would win Utah vs BYU?", null], ["Should I bet on Utah vs BYU?", null],
  ["How hard is BYU's remaining schedule?", "schedule_strength"], ["Toughest schedule left in the Big 12", "schedule_strength"], ["Who has the easiest schedule left?", "schedule_strength"], ["Alabama's schedule strength so far", "schedule_strength"],
  ["Alabama's worst loss", "quality_wins"], ["Who has beaten a top 10 team?", "quality_wins"], ["Does Utah have a quality win?", "quality_wins"], ["Indiana's best win", "quality_wins"],
  ["Utah vs BYU", "team_compare"], ["Compare Arizona and BYU", "team_compare"], ["Indiana vs Ohio State", "team_compare"],
  ["Top 10 teams", "rankings_list"], ["Who is ranked #1?", "any:rankings_list|team_snapshot"], ["Where is Utah ranked?", "team_snapshot"], ["What are Utah's playoff chances?", "any:team_snapshot|playoff_field|team_needs"],
  ["Which games matter most for Utah?", "games_that_matter"], ["What games are on Saturday?", "slate_this_week"], ["How does the playoff work?", "explain_site"],
  ["Has Utah clinched a bye?", "status_check"], ["What does Utah need to make the playoff?", "team_needs"]
];
(async () => {
  for (const tool of NEW) {
    TB.setLive([tool]);
    chk(tool + ": at least 8 questions, 6+ refusals", Q[tool].length >= 14 && Q[tool].filter(x => x[1] === null).length >= 6);
    for (const [q, exp] of Q[tool]) {
      const m = await T.match(q, exp && exp.page ? { page: exp.page } : undefined), lab = tool + ' "' + q + '"';
      if (exp === null) { chk(lab + " -> no match (falls to the existing path)", !m, m); continue; }
      if (exp.clar) { chk(lab + " -> clarify", !!(m && m.tool === exp.clar && m.clarify && m.clarify.param === "team"), m); continue; }
      const ok = !!(m && m.tool === exp.tool && !m.clarify && sub(m.params, exp.params) && (exp.absent || []).every(k => !(k in m.params)));
      chk(lab + " -> " + exp.tool + " " + JSON.stringify(exp.params), ok, m);
      if (!ok) continue;
      const a = await T.answer(m.tool, m.params);
      chk(lab + " -> card built, no errors, as-of label, no banned wording", !!(a.card && !a.card.errors.length && /As of /.test(a.card.text) && /estimate/i.test(a.card.text) && !BAN.test(a.card.text) && !/Resum\u00e9/.test(a.card.text)), a.card && a.card.errors.concat(a.r));
      chk(lab + " -> digit provenance", !a.card || !TB.card.digitProblems || !TB.card.digitProblems(a.card, q).length, a.card && TB.card.digitProblems(a.card, q));
    }
    const probe = Q[tool].find(x => x[1] && x[1].tool === tool && !x[1].page);
    for (const [lab, list, should] of [["listed alone", [tool], true], ["list empty", [], false], ["the 16 shipped ids", OLD16, false], ["the other two new tools", NEW.filter(x => x !== tool), false], ["the 16 + this tool", OLD16.concat([tool]), true]]) {
      TB.setLive(list); const m = await T.match(probe[0]);
      if (should) chk(tool + " flag fixture (" + lab + "): answers", !!(m && m.tool === tool), m);
      else chk(tool + " flag fixture (" + lab + "): absent", !m || m.tool !== tool, m);
    }
  }
  /* boundaries with everything live (harness only) */
  TB.setLive(OLD16.concat(NEW));
  for (const [q, want] of BOUNDARY) {
    const m = await T.match(q), got = m ? m.tool + (m.clarify ? "(clarify)" : "") : null;
    let ok; if (want === null) ok = !m || !NEW.includes(m.tool); else if (want.indexOf("any:") === 0) ok = !!m && want.slice(4).split("|").indexOf(m.tool) >= 0; else ok = !!m && m.tool === want;
    chk('boundary (19 live) "' + q + '" -> ' + (want === null ? "not a new tool / existing path" : want), ok, got);
    if (want === null) chk('boundary (19 live) "' + q + '" -> no rule of the three tools fires', !m || !NEW.includes(m.tool), got);
  }
  /* the pre-existing tools answer exactly as before on a page context: team page "Utah vs BYU" with a team page for a third team still two teams -> compare */
  TB.setLive(NEW);
  const pm = await T.match("Utah vs BYU", { page: { mode: "team", team: "arizona" } });
  chk("team page (Arizona): 'Utah vs BYU' still compares the two named teams", !!(pm && pm.tool === "team_compare" && JSON.stringify(pm.params.teams) === '["utah","byu"]'), pm);
  const cm = await T.match("Toughest schedule left", { page: { mode: "conference", conf: "sec", conference: "sec" } });
  chk("conference page (SEC): 'Toughest schedule left' -> schedule_strength", !!(cm && cm.tool === "schedule_strength"), cm);
  console.log("\n" + n + " checks, " + bad.length + " failed"); process.exit(bad.length ? 1 : 0);
})();
