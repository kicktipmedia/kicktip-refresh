/* What would change if the two new tools were switched on: the whole QA bank, 19 live vs 21 live (test switch only). usage: node tests/bank_on.js <tree> <questions.json> */
"use strict";
const fs = require("fs"), T = require("./lib/tbq.js")(process.argv[2]), TB = T.TB;
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const rows = JSON.parse(fs.readFileSync(process.argv[3], "utf8")).rows, seen = {}, texts = []; rows.forEach(r => { if (!seen[r.text]) { seen[r.text] = 1; texts.push(r.text); } });
(async () => {
  const diff = [];
  for (const t of texts) { TB.setLive(L19); const a = await T.match(t); TB.setLive(L19.concat(["ccg_matchup", "team_trend"])); const b = await T.match(t); if (JSON.stringify(a) !== JSON.stringify(b)) diff.push({ q: t, was: a ? a.tool : null, now: b ? b.tool : null, rule: b && b.rule }); }
  console.log("bank " + texts.length + " unique questions; routes that change when the two new tools are on: " + diff.length);
  diff.forEach(d => console.log("  \"" + d.q + "\": " + d.was + " -> " + d.now + " (" + d.rule + ")"));
})();
