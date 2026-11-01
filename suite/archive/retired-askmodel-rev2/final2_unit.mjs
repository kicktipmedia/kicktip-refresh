// final2 unit tests: percent '(model)' rule (Worker scnProse rewrite + browser validator reject + prompt) and 'will be out' softening.
// usage: node tests/final2_unit.mjs BASE_TREE(final1) NEW_TREE(final2)
import fs from 'node:fs'; import path from 'node:path'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const W = await loadWorker(NEWT), OW = await loadWorker(BASET), T = W._ask, OT = OW._ask;
const S = require(path.join(NEWT, 'assets/ks/scnai.js')), EX = require(path.join(NEWT, 'assets/ks/explain.js'));
const FX = require('./eval_facts.json').items, B = JSON.parse(fs.readFileSync(path.join(NEWT, 'data/sim-bundle.json'))); B.teams.forEach((t) => { t.f = t.n; if (t.s) t.n = t.s; });
const known = []; B.teams.forEach((t) => { known.push(t.n); if (t.f !== t.n) known.push(t.f); });
const X = FX.find((x) => x.q === 'What if BYU and Texas Tech both end with just one loss?'), F = X.facts, C = X.compact;
const V = (p) => S.validate(p, F, { known, vocab: EX.vocab(F) });
let n = 0, bad = 0; const chk = (k, f) => { n++; try { f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).slice(0, 600)); } };
const HEAD = "In this scenario, BYU and Texas Tech both finish 8-1 in Big 12 play. ";
const BARE = HEAD + "KickTip's numbers show BYU's playoff chance increases to 45.6%. The result depends on games the scenario does not set.";
const TAGGED = HEAD + "KickTip's numbers show BYU's playoff chance moves from 12.3% (model) to 45.6% (model). The result depends on games the scenario does not set.";
const MIXED = HEAD + "KickTip's numbers show BYU's playoff chance moves from 12.3% (model) to 45.6%. The result depends on games the scenario does not set.";
const WILLBE = HEAD + "In this scenario, Utah will be out of the conference championship game, on our reading of the rules. The result depends on games the scenario does not set.";
const ISOUT = HEAD + "Utah is out of the conference championship game on our reading of the rules. The result depends on games the scenario does not set.";
// prompt
chk('SCN_SYS has the line "Write every percent as N% (model)."', () => assert.ok(T.SCN_SYS.includes('Write every percent as N% (model).')));
chk('SCN_SYS tells the model to say "is out on our reading of the rules" instead of "will be out"', () => assert.ok(/is out on our reading of the rules/.test(T.SCN_SYS) && /will be out/.test(T.SCN_SYS)));
chk('SCN_SYS = final1 SCN_SYS + exactly 2 added lines; ASCII', () => { assert.ok(/^[\x20-\x7e\n]*$/.test(T.SCN_SYS)); const a = OT.SCN_SYS.split('\n'), b = T.SCN_SYS.split('\n'); assert.equal(b.length, a.length + 2); assert.deepEqual(b.filter((l) => !/^[78]\. /.test(l)), a); });
chk('final1 Worker accepted a bare percent (reproduces the QA gap)', () => assert.equal(OT.scnProse(BARE, C), BARE));
// Worker scnProse
chk('scnProse rewrites a bare 45.6% to "45.6% (model)"', () => { const r = T.scnProse(BARE, C); assert.ok(r && r.includes('45.6% (model)') && !/\d%(?! \(model\))/.test(r), r); });
chk('scnProse leaves already-tagged percents unchanged (no double tag)', () => assert.equal(T.scnProse(TAGGED, C), TAGGED));
chk('scnProse fixes a mixed tagged/bare text', () => { const r = T.scnProse(MIXED, C); assert.ok(r && !/\(model\) \(model\)/.test(r) && !/\d%(?! \(model\))/.test(r), r); });
chk('scnProse output never has a percent without " (model)" across all eval fixtures with the f01/f04 sample shape', () => { for (const x of FX) { if (!x.compact) continue; const r = T.scnProse(BARE, x.compact); if (r) assert.ok(!/\d%(?! \(model\))/.test(r), r); } });
chk('scnProse rejects "will be out"', () => assert.equal(T.scnProse(WILLBE, C), null));
chk('scnProse rejects "will miss"', () => assert.equal(T.scnProse(HEAD + "In this scenario, Utah will miss the conference championship game. That depends on games the scenario does not set.", C), null));
chk('scnProse accepts "is out on our reading of the rules"', () => assert.equal(T.scnProse(ISOUT, C), ISOUT));
chk('scnProse keeps the "will win" rejection', () => assert.equal(T.scnProse(HEAD + "In this scenario, BYU will win the conference championship game. That depends on games the scenario does not set.", C), null));
chk('scnProse still lets "in this scenario ... will finish" through', () => { const p = "In this scenario, BYU will finish 8-1 in Big 12 play. Texas Tech also finishes 8-1. The result depends on games the scenario does not set."; assert.equal(T.scnProse(p, C), p); });
// browser validator
chk('validator rejects a bare percent: percent_without_model', () => assert.equal(V(BARE).why, 'percent_without_model'));
chk('validator rejects mixed tagged/bare: percent_without_model', () => assert.equal(V(MIXED).why, 'percent_without_model'));
chk('validator accepts tagged percents', () => assert.ok(V(TAGGED).ok, JSON.stringify(V(TAGGED))));
chk('validator accepts the Worker-rewritten bare sample', () => { const r = T.scnProse(BARE, C); assert.ok(V(r).ok, JSON.stringify(V(r))); });
chk('validator rejects "will be out": will_be_out', () => assert.equal(V(WILLBE).why, 'will_be_out'));
chk('validator accepts "is out on our reading of the rules"', () => assert.ok(V(ISOUT).ok, JSON.stringify(V(ISOUT))));
chk('validator still rejects "will win" as banned_word', () => assert.equal(V(HEAD + "In this scenario, BYU will win the conference championship game. That depends on games the scenario does not set.").why, 'banned_word'));
chk('validator exports WILLBE_RE', () => assert.ok(S.WILLBE_RE instanceof RegExp || typeof S.WILLBE_RE === 'object'));
chk('Worker diff vs final1 is exactly the final2 edits (SCN_WILLBE const, prompt lines 7-8, scnProse will-be check + percent rewrite)', () => {
  const a = fs.readFileSync(path.join(BASET, '_worker.js'), 'utf8'), b = fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8');
  const u = b.replace(/^const SCN_WILLBE = .*\n/m, '').replace(/^  "7\. Write every percent.*\n/m, '').replace(/^  "8\. Never say a team will be out.*\n/m, '').replace(/^  if \(SCN_WILLBE\.test\(s\)\) return null;.*\n/m, '').replace(/^  const out = s\.replace.*\n  return \/.*\n/m, "  return s.replace(/\\u2019/g, \"'\");\n");
  assert.equal(u, a); assert.equal(b.split('\n').length - a.split('\n').length, 5); });
chk('scnai.js diff vs final1 is only the two new checks, WILLBE_RE and its export', () => {
  const a = fs.readFileSync(path.join(BASET, 'assets/ks/scnai.js'), 'utf8'), b = fs.readFileSync(path.join(NEWT, 'assets/ks/scnai.js'), 'utf8');
  const u = b.replace(/^  var WILLBE_RE = .*\n/m, '').replace(/^      if \(\/\\d%.*final2 \*\/\n/m, '').replace(/^      if \(WILLBE_RE\.test\(s\)\).*\n/m, '').replace('WILLBE_RE: WILLBE_RE, ', ''); assert.equal(u, a); });
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
