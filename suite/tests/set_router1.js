/* router1 client tests: "Which conference?" chooser (router OFF, pure client), saved-team default, plan.rerunConf, plan.runRouted (the client fill), the Lab no-match line. usage: node tests/set_router1.js TREE */
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const tree = path.resolve(process.argv[2]), T = require("./lib/tbq.js")(tree), TB = T.TB, C = TB.core, P = TB.plan;
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 300) : "")); } else console.log("PASS " + what); };
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const BANNED = /\b(bets?|betting|wagers?|spreads?|parlays?|CCG|title game|the 12(?!-team))\b|\u00e9/i;
(async () => {
  TB.setLive(L19);
  const FAM = ["Who is still in the mix?", "who is still in the mix", "Who's still in the mix?", "Who is still alive?", "who's still alive", "Which teams are still alive?", "Who is still in the race?", "Who is still in the hunt?", "Who is eliminated?", "Which teams are eliminated?", "Who is out of it?", "Who is still in contention?", "Which teams are ruled out?", "Who is knocked out?", "what teams are still in the running", "Who is still alive right now?"];
  const home = { mode: "home" };
  for (const q of FAM) {
    const r = await TB.dispatch(q, home, {}); const c = r.cards && r.cards[0];
    ck(r.route === "clarify" && c && c.code === "which_conf" && c.options.length === 10 && /data-miss="which_conf"/.test(c.html), "chooser (home, nothing saved): " + q, [r.route, c && c.code]);
    if (c) { ck(!BANNED.test(c.text) && !/CCG/.test(c.html), "chooser card has no banned wording: " + q); }
  }
  { const r = await TB.dispatch(FAM[0], home, {}), h = r.cards[0].html; ck((h.match(/<button /g) || []).length === 10 && /Which conference\?/.test(h) && !/<script|onclick/i.test(h), "chooser html: 10 chip buttons, title, no script/handlers"); ck(h.length < 2600, "chooser html is small", h.length); ck(!/data-q="[^"]*[<>]/.test(h), "chooser data-q escaped"); }
  { const r = await TB.dispatch(FAM[0], home, {}), h = r.cards[0].html; ck(h.includes("Choose a conference to see who is still in the race for its conference championship game.") && !/its championship game/.test(h), "chooser body: conference championship game spelled out (router1b)"); }
  // saved team: answer for that team's conference
  { const r = await TB.dispatch("Who is still in the mix?", { mode: "home", savedTeam: "utah" }, {}); ck(r.route === "matcher" && r.plan[0].tool === "conf_race_alive" && r.plan[0].params.conference === "big12" && r.plan[0].params.status === "in", "saved team utah -> conf_race_alive big12", r.plan); }
  { const r = await TB.dispatch("Who is still alive?", { mode: "home", savedTeams: ["ohio-state"] }, {}); ck(r.route === "matcher" && r.plan[0].params.conference === "big10", "saved team ohio-state -> big10", r.plan); }
  { const r = await TB.dispatch("Who is eliminated?", { mode: "home", savedTeams: ["texas"] }, {}); ck(r.route === "matcher" && r.plan[0].params.status === "out" && r.plan[0].params.conference === "sec", "eliminated + saved texas -> sec, out", r.plan); }
  { const r = await TB.dispatch("Who is still in the mix?", { mode: "home", savedTeams: ["ohio-state", "texas"] }, {}); ck(r.route === "clarify" && r.cards[0].options.slice(0, 2).join() === "sec,big10" || r.cards[0].options.slice(0, 2).join() === "big10,sec", "two saved teams in two conferences -> chooser, theirs first", r.cards[0].options); }
  { const r = await TB.dispatch("Who is still in the mix?", { mode: "home", savedTeams: ["not-a-team", 5, null] }, {}); ck(r.route === "clarify", "junk saved teams ignored -> chooser"); }
  // conference page unchanged; named team / conference unchanged
  { const r = await TB.dispatch("Who is still in the mix?", { mode: "conference", conf: "sec" }, {}); ck(r.route === "matcher" && r.plan[0].params.conference === "sec", "conference page: unchanged (that conference)", r.plan); }
  { const r = await TB.dispatch("Who is still in the race for the Big 12?", home, {}); ck(r.route === "matcher" && r.plan[0].params.conference === "big12", "named conference: direct answer"); }
  { const r = await TB.dispatch("Is Utah still alive?", home, {}); ck(r.route !== "clarify" || r.cards[0].code !== "which_conf", "a named team never gets the conference chooser"); }
  for (const q of ["Who is in the playoff?", "Who is the best team?", "What is the weather?", "Who is still in the race for the Big 12 and the SEC?"]) { const r = await TB.dispatch(q, home, {}); ck(!(r.cards && r.cards[0] && r.cards[0].code === "which_conf"), "no chooser for: " + q, r.route); }
  ck((TB.get("conf_race_alive").modes || []).slice().sort().join() === "conference,home", "conf_race_alive modes are home + conference only", TB.get("conf_race_alive").modes);
  // chip tap = local re-run, nothing counted, no model
  { const r = await TB.dispatch(FAM[0], home, {}); const cl = r.clarify; let called = 0;
    const rr = await P.rerunConf(cl, "sec", home, { model: () => { called++; } });
    ck(rr.route === "clarify_pick" || rr.route === "matcher" || rr.status === "ok", "rerunConf: ok", [rr.route, rr.status, rr.code]); ck(called === 0 && rr.plan && rr.plan[0].params.conference === "sec" && rr.cards[0].html.indexOf("which_conf") < 0, "rerunConf: SEC answer, no model call");
    for (const bc of ["", "nope", "ccg", undefined, "notre-dame"]) { const x = await P.rerunConf(cl, bc, home, {}); ck(x.route === "none" && x.code === "bad_call", "rerunConf rejects conference " + JSON.stringify(bc)); }
    const y = await P.rerunConf({ tool: "team_snapshot", params: {} }, "sec", home, {}); ck(y.route === "none", "rerunConf only for conf_race_alive"); }
  // runRouted: the client fill
  const RR = (calls, text, page) => P.runRouted({ calls }, text, page || home, {});
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Utah" } }], "How is Utah doing this year?"); ck(r.route === "router" && r.status === "ok" && r.cards.length === 1 && r.plan[0].params.team === "utah", "runRouted: valid single call", [r.route, r.code]); }
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Utah" } }], "How is BYU doing?"); ck(r.route === "none" && r.code === "bad_team", "runRouted: team not in the typed text -> fallback", r.code); }
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Narnia" } }], "How is Narnia doing?"); ck(r.route === "none", "runRouted: unknown team -> fallback", r.code); }
  for (const id of ["ccg_matchup", "team_trend", "nope", ""]) { const r = await RR([{ tool: id, params: {} }], "How is Utah doing?"); ck(r.route === "none", "runRouted: tool '" + id + "' -> fallback", r.code); }
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Utah" } }], "What are the odds Utah covers the spread?"); ck(r.route === "none" && r.code === "gated", "runRouted: betting text re-gated on the client", r.code); }
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Utah" } }, { tool: "team_snapshot", params: { team: "BYU" } }, { tool: "team_snapshot", params: { team: "Iowa State" } }], "Utah BYU Iowa State"); ck(r.route === "none" && r.code === "bad_calls", "runRouted: more than 2 calls -> fallback"); }
  { const r = await RR([{ tool: "team_snapshot", params: { team: "Utah", evil: "<img>" } }], "How is Utah doing?"); ck(r.route === "router" && !/<img/.test(r.cards[0].html), "runRouted: unknown params dropped"); }
  { const r = await RR([{ tool: "team_compare", params: { teams: ["Utah", "BYU"], aspect: "all" } }], "Compare Utah and BYU"); ck(r.route === "router" && r.plan[0].params.teams.length === 2, "runRouted: teams list filled", [r.route, r.code]); }
  { const r = await RR([{ tool: "team_compare", params: { teams: ["Utah", "BYU"], aspect: "bogus" } }], "Compare Utah and BYU"); ck(r.route === "none", "runRouted: bad enum -> fallback", r.code); }
  { const r = await RR([{ tool: "conf_race_alive", params: { status: "in" } }], "Who is still in the mix?"); ck(r.route === "clarify" && r.code === "which_conf" && /which_conf/.test(r.cards[0].html), "runRouted: conf_race_alive with no conference -> the chooser", [r.route, r.code]); }
  { const r = await RR([{ tool: "conf_race_alive", params: { status: "in" } }], "Who is still in the mix?", { mode: "home", savedTeams: ["utah"] }); ck(r.route === "router" && r.plan[0].params.conference === "big12", "runRouted: saved team default for conf_race_alive", [r.route, r.code]); }
  { const r = await RR([{ tool: "conf_race_alive", params: { status: "in" } }], "who is in it?", { mode: "conference", conf: "acc" }); ck(r.route === "router" && r.plan[0].params.conference === "acc", "runRouted: conference page supplies its conference", [r.route, r.code]); }
  { const r = await RR([{ tool: "conf_race_alive", params: { status: "in", conference: "Big Ten" } }], "Who can still win the Big Ten?"); ck(r.route === "router" && r.plan[0].params.conference === "big10", "runRouted: conference name -> id"); }
  { const r = await RR([{ tool: "conf_race_alive", params: { status: "in", conference: "Narnia League" } }], "Who can still win the Narnia League?"); ck(r.route === "none", "runRouted: bad conference -> fallback", r.code); }
  { const r = await P.runRouted(null, "x", home, {}); ck(r.route === "none" && r.code === "bad_calls", "runRouted: null route"); const r2 = await P.runRouted({ calls: [] }, "x", home, {}); ck(r2.route === "none", "runRouted: no calls"); }
  // Lab no-match line (assets/ccgsim-ui.js)
  { const src = fs.readFileSync(path.join(tree, "assets/ccgsim-ui.js"), "utf8"); const m1 = src.match(/var AI_NOTEAM_Q = ("[^"]*");/), m2 = src.match(/function aiNoTeam\(q\) \{[^\n]*\}/);
    ck(!!m1 && !!m2, "ccgsim-ui has AI_NOTEAM_Q and aiNoTeam");
    if (m1 && m2) { const f = vm.runInNewContext("var AI_CLARIFY={no_team:'OLD'};var AI_NOTEAM_Q=" + m1[1] + ";" + m2[0] + ";aiNoTeam"); const Q = JSON.parse(m1[1]);
      ck(!BANNED.test(Q) && /^[\x20-\x7e]+$/.test(Q), "Lab line: ASCII, no banned words");
      for (const q of ["Who is still in the mix?", "which teams are alive", "Is Utah alive", "How does Texas get in"]) ck(f(q) === Q, "Lab: question-style ask -> new line: " + q);
      ck(Q === "I couldn't match that one. Name a team or a conference, like: What if BYU beats Utah?", "Lab line is the Creative-approved router1b text", Q);
      { const kv = require("vm"), KC = { window: {} }; kv.createContext(KC); kv.runInContext(fs.readFileSync(path.join(tree, "assets/ks/parse.js"), "utf8"), KC); const KP = KC.KTParse || (KC.window && KC.window.KTParse), B = JSON.parse(fs.readFileSync(path.join(tree, "data/sim-bundle.json"), "utf8")), ex = Q.slice(Q.lastIndexOf("like: ") + 6), R = KP.parse(ex, B.aliases, { choices: {} }), nm = i => B.teams[i].g;
        ck(!R.clarify && !R.refusal && R.items.length === 1 && R.items[0].kind === "beats" && nm(R.items[0].winner) === "byu" && nm(R.items[0].loser) === "utah", "Lab: the line's own example runs in the Lab parser (BYU beats Utah)", R); ck(f(ex) === Q, "Lab (router2): aiNoTeam is only reached when no team was found, so what-if asks get the line too"); } 
      for (const q of ["BYU beats Utah", "Utah", "", "BYU over Utah by 7"]) ck(f(q) === "OLD", "Lab: other asks keep the old line: " + JSON.stringify(q));
      for (const q of ["what if the sun explodes", "What if everyone wins out?", "what if"]) ck(f(q) === Q, "Lab (router2): odd what-if ask with no team -> approved line: " + q); } }
  console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})().catch(e => { console.log("CRASH", e.stack); process.exit(2); });
