// final3 unit tests, askmodel rev2 contract: percents are plain N%; every '(model...)' tag (any case, spacing, suffix, doubled, glued) is stripped by BOTH the Worker (scnProse/scnStripModel) and the validator; '45.6 %' / 'N percent' stay rejected. usage: node tests/final3_unit.mjs NEW_TREE
import path from 'node:path'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker } from './browser/mock.mjs';
const NEWT = path.resolve(process.argv[2]); const require = createRequire(import.meta.url);
const W = await loadWorker(NEWT), T = W._ask;
const S = require(path.join(NEWT, 'assets/ks/scnai.js')), EX = require(path.join(NEWT, 'assets/ks/explain.js'));
const FX = require('./eval_facts.json').items, B = require(path.join(NEWT, 'data/sim-bundle.json')); B.teams.forEach((t) => { t.f = t.n; if (t.s) t.n = t.s; });
const known = []; B.teams.forEach((t) => { known.push(t.n); if (t.f !== t.n) known.push(t.f); });
const X = FX.find((x) => x.q === 'What if BYU and Texas Tech both end with just one loss?'), F = X.facts, C = X.compact;
const V = (p) => S.validate(p, F, { known, vocab: EX.vocab(F) });
let n = 0, bad = 0; const chk = (k, f) => { n++; try { f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).slice(0, 600)); } };
const HEAD = "In this scenario, BYU and Texas Tech both finish 8-1 in Big 12 play. ", TAIL = " The result depends on games the scenario does not set.";
const P = (mid) => HEAD + "KickTip's numbers show " + mid + TAIL;
const plain = P("BYU's playoff chance moves from 12.3% to 45.6%.");
const TAGGED = [
  ['(model)', P("BYU's playoff chance moves from 12.3% (model) to 45.6% (model).")],
  ['(Model)', P("BYU's playoff chance moves from 12.3% (Model) to 45.6% (Model).")],
  ['(MODEL)', P("BYU's playoff chance moves from 12.3% (MODEL) to 45.6% (MODEL).")],
  ['( model )', P("BYU's playoff chance moves from 12.3% ( model ) to 45.6% ( model ).")],
  ['(model est.)', P("BYU's playoff chance moves from 12.3% (model est.) to 45.6% (model est.).")],
  ['doubled (model) (model)', P("BYU's playoff chance moves from 12.3% (model) (model) to 45.6% (model)(model).")],
  ['glued 45.6%(model)', P("BYU's playoff chance moves from 12.3%(model) to 45.6%(Model).")],
];
const NOMODEL = (r) => !/model/i.test(r);
// Worker cleanup function itself
chk('Worker exports scnStripModel', () => assert.equal(typeof T.scnStripModel, 'function'));
for (const [s, want] of [['45.6% (model)', '45.6%'], ['45.6% (Model)', '45.6%'], ['45.6% (MODEL)', '45.6%'], ['45.6% ( model )', '45.6%'], ['45.6% (model est.)', '45.6%'], ['45.6% (model)(model)', '45.6%'], ['45.6% (model) (Model)', '45.6%'], ['45.6%(model)', '45.6%'], ['in the KickTip model', 'in the KickTip model'], ['a (modeling) note', 'a (modeling) note']])
  chk(`scnStripModel("${s}") -> "${want}"`, () => assert.equal(T.scnStripModel(s), want));
for (const s of ['45.6% (model', '45.6% ( MODEL est']) chk(`scnStripModel rejects leftover "${s}"`, () => assert.equal(T.scnStripModel(s), null));
chk('scnStripModel(non-string) -> null', () => assert.equal(T.scnStripModel(42), null));
// Worker scnProse
chk('scnProse plain N% passes unchanged', () => assert.equal(T.scnProse(plain, C), plain));
for (const [k, p] of TAGGED) chk(`scnProse strips ${k} -> plain N%`, () => assert.equal(T.scnProse(p, C), plain));
for (const [k, mid] of [['45.6 %', "BYU's playoff chance increases to 45.6 %."], ['45.6 percent', "BYU's playoff chance increases to 45.6 percent."], ['45.6 Percent', "BYU's playoff chance increases to 45.6 Percent."], ['46 percent', "BYU's playoff chance increases to 46 percent."]]) chk(`scnProse rejects "${k}"`, () => assert.equal(T.scnProse(P(mid), C), null));
chk('scnProse rejects an unclosed "(model"', () => assert.equal(T.scnProse(P("BYU's playoff chance increases to 45.6% (model."), C), null));
chk('scnProse keeps legit "in the KickTip model"', () => { const p = P("BYU's playoff chance in the KickTip model moves from 12.3% to 45.6%."); assert.equal(T.scnProse(p, C), p); });
chk('scnProse idempotent', () => { for (const [, p] of TAGGED) { const a = T.scnProse(p, C); assert.equal(T.scnProse(a, C), a); } });
chk('every eval fixture x every tagged shape: output never carries "model"', () => { let k = 0; for (const x of FX) { if (!x.compact) continue; for (const [, p] of TAGGED) { const r = T.scnProse(p, x.compact); if (r) { k++; assert.ok(NOMODEL(r), r); } } } assert.ok(k > 0); });
// validator (browser)
chk('validator accepts plain N% unchanged', () => { const v = V(plain); assert.ok(v.ok && v.prose === plain, JSON.stringify(v)); });
for (const [k, p] of TAGGED) chk(`validator strips ${k} -> plain N%`, () => { const v = V(p); assert.ok(v.ok && v.prose === plain, JSON.stringify(v)); });
for (const [k, mid] of [['45.6 %', "BYU's playoff chance increases to 45.6 %."], ['45.6 percent', "BYU's playoff chance increases to 45.6 percent."], ['46 percent', "BYU's playoff chance increases to 46 percent."]]) chk(`validator rejects "${k}": percent_without_model`, () => assert.equal(V(P(mid)).why, 'percent_without_model'));
chk('validator rejects an unclosed "(model": model_label', () => assert.equal(V(P("BYU's playoff chance increases to 45.6% (model.")).why, 'model_label'));
chk('validator accepts the Worker output for every tagged case', () => { for (const [, p] of TAGGED) { const v = V(T.scnProse(p, C)); assert.ok(v.ok, JSON.stringify(v)); } });
// prompt: plain N%
chk('SCN_SYS asks for plain N%, no "(model)" instruction left', () => { assert.ok(!/\(model\)/i.test(T.SCN_SYS), 'SCN_SYS still mentions (model)'); assert.ok(/^[\x20-\x7e\n]*$/.test(T.SCN_SYS)); });
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
