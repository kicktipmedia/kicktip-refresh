/* toolbox9 vs 8b code on the SAME (refreshed) data over the whole QA bank (every unique question text), 19 tools live in both.
 * Classes: GATE (TB.gate result differs), ROUTE (tool/params/clarify differ), CARD (same route, card text differs). Each is printed; nothing else may differ.
 * usage: node tests/equiv_bank9.js <tree8b-code-on-new-data> <tree9> <questions.json> [out.json] */
"use strict";
const fs = require("fs");
const [t8, t9, qf, outf] = process.argv.slice(2);
const A = require("./lib/tbq.js")(t8), B = require("./lib/tbq.js")(t9);
const L19 = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain", "status_check", "team_projection", "head_to_head", "slate_this_week", "explain_site", "schedule_strength", "quality_wins", "team_compare"];
const rows = JSON.parse(fs.readFileSync(qf, "utf8")).rows, seen = {}, texts = [];
rows.forEach(r => { if (!seen[r.text]) { seen[r.text] = r; texts.push(r.text); } });
async function ans(T, text) {
  const m = await T.match(text); if (!m) return { m: null };
  const o = { m: { tool: m.tool, params: m.params, clarify: m.clarify || null } };
  if (m.tool && !m.clarify) { const a = await T.answer(m.tool, m.params); o.card = a.card ? a.card.text : JSON.stringify(a.r); }
  return o;
}
const lab = j => j.m ? j.m.tool + (j.m.clarify ? " (clarify)" : "") + " " + JSON.stringify(j.m.params || {}) : "none";
(async () => {
  const gate = [], route = [], card = []; let same = 0;
  A.TB.setLive(L19); B.TB.setLive(L19);
  for (const t of texts) {
    const g8 = A.TB.gate(t), g9 = B.TB.gate(t);
    const a = await ans(A, t), b = await ans(B, t);
    const e = { id: seen[t].id, group: seen[t].group, q: t };
    if (g8 !== g9) { gate.push(Object.assign(e, { gate8: g8, gate9: g9, was: lab(a), now: lab(b) })); continue; }
    if (JSON.stringify(a.m) !== JSON.stringify(b.m)) { route.push(Object.assign(e, { before: lab(a), after: lab(b) })); continue; }
    if (a.card !== b.card) { card.push(Object.assign(e, { tool: lab(b) })); continue; }
    same++;
  }
  console.log("bank " + texts.length + " unique questions; 8b code vs 9 code on the same data: identical " + same + ", GATE " + gate.length + ", ROUTE " + route.length + ", CARD " + card.length);
  gate.forEach(c => console.log("  GATE " + c.id + " \"" + c.q + "\": " + c.gate8 + " -> " + c.gate9 + " (was " + c.was + ", now " + c.now + ")"));
  route.forEach(c => console.log("  ROUTE " + c.id + " \"" + c.q + "\": " + c.before + " -> " + c.after));
  card.forEach(c => console.log("  CARD " + c.id + " \"" + c.q + "\": " + c.tool));
  if (outf) fs.writeFileSync(outf, JSON.stringify({ n: texts.length, same, gate, route, card }, null, 1));
})();
