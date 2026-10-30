/* B vs A2b over the whole QA bank (+ a1/a2/loss banks): parse+resolve identical with no option for ALL questions; with {branches:true} identical except the shared_game clarifies (listed with what each becomes); EX.build identical for non-branched questions. usage: node tests/equiv_b_bank.js TREE_A2B TREE_B BANK [out.json] */
const path = require("path"), fs = require("fs"), [ta, tb, bank, out] = process.argv.slice(2);
const A = require("./lib/scn_harness.js")(path.resolve(ta)), B = require("./lib/scn_harness.js")(path.resolve(tb));
const seen = {}, texts = [];
JSON.parse(fs.readFileSync(bank, "utf8")).rows.map(r => r.text).concat(require("./qbank_scn_a1.json").rows.map(r => r.text), require("./qbank_loss_r2.json"), require("./qbank_scn_b.json").rows.map(r => r.text)).forEach(t => { if (t && !seen[t]) { seen[t] = 1; texts.push(t); } });
const J = JSON.stringify;
let d0 = 0, d1 = 0, dB = 0, nres = 0, shared = [];
texts.forEach(t => {
  const pa = A.KP.parse(t, A.B.aliases, { choices: {} }), pb = B.KP.parse(t, B.B.aliases, { choices: {} });
  if (J(pa) !== J(pb)) { d0++; console.log("PARSE DIFF " + t); return; }
  if (pa.refusal || pa.clarify || !pa.items || !pa.items.length) return;
  nres++;
  const ra = A.KS.resolve(pa, A.B), rb = B.KS.resolve(pb, B.B); if (J(ra) !== J(rb)) { d0++; console.log("RESOLVE DIFF (no option) " + t); }
  const rb2 = B.KS.resolve(pb, B.B, { branches: true }), isShared = ra.clarify && ra.clarify.reason === "shared_game";
  if (isShared) { shared.push({ q: t, becomes: rb2.branches ? "branches x" + rb2.branches.length + " (" + rb2.branches.map(b => b.impossible ? "impossible:" + b.impossible.kind : "live").join(",") + ")" : (rb2.clarify ? "clarify " + rb2.clarify.reason : "other") }); return; }
  if (J(ra) !== J(rb2)) { d1++; console.log("RESOLVE DIFF (branches option) " + t); }
  if (ra.ok) { const oa = A.run(t), ob = B.run(t); if (oa.stage !== ob.stage || (oa.f && J(oa.f) !== J(ob.f))) { dB++; console.log("BUILD DIFF " + t); } }
});
console.log("questions " + texts.length + "; reach the resolver " + nres + "; parse+resolve (no option) differing " + d0 + "; resolve with branches option differing outside shared_game " + d1 + "; EX.build differing " + dB + "; shared_game questions " + shared.length);
shared.forEach(s => console.log("SHARED " + J(s.q) + " -> " + s.becomes));
if (out) fs.writeFileSync(out, J(shared, null, 1));
const bad = d0 + d1 + dB; console.log(bad ? "UNEXPECTED DIFFS" : "ALL IDENTICAL EXCEPT THE SHARED-GAME QUESTIONS"); process.exit(bad ? 1 : 0);
