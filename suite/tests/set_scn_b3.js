/* scn_b3 browser-module tests: B3 vs B2. The only browser change is the all-impossible card (no shared-game lead). Everything else identical: scenario.js, chat.js, scnai.js, ai-client.js byte-identical; buildBranched / lines / render / compact identical to B2 for every question except the all-impossible ones; the fold sweep. usage: node tests/set_scn_b3.js TREE_B3 TREE_B2 */
"use strict";
const fs = require("fs"), path = require("path"); const [T3, T2] = process.argv.slice(2).map((p) => path.resolve(p));
const H3 = require("./lib/scn_harness.js")(T3), H2 = require("./lib/scn_harness.js")(T2), S3 = require(path.join(T3, "assets/ks/scnai.js"));
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 400) : "")); } else console.log("PASS " + what); }; const J = JSON.stringify;
const rd = (t, f) => fs.readFileSync(path.join(t, f));
for (const f of ["assets/ks/scenario.js", "assets/ks/scnai.js", "assets/ks/parse.js", "assets/ai-client.js", "assets/ks/sim.js"]) if (fs.existsSync(path.join(T3, f))) ck(rd(T3, f).equals(rd(T2, f)), f + " byte-identical to B2");
const tok = (s) => s.replace(/\?v=[0-9a-f]{10}/g, "?v=T");
ck(tok(rd(T3, "assets/chat.js").toString()) === tok(rd(T2, "assets/chat.js").toString()), "chat.js identical to B2 except ?v= tokens (SCNIMPALL, allImpOn unchanged)");
const texts = []; { const seen = {}; const add = (t) => { if (t && !seen[t]) { seen[t] = 1; texts.push(t); } };
  const bankP = "/workspace/hub/kicktip-toolbox-1026/qbank/questions.json"; if (fs.existsSync(bankP)) JSON.parse(fs.readFileSync(bankP, "utf8")).rows.forEach((r) => add(r.text));
  require("./qbank_scn_a1.json").rows.forEach((r) => add(r.text)); require("./qbank_loss_r2.json").forEach(add); require("./qbank_scn_b.json").rows.forEach((r) => add(r.text));
  const by = {}; H3.B.teams.forEach((t) => { if (t.c && t.c !== "ind") (by[t.c] = by[t.c] || []).push(t.n); });
  for (const c in by) { const L = by[c]; for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { add("What if " + L[i] + " and " + L[j] + " each end with 4 losses"); add("What if " + L[i] + " and " + L[j] + " both end with just one loss"); add("What if " + L[i] + " wins out and " + L[j] + " loses out"); add("What if " + L[i] + " and " + L[j] + " both win out"); } } }
const MODES = [{ branches: true }, { branches: true, allImp: true }];
const build = (H, q, o) => { const p = H.KP.parse(q, H.B.aliases, { choices: {} }); if (p.refusal || p.clarify) return null; const r = H.KS.resolve(p, H.B, o); if (!r.ok) return null; const b = { parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }; try { return { r, f: r.branches ? H.EX.buildBranched(b) : H.EX.build(b) }; } catch (e) { return null; } };
let same = 0, diff = 0, allImp = 0, shotDiff = []; const imp = [];
for (const q of texts) for (const o of MODES) {
  const a = build(H2, q, o), b = build(H3, q, o); if (!a || !b) { if (!!a !== !!b) { diff++; shotDiff.push(q); } continue; }
  const fa = a.f, fb = b.f; if (!fa || !fb) continue; if (J(fa) !== J(fb)) { diff++; shotDiff.push(q + " (facts)"); continue; }
  if (fa.ok === false) continue;
  const la = H2.EX.lines(fa), lb = H3.EX.lines(fb), ra = H2.EX.render(fa, (s) => String(s)), rb = H3.EX.render(fb, (s) => String(s));
  if (fa.all_impossible) { allImp++; imp.push([q, fa, la, lb, ra, rb]); continue; }
  if (J(la) === J(lb) && ra === rb && J(S3.compact(fa)) === J(require(path.join(T2, "assets/ks/scnai.js")).compact(fa))) same++; else { diff++; shotDiff.push(q + " (text)"); }
}
ck(same > 100 && diff === 0, "facts, lines, render and compact are identical to B2 for " + same + " question/mode pairs that are not all-impossible", [same, diff, shotDiff.slice(0, 3)]);
ck(allImp >= 5, "the all-impossible state is covered: " + allImp + " question/mode pairs", allImp);
const LINE = "No result of those games fits your scenario.";
const seenImp = new Set(); let okI = 0;
for (const [q, f, la, lb, ra, rb] of imp) { if (seenImp.has(q)) continue; seenImp.add(q);
  ck(J(lb) === J([la[0], LINE, la[la.length - 2], la[la.length - 1]]) && lb.length === 4, "B3 lines: title, the approved line, rules source, as-of; nothing else: " + q, lb);
  ck(la.length === 5 && /Here is each result|play each other/.test(la[1]), "B2 had the lead (the change is real): " + q);
  ck(!/Here is each result|play each other|If .* beats /.test(lb.join("\n") + rb) && rb.split(LINE).length === 2 && !/class="sxl"|class="sxb"/.test(rb), "B3 card html: the line once, no lead paragraph, no branch sections: " + q);
  ck(rb.indexOf("<h3") < rb.indexOf(LINE) && rb.indexOf(LINE) < rb.indexOf("Rules source") && /Rules source/.test(rb) && /As of/.test(rb), "B3 card html order: title, the line, rules source, as-of: " + q);
  ck(rb.replace(/<p class="sxl">.*?<\/p>/, "") === rb && ra.replace(/<p class="sxl">.*?<\/p>/, "") === rb, "B3 card html == B2 card html minus the lead paragraph: " + q);
  ck(/^[\x20-\x7e\n]+$/.test(lb.join("\n")), "ASCII only: " + q); ck(S3.compact(f) === null, "no write-up offered (compact null): " + q); okI++; }
ck(okI >= 5, "checked " + okI + " all-impossible questions");
const bb = H3.EX.COPY; ck(bb.bImpAll === LINE && /Here is each result/.test(bb.bShared1) && /Here is each result/.test(bb.bSharedN), "COPY.bImpAll unchanged; bShared1 / bSharedN (the lead for every other shared-game card) unchanged");
ck(rd(T3, "assets/ks/explain.js").toString().split("\n").filter((l, i) => rd(T2, "assets/ks/explain.js").toString().split("\n")[i] !== l).length === 2, "explain.js: exactly 2 lines differ from B2 (linesB, renderB)");
console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
