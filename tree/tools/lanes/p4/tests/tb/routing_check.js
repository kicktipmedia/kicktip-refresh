#!/usr/bin/env node
/* Phase 4 routing check (zero model calls, no network). node routing_check.js <old tree> <new tree> <qbank dir> [--out report.json]
 * 1. BR-01..BR-12 (PHASE4_SPEC R1 boundary rows; the shipped bank does not carry them yet, they live in br_rows.json beside this file) route as the spec says.
 * 2. The 14 T02 rows of the QA bank route to the SAME tool with the SAME params through the OLD tree (toolbox1) and the NEW tree.
 * 3. Differential over every text in the bank (492 rows, home page or the row's own page): the new matcher may only differ from the old one where the new tool is team_path or path_compare
 *    AND the text has path wording; every other text must be unchanged. Prints each change. */
"use strict";
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../.."), loadTree = require(path.join(ROOT, "core/tools/tbnode.js"));
const [oldT, newT, qb] = process.argv.slice(2).map(p => path.resolve(p));
const FROZEN = path.join(ROOT, "core/tests/tb/frozen/2026-10-24");
const rows = JSON.parse(fs.readFileSync(path.join(qb, "questions.json"), "utf8")).rows;
const br = JSON.parse(fs.readFileSync(path.join(__dirname, "br_rows.json"), "utf8")).rows;
const T02 = ["T02-01", "T02-02", "T02-03", "T02-04", "T02-05", "T02-06", "T02-07", "L-H16", "L-H17", "L-C04", "L-X24", "L-GH131", "A-02", "X-09"];
async function route(tree, items) {
  const { TB } = loadTree(tree, {});
  TB.setLoader(n => JSON.parse(fs.readFileSync(n.startsWith("tb/") ? path.join(tree, "data", n + ".json") : path.join(FROZEN, n + ".json"), "utf8")));
  const data = { "sim-bundle": await TB.data("sim-bundle") }, out = {};
  for (const it of items) { const r = TB.match(it.text, it.page || { mode: "home" }, data, { dark: true }); out[it.id] = r ? { tool: r.tool, params: r.params, clarify: r.clarify || null } : null; }
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
    const n = N[r.id], allowed = n && (n.tool === "team_path" || n.tool === "path_compare") && PATHISH.test(r.text.replace(/'/g, ""));
    report.changed.push({ id: r.id, text: r.text, old: O[r.id], now: n, allowed: !!allowed }); if (!allowed) { fail++; console.log("UNEXPECTED CHANGE " + r.id + " " + r.text + " old " + JSON.stringify(O[r.id]) + " new " + JSON.stringify(n)); }
  });
  console.log("BR %d/%d  T02 %d/%d  bank texts %d, changed routing %d (allowed %d)", report.br.filter(x => x.ok).length, br.length, report.t02.filter(x => x.ok).length, T02.length, rows.length, report.changed.length, report.changed.filter(x => x.allowed).length);
  const oi = process.argv.indexOf("--out"); if (oi > 0) fs.writeFileSync(process.argv[oi + 1], JSON.stringify(report, null, 1));
  process.exit(fail ? 1 : 0);
})();
