// final3 unit tests: QA final2 B1 (percent spellings) + B2 (doubled "(model)", SYS rule 4). usage: node tests/final3_unit.mjs BASE_TREE(final2) NEW_TREE(final3)
import path from 'node:path'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const W = await loadWorker(NEWT), OW = await loadWorker(BASET), T = W._ask, OT = OW._ask;
const S = require(path.join(NEWT, 'assets/ks/scnai.js')), EX = require(path.join(NEWT, 'assets/ks/explain.js'));
const FX = require('./eval_facts.json').items, B = require(path.join(NEWT, 'data/sim-bundle.json')); B.teams.forEach((t) => { t.f = t.n; if (t.s) t.n = t.s; });
const known = []; B.teams.forEach((t) => { known.push(t.n); if (t.f !== t.n) known.push(t.f); });
const X = FX.find((x) => x.q === 'What if BYU and Texas Tech both end with just one loss?'), F = X.facts, C = X.compact;
const V = (p) => S.validate(p, F, { known, vocab: EX.vocab(F) });
let n = 0, bad = 0; const chk = (k, f) => { n++; try { f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).slice(0, 600)); } };
const HEAD = "In this scenario, BYU and Texas Tech both finish 8-1 in Big 12 play. ", TAIL = " The result depends on games the scenario does not set.";
const P = (mid) => HEAD + "KickTip's numbers show " + mid + TAIL;
const NODBL = (r) => !/\(model\)\s*\(model\)/.test(r) && !/\(model\)[^.]*\(model\)[^.]*\(model\)/.test(r.replace(/\d% \(model\)/g, '')) && !/\d% \(model\) (?:playoff )?chance \(model\)/.test(r);
const BARE_OK = (r) => !/\d%(?! \(model\))/.test(r);
const sp = P("BYU's playoff chance increases to 45.6 %."), pc = P("BYU's playoff chance increases to 45.6 percent."), PC = P("BYU's playoff chance increases to 45.6 Percent."), pi = P("BYU's playoff chance increases to 46 percent.");
const glued = P("BYU's playoff chance increases to 45.6%(model)."), glued2 = P("BYU's playoff chance increases to 45.6%(model)(model).");
const trail = P("BYU has a 45.6% playoff chance (model)."), trail2 = P("BYU has a 45.6% chance (model).");
const ft = P("BYU's playoff chance moves from 12.3% to 45.6% (model).");
const r4 = P("BYU has a playoff chance of 45.6% (model).");
chk('final2 Worker let "45.6 %" through (reproduces B1)', () => assert.ok(OT.scnProse(sp, C)));
chk('final2 Worker doubled "45.6%(model)" (reproduces B2)', () => assert.ok(/\(model\)\(model\)/.test(OT.scnProse(glued, C) || '')));
// B1 Worker
for (const [k, p] of [['45.6 %', sp], ['45.6 percent', pc], ['45.6 Percent', PC], ['46 percent', pi]]) chk(`scnProse rejects "${k}"`, () => assert.equal(T.scnProse(p, C), null));
chk('scnProse still accepts "percentage" wording-free text and "12-team"', () => assert.ok(T.scnProse(P("BYU's playoff chance moves from 12.3% (model) to 45.6% (model)."), C)));
// B1 validator
for (const [k, p] of [['45.6 %', sp], ['45.6 percent', pc], ['45.6 Percent', PC], ['46 percent', pi]]) chk(`validator rejects "${k}": percent_without_model`, () => assert.equal(V(p).why, 'percent_without_model'));
// B2 Worker
chk('scnProse "45.6%(model)" -> exactly "45.6% (model)"', () => { const r = T.scnProse(glued, C); assert.ok(r && r.includes('45.6% (model).') && NODBL(r) && BARE_OK(r), r); });
chk('scnProse "45.6%(model)(model)" -> one label', () => { const r = T.scnProse(glued2, C); assert.ok(r && r.includes('45.6% (model).') && NODBL(r), r); });
chk('scnProse "45.6% playoff chance (model)" -> "45.6% (model) playoff chance"', () => { const r = T.scnProse(trail, C); assert.ok(r && r.includes('45.6% (model) playoff chance.') && NODBL(r) && BARE_OK(r), r); });
chk('scnProse "45.6% chance (model)" -> "45.6% (model) chance"', () => { const r = T.scnProse(trail2, C); assert.ok(r && r.includes('45.6% (model) chance.') && NODBL(r), r); });
chk('scnProse "from 12.3% to 45.6% (model)" tags 12.3% too, once each', () => { const r = T.scnProse(ft, C); assert.ok(r && r.includes('from 12.3% (model) to 45.6% (model).') && NODBL(r) && BARE_OK(r), r); });
chk('scnProse rule-4 form "playoff chance of 45.6% (model)" unchanged', () => assert.equal(T.scnProse(r4, C), r4));
chk('scnProse "playoff chance (model) moves from 12.3% (model) to 45.6% (model)" unchanged', () => { const p = P("BYU's playoff chance (model) moves from 12.3% (model) to 45.6% (model)."); assert.equal(T.scnProse(p, C), p); });
chk('scnProse is idempotent on its own output (no doubling on a second pass)', () => { for (const p of [glued, glued2, trail, trail2, ft, r4, P("BYU's playoff chance increases to 45.6%.")]) { const a = T.scnProse(p, C); assert.ok(a, p); assert.equal(T.scnProse(a, C), a); } });
chk('no doubling anywhere: every eval fixture x every sample shape', () => { let k = 0; for (const x of FX) { if (!x.compact) continue; for (const p of [glued, glued2, trail, trail2, ft, r4]) { const r = T.scnProse(p, x.compact); if (r) { k++; assert.ok(NODBL(r) && BARE_OK(r), r); } } } assert.ok(k > 0); });
// B2 validator
chk('validator accepts the Worker output for every B2 case', () => { for (const p of [glued, glued2, trail, trail2, ft, r4]) { const r = T.scnProse(p, C); const v = V(r); assert.ok(v.ok, r + ' ' + JSON.stringify(v)); } });
chk('validator rejects raw "45.6%(model)" (bare by its rule)', () => assert.equal(V(glued).ok, false));
chk('validator rejects "45.6% (model)(model)": model_label_doubled', () => assert.equal(V(P("BYU's playoff chance increases to 45.6% (model)(model).")).why, 'model_label_doubled'));
chk('validator rejects "45.6% (model) playoff chance (model)": model_label_doubled', () => assert.equal(V(P("BYU has a 45.6% (model) playoff chance (model).")).why, 'model_label_doubled'));
chk('validator rejects raw "45.6% playoff chance (model)" (bare)', () => assert.equal(V(trail).ok, false));
chk('validator rejects raw "from 12.3% to 45.6% (model)": percent_without_model', () => assert.equal(V(ft).why, 'percent_without_model'));
chk('validator accepts "playoff chance of 45.6% (model)"', () => assert.ok(V(r4).ok, JSON.stringify(V(r4))));
chk('validator exports MODEL2_RE', () => assert.ok(S.MODEL2_RE instanceof RegExp || typeof S.MODEL2_RE === 'object'));
// prompt
chk('SCN_SYS rule 4 uses "playoff chance of N% (model)"; no bare "playoff chance (model)" form left', () => { assert.ok(T.SCN_SYS.includes('"playoff chance of N% (model)"')); assert.ok(!T.SCN_SYS.includes('"playoff chance (model)"')); assert.ok(T.SCN_SYS.includes('Write every percent as N% (model).')); assert.ok(/^[\x20-\x7e\n]*$/.test(T.SCN_SYS)); });
const V1 = require('./lib/vis1_expect.cjs');
chk('SCN_SYS differs from final2 only on the rule 4 line (after mapping back the exact vis1 rule 3/4 tweak)', () => { const a = OT.SCN_SYS.split('\n'), b = V1.unSys(T.SCN_SYS).split('\n'); assert.equal(a.length, b.length); const d = a.map((l, i) => l !== b[i] ? i : -1).filter((i) => i >= 0); assert.equal(d.length, 1); assert.ok(/^4\. /.test(b[d[0]])); });
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
