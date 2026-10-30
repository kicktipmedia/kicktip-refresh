// scn_b Worker tests (offline: stub AI binding, mock D1 + Turnstile). Branched facts through the closed schema scnFacts and the prose check. usage: node tests/worker_scn_b.mjs BASE_TREE(A2b) NEW_TREE(B)
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const OW = await loadWorker(BASET), W = await loadWorker(NEWT), T = W._ask, OT = OW._ask; const H = require('./lib/scn_harness.js')(NEWT);
const HOST = 'https://preview.kicktip.pages.dev';
let n = 0, bad = 0; const chk = async (k, f) => { n++; try { await f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).split('\n').slice(0, 10).join(' | ').slice(0, 900)); } };
const S = (() => { const c = vm.createContext({ window: {}, console }); vm.runInContext(fs.readFileSync(path.join(NEWT, 'assets/ks/scnai.js'), 'utf8'), c); return c.KTScnAI || c.window.KTScnAI; })();
const mkSim = (names) => ({ table: { rows: names.map((t) => ({ name: t, team: H.B.teams.findIndex((z) => z.n === t), cells: t === 'Texas Tech' ? { ccg: { before: 0.2, after: 0.01, before_text: '20%', after_text: '1%' }, cfp12: { before: 0.1, after: 0.02, before_text: '10%', after_text: '2%' } } : { ccg: { before: 0.31, after: 0.97, before_text: '31%', after_text: '97%' }, cfp12: { before: 0.12, after: 0.5, before_text: '12%', after_text: '50%' } } })) } });
const facts = (q, sims) => { const p = H.KP.parse(q, H.B.aliases, { choices: {} }), r = H.KS.resolve(p, H.B, { branches: true }); const f = H.EX.buildBranched({ parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }); H.EX.attachSim(f, sims, H.B); return f; };
const f1 = facts('What if BYU, Utah and Texas Tech all end with just one loss?', [mkSim(['BYU', 'Utah', 'Texas Tech']), null]);
const C1 = S.compact(f1); assert.ok(C1, 'compact exists');
const f4 = facts('What if BYU, Utah and Arizona all end with 3 losses', [0, 1, 2, 3].map(() => mkSim(['BYU', 'Utah', 'Arizona']))), C4 = S.compact(f4);
const fm = facts('What if BYU and Utah each end with 3 losses', [mkSim(['BYU', 'Utah']), mkSim(['BYU', 'Utah'])]), CM = S.compact(fm);
const clone = (o) => JSON.parse(JSON.stringify(o)), mut = (f, o = C1) => { const c = clone(o); f(c); return c; };
await chk('schema: the compact branched facts of the exact one-loss question pass scnFacts (new Worker) and the base Worker refuses them (impossible list / label keys unknown)', async () => { assert.ok(T.scnFacts(clone(C1))); assert.equal(OT.scnFacts(clone(C1)), null); });
await chk('schema: ordinary (unbranched) compact facts pass in both Workers unchanged', async () => { const o = H.run('What if BYU and Texas Tech both end with just one loss'); const c = S.compact(o.f); assert.ok(c); assert.ok(T.scnFacts(clone(c))); assert.ok(OT.scnFacts(clone(c))); });
await chk('schema: a two-branch question with live chances on both branches passes', async () => { assert.ok(CM, 'compact'); assert.ok(JSON.stringify(CM).length <= 3300); assert.ok(T.scnFacts(clone(CM))); });
await chk('by design: the four-branch question is too big for the write-up input (compact is null, so no write-up is offered and the card stands alone)', async () => { assert.equal(C4, null); });
const BADS = { 'unknown key on a branch': mut((c) => { c.branches[0].note = 'x'; }), 'unknown top-level key': mut((c) => { c.extra = 1; }), 'label with a banned word (bet)': mut((c) => { c.branches[0].label = 'If BYU wins the bet'; }), 'label non-string': mut((c) => { c.branches[0].label = 5; }), 'label too long': mut((c) => { c.branches[0].label = 'If '.padEnd(200, 'x'); }), 'impossible entry with an unknown key': mut((c) => { c.impossible[0].why = 'x'; }), 'nine branches': mut((c) => { const b = c.branches[0]; c.branches = [0, 1, 2, 3, 4, 5, 6, 7, 8].map(() => clone(b)); }), 'branch sim with a made-up key': mut((c) => { c.branches[0].sim[0].odds = '5%'; }), 'impossible not an array': mut((c) => { c.impossible = 'none'; }) };
for (const [k, v] of Object.entries(BADS)) await chk('schema rejects: ' + k, async () => { assert.equal(T.scnFacts(v), null); });
await chk('prose: a write-up that uses the branch labels and only given numbers passes the Worker check', async () => {
  const prose = 'If BYU beats Utah, BYU and Utah both finish 8-1 in this scenario and reach the Big 12 conference championship game, on our reading of the rules. If Utah beats BYU, BYU would end with more losses than the scenario allows, so that branch is not possible. The result depends on games the scenario does not set.';
  assert.ok(T.scnProse(prose, T.scnFacts(clone(C1))), 'prose accepted');
});
await chk('prose: the browser validator accepts the same text for the branched facts and rejects an invented team and an invented number', async () => {
  const voc = H.EX.vocab(f1), known = H.B.teams.map((t) => t.n).concat(H.B.teams.map((t) => t.f)).filter(Boolean); const okp = 'If BYU beats Utah, BYU and Utah both finish 8-1 and reach the Big 12 conference championship game, on our reading of the rules. If Utah beats BYU, that branch is not possible. KickTip\'s numbers show Utah at 50% (model) to make the 12-team playoff field.';
  const v1 = S.validate(okp, f1, { known: known, vocab: voc }); assert.ok(v1.ok, JSON.stringify(v1));
  assert.ok(!S.validate(okp.replace('Utah beats BYU', 'Arizona beats BYU'), f1, { known: known, vocab: voc }).ok); assert.ok(!S.validate(okp.replace('50%', '63%'), f1, { known: known, vocab: voc }).ok);
});
await chk('end to end: POST mode scn with branched facts and a stub AI returns the write-up (source scn); a bad facts object is 400 bad_facts with no AI call', async () => {
  const E = makeEnv(W, { AI_SCN: 'on' }); installFetch(E.st); E.env.__st = E.st; const prose = 'If BYU beats Utah, BYU and Utah both finish 8-1 and reach the Big 12 conference championship game, on our reading of the rules. If Utah beats BYU, that branch is not possible. The result depends on games the scenario does not set.';
  E.env.AI = { run: async (m, input) => { E.st.ai_calls.push([m, 1]); return { response: JSON.stringify({ v: 1, prose }) }; } };
  const post = (facts) => new Request(HOST + '/api/ask', { method: 'POST', headers: { 'CF-Connecting-IP': '203.0.113.9', Origin: HOST, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin' }, body: JSON.stringify({ mode: 'scn', facts, cf_turnstile: 'good' }) });
  const r = await W.fetch(post(clone(C1)), E.env), j = await r.json(); assert.equal(r.status, 200); assert.equal(j.source, 'scn', JSON.stringify(j).slice(0, 200)); assert.equal(E.st.ai_calls.length, 1);
  const r2 = await W.fetch(post(BADS['nine branches']), E.env); assert.ok(r2.status === 400 || r2.status === 413, 'status ' + r2.status); assert.equal(E.st.ai_calls.length, 1);
});
await chk('prompt: SCN_SYS still holds every A2 rule and adds the branch-label sentence; ASCII; MODEL constant is 70b (scn_b4)', async () => { const s = T.SCN_SYS, o = OT.SCN_SYS; assert.ok(s.length > o.length); assert.ok(/label/i.test(s)); assert.ok(/^[\x20-\x7e\n]*$/.test(s)); assert.equal(OT.SCN.MODEL, '@cf/meta/llama-3.3-70b-instruct-fp8-fast'); assert.equal(T.SCN.MODEL, '@cf/meta/llama-3.3-70b-instruct-fp8-fast'); });   /* scn_b2: the model constant is now 8b (the base Worker, A2b, is still 70b) */
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
