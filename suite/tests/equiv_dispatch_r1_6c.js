/* router1 (router OFF) vs 10d at the dispatch level (matcher -> plan.validate -> tools -> cards) over the whole QA bank on home, a conference page and a team page, plus the "who is still in the mix" family. Identical except the chooser family.
   usage: node tests/equiv_dispatch_r1.js TREE10D TREE_R1 questions.json [out.json] */
"use strict";
const fs = require("fs"); const [t0, t1, qf, outf] = process.argv.slice(2);
const A = require("./lib/tbq.js")(t0), B = require("./lib/tbq.js")(t1);
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const rows = JSON.parse(fs.readFileSync(qf, "utf8")).rows, seen = {}, texts = []; rows.forEach(r => { if (!seen[r.text]) { seen[r.text] = r; texts.push(r.text); } });
const EXTRA = require("./qbank_loss_r2.json").concat(["Who is still in the mix?", "who is still in the mix", "Who's still in the mix?", "Who is still alive?", "Which teams are still alive?", "Who is still in the race?", "Who is eliminated?", "Who is out of it?", "Who is still in the hunt?", "Who is still in contention?"]); EXTRA.forEach(t => { if (!seen[t]) { seen[t] = { id: "extra", group: "extra" }; texts.push(t); } });
const sig = r => JSON.stringify({ route: r.route, status: r.status, plan: r.plan || null, miss: r.miss || null, code: r.code || null, cards: (r.cards || []).map(c => c.text.split(" (model)").join("").split("Reach the conference championship game").join("Make conference championship")) });
(async () => {
  A.TB.setLive(L19); B.TB.setLive(L19); const pages = [{ mode: "home" }, { mode: "conference", conf: "big12" }, { mode: "team", team: "utah" }]; const diffs = []; let same = 0, total = 0;
  for (const pg of pages) for (const t of texts) {
    total++; const a = await A.TB.dispatch(t, pg, {}), b = await B.TB.dispatch(t, pg, {});
    if (sig(a) === sig(b)) same++; else diffs.push({ id: seen[t].id, page: pg.mode, q: t, before: a.route + (a.plan ? " " + JSON.stringify(a.plan) : "") + (a.cards && a.cards[0] ? " | " + a.cards[0].text.slice(0, 50) : ""), after: b.route + " " + (b.code || "") + (b.plan ? " " + JSON.stringify(b.plan) : "") });
  }
  console.log("dispatch equivalence vs 10d (router off): " + total + " (question x page) pairs; identical " + same + ", differing " + diffs.length);
  diffs.forEach(d => console.log("DIFF [" + d.page + "] " + d.id + " " + JSON.stringify(d.q) + "\n   10d: " + d.before + "\n   r1 : " + d.after));
  if (outf) fs.writeFileSync(outf, JSON.stringify(diffs, null, 1));
  const leadOnly = d => d.q && /championship game|race/i.test(d.q) && d.before.split(" | ")[0].replace(/\s+/g, " ").trim() === d.after.split(" | ")[0].replace(/\s+/g, " ").trim() && /conf_race_alive/.test(d.after);   /* router2: same route and plan, only the new lead sentence on the card */
  const ok = diffs.every(d => leadOnly(d) || d.page === "home" && /^(Who|Which|What)\b|^Who's/i.test(d.q) && /still|alive|eliminated|out of it/i.test(d.q) && /clarify which_conf/.test(d.after));
  console.log(ok ? "ALL DIFFS ARE THE CHOOSER FAMILY (home, no conference, no team)" : "UNEXPECTED DIFFS"); process.exit(ok ? 0 : 1);
})();
