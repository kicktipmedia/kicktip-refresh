/* toolbox9c polish Lows: gate/matcher/route/card checks. usage: node tests/set9_polish.js <tree9> [<tree8b-code-on-new-data>] */
"use strict";
const T = require("./lib/tbq.js")(process.argv[2]); const P = process.argv[3] ? require("./lib/tbq.js")(process.argv[3]) : null;
let n = 0, bad = 0; const ck = (ok, what) => { n++; if (!ok) { bad++; console.log("FAIL " + what); } else console.log("PASS " + what); };
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
(async () => {
  T.TB.setLive(L19); if (P) P.TB.setLive(L19);
  // 1. gate: legit words pass; pure betting still refuses
  for (const q of ["Las Vegas Bowl", "Who is in the Las Vegas Bowl?", "orange juice", "juice cleanse", "Utah win total", "Utah's win total this year", "BYU win total", "win total for Arizona State", "wins total for Utah"]) ck(T.TB.gate(q) !== "money", "gate passes (not money): " + q + " [" + T.TB.gate(q) + "]");
  for (const q of ["over under", "over/under for Utah", "What is the over under on Utah vs BYU?", "win total", "win totals", "win totals for the Big 12", "the win totals", "make money", "How do I make money on Utah?", "can I make money on this", "making money on football", "what's the vegas number", "Vegas favorite this week", "Las Vegas line for Utah", "who has the juice", "Utah juice", "Las Vegas odds on Utah"]) ck(T.TB.gate(q) === "money", "gate refuses money: " + q + " [" + T.TB.gate(q) + "]");
  // 2. O/U
  for (const q of ["O/U on Utah vs BYU", "o/u for Utah", "Utah vs BYU O / U", "what's the O/U"]) ck(T.TB.gate(q) === "money", "O/U refused: " + q);
  for (const q of ["OU vs Texas", "How is OU doing?", "Utah vs BYU", "Ohio State vs Oregon"]) ck(T.TB.gate(q) !== "money", "no false refusal: " + q);
  // "win total" with a team: no tool takes it (page path)
  for (const q of ["Utah win total", "BYU win total"]) { const m = await T.match(q, { dark: true }); ck(m === null, "win total with a team goes to the page path (no tool): " + q + " -> " + JSON.stringify(m && m.tool)); }
  // toolbox9c B1: win total with market wording / a number beside it is refused; bare ones stay open
  for (const q of ["will BYU go over its win total", "BYU under its win total", "Utah season win total 9.5", "will Utah go over its win total", "Utah win total over or under", "BYU win total line", "BYU win total 8.5", "Utah win total odds", "what is Utah's win total pick", "Utah win total o/u", "BYU win total lock", "Utah win total cover", "Utah win total prop", "Utah win total 10", "BYU win total eight and a half", "BYU win total bet", "Utah win total spread", "Utah win total number"]) ck(T.TB.gate(q) === "money", "9b refuse: " + q + " [" + T.TB.gate(q) + "]");
  for (const q of ["Utah win total", "BYU win total", "Utah's win total this year", "what is BYU's win total", "projected win total for Utah", "expected win total BYU", "average win total for Arizona State", "Utah's projected final win total"]) ck(T.TB.gate(q) !== "money", "9b open: " + q + " [" + T.TB.gate(q) + "]");
  // toolbox9c: projected / expected / average win total with market wording or a decimal figure is refused too; plain ones stay open
  for (const q of ["expected win total over 9.5", "projected win total under 8.5", "average win total line", "BYU expected win total odds", "Utah projected win total 9.5", "BYU projected win total over", "average win total o/u", "Utah's expected win total bet", "projected win total pick for Utah", "expected win total spread", "BYU projected win total eight and a half", "average win total prop", "projected final win total lock", "Will Utah cover its projected win total", "expected win total number for BYU", "Utah projected win total price", "projected win total 8,5"]) ck(T.TB.gate(q) === "money", "9c refuse: " + q + " [" + T.TB.gate(q) + "]");
  for (const q of ["Utah's projected win total", "BYU expected wins", "average win total", "projected win total for Utah", "BYU's expected win total this season", "Utah projected final win total", "average win total for the Big 12", "Utah projected win total in 2026", "expected win total for the Utes if they beat BYU"]) ck(T.TB.gate(q) !== "money", "9c open: " + q + " [" + T.TB.gate(q) + "]");
  for (const q of ["Utah win total", "BYU win total"]) { const m = await T.match(q, { dark: true }); ck(m === null, "9b bare win total still goes to page path: " + q); }
  // 3. SOS rank routes to schedule_strength team card
  for (const q of ["Utah's SOS rank", "BYU SOS rank", "What is Alabama's SOS ranking?", "Utah SOS"]) { const m = await T.match(q, { dark: true }); ck(m && (m.tool === "schedule_strength" || m.tool === "team_snapshot") && !m.clarify, q + " -> " + (m && m.tool) + " " + JSON.stringify(m && m.params)); }
  { const m = await T.match("Utah's SOS rank", { dark: true }); ck(m && m.tool === "schedule_strength" && m.params.team === "utah", "Utah's SOS rank -> schedule_strength team utah"); }
  for (const q of ["Who has the toughest SOS?", "top 10 strength of schedule", "easiest schedule in the nation"]) { const m = await T.match(q, { dark: true }); ck(m && m.tool === "schedule_strength" && !m.params.team, "league list unchanged: " + q + " -> " + JSON.stringify(m && m.params)); }
  // 4. conference easiest honored
  const run = async (p) => (await T.answer("schedule_strength", p));
  const tough = await run({ view: "remaining", conference: "big12" }), easy = await run({ view: "remaining", conference: "big12", order: "easiest" });
  ck(tough.card && easy.card && tough.card.text !== easy.card.text, "conference easiest differs from toughest");
  const rowsOf = (a) => a.r.facts ? (a.r.facts.rows || a.r.facts.list || []) : [];
  const nm = (a) => (a.r.facts.rows || []).map(x => x.id || x.team || x.name);
  const t1 = nm(tough), e1 = nm(easy); ck(t1.length > 3 && JSON.stringify(t1.slice().reverse()) === JSON.stringify(e1), "easiest is the exact reverse order of toughest (" + t1.length + " teams)");
  { const m = await T.match("Easiest schedule left in the Big 12", { dark: true }); ck(m && m.tool === "schedule_strength" && m.params.order === "easiest" && m.params.conference === "big12", "match carries order=easiest for a conference: " + JSON.stringify(m && m.params)); }
  { const m = await T.match("Toughest schedule left in the Big 12", { dark: true }); ck(m && m.tool === "schedule_strength" && !m.params.order, "toughest has no order param (default)"); }
  // 5. biggest games on an empty day
  for (const day of ["sunday", "monday"]) { const a = await T.answer("slate_this_week", { view: "biggest", day }); const b = await T.answer("slate_this_week", { view: "all", day }); ck(a.card && /No games on that day this week/.test(a.card.text) && !/tracked effect/.test(a.card.text), "biggest " + day + " (truly empty day) says no games that day: " + (a.card ? a.card.text.slice(-120) : "")); ck(b.card && /No games on that day this week/.test(b.card.text), "all-games " + day + " keeps the true no-games text"); }
  { const a = await T.answer("slate_this_week", { view: "biggest", day: "tuesday" }); ck(a.card && /tracked effect/.test(a.card.text) || (a.card && /Biggest games/.test(a.card.text)), "biggest tuesday: " + (a.card ? a.card.text.slice(-130) : "")); }
  // 6. TBD
  for (const [id, p] of [["team_schedule", { team: "utah", view: "remaining" }], ["team_schedule", { team: "byu", view: "both" }], ["head_to_head", { teams: ["utah", "byu"] }], ["team_compare", { teams: ["texas", "lsu"], aspect: "all" }], ["slate_this_week", { view: "all" }]]) { const a = await T.answer(id, p); if (!a.card) { ck(false, id + " no card"); continue; } ck(!/\bTBA\b/.test(a.card.text), id + " " + JSON.stringify(p) + " has no TBA" + (/time TBD/.test(a.card.text) ? " (shows time TBD)" : "")); }
  console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})();
