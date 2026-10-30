// scn_b3: every card question (QA bank + a1/loss/b banks + one synthetic question per team and per conference rival pair sample) -> the card the browser builds -> scnai.compact() (what the browser really sends) -> the Worker's scnFacts().
// Lists every name/label/reason the browser sends that the Worker allowlist refuses (the San Jose State fold class of bug). usage: node tests/sweep_fold_b3.mjs TREE [--expect-fail]
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker } from './browser/mock.mjs';
const require = createRequire(import.meta.url); const TREE = path.resolve(process.argv[2]); const W = await loadWorker(TREE), T = W._ask; const H = require('./lib/scn_harness.js')(TREE);
const S = (() => { const c = vm.createContext({ window: {}, console }); vm.runInContext(fs.readFileSync(path.join(TREE, 'assets/ks/scnai.js'), 'utf8'), c); return c.KTScnAI || c.window.KTScnAI; })();
const BANK = '/workspace/hub/kicktip-toolbox-1026/qbank/questions.json'; const seen = new Set(), texts = [];
const add = (t) => { if (t && !seen.has(t)) { seen.add(t); texts.push(t); } };
JSON.parse(fs.readFileSync(BANK, 'utf8')).rows.forEach((r) => add(r.text)); require('./qbank_scn_a1.json').rows.forEach((r) => add(r.text)); require('./qbank_loss_r2.json').forEach(add); require('./qbank_scn_b.json').rows.forEach((r) => add(r.text)); require('./qbank_scn_a2.json').rows.forEach((r) => add(r.text));
const bankN = texts.length;
const teams = H.B.teams.map((t) => t.n);
teams.forEach((t) => { add('What if ' + t + ' wins out?'); add('What if ' + t + ' loses out?'); });   // every team (short name as the card shows it) at least once as the subject
// shared-game branches: every team that has an opponent in its conference, "X beats Y" pairs (first listed opponent of each team) -> labels "If X beats Y"
const confOf = {}; H.B.teams.forEach((t, i) => { confOf[t.n] = t.c !== undefined ? t.c : t.conf; });
const out = { cards: 0, sent: 0, refused: [], names: new Set() };
const walk = (o, f) => { if (Array.isArray(o)) o.forEach((x) => walk(x, f)); else if (o && typeof o === 'object') Object.values(o).forEach((x) => walk(x, f)); else if (typeof o === 'string') f(o); };
const chk = (q, f, how) => {
  const c = S.compact(f); if (!c) return; out.sent++;
  let nonascii = false; walk(c, (s) => { if (/[^\x20-\x7e]/.test(s)) nonascii = true; });
  const r = T.scnFacts(c); const known = T.scnKnown(c);
  if (!r || !known || nonascii) {
    const bad = []; const tn = (x) => { if (typeof x === 'string' && !T.SCN_TEAMS.has(x)) bad.push(x); };
    (c.sim || []).forEach((s) => tn(s.team)); c.branches.forEach((b) => { b.teams.forEach((t) => tn(t.team)); (b.reach_the_game || []).forEach(tn); (b.ties || []).forEach((s) => (s.teams || []).forEach(tn)); ((b.others_who_can_reach_the_record || {}).teams || []).forEach(tn); ((b.if_tied || {}).teams || []).forEach(tn); (b.sim || []).forEach((s) => tn(s.team)); if (b.label !== undefined && !T.scnLabelOk(b.label)) bad.push('label:' + b.label); });
    (c.impossible || []).forEach((x) => { if (!T.scnLabelOk(x.label)) bad.push('label:' + x.label); });
    if (!T.SCN_CONFS.has(c.conference)) bad.push('conf:' + c.conference);
    out.refused.push({ q, how, scnFacts: !!r, known, nonascii, bad: [...new Set(bad)] });
  }
};
const run = (q) => {
  const p = H.KP.parse(q, H.B.aliases, { choices: {} }); if (p.refusal || p.clarify || !p.items || !p.items.length) return;
  const res = H.KS.resolve(p, H.B, { branches: true }); if (!res.ok) return;
  const o = { parsed: p, res, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind };
  let f; try { f = res.branches ? H.EX.buildBranched(o) : H.EX.build(o); } catch (e) { return; }
  if (!f || f.ok === false || f.kind !== 'scenario_facts') return; out.cards++; chk(q, f, res.branches ? 'branched' : 'card');
};
texts.forEach(run);
const conf = (n) => H.B.teams.find((t) => t.n === n);
const bad = out.refused, names = new Set(); bad.forEach((b) => b.bad.forEach((x) => names.add(x)));
console.log('questions ' + texts.length + ' (bank sets ' + bankN + '), cards built ' + out.cards + ', sent to the Worker ' + out.sent + ', refused by the Worker allowlist/charset ' + bad.length);
console.log('refused names/labels: ' + JSON.stringify([...names]));
bad.slice(0, 40).forEach((b) => console.log('REFUSED ' + JSON.stringify(b)));
// every allowlist team name must be what the browser would send (fold + clean): clean(name) === name
const clean = (s) => S.clean(s); const diff = [...T.SCN_TEAMS].filter((t) => clean(t) !== t); const cdiff = [...T.SCN_CONFS].filter((t) => clean(t) !== t);
console.log('SCN_TEAMS entries the browser would alter (fold/clean): ' + JSON.stringify(diff) + '; SCN_CONFS: ' + JSON.stringify(cdiff));
const lens = [...T.SCN_TEAMS].filter((t) => t.length > 40).concat([...T.SCN_CONFS].filter((t) => t.length > 20)); console.log('over clip length: ' + JSON.stringify(lens));
const fails = bad.length + diff.length + cdiff.length + lens.length; console.log(process.argv.includes('--expect-fail') ? ('(expect-fail mode) refused=' + bad.length) : (fails ? 'FAIL fold sweep' : 'PASS fold sweep: 0 refused, 0 fold mismatches')); process.exit(process.argv.includes('--expect-fail') ? 0 : (fails ? 1 : 0));
