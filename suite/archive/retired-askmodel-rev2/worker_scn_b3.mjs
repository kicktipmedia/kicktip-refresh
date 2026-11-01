// scn_b3 Worker tests (SJSU fold). Base tree = B2, new tree = B3. Original header: scn_b2 Worker tests (offline: stub AI binding, mock D1 + Turnstile; no network). M1 allowlist, M2 counting + worst-case neurons, 8b default, 'as an ai', flag-off identity vs B.
// usage: node tests/worker_scn_b3.mjs BASE_TREE(B2) NEW_TREE(B3)
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const OW = await loadWorker(BASET), W = await loadWorker(NEWT), T = W._ask, OT = OW._ask; const H = require('./lib/scn_harness.js')(NEWT); const FX = require('./eval_facts.json').items;
const S = (() => { const c = vm.createContext({ window: {}, console }); vm.runInContext(fs.readFileSync(path.join(NEWT, 'assets/ks/scnai.js'), 'utf8'), c); return c.KTScnAI || c.window.KTScnAI; })();
const HOST = 'https://preview.kicktip.pages.dev', PROD = 'https://kicktipmedia.com'; const M8 = '@cf/meta/llama-3.1-8b-instruct-fp8', M70 = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
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

const fold = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const cardFacts = (q) => { const p = H.KP.parse(q, H.B.aliases, { choices: {} }), r = H.KS.resolve(p, H.B, { branches: true }); assert.ok(r.ok, q); const o = { parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }; return r.branches ? H.EX.buildBranched(o) : H.EX.build(o); };
// the questions QA found (13 of 329): every Mountain West card that names San Jose State
const SJ = ['What if San José State wins out?', 'What if San José State loses out?', 'What if Nevada wins out?', 'What if Hawai\'i wins out?', 'What if New Mexico loses out?', 'What if Air Force loses out?', 'What if UTEP wins out?', 'What if Northern Illinois wins out?', 'What if North Dakota State loses out?'];
await chk('SJSU: the allowlist holds the folded name exactly as the browser sends it, and no non-ASCII name remains', async () => {
  assert.ok(T.SCN_TEAMS.has('San Jose State')); assert.ok(!T.SCN_TEAMS.has('San Jos\u00e9 State')); assert.ok(OT.SCN_TEAMS.has('San Jos\u00e9 State') && !OT.SCN_TEAMS.has('San Jose State'), 'B2 had the accented name');
  assert.equal([...T.SCN_TEAMS].filter((s) => !/^[\x20-\x7e]+$/.test(s)).length, 0); assert.equal(T.SCN_TEAMS.size, OT.SCN_TEAMS.size);
  assert.deepEqual([...T.SCN_TEAMS].filter((s) => !OT.SCN_TEAMS.has(s)), ['San Jose State']); assert.deepEqual([...OT.SCN_TEAMS].filter((s) => !T.SCN_TEAMS.has(s)), ['San Jos\u00e9 State']);
  assert.deepEqual([...T.SCN_CONFS].sort(), [...OT.SCN_CONFS].sort());
  for (const s of T.SCN_TEAMS) assert.equal(S.clean(s), s, 'what the browser sends for ' + s + ' is the same string');
});
await chk('SJSU: every card question that names San Jose State in what the browser sends passes scnFacts in B3 (and was refused by B2)', async () => {
  let seen = 0; for (const q of SJ) { const f = cardFacts(q); assert.ok(f && f.ok !== false, q); const c = S.compact(f); assert.ok(c, q); const blob = JSON.stringify(c); if (!/San Jose State/.test(blob)) continue; seen++; assert.ok(!/Jos\u00e9/.test(blob), 'the browser sends the folded name: ' + q); assert.ok(T.scnFacts(clone(c)), 'B3 accepts ' + q); assert.equal(OT.scnFacts(clone(c)), null, 'B2 refused ' + q); }
  assert.ok(seen >= 7, 'cards naming SJSU seen: ' + seen);
});
await chk('SJSU: a branch label naming San Jose State (If X beats San Jose State) is accepted; the accented spelling is still refused by the closed charset', async () => {
  const c = clone(C1); c.branches[0].label = 'If Nevada beats San Jose State'; assert.ok(T.scnLabelOk(c.branches[0].label) && T.scnFacts(clone(c))); assert.ok(!OT.scnLabelOk(c.branches[0].label));
  const d = clone(C1); d.branches[0].teams[0].team = 'San Jos\u00e9 State'; assert.equal(T.scnFacts(d), null); const e = clone(C1); e.branches[0].label = 'If Nevada beats San Jos\u00e9 State'; assert.equal(T.scnFacts(e), null);
  const g = clone(C1); g.impossible = [{ label: 'If San Jose State beats Nevada', reason: 'San Jose State would win more games than your scenario allows.' }]; assert.ok(T.scnFacts(g)); assert.ok(T.scnFacts(clone(g)) !== null);
  const h = clone(C1); h.branches[0].teams[0].team = 'San Jose'; assert.equal(T.scnFacts(h), null, 'a near miss is still refused'); const k = clone(C1); k.branches[0].teams[0].team = 'san jose state'; assert.equal(T.scnFacts(k), null);
});
await chk('SJSU: end to end, a San Jose State card is answered by the Worker (stub model): 200, one global count, one scenario count; the accented name is 400 bad_facts with no spend', async () => {
  const f = cardFacts('What if San José State wins out?'), c = S.compact(f); assert.ok(c);
  const prose = "In this scenario, San Jose State wins its remaining games. The result depends on games the scenario does not set."; const E = mk(ON); E.env.AI = stubAI(PROSE(prose), E.st); const r = await scn(E, clone(c)); assert.equal(r.s, 200, r.t); assert.equal(r.j.source, 'scn', r.t); assert.equal(E.st.ai_calls.length, 1); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1);
  const E0 = mk(ON, OW); E0.env.AI = stubAI(PROSE(prose), E0.st); const r0 = await scn(E0, clone(c), {}, HOST, OW); assert.equal(r0.s, 400); assert.equal(r0.j.error, 'bad_facts');
  const bad = clone(c); (function w(o) { if (Array.isArray(o)) o.forEach(w); else if (o && typeof o === 'object') for (const k of Object.keys(o)) { if (typeof o[k] === 'string') o[k] = o[k].replace(/San Jose State/g, 'San Jos\u00e9 State'); else w(o[k]); } })(bad); const E2 = mk(ON); const r2 = await scn(E2, bad); assert.equal(r2.s, 400, r2.t); assert.equal(E2.st.ai_calls.length, 0); assert.equal(E2.st.siteverify.length, 0); assert.equal(E2.db.rows.size, 0);
});
await chk('SJSU: flag off (AI_SCN unset) the Worker answers exactly as B2 on a San Jose State payload (same status, body)', async () => {
  const c = S.compact(cardFacts('What if Nevada wins out?')); assert.ok(/San Jose State/.test(JSON.stringify(c))); const E1 = mk({}, OW), E2 = mk({}); const a = await scn(E1, clone(c), {}, HOST, OW), b = await scn(E2, clone(c)); assert.equal(b.s, a.s); assert.equal(b.t, a.t); assert.equal(E1.db.rows.size, E2.db.rows.size);
});
await chk('scn_b3: Worker diff vs B2 is exactly the allowlist line and its comment (SCN.MODEL 8b, TICKET_COUNTS true unchanged)', async () => {
  const a = fs.readFileSync(path.join(BASET, '_worker.js'), 'utf8').split('\n'), b = fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8').split('\n'); assert.equal(a.length, b.length); const d = a.map((l, i) => i).filter((i) => a[i] !== b[i]); assert.equal(d.length, 2, 'changed lines: ' + d); assert.ok(a[d[1]].startsWith('const SCN_TEAMS = new Set(') && b[d[1]].startsWith('const SCN_TEAMS = new Set(')); assert.ok(a[d[0]].startsWith('/* ===== scn_b2 (QA M1)') && b[d[0]].startsWith('/* ===== scn_b2 (QA M1; scn_b3'));
  assert.equal(a[d[1]].replace('"San Jos\\u00e9 State"', '"San Jose State"'), b[d[1]]); assert.equal(T.SCN.MODEL, M8); assert.equal(T.SCN.TICKET_COUNTS, true); assert.equal(OT.SCN.MODEL, M8);
});
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
