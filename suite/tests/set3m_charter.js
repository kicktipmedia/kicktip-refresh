/* set3m charter lint over the six Set 3 tools (#23-#28): copy strings, examples, description, and rendered cards for a fixed question set (tools on via setLive).
 * banned: bet, wager, spread (ESPN strings excepted), parlay, CCG, title game, 'the 12' (allowed when followed by '-team'); 'KickTip is not a betting site.' is the one allowed bet- sentence;
 * every percent in card text reads 'N% (model)' or is an edge 'under 0.05%' / 'at least 99.95%' followed by ' (model)'; no dates in copy (the as-of footer excepted); links only from the closed list (no betting links). usage: node tests/set3m_charter.js <tree> */
"use strict";
const path = require("path"), tree = path.resolve(process.argv[2]);
const T = require("/workspace/kicktip-scn-b3/tests/lib/tbq.js")(tree), TB = T.TB;
const IDS = ["cfp_committee_rankings", "whatif_conference_outcome", "team_history", "team_stats", "my_teams_digest", "game_win_chance"];
const ALLOW = /KickTip is not a betting site\./g;
const BAN = /\b(bets?|betting|bettors?|wagers?|wagering|parlays?|ccg|ccgs|title games?|sportsbooks?)\b|\bthe 12\b(?!-team)|\bspreads?\b/i;
const DATE = /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}\b|\b\d{1,2}\/\d{1,2}(\/\d{2,4})?\b|\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i;
/* OPEN (reported to Creative, not changed): set3b's whatif refusal lines say "in under 1% of simulated seasons" (a sample-size floor, not a model chance); listed exactly so any other percent copy still fails */
const OPEN = ["{team} reaches the conference championship game in under 1% of simulated seasons, so KickTip does not show this view.", "{team} wins the conference championship game in under 1% of simulated seasons, so KickTip does not show this view.", "{team} beats {opp} in the conference championship game in under 1% of simulated seasons, so KickTip does not show that result."];
let n = 0, bad = 0; const chk = (k, c, x) => { n++; if (!c) { bad++; console.log("FAIL " + k + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 300) : "")); } else console.log("PASS " + k); };
const scrub = s => String(s).replace(ALLOW, " ").replace(/ESPN[^.]*?spread[^.]*\./gi, " ");
for (const id of IDS) {
  const t = TB.get(id); chk(id + " registered", !!t); if (!t) continue;
  const strs = Object.values(t.copy || {}).map(e => typeof e === "string" ? e : (e && e.t) || "").concat(t.examples || [], [t.description || "", t.title || ""]);
  const b = strs.filter(s => BAN.test(scrub(s))); chk(id + " copy: no banned words", !b.length, b);
  const d = strs.filter(s => DATE.test(s)); chk(id + " copy: no dates", !d.length, d);
  const p = strs.filter(s => !OPEN.includes(s)).filter(s => /%/.test(s) && !/% \(model\)|\{[a-z0-9]+\} \(model\)/.test(s) && /\d%|\}%/.test(s)); chk(id + " copy: every percent template reads (model)", !p.length, p);
}
/* set3m3: team_history no-CFP line by range length; the open-ended 'since at least' wording is retired */
{ const c = (TB.get("team_history") || {}).copy || {}, all = Object.values(c).map(e => typeof e === "string" ? e : (e && e.t) || "");
  chk("team_history copy: no 'since at least'", !all.some(s => /since at least/i.test(s)), all.filter(s => /since at least/i.test(s)));
  chk("team_history cfpNo1 (1 season)", c.cfpNo1 === "{team} did not make the College Football Playoff in {year}, on KickTip's records.", c.cfpNo1);
  chk("team_history cfpNo2 (2 seasons)", c.cfpNo2 === "{team} did not make the College Football Playoff in {first} or {last}, on KickTip's records.", c.cfpNo2);
  chk("team_history cfpNoN (3+ seasons)", c.cfpNoN === "{team} did not make the College Football Playoff from {first} to {last}, on KickTip's records.", c.cfpNoN); }
const Q = [["cfp_committee_rankings", "Committee top 12"], ["cfp_committee_rankings", "Where is Indiana in the committee rankings?"], ["whatif_conference_outcome", "if Utah wins the Big 12"], ["whatif_conference_outcome", "what if Texas Tech wins the conference"],
  ["team_history", "When did Utah last make the playoff?"], ["team_history", "BYU all-time vs Utah"], ["team_history", "Utah record by season"], ["team_stats", "How many points per game does BYU score?"], ["team_stats", "Indiana points allowed per game"],
  ["my_teams_digest", "How are my teams doing?"], ["game_win_chance", "Will Utah beat BYU?"], ["game_win_chance", "Will Indiana beat Ohio State?"]];
globalThis.KTMyTeams = { get: () => ({ teams: ["utah", "byu", "indiana", "notre-dame", "ohio-state"], lead: {} }) };
(async () => {
  const W = require("fs").readFileSync(path.join(tree, "_worker.js"), "utf8"), L = JSON.parse(/const TB_LIVE_TOOLS = (\[[^\]]*\]);/.exec(W)[1].replace(/'/g, '"'));
  TB.setLive(L.concat(IDS.filter(i => !L.includes(i))));
  for (const [id, q] of Q) {
    const m = await T.match(q); chk(q + " -> " + id, !!(m && m.tool === id), m); if (!m || m.tool !== id) continue;
    const r = await T.run(id, m.params), c = TB.render(id, r), tx = c.text || "", asof = (/As of ([^.]+?\d{4}[^.]*?)\./.exec(tx) || [])[0] || "", body = tx.replace(asof, " ");
    chk(q + ": card renders, no errors", !(c.errors && c.errors.length), c.errors);
    chk(q + ": no banned words", !BAN.test(scrub(body)), (scrub(body).match(BAN) || [])[0]);
    chk(q + ": no dates outside the as-of footer", !DATE.test(body), (body.match(DATE) || [])[0]);
    const pcts = body.match(/(under |at least )?\d+(\.\d+)?%( \(model\))?/g) || [];
    const badp = pcts.filter(p => / \(model\)$/.test(p) || /^(?!under |at least )(0\.0|100\.0|100)%/.test(p) || /^under (?!0\.05%)|^at least (?!99\.95%)/.test(p));
    chk(q + ": every percent reads 'N%' with no (model) label (home6c ruling; edges: under 0.05% / at least 99.95%) [" + pcts.length + "]", !badp.length, badp);
    const hrefs = (c.html.match(/href="[^"]*"/g) || []); chk(q + ": links closed list, no betting links", hrefs.every(h => /^href="(#|\/method\/|\/disclaimer\/|\/#field|\/#top25|\/conference\/(acc|american|big-12|big-ten|conference-usa|independents|mac|mountain-west|pac-12|sec|sun-belt)\/)"$/.test(h)) && !/bet|sportsbook|odds/i.test(c.html.replace(ALLOW, "")), hrefs);
  }
  console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})();
