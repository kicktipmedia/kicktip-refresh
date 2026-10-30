#!/usr/bin/env node
/* final1 variant (KickTip final1 merge): same as routing_check.js, plus: --live runs the matcher with dark:false; (--live is NOT meaningful without TB.setLive; not used) in dark mode a change whose NEW tool is one of the two dark Set 2b tools (strength_of_record, conf_vs_conf) is allowed and listed. Phase 4 routing check (zero model calls, no network). node routing_check.js <old tree> <new tree> <qbank dir> [--out report.json]
 * 1. BR-01..BR-12 (PHASE4_SPEC R1 boundary rows; the shipped bank does not carry them yet, they live in br_rows.json beside this file) route as the spec says.
 * 2. The 14 T02 rows of the QA bank route to the SAME tool with the SAME params through the OLD tree (toolbox1) and the NEW tree.
 * 3. Differential over every text in the bank (492 rows, home page or the row's own page): the new matcher may only differ from the old one where the new tool is team_path or path_compare
 *    AND the text has path wording; every other text must be unchanged. Prints each change. */
"use strict";
const SET3B_ALLOW = {"T25-02":"team_history","T25-03":"team_history","U-10":"team_history","T28-01":"game_win_chance","U-04":"game_win_chance","T24-01":"whatif_conference_outcome","T24-03":"whatif_conference_outcome","T24-04":"whatif_conference_outcome","T26-01":"team_stats","T26-02":"team_stats","T26-03":"team_stats","T26-04":"team_stats","L-H21":"whatif_conference_outcome","L-C07":"whatif_conference_outcome","L-C17":"whatif_conference_outcome","L-GCBIG12-023":"whatif_conference_outcome","T27-01":"my_teams_digest","T27-02":"my_teams_digest","T27-03":"my_teams_digest"};   /* set3m: union of the set3c and set3b2 maps plus set3a's T27 rows: only these rows, only no answer -> the named new tool */
const SET3A_TAKE = {"T23-01":["rankings_list","cfp_committee_rankings"],"T23-02":["team_snapshot","cfp_committee_rankings"],"T23-03":["rankings_list","cfp_committee_rankings"]};   /* set3m: Creative's ruling - committee questions go to cfp_committee_rankings; only these rows, only from the named old tool */
const fs = require("fs"), path = require("path");
const ROOT = "/workspace/kicktip-toolbox3/src"   /* set3b2 copy: read-only use of the toolbox3 helpers */, loadTree = require(path.join(ROOT, "core/tools/tbnode.js"));
const [oldT, newT, qb] = process.argv.slice(2).map(p => path.resolve(p));
const FROZEN = path.join(ROOT, "core/tests/tb/frozen/2026-10-24");
const rows = JSON.parse(fs.readFileSync(path.join(qb, "questions.json"), "utf8")).rows;
const br = JSON.parse(fs.readFileSync("/workspace/kicktip-toolbox3/src/lanes/p4/tests/tb/br_rows.json", "utf8")).rows;
const T02 = ["T02-01", "T02-02", "T02-03", "T02-04", "T02-05", "T02-06", "T02-07", "L-H16", "L-H17", "L-C04", "L-X24", "L-GH131", "A-02", "X-09"];
async function route(tree, items) {
  const { TB } = loadTree(tree, {});
  TB.setLoader(n => JSON.parse(fs.readFileSync(n.startsWith("tb/") ? path.join(tree, "data", n + ".json") : path.join(FROZEN, n + ".json"), "utf8")));
  const data = { "sim-bundle": await TB.data("sim-bundle") }, out = {};
  for (const it of items) { const r = TB.match(it.text, it.page || { mode: "home" }, data, { dark: !process.argv.includes("--live") }); out[it.id] = r ? { tool: r.tool, params: r.params, clarify: r.clarify || null } : null; }
  return out;
}
(async () => {
  const items = rows.map(r => ({ id: r.id, text: r.text, page: r.ctx && r.ctx.page })).concat(br.map(r => ({ id: r.id, text: r.text })));
  const O = await route(oldT, items), N = await route(newT, items);
  let fail = 0, report = { br: [], t02: [], changed: [] };
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  br.forEach(r => {
    const g = N[r.id], ok = !!g && g.tool === r.expect.tool && !g.clarify && Object.keys(r.expect.params || {}).every(k => eq(g.params[k], r.expect.params[k]));
    report.br.push({ id: r.id, ok, got: g }); if (!ok) { fail++; console.log("FAIL " + r.id + " " + r.text + " -> " + JSON.stringify(g)); }
  });
  T02.forEach(id => { const ok = rows.some(r => r.id === id) && eq(O[id], N[id]) && !!N[id] && N[id].tool === "team_needs"; report.t02.push({ id, ok, got: N[id] }); if (!ok) { fail++; console.log("FAIL T02 " + id + " old " + JSON.stringify(O[id]) + " new " + JSON.stringify(N[id])); } });
  const PATHISH = /\b(path|paths|road)\b|how (can|could|would|does|do) .* (make|reach|get|earn)|how many (games|losses) can|minimum record|fewest wins|afford to lose|cant lose|cannot lose/i;
  rows.forEach(r => {
    if (eq(O[r.id], N[r.id])) return;
    let n = N[r.id], NEW2B = ["strength_of_record", "conf_vs_conf"].includes(n && n.tool), allowed = n && (NEW2B || ((n.tool === "team_path" || n.tool === "path_compare") && PATHISH.test(r.text.replace(/'/g, ""))));
    const s3 = SET3B_ALLOW[r.id] && O[r.id] === null && n && n.tool === SET3B_ALLOW[r.id]; allowed = allowed || s3; const s3a = SET3A_TAKE[r.id] && O[r.id] && O[r.id].tool === SET3A_TAKE[r.id][0] && n && n.tool === SET3A_TAKE[r.id][1]; allowed = allowed || s3a;
    report.changed.push({ id: r.id, text: r.text, old: O[r.id], now: n, allowed: !!allowed }); if (!allowed) { fail++; console.log("UNEXPECTED CHANGE " + r.id + " " + r.text + " old " + JSON.stringify(O[r.id]) + " new " + JSON.stringify(n)); }
  });
  console.log("BR %d/%d  T02 %d/%d  bank texts %d, changed routing %d (allowed %d)", report.br.filter(x => x.ok).length, br.length, report.t02.filter(x => x.ok).length, T02.length, rows.length, report.changed.length, report.changed.filter(x => x.allowed).length);
  const oi = process.argv.indexOf("--out"); if (oi > 0) fs.writeFileSync(process.argv[oi + 1], JSON.stringify(report, null, 1));
  process.exit(fail ? 1 : 0);
})();
