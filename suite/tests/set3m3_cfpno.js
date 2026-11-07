/* set3m3: team_history no-CFP line, all three range forms (1 / 2 / 3+ seasons), rendered from facts; plus the real Utah card */
"use strict";
const path = require("path"), tree = path.resolve(process.argv[2]);
const T = require("./lib/tbq.js")(tree), TB = T.TB;
let n = 0, bad = 0; const chk = (k, c, x) => { n++; if (!c) { bad++; console.log("FAIL " + k + " :: " + JSON.stringify(x).slice(0, 300)); } else console.log("PASS " + k); };
TB.setLive(["team_history"]); let ASOF;
const card = (first, last) => TB.render("team_history", { ok: true, tool: "team_history", params: { team: "utah", view: "last_cfp" }, asof: ASOF,
  facts: { view: "last_cfp", team: "Utah", yes: false, season: null, first: first, last: last } });
const W = [["2025", "2025", "Utah did not make the College Football Playoff in 2025, on KickTip's records."],
  ["2024", "2025", "Utah did not make the College Football Playoff in 2024 or 2025, on KickTip's records."],
  ["2023", "2025", "Utah did not make the College Football Playoff from 2023 to 2025, on KickTip's records."],
  ["2014", "2025", "Utah did not make the College Football Playoff from 2014 to 2025, on KickTip's records."]];
(async () => { const m0 = await T.match("When did Utah last make the playoff?"); ASOF = (await T.run("team_history", m0.params)).asof;
for (const [f, l, want] of W) { const c = card(f, l); chk(f + "-" + l + " form", (c.text || "").includes(want) && !(c.errors && c.errors.length), [c.text, c.errors]);
  chk(f + "-" + l + " no old wording / no placeholders", !/since at least|\{[a-z]+\}/.test(c.text + c.html), c.text); }
const cp = TB.get("team_history").copy; chk("copy: cfpNo removed, three forms present", !("cfpNo" in cp) && cp.cfpNo1 && cp.cfpNo2 && cp.cfpNoN, Object.keys(cp));
const m = await T.match("When did Utah last make the playoff?"); const r = await T.run("team_history", m.params), c = TB.render("team_history", r), F = r.facts;
  const nS = (+F.last) - (+F.first) + 1;
  const want = F.yes
    ? F.team + "'s most recent College Football Playoff trip on KickTip's records: " + F.season + "."
    : nS === 1 ? F.team + " did not make the College Football Playoff in " + F.first + ", on KickTip's records."
    : nS === 2 ? F.team + " did not make the College Football Playoff in " + F.first + " or " + F.last + ", on KickTip's records."
    : F.team + " did not make the College Football Playoff from " + F.first + " to " + F.last + ", on KickTip's records.";
  chk("real Utah card uses the range form implied by its own history (" + F.first + ".." + F.last + ", made it: " + F.yes + ")", (c.text || "").includes(want) && !(c.errors && c.errors.length), [c.text, F]);
  console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})();
