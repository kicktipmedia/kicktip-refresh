// toolbox10: live /api/ask-config and /api/tb-count do not list the two new tools. usage: node worker_dark10.mjs TREE10
import path from 'node:path'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
import { createRequire } from 'node:module'; const V1 = createRequire(import.meta.url)('./lib/vis1_expect.cjs');   /* vis1: Set 2b live (21 ids), SCN_SYS rule 3/4 tweak */
const T = path.resolve(process.argv[2]); const W = await loadWorker(T); const HOST = 'https://preview.kicktip.pages.dev';
const E = makeEnv(W, {}); installFetch(E.st);
const post = (p, b) => new Request(HOST + p, { method: 'POST', headers: { 'CF-Connecting-IP': '203.0.113.9', Origin: HOST, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin' }, body: JSON.stringify(b) });
let bad = 0, n = 0; const chk = (k, f) => { n++; try { f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + e.message.slice(0, 300)); } };
const r = await W.fetch(new Request(HOST + '/api/ask-config', { headers: { 'CF-Connecting-IP': '203.0.113.9' } }), E.env); const body = await r.text(); let j = {}; try { j = JSON.parse(body); } catch (e) {}
chk('ask-config answers 200', () => assert.equal(r.status, 200));
chk('ask-config (set3m, Preview host) lists the 22 live ids then the 5 Set 3 Preview ids, and neither dark tool', () => { const ids = j.tb || []; assert.equal(ids.length, 27); assert.deepEqual(ids, V1.ALL22.concat(V1.SET3)); assert.ok(!ids.includes('ccg_matchup') && !ids.includes('team_trend')); assert.ok(!/ccg_matchup|team_trend/.test(body)); });
for (const id of ['ccg_matchup', 'team_trend']) { const c = await W.fetch(post('/api/tb-count', { tool: id }), E.env); chk('tb-count rejects ' + id + ' (400)', () => assert.equal(c.status, 400)); }
console.log(n + ' checks, ' + bad + ' failed'); process.exit(bad ? 1 : 0);
