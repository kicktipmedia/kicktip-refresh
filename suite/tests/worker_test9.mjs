// toolbox8 Worker test (offline; mocks only; nothing leaves the machine).
// usage: node worker_test7.mjs BASE_TREE(7b) NEW_TREE(8)
import fs from 'node:fs'; import path from 'node:path'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [BASE, NEW] = process.argv.slice(2).map((p) => path.resolve(p));
let n = 0, bad = 0;
const chk = async (k, f) => { n++; try { await f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).split('\n').slice(0, 4).join(' | ').slice(0, 400)); } };
const OLD11 = ['conf_race_alive', 'conf_standings', 'games_that_matter', 'path_compare', 'playoff_field', 'rankings_list', 'team_needs', 'team_path', 'team_schedule', 'team_snapshot', 'tiebreak_explain'];
const NEW5 = ['status_check', 'team_projection', 'head_to_head', 'slate_this_week', 'explain_site'];
const ALL16 = OLD11.concat(NEW5).sort(); const NEW3 = ['schedule_strength', 'quality_wins', 'team_compare']; const ALL19 = ALL16.concat(NEW3).sort();
const W6 = await loadWorker(BASE), W7 = await loadWorker(NEW);
const HOST = 'https://preview.kicktip.pages.dev';
const req = (p, o = {}) => new Request(HOST + p, { method: o.method || 'GET', headers: Object.assign({ 'CF-Connecting-IP': '203.0.113.9' }, o.h || {}), body: o.body });
const post = (p, body, h = {}) => req(p, { method: 'POST', h: Object.assign({ Origin: HOST, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin' }, h), body: typeof body === 'string' ? body : JSON.stringify(body) });
const snap = async (r) => { const h = {}; r.headers.forEach((v, k) => { h[k] = v; }); return { status: r.status, h, body: (await r.text()).replace(/"(verifyMs|ms)":\d+/g, '"$1":0') }; };
const SCRIPT = [
  ['GET ask', () => req('/api/ask')], ['GET ask-env', () => req('/api/ask-env')], ['POST ask-config', () => post('/api/ask-config', {})],
  ['ask no origin', () => req('/api/ask', { method: 'POST', h: { 'Content-Type': 'application/json' }, body: '{}' })], ['ask bad origin', () => post('/api/ask', { text: 'x' }, { Origin: 'https://evil.example' })],
  ['ask bad json', () => post('/api/ask', '{nope')], ['ask empty', () => post('/api/ask', { text: '', mode: 'home', cf_turnstile: 'good' })], ['ask betting', () => post('/api/ask', { text: 'Who should I bet on?', mode: 'home', cf_turnstile: 'good' })],
  ['ask no token', () => post('/api/ask', { text: 'What if BYU Cougars wins out?', mode: 'home' })], ['ask bad token', () => post('/api/ask', { text: 'What if BYU Cougars wins out?', mode: 'home', cf_turnstile: 'bad' })],
  ['ask ok 1', () => post('/api/ask', { text: 'What if BYU Cougars wins out?', mode: 'home', cf_turnstile: 'good' })], ['ask ok 2', () => post('/api/ask', { text: 'What if Utah Utes wins out?', mode: 'home', cf_turnstile: 'good' })], ['ask ok 3', () => post('/api/ask', { text: 'What if Iowa State wins out?', mode: 'home', cf_turnstile: 'good' })],
  ['ask too long', () => post('/api/ask', { text: 'a'.repeat(900), mode: 'home', cf_turnstile: 'good' })],
  ['tb-count GET', () => req('/api/tb-count')], ['unknown api', () => req('/api/nope')], ['non-api', () => req('/index.html')], ['auth session', () => req('/api/auth/session')],
];
async function run(W, over, only) { const E = makeEnv(W, over); installFetch(E.st); const out = []; for (const [name, mk] of SCRIPT) { if (only && !only(name)) continue; let r; try { r = await W.fetch(mk(), E.env); } catch (e) { r = { status: -1, headers: new Headers(), text: async () => 'THROW ' + e.message }; } out.push({ name, s: await snap(r) }); } return { out, E }; }
const ENVS = { ready: { AI_DAY_CAP_OVERRIDE: '2' }, killed: { AI_ENABLED: 'off' }, noAI: { AI: undefined }, noDB: { DB: undefined }, plain: {} };
await chk('static: Worker byte-identical to 8b; both lists are the 19 ids; TB_ON = 19', () => {
  const a = fs.readFileSync(path.join(BASE, '_worker.js'), 'utf8').split('\n'), b = fs.readFileSync(path.join(NEW, '_worker.js'), 'utf8').split('\n'); assert.equal(a.length, b.length);
  assert.equal(fs.readFileSync(path.join(BASE, '_worker.js'), 'utf8'), fs.readFileSync(path.join(NEW, '_worker.js'), 'utf8'), 'Worker must be byte-identical to 8b');
  assert.deepEqual(W7._tb.TB_ON.slice().sort(), ALL19); assert.deepEqual(W7._tb.TB_TOOL_IDS.slice().sort(), ALL19); assert.equal(ALL19.length, 19); assert.deepEqual(W7._tb.TB_ON, W7._tb.TB_ON.slice().sort()); assert.deepEqual(W6._tb.TB_ON, ALL19); assert.equal(ALL16.length, 16);
});
const ACFG = (name) => name === 'POST ask-config';
await chk('every scripted response (status, headers, body) identical to 8b (both 19 ids); same D1 writes / model calls / siteverify calls; 5 env shapes; both hosts', async () => {
  const strip = (x, W) => { const y = JSON.parse(JSON.stringify(x)); try { const j = JSON.parse(y.s.body); if (Array.isArray(j.tb)) { assert.deepEqual(j.tb, ALL19); delete j.tb; y.s.body = JSON.stringify(j); } } catch (e) { if (e instanceof assert.AssertionError) throw e; } delete y.s.h['content-length']; return y; };
  for (const [en, over] of Object.entries(ENVS)) { const a = await run(W6, over), b = await run(W7, over);
    for (let i = 0; i < a.out.length; i++) assert.deepEqual(strip(b.out[i], 7).s, strip(a.out[i], 6).s, en + ': ' + a.out[i].name);
    assert.deepEqual(b.E.db.log.map((x) => [x.k, x.a]), a.E.db.log.map((x) => [x.k, x.a]), en); assert.deepEqual(b.E.st.ai_calls, a.E.st.ai_calls, en); assert.deepEqual(b.E.st.siteverify, a.E.st.siteverify, en); }
  for (const host of ['https://preview.kicktip.pages.dev', 'https://kicktipmedia.com']) for (const p of ['/api/ask-config', '/api/ask-config/']) {
    const ra = makeEnv(W6, {}), rb = makeEnv(W7, {}); installFetch(ra.st); const x = await snap(await W6.fetch(new Request(host + p, { headers: { 'CF-Connecting-IP': '203.0.113.9' } }), ra.env)); installFetch(rb.st); const y = await snap(await W7.fetch(new Request(host + p, { headers: { 'CF-Connecting-IP': '203.0.113.9' } }), rb.env));
    const jx = JSON.parse(x.body), jy = JSON.parse(y.body); assert.deepEqual(jy.tb, ALL19); assert.deepEqual(jx.tb, ALL19); delete jx.tb; delete jy.tb; assert.deepEqual(jy, jx); assert.equal(y.status, x.status);
  }
});
const C = async (W, body, h = {}, E) => { E = E || makeEnv(W); installFetch(E.st); const r = await W.fetch(post('/api/tb-count', body, h), E.env); return { s: r.status, j: await r.json().catch(() => null), E }; };
await chk('tb-count: exactly the 19 ids accepted (200, one D1 write); other ids (and near misses) rejected 400 with no D1 call', async () => {
  for (const id of ALL19) { const r = await C(W7, { e: [['matched', id]] }); assert.equal(r.s, 200, id); assert.deepEqual(r.j, { ok: true, n: 1 }, id); }
  const E = makeEnv(W7); for (const id of ['schedule_strengths', 'team_compar', 'quality_win', 'strength_of_record', 'cfp_committee_rankings', 'ccg_matchup', 'team_trend', 'nope', '', 'TEAM_COMPARE']) assert.equal((await C(W7, { e: [['matched', id]] }, {}, E)).s, 400, id);
  assert.equal(E.db.log.length, 0);
  for (const id of NEW3) assert.equal((await C(W6, { e: [['matched', id]] })).s, 200, '8b accepts ' + id);
});
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
