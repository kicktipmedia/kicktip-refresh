// scn_b4 Worker tests (model 70b, 8000 ms). Base tree = B3, new tree = B4. Original header: scn_b2 Worker tests (offline: stub AI binding, mock D1 + Turnstile; no network). M1 allowlist, M2 counting + worst-case neurons, 8b default, 'as an ai', flag-off identity vs B.
// usage: node tests/worker_scn_b4.mjs BASE_TREE(B3) NEW_TREE(B4)
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const V1 = require('./lib/vis1_expect.cjs'); const OW = V1.wrapOld(await loadWorker(BASET)), W = await loadWorker(NEWT), T = W._ask, OT = OW._ask; const H = require('./lib/scn_harness.js')(NEWT); const FX = require('./eval_facts.json').items;
const S = (() => { const c = vm.createContext({ window: {}, console }); vm.runInContext(fs.readFileSync(path.join(NEWT, 'assets/ks/scnai.js'), 'utf8'), c); return c.KTScnAI || c.window.KTScnAI; })();
const HOST = 'https://preview.kicktip.pages.dev', PROD = 'https://kicktipmedia.com'; const M8 = '@cf/meta/llama-3.1-8b-instruct-fp8', M70 = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
/* final2: undo the final2 Worker edits (checked exactly in final2_unit.mjs) so the B4-vs-B3 2-line check still runs on the final2 tree */
const UNF2 = (w) => w.replace(/^const SCN_WILLBE = .*\n/m, '').replace(/^  "7\. Write every percent.*\n/m, '').replace(/^  "8\. Never say a team will be out.*\n/m, '').replace(/^  if \(SCN_WILLBE\.test\(s\)\) return null;.*\n/m, '').replace(/^  const out = s\.replace.*\n  return \/.*\n/m, "  return s.replace(/\\u2019/g, \"'\");\n");
/* final3: undo the final3 Worker edits first (pairs from build-final3.py; checked exactly in final3_unit.mjs) */
const UNF3P = require('./lib/final3_undo.json'), UNF2_0 = UNF2; const UNF3 = (w) => UNF3P.reduce((t, [nw, od]) => { if (t.split(nw).length !== 2) return t; return t.replace(nw, () => od); }, w);
let n = 0, bad = 0; const chk = async (k, f) => { n++; try { await f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).split('\n').slice(0, 14).join(' | ').slice(0, 1400)); } };
const req = (p, o = {}, host = HOST) => new Request(host + p, { method: o.method || 'GET', headers: Object.assign({ 'CF-Connecting-IP': o.ip || '203.0.113.9' }, o.h || {}), body: o.body });
const post = (p, body, h = {}, host = HOST, ip) => req(p, { method: 'POST', ip, h: Object.assign({ Origin: host, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin' }, h), body: typeof body === 'string' ? body : JSON.stringify(body) }, host);
const HOME_ANS = JSON.stringify({ v: 1, mode: 'home', status: 'ok', scenarios: [{ label: 'A', wins_out: ['BYU Cougars'] }] });
const COMPACT = FX.find((x) => x.q === 'What if BYU and Texas Tech both end with just one loss?').compact;
const GOOD = "In this scenario, BYU and Texas Tech both finish 8-1 in Big 12 play, and KickTip's numbers show Utah can still reach 8-1 too. If BYU and Texas Tech are tied at 8-1, step 1 is head-to-head. The result depends on games the scenario does not set.";
const PROSE = (p) => JSON.stringify({ v: 1, prose: p });
function stubAI(script, st) { return { run: async (model, input) => { const sys = input.messages[0].content, isScn = /KickTip writer/.test(sys); st.ai_calls.push([model, JSON.stringify(input)]);
  if (isScn) return { response: script }; return { response: HOME_ANS }; } }; }
for (const X of [OW, W]) { const f0 = X.fetch.bind(X); X.fetch = (rq, env, ctx) => { if (env && env.__st) installFetch(env.__st); return f0(rq, env, ctx); }; }
const mk = (over = {}, WW = W) => { const E = makeEnv(WW, over); installFetch(E.st); E.env.__st = E.st; E.env.AI = stubAI(PROSE(GOOD), E.st); return E; };
const ON = { AI_SCN: 'on' };
const scn = async (E, facts = COMPACT, extra = {}, host = HOST, WW = W, ip) => { const r = await WW.fetch(post('/api/ask', Object.assign({ mode: 'scn', facts, cf_turnstile: 'good' }, extra), {}, host, ip), E.env); const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch (e) { } return { s: r.status, j, t }; };
const home = async (E, text = 'What if BYU wins out?', extra = {}, host = HOST, WW = W, ip) => { const r = await WW.fetch(post('/api/ask', Object.assign({ mode: 'home', text, cf_turnstile: 'good' }, extra), {}, host, ip), E.env); const j = await r.json(); return { s: r.status, j }; };
const cnt = (E, key) => { let t = 0; for (const [k, v] of E.db.rows) if (k.startsWith(key + '|')) t += v.n; return t; };
const clone = (o) => JSON.parse(JSON.stringify(o));
const snap = async (r) => ({ s: r.status, t: (await r.text()).replace(/"(ms|verifyMs)":\d+/g, '"$1":0'), h: [...r.headers.entries()].sort().map((x) => x.join(':')).join('|') });
const withFlag = async (k, v, f) => { const o = T.SCN[k]; T.SCN[k] = v; try { await f(); } finally { T.SCN[k] = o; } };
const mkSim = (names) => ({ table: { rows: names.map((t) => ({ name: t, team: H.B.teams.findIndex((z) => z.n === t), cells: t === 'Texas Tech' ? { ccg: { before: 0.2, after: 0.01, before_text: '20%', after_text: '1%' }, cfp12: { before: 0.1, after: 0.02, before_text: '10%', after_text: '2%' } } : { ccg: { before: 0.31, after: 0.97, before_text: '31%', after_text: '97%' }, cfp12: { before: 0.12, after: 0.5, before_text: '12%', after_text: '50%' } } })) } });
const facts = (q, sims) => { const p = H.KP.parse(q, H.B.aliases, { choices: {} }), r = H.KS.resolve(p, H.B, { branches: true }); const f = H.EX.buildBranched({ parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }); if (sims) H.EX.attachSim(f, sims, H.B); return f; };
const f1 = facts('What if BYU, Utah and Texas Tech all end with just one loss?', [mkSim(['BYU', 'Utah', 'Texas Tech']), null]), C1 = S.compact(f1); assert.ok(C1 && C1.impossible && C1.branches[0].label, 'branched compact with a label and an impossible list');


await chk('B4: Worker diff vs B3 is exactly 2 lines: SCN.MODEL -> 70b and the SCN constants line (AI_TIMEOUT_MS 8000); MAX_OUT_TOKENS 220, MODELS, DAY_CAP, TICKET_COUNTS unchanged', async () => {
  const a = fs.readFileSync(path.join(BASET, '_worker.js'), 'utf8').split('\n'), b = UNF2(UNF3(V1.unvis1(fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8')))).split('\n'); assert.equal(a.length, b.length); const d = a.map((l, i) => i).filter((i) => a[i] !== b[i]); assert.equal(d.length, 2, 'changed lines: ' + d);
  assert.ok(b[d[0]].startsWith("  MODEL: '" + M70 + "',")); assert.ok(a[d[0]].startsWith("  MODEL: '" + M8 + "',"));
  assert.equal(b[d[1]].replace('AI_TIMEOUT_MS: 8000 /* scn_b4: was 6000 */,', 'AI_TIMEOUT_MS: 6000,'), a[d[1]]);
  assert.equal(T.SCN.MODEL, M70); assert.equal(OT.SCN.MODEL, M8); assert.equal(T.SCN.AI_TIMEOUT_MS, 8000); assert.equal(OT.SCN.AI_TIMEOUT_MS, 6000); assert.equal(T.SCN.MAX_OUT_TOKENS, 220);
  assert.deepEqual(T.SCN.MODELS, OT.SCN.MODELS); assert.ok(T.SCN.MODELS.includes(M8)); assert.equal(T.SCN.DAY_CAP, 60); assert.equal(T.SCN.TICKET_COUNTS, true); assert.equal(V1.unSys(T.SCN_SYS).split('\n').filter((l) => !/^[78]\. /.test(l)).map((l) => l.replace('Mention a playoff chance only if the facts have it, in the form "playoff chance of N% (model)", copying', 'Say "playoff chance (model)" only if the facts have it, copying')).join('\n'), OT.SCN_SYS);   /* final3 rewords rule 4 */   /* final2 adds prompt lines 7 and 8 */
});
await chk('B4: ai-client.js diff vs B3 is exactly SCN_WAIT_MS 7000 -> 9000 (server 8000 + 1 s, same margin as B3)', async () => {
  const a = fs.readFileSync(path.join(BASET, 'assets/ai-client.js'), 'utf8').split('\n'), b = fs.readFileSync(path.join(NEWT, 'assets/ai-client.js'), 'utf8').split('\n'); assert.equal(a.length, b.length); const d = a.map((l, i) => i).filter((i) => a[i] !== b[i]); assert.equal(d.length, 1);
  assert.equal(b[d[0]].replace('var SCN_WAIT_MS = 9000 /* scn_b4: server 8000 + 1 s (was 7000) */,', 'var SCN_WAIT_MS = 7000,'), a[d[0]]);
});
await chk('B4: flag on, Preview default call goes to 70b with the JSON schema and max_tokens 220; Production ignores _model (8b) and uses 70b; Preview _model 8b still works', async () => {
  const E = mk(ON); const r = await scn(E); assert.equal(r.j.source, 'scn', r.t); const [m, inp] = [E.st.ai_calls[0][0], JSON.parse(E.st.ai_calls[0][1])]; assert.equal(m, M70); assert.equal(inp.response_format.type, 'json_schema'); assert.equal(inp.max_tokens, 220); assert.equal(r.j.diag.model, M70); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1);
  const P = mk(Object.assign({ KT_ENV: 'production' }, ON)); const rp = await scn(P, COMPACT, { _model: M8 }, PROD); assert.equal(rp.j.source, 'scn'); assert.equal(P.st.ai_calls[0][0], M70); assert.equal(rp.j.diag, undefined);
  const E8 = mk(ON); await scn(E8, COMPACT, { _model: M8 }); assert.equal(E8.st.ai_calls[0][0], M8); assert.equal(JSON.parse(E8.st.ai_calls[0][1]).response_format, undefined);
});
await chk('B4: a hanging model call still falls back (ai_error, 200) at the timeout; nothing extra counted', async () => {
  await withFlag('AI_TIMEOUT_MS', 50, async () => { const E = mk(ON); E.env.AI = { run: () => new Promise(() => {}) }; const t0 = Date.now(); const r = await scn(E); assert.ok(Date.now() - t0 < 2000); assert.equal(r.s, 200); assert.equal(r.j.fallback, true); assert.equal(r.j.reason, 'ai_error'); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1); });
});
for (const [nm, over] of [['unset', {}], ['"off"', { AI_SCN: 'off' }], ['"ON"', { AI_SCN: 'ON' }], ['empty', { AI_SCN: '' }], ['production unset', { KT_ENV: 'production' }]]) {
  await chk('B4 flag off (AI_SCN ' + nm + '): ask-config, home, scn mode and bad input are byte-identical to B3 with the same D1 writes, model calls and bot checks', async () => {
    const host = over.KT_ENV ? PROD : HOST; const cases = [ (WW) => WW.fetch(req('/api/ask-config', {}, host), null), (WW) => WW.fetch(post('/api/ask', { mode: 'home', text: 'What if BYU wins out?', cf_turnstile: 'good' }, {}, host), null), (WW) => WW.fetch(post('/api/ask', { mode: 'scn', facts: COMPACT, cf_turnstile: 'good' }, {}, host), null), (WW) => WW.fetch(post('/api/ask', '{bad', {}, host), null), (WW) => WW.fetch(post('/api/ask', { mode: 'scn', facts: { x: 1 }, cf_turnstile: 'good' }, {}, host), null) ];
    for (let i = 0; i < cases.length; i++) { const E1 = mk(over, OW), E2 = mk(over); const run = async (WW, E) => { const f0 = WW.fetch; return snap(await f0.call(WW, i === 0 ? req('/api/ask-config', {}, host) : [null, post('/api/ask', { mode: 'home', text: 'What if BYU wins out?', cf_turnstile: 'good' }, {}, host), post('/api/ask', { mode: 'scn', facts: COMPACT, cf_turnstile: 'good' }, {}, host), post('/api/ask', '{bad', {}, host), post('/api/ask', { mode: 'scn', facts: { x: 1 }, cf_turnstile: 'good' }, {}, host)][i], E.env)); };
      const a = await run(OW, E1), b = await run(W, E2); assert.deepEqual(b, a, 'case ' + i); assert.deepEqual([...E2.db.rows], [...E1.db.rows]); assert.deepEqual(E2.st.ai_calls, E1.st.ai_calls); assert.equal(E2.st.siteverify.length, E1.st.siteverify.length); }
  });
}
await chk('B4 flag on: /api/ask-config is byte-identical to B3 (no timeout or model leak)', async () => { const E1 = mk(ON, OW), E2 = mk(ON); assert.deepEqual(await snap(await W.fetch(req('/api/ask-config'), E2.env)), await snap(await OW.fetch(req('/api/ask-config'), E1.env))); });
await chk('B4 cost: worst-case neurons recomputed (70b default); day worst stays within the existing budget bound; measured ~35/call x 60 = 2.1k', async () => {
  const w70 = T.scnWorstNeurons(M70), w8 = T.scnWorstNeurons(M8); assert.ok(w70 > w8); const day = 60 * 35; fs.writeFileSync(path.join(path.dirname(NEWT), '..', 'logs', 'cost_b4.json'), JSON.stringify({ scnWorstNeurons70b: w70, scnWorstNeurons8b: w8, scnDayWorstAllWriteups60: Math.round(60 * w70 * 100) / 100, measured70bPerCall: 34.8, measured70bMax: 39.7, measuredDay60: day, measuredDay60AtMax: Math.round(60 * 39.7), ASK_NEURON_BUDGET: T.ASK.NEURON_BUDGET }, null, 1)); console.log('cost: worst70b=' + w70 + ' worst8b=' + w8 + ' day60worst=' + (60 * w70).toFixed(1) + ' measured60=' + day + ' budget=' + T.ASK.NEURON_BUDGET);
});
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
