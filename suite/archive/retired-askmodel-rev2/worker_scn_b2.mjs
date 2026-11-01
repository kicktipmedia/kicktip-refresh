// scn_b2 Worker tests (offline: stub AI binding, mock D1 + Turnstile; no network). M1 allowlist, M2 counting + worst-case neurons, 8b default, 'as an ai', flag-off identity vs B.
// usage: node tests/worker_scn_b2.mjs BASE_TREE(B) NEW_TREE(B2)
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [BASET, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const V1 = require('./lib/vis1_expect.cjs'); const OW = V1.wrapOld(await loadWorker(BASET)), W = await loadWorker(NEWT), T = W._ask, OT = OW._ask; const H = require('./lib/scn_harness.js')(NEWT); const FX = require('./eval_facts.json').items;
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

// ===== M1: the allowlist =====
await chk('M1: the Worker allowlists are exactly the shipped data (team short names from sim-bundle.json, conference names), and every conference name of ccg-rules / ccg-sim is in it', async () => {
  const fold = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''), want = [...new Set(H.B.teams.map((t) => fold(t.n)))].sort(), got = [...T.SCN_TEAMS].sort(); assert.deepEqual(got, want); assert.ok(got.length >= 130);
  const sj = JSON.parse(fs.readFileSync(path.join(NEWT, 'data/sim-bundle.json'), 'utf8')); assert.deepEqual([...T.SCN_CONFS].sort(), sj.confs.map((c) => c.name).sort()); assert.ok(T.SCN_TEAMS.has('San Jose State') && !T.SCN_TEAMS.has('San Jos\u00e9 State'), 'scn_b3: the allowlist holds the folded name');
  for (const R of Object.values(H.rules.rules)) assert.ok(T.SCN_CONFS.has(R.name), R.name); assert.ok(T.SCN_TEAMS.has('BYU') && T.SCN_TEAMS.has('Texas Tech') && T.SCN_CONFS.has('Big 12'));
  const na = [...T.SCN_TEAMS].filter((s) => !/^[\x20-\x7e]+$/.test(s)); assert.equal(na.length, 0, 'scn_b3: no non-ASCII short names remain: ' + na); for (const nm of na) { const c = clone(C1); c.branches[0].teams[0].team = nm; assert.equal(T.scnFacts(c), null, 'the closed charset already refuses ' + nm + ' (a write-up is never offered for it; the card stands alone)'); } const w = fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8').split('\n').filter((l) => l.includes('SCN_TEAMS = new Set')); assert.equal(w.length, 1); assert.ok(/^[\x20-\x7e]*$/.test(w[0]), 'the generated line is ASCII');
});
await chk('M1: every real compact facts object passes (the 20+ eval fixtures, the one-loss branched facts, an ordinary unbranched one)', async () => {
  assert.ok(FX.length >= 20); for (const x of FX) assert.ok(T.scnFacts(clone(x.compact)), x.q); assert.ok(T.scnFacts(clone(C1))); const o = H.run('What if BYU and Texas Tech both end with just one loss'); assert.ok(T.scnFacts(clone(S.compact(o.f))));
});
await chk('M1: every question of the recorded scenario banks that produces compact facts passes (same answer as the base Worker)', async () => {
  const rows = require('./qbank_scn_b.json').rows.map((r) => r.text).concat(require('./qbank_scn_a2.json').rows ? require('./qbank_scn_a2.json').rows.map((r) => r.text || r.q) : []); let seen = 0, pass = 0;
  for (const q of rows) { if (!q) continue; const p = H.KP.parse(q, H.B.aliases, { choices: {} }); if (p.refusal || p.clarify) continue; const r = H.KS.resolve(p, H.B, { branches: true }); if (!r.ok) continue; let f; try { f = r.branches ? H.EX.buildBranched({ parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }) : H.EX.build({ parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg }); } catch (e) { continue; } if (!f || f.ok === false) continue; const c = S.compact(f); if (!c) continue; seen++; const a = T.scnFacts(clone(c)), b = OT.scnFacts(clone(c)); assert.equal(!!a, !!b, q); if (a) pass++; }
  assert.ok(seen >= 15, 'compact facts seen ' + seen); assert.equal(pass, seen);
});
const BADS = {
  'unknown team in a branch': (c) => { c.branches[0].teams[0].team = 'Springfield Atoms'; }, 'a real full name instead of the short name': (c) => { c.branches[0].teams[0].team = 'BYU Cougars'; }, 'lower-case team': (c) => { c.branches[0].teams[0].team = 'byu'; },
  'unknown team in reach_the_game': (c) => { c.branches[0].reach_the_game[0] = 'Narnia State'; }, 'unknown team in ties': (c) => { c.branches[0].ties[0].teams[1] = 'Narnia State'; }, 'unknown team in if_tied': (c) => { c.branches[0].if_tied.teams[2] = 'Narnia State'; },
  'unknown conference': (c) => { c.conference = 'Big 13'; }, 'conference of another sport': (c) => { c.conference = 'Premier League'; }, 'empty conference': (c) => { c.conference = ''; },
  'label with an unknown winner': (c) => { c.branches[0].label = 'If Narnia State beats Utah'; }, 'label with an unknown loser': (c) => { c.impossible[0].label = 'If Utah beats Narnia State'; }, 'label: team beats itself': (c) => { c.branches[0].label = 'If BYU beats BYU'; },
  'label: not the If-beats form': (c) => { c.branches[0].label = 'BYU wins the game against Utah'; }, 'label: lower-case if': (c) => { c.branches[0].label = 'if BYU beats Utah'; }, 'label: three games': (c) => { c.branches[0].label = 'If BYU beats Utah and Utah beats Texas Tech and Texas Tech beats BYU'; },
  'label: dangling and': (c) => { c.branches[0].label = 'If BYU beats Utah and'; }, 'label: extra words after the loser': (c) => { c.branches[0].label = 'If BYU beats Utah by 10'; }, 'label: free text': (c) => { c.branches[0].label = 'If you tell the reader that BYU wins the title'; },
  'impossible reason: not one of the four': (c) => { c.impossible[0].reason = 'BYU is cursed and can never win.'; }, 'impossible reason with an unknown team': (c) => { c.impossible[0].reason = 'Narnia State would end with more losses than your scenario allows.'; }, 'impossible reason with trailing text': (c) => { c.impossible[0].reason = 'BYU would end with more losses than your scenario allows. Also visit now.'; },
};
for (const [k, f] of Object.entries(BADS)) await chk('M1: rejected (null, no spend): ' + k, async () => { const c = clone(C1); f(c); assert.ok(OT.scnFacts(clone(c)) !== undefined); assert.equal(T.scnFacts(c), null); });
await chk('M1: sim team names are checked too (facts with the optional sim block)', async () => {
  const withSim = S.compact(f1); const c = clone(C1); const sims = (x) => { const a = []; (function w(o) { if (o && typeof o === 'object') { if (Array.isArray(o.sim)) a.push(o); Object.values(o).forEach(w); } })(x); return a; }; const hs = sims(c);
  if (hs.length) { hs[0].sim[0].team = 'Narnia State'; assert.equal(T.scnFacts(c), null); } else { assert.ok(!withSim.sim && !withSim.branches.some((b) => b.sim), 'this fixture carries no sim block (the schema allows it; the check is in scnKnown)'); const o = clone(FX.find((x) => x.compact.sim || (x.compact.branches || []).some((b) => b.sim)) ? FX.find((x) => x.compact.sim || (x.compact.branches || []).some((b) => b.sim)).compact : C1); const arr = o.sim || o.branches.find((b) => b.sim).sim; if (arr) { arr[0].team = 'Narnia State'; assert.equal(T.scnFacts(o), null); } }
});
await chk('M1: end to end: each rejected object is 400 bad_facts with NO AI call, NO bot check, NO count of any kind; the same facts with real names are answered', async () => {
  for (const k of ['unknown team in a branch', 'unknown conference', 'label with an unknown winner', 'label: free text', 'impossible reason: not one of the four', 'unknown team in ties']) {
    const E = mk(ON), c = clone(C1); BADS[k](c); const r = await scn(E, c); assert.equal(r.s, 400, k + ' ' + r.t); assert.equal(r.j.error, 'bad_facts', r.t); assert.equal(E.st.ai_calls.length, 0, k); assert.equal(E.st.siteverify.length, 0, k); assert.equal(E.db.rows.size, 0, k); const o = mk(ON, OW); }
  const E = mk(ON); const ok = await scn(E, clone(C1)); assert.equal(ok.s, 200, ok.t); assert.equal(ok.j.source === 'scn' || ok.j.fallback === true, true);
});
await chk('M1: the error shape is the one the base uses for any bad facts (same status, same body)', async () => {
  const E1 = mk(ON, OW), E2 = mk(ON); const c = clone(C1); c.branches[0].teams[0].team = 'bad<team>'; const a = await scn(E1, c, {}, HOST, OW), b = await scn(E2, c); assert.equal(b.s, a.s); assert.equal(b.t, a.t);
  const d = clone(C1); d.conference = 'Big 13'; const e = await scn(mk(ON), d); assert.equal(e.s, a.s); assert.equal(e.t, a.t);
});
await chk('M1: the allowlist is not consulted when the flag is off (the scn mode answers exactly as the base Worker does: no scn)', async () => {
  const E1 = mk({}, OW), E2 = mk({}); const c = clone(C1); c.conference = 'Big 13'; const a = await scn(E1, c, {}, HOST, OW), b = await scn(E2, c); assert.equal(b.s, a.s); assert.equal(b.t, a.t);
});

// ===== M2: the counting =====
await chk('M2: a ticket-less write-up (bot-check token) takes ONE global count and ONE scenario count', async () => { const E = mk(ON); const r = await scn(E); assert.equal(r.j.source, 'scn', r.t); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1); assert.equal(E.st.siteverify.length, 1); });
await chk('M2: a ticketed write-up takes ONE global count of its own and ONE scenario count, with no bot check; the ticket works once and the replay counts nothing', async () => {
  const E = mk(ON); const h = await home(E); assert.equal(cnt(E, 'askg:p'), 1); const sv = E.st.siteverify.length; const r = await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk }); assert.equal(r.j.source, 'scn', r.t);
  assert.equal(E.st.siteverify.length, sv); assert.equal(cnt(E, 'askg:p'), 2); assert.equal(cnt(E, 'askscn:p'), 1); const r2 = await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk }); assert.equal(r2.j.reason, 'ticket_invalid'); assert.equal(cnt(E, 'askg:p'), 2); assert.equal(cnt(E, 'askscn:p'), 1); assert.equal(E.st.ai_calls.length, 2);
});
await chk('M2: a refused write-up (bad facts, bad ticket, no token) counts nothing; one write-up never takes two counts', async () => {
  const E = mk(ON); await scn(E, { v: 1 }); await scn(E, COMPACT, { cf_turnstile: undefined, tk: 'x.y.z' }); await scn(E, COMPACT, { cf_turnstile: undefined }); assert.equal(cnt(E, 'askg:p'), 0); assert.equal(cnt(E, 'askscn:p'), 0); assert.equal(E.st.ai_calls.length, 0);
  const r = await scn(E); assert.equal(r.j.source, 'scn'); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1);
});
await chk('M2: production host counts askg / askscn (not :p) the same way, ticketed and ticket-less', async () => {
  const E = mk(Object.assign({ KT_ENV: 'production' }, ON)); const h = await home(E, 'What if BYU wins out?', {}, PROD); await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk }, PROD); await scn(E, COMPACT, {}, PROD); assert.equal(cnt(E, 'askg'), 3); assert.equal(cnt(E, 'askscn'), 2); assert.equal(cnt(E, 'askg:p'), 0);
});
await chk('M2: SCN.TICKET_COUNTS = false is exactly the B behavior (a ticketed write-up takes no global count; a ticket-less one still does)', async () => {
  await withFlag('TICKET_COUNTS', false, async () => { const E = mk(ON); const h = await home(E); await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk }); assert.equal(cnt(E, 'askg:p'), 1); assert.equal(cnt(E, 'askscn:p'), 1); await scn(E); assert.equal(cnt(E, 'askg:p'), 2); assert.equal(cnt(E, 'askscn:p'), 2); }); assert.equal(T.SCN.TICKET_COUNTS, true);
  const E1 = mk(ON, OW), h1 = await home(E1, 'What if BYU wins out?', {}, HOST, OW); await scn(E1, COMPACT, { cf_turnstile: undefined, tk: h1.j.scn_tk }, HOST, OW); assert.equal(cnt(E1, 'askg:p'), 1, 'B itself');
});
await chk('M2: the global daily cap stops write-ups, ticketed or not (AI_DAY_CAP_OVERRIDE=3: ask, ticketed write-up, ticket-less write-up fit; the 4th model call of any kind is refused with daily_cap and no model call)', async () => {
  const E = mk(Object.assign({ AI_DAY_CAP_OVERRIDE: '3' }, ON)); const h = await home(E); assert.equal((await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk })).j.source, 'scn'); assert.equal((await scn(E)).j.source, 'scn'); assert.equal(E.st.ai_calls.length, 3);
  const h2 = await home(E, 'What if BYU wins out?', {}, HOST, W, '198.51.100.20'); assert.ok(h2.j.fallback === true || h2.j.reason, JSON.stringify(h2.j).slice(0, 120)); const r = await scn(E, COMPACT, {}, HOST, W, '198.51.100.21'); assert.equal(r.j.fallback, true); assert.equal(r.j.reason, 'daily_cap'); assert.equal(E.st.ai_calls.length, 3);
  const E2 = mk(Object.assign({ AI_DAY_CAP_OVERRIDE: '2' }, ON)); const g = await home(E2); const g2 = await home(E2, 'What if Utah wins out?', {}, HOST, W, '198.51.100.30'); assert.ok(g.j.scn_tk); const w = await scn(E2, COMPACT, { cf_turnstile: undefined, tk: g.j.scn_tk }); assert.equal(w.j.reason, 'daily_cap', 'a valid ticket does not get a write-up past the global cap'); assert.equal(E2.st.ai_calls.length, 2);
});
await chk('M2: the 60/day scenario sub-cap is enforced for ticket-less and ticketed write-ups (AI_SCN_CAP_OVERRIDE=2), and a sub-cap refusal makes no model call', async () => {
  const E = mk(Object.assign({ AI_SCN_CAP_OVERRIDE: '2' }, ON)); const h = await home(E); const a = await scn(E, COMPACT, { cf_turnstile: undefined, tk: h.j.scn_tk }), b = await scn(E), c = await scn(E); assert.equal(a.j.source, 'scn'); assert.equal(b.j.source, 'scn'); assert.equal(c.j.reason, 'scn_cap'); assert.equal(E.st.ai_calls.length, 3);
  assert.equal(T.SCN.DAY_CAP, 60);
});
await chk('M2: a whole production-shaped day against the mock D1 (no overrides): 120 write-ups + 200 home asks from 320 different visitors make at most 150 model calls, and at most 60 of them write-ups', async () => {
  for (const model of [M8, M70]) { await withFlag('MODEL', model, async () => {
    const E = mk(Object.assign({ KT_ENV: 'production' }, ON)); let k = 0; const ip = () => '198.18.' + Math.floor(k / 250) + '.' + (k++ % 250 + 1); const tks = [];
    for (let i = 0; i < 40; i++) { const h = await home(E, 'What if BYU wins out?', {}, PROD, W, ip()); if (h.j.scn_tk) tks.push(h.j.scn_tk); }
    for (let i = 0; i < 120; i++) await scn(E, COMPACT, i % 2 && tks.length ? { cf_turnstile: undefined, tk: tks.pop() } : {}, PROD, W, ip());
    for (let i = 0; i < 200; i++) await home(E, 'What if Utah wins out?', {}, PROD, W, ip());
    const calls = E.st.ai_calls.length, scnCalls = E.st.ai_calls.filter((c) => c[1].includes('KickTip writer')).length; assert.ok(calls <= 150, model + ' model calls ' + calls); assert.ok(scnCalls <= 60, 'write-ups ' + scnCalls); assert.equal(scnCalls, 60); assert.equal(calls, 150);
    assert.ok(scnCalls * T.scnWorstNeurons(model) + (calls - scnCalls) * 74.899 <= T.ASK.NEURON_BUDGET, 'the real mix is inside the budget');
  }); }
});
await chk('M2: worst-case neurons per UTC day is computable and inside NEURON_BUDGET 11,235 for 8b AND 70b (worst day = 150 counts x the larger of an ask / a write-up)', async () => {
  const B = T.ASK.NEURON_BUDGET; assert.equal(B, 11235); const d8 = T.scnDayWorst(M8), d70 = T.scnDayWorst(M70), w8 = T.scnWorstNeurons(M8), w70 = T.scnWorstNeurons(M70), ask = B / 150;
  console.log('  worst case per write-up: 8b ' + w8.toFixed(2) + ' neurons, 70b ' + w70.toFixed(2) + '; per home ask ' + ask.toFixed(3) + '; worst UTC day (150 counts, all at the larger worst case): 8b ' + d8.toFixed(1) + ', 70b ' + d70.toFixed(1) + ' of ' + B);
  assert.ok(d8 <= B + 1e-6 && d70 <= B + 1e-6, d8 + ' / ' + d70); assert.ok(w8 < 30 && w8 < w70 / 2 && w70 <= ask + 1e-9); assert.equal(T.scnDayWorst(), d8, 'default model is 8b');
  const mixed = (m) => 60 * T.scnWorstNeurons(m) + 90 * ask; assert.ok(mixed(M8) < d8 && mixed(M70) < d70);
  const bBehaviour = 150 * ask + 60 * w70; assert.ok(bBehaviour > B, 'B (ticketed write-ups uncounted) could reach ' + bBehaviour.toFixed(0) + ' on 70b');
});

// ===== 8b default =====
await chk('8b: the write-up model is 8b by default (no JSON schema, 8b request shape), 70b is a one-line constant, and the base Worker was 70b', async () => {
  assert.equal(OT.SCN.MODEL, M70); assert.equal(T.SCN.MODEL, M70);   /* scn_b4: back to 70b */ assert.ok(T.SCN.MODELS.includes(M70) && T.SCN.MODELS.includes(M8));
  const E = mk(ON); await scn(E); const [m, inp] = [E.st.ai_calls[0][0], JSON.parse(E.st.ai_calls[0][1])]; assert.equal(m, M70); assert.equal(inp.response_format.type, 'json_schema'); assert.equal(inp.temperature, 0);
  const src = fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8'); assert.equal(src.split('\n').filter((l) => /^  MODEL: '@cf\/meta\//.test(l)).length, 1); assert.ok(/^  MODEL: '@cf\/meta\/llama-3\.3-70b-instruct-fp8-fast',/m.test(src));
  await withFlag('MODEL', M8, async () => { const E2 = mk(ON); await scn(E2); assert.equal(E2.st.ai_calls[0][0], M8); assert.equal(JSON.parse(E2.st.ai_calls[0][1]).response_format, undefined); });
});
await chk('8b: replies the way 8b does (JSON text, JSON wrapped in chatter) are parsed; a bare number or empty reply falls back with no spend beyond the call', async () => {
  for (const [rep, ok] of [[PROSE(GOOD), true], ['Here you go: ' + PROSE(GOOD) + ' done', true], ['5025', false], ['', false]]) { const E = mk(ON); E.env.AI = stubAI(rep, E.st); const r = await scn(E); assert.equal(r.j.source === 'scn', ok, rep.slice(0, 20)); if (!ok) assert.equal(r.j.fallback, true); }
});

// ===== 'as an ai' =====
await chk("prose: 'as an ai' (any case) is rejected by the Worker like the browser; the same text without it passes; the base Worker accepted it", async () => {
  const f = T.scnFacts(clone(COMPACT)), bad = GOOD.replace('In this scenario,', 'As an AI, in this scenario,'); assert.ok(T.scnProse(GOOD, f)); assert.equal(T.scnProse(bad, f), null); assert.equal(T.scnProse(bad.replace('As an AI', 'as an ai'), f), null); assert.equal(T.scnProse(bad.replace('As an AI', 'AS AN AI'), f), null);
  assert.ok(OT.scnProse(bad, OT.scnFacts(clone(COMPACT))), 'B accepted it (the gap QA found)');
  const E = mk(ON); E.env.AI = stubAI(PROSE(bad), E.st); const r = await scn(E); assert.equal(r.j.reason, 'bad_output');
  assert.ok(T.scnProse(GOOD.replace('KickTip', 'Kick Tip').replace('Kick Tip', 'KickTip'), f), 'unrelated text still passes'); assert.ok(T.scnProse(GOOD.replace('Utah can still', 'Utah has a chance and can still'), f), 'words like a chance are not matched by the new rule');
});

// ===== flag off: identical to B =====
for (const [lab, over] of [['AI_SCN unset', {}], ['AI_SCN "off"', { AI_SCN: 'off' }], ['AI_SCN "ON"', { AI_SCN: 'ON' }], ['AI_SCN empty', { AI_SCN: '' }]]) {
  await chk('flag off (' + lab + '): ask-config, home answers, router, conference mode, scn mode and bad input answer byte-identically to B, with the same D1 writes, model calls and bot checks', async () => {
    const shapes = [[{}, HOST], [{ KT_ENV: 'production' }, PROD], [{ AI_ENABLED: 'off' }, HOST], [{ AI_ROUTER: 'on' }, HOST]];
    for (const [o2, host] of shapes) {
      const a = mk(Object.assign({}, over, o2), OW), b = mk(Object.assign({}, over, o2)); const ca = await snap(await OW.fetch(req('/api/ask-config', {}, host), a.env)), cb = await snap(await W.fetch(req('/api/ask-config', {}, host), b.env)); assert.deepEqual(cb, ca); assert.ok(!/scn/.test(cb.t));
      const bodies = [{ mode: 'home', text: 'What if BYU wins out?', cf_turnstile: 'good' }, { mode: 'home', text: 'give me a parlay for Utah', cf_turnstile: 'good' }, { mode: 'home', text: 'What if BYU wins out?', cf_turnstile: 'bad' }, { mode: 'conference', conf: 'big12', text: 'What if BYU wins out?', cf_turnstile: 'good' }, { mode: 'scn', facts: COMPACT, cf_turnstile: 'good' }, { mode: 'scn', facts: Object.assign(clone(COMPACT), { conference: 'Big 13' }), cf_turnstile: 'good' }, { mode: 'scn', facts: COMPACT, tk: 'a.b.c' }, { mode: 'nope' }, '{bad json', ''];
      for (const bd of bodies) { const ra = await snap(await OW.fetch(post('/api/ask', bd, {}, host), a.env)), rb = await snap(await W.fetch(post('/api/ask', bd, {}, host), b.env)); assert.deepEqual(rb, ra, JSON.stringify(bd).slice(0, 60)); assert.ok(!/scn_tk/.test(rb.t)); }
      assert.deepEqual(b.db.log.map((x) => [x.k, x.a.length]), a.db.log.map((x) => [x.k, x.a.length])); assert.equal(b.st.ai_calls.length, a.st.ai_calls.length); assert.equal(b.st.siteverify.length, a.st.siteverify.length); assert.deepEqual([...b.db.rows.keys()].sort(), [...a.db.rows.keys()].sort());
    }
  });
}
await chk('flag off: every changed line of the Worker is inside the scenario block (between "const SCN = {" and "end scn_a2"); everything else is byte-identical to B', async () => {
  const a = fs.readFileSync(path.join(BASET, '_worker.js'), 'utf8').split('\n'), b = V1.unvis1(fs.readFileSync(path.join(NEWT, '_worker.js'), 'utf8')).split('\n');   /* vis1: tool lists, ROUTER_TOOLS and SCN_SYS rule 3/4 checked exactly, then mapped back */
  const lo = (x) => x.findIndex((l) => /^const SCN = \{/.test(l)), hi = (x) => x.findIndex((l) => l.includes('/* ===== end scn_a2 ===== */')); assert.ok(lo(a) > 0 && hi(a) > lo(a) && lo(b) === lo(a));
  assert.deepEqual(a.slice(0, lo(a)), b.slice(0, lo(b)), 'before the block'); assert.deepEqual(a.slice(hi(a)), b.slice(hi(b)).slice(b.slice(hi(b)).length - a.slice(hi(a)).length), 'after the block');
});
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
