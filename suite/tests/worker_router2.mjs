// router2 Worker tests (tuning) (offline: stub AI binding, mock D1 + Turnstile; no network). usage: node worker_router1.mjs OLD_TREE(10d) NEW_TREE(router1)
import fs from 'node:fs'; import path from 'node:path'; import { createRequire } from 'node:module'; import assert from 'node:assert/strict';
import { loadWorker, makeEnv, installFetch } from './browser/mock.mjs';
const [OLDT, NEWT] = process.argv.slice(2).map((p) => path.resolve(p)); const require = createRequire(import.meta.url);
const OW = await loadWorker(OLDT), W = await loadWorker(NEWT);
const HOST = 'https://preview.kicktip.pages.dev', PROD = 'https://kicktipmedia.com';
let n = 0, bad = 0; const chk = async (k, f) => { n++; try { await f(); console.log('PASS ' + k); } catch (e) { bad++; console.log('FAIL ' + k + ' :: ' + String(e.message).split('\n').slice(0, 5).join(' | ').slice(0, 500)); } };
const req = (p, o = {}, host = HOST) => new Request(host + p, { method: o.method || 'GET', headers: Object.assign({ 'CF-Connecting-IP': o.ip || '203.0.113.9' }, o.h || {}), body: o.body });
const post = (p, body, h = {}, host = HOST, ip) => req(p, { method: 'POST', ip, h: Object.assign({ Origin: host, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin' }, h), body: typeof body === 'string' ? body : JSON.stringify(body) }, host);
const ROUTE = (tool, params) => JSON.stringify({ v: 2, status: 'ok', calls: [{ tool, params }] });
const ANSWER = JSON.stringify({ v: 1, mode: 'home', status: 'ok', scenarios: [{ label: 'A', wins_out: ['BYU Cougars'] }] });
// stub AI: first call = router when the system prompt is the router's; scripted by `mode`
function stubAI(script, st) { return { run: async (model, input) => { const sys = input.messages[0].content, isRouter = /KickTip router/.test(sys); st.ai_calls.push([model, JSON.stringify(input)]); st.kinds = (st.kinds || []).concat(isRouter ? 'router' : 'answer');
  if (isRouter) { const s = typeof script === 'function' ? script(input) : script; if (s === 'hang') return new Promise(() => {}); if (s === 'throw') throw new Error('boom'); return { response: s }; } return { response: ANSWER }; } }; }
const mk = (script, over = {}, WW = W) => { const E = makeEnv(WW, over); installFetch(E.st); E.env.AI = stubAI(script, E.st); return E; };
const ask = async (E, text, extra = {}, host = HOST, WW = W) => { const r = await WW.fetch(post('/api/ask', Object.assign({ text, mode: 'home', cf_turnstile: 'good' }, extra), {}, host), E.env); const j = await r.json(); delete j.diag; return { s: r.status, j }; };
const rateN = (E) => E.db.log.filter((x) => x.k === 'rate').length;
const R = { router: true, rp: { m: 'home' } }, ON = { AI_ROUTER: 'on' };

const OK = (out, text, extra) => async () => { const E = mk(out, ON); const r = await ask(E, text, extra || R); return { E, r }; };
const routed = async (name, out, text, calls, rp) => chk('router2: ' + name, async () => { const E = mk(out, ON); const r = await ask(E, text, rp || R); assert.equal(r.j.source, 'router', JSON.stringify(r.j)); assert.deepEqual(r.j.route.calls, calls); assert.deepEqual(E.st.kinds, ['router'], 'one model call'); assert.equal(rateN(E), 1, 'one count'); });
const falls = async (name, out, text, rp) => chk('router2: ' + name, async () => { const E = mk(out, ON); const r = await ask(E, text, rp || R); assert.equal(r.j.source, 'model', JSON.stringify(r.j)); assert.equal(r.j.rt, 'error'); assert.deepEqual(E.st.kinds, ['router', 'answer'], 'falls through to the unchanged answer call'); assert.equal(rateN(E), 1, 'still ONE count'); });
// QA's exact failing questions, with the stub returning the string shapes the real model returned
await routed('QA: "compare Utah and BYU" teams:"Utah,BYU"', ROUTE('team_compare', { teams: 'Utah,BYU', aspect: 'all' }), 'compare Utah and BYU', [{ tool: 'team_compare', params: { teams: ['Utah', 'BYU'], aspect: 'all' } }]);
await routed('QA: "Utah record vs BYU" teams:"Utah vs BYU"', ROUTE('team_compare', { teams: 'Utah vs BYU', aspect: 'record' }), 'Utah record vs BYU', [{ tool: 'team_compare', params: { teams: ['Utah', 'BYU'], aspect: 'record' } }]);
await routed('QA: "what are the top 10 teams right now" n:"10"', ROUTE('rankings_list', { list: 'kicktip', n: '10' }), 'what are the top 10 teams right now', [{ tool: 'rankings_list', params: { list: 'kicktip', n: 10 } }]);
await routed('teams "Utah and BYU"', ROUTE('team_compare', { teams: 'Utah and BYU' }), 'Utah and BYU', [{ tool: 'team_compare', params: { teams: ['Utah', 'BYU'] } }]);
await routed('teams "Utah, BYU" with spaces', ROUTE('team_compare', { teams: 'Utah, BYU' }), 'how do Utah and BYU compare', [{ tool: 'team_compare', params: { teams: ['Utah', 'BYU'] } }]);
await routed('teams "Utah versus BYU"', ROUTE('head_to_head', { teams: 'Utah versus BYU' }), 'Utah versus BYU', [{ tool: 'head_to_head', params: { teams: ['Utah', 'BYU'] } }]);
await routed('a school name that contains no separator stays whole ("Iowa State")', ROUTE('team_compare', { teams: 'Iowa State, BYU' }), 'compare Iowa State and BYU', [{ tool: 'team_compare', params: { teams: ['Iowa State', 'BYU'] } }]);
await routed('team as a one-item array', ROUTE('team_snapshot', { team: ['Utah'] }), 'How is Utah doing?', [{ tool: 'team_snapshot', params: { team: 'Utah' } }]);
await routed('array teams still fine', ROUTE('team_compare', { teams: ['Utah', 'BYU'] }), 'compare Utah and BYU', [{ tool: 'team_compare', params: { teams: ['Utah', 'BYU'] } }]);
await routed('n:10 number still fine; n typed as a word is accepted when the word is typed', ROUTE('rankings_list', { n: 10 }), 'top ten teams', [{ tool: 'rankings_list', params: { n: 10 } }]);
await routed('numeric string n that the visitor did NOT type is dropped (default applies)', ROUTE('rankings_list', { n: '10' }), 'who are the best teams', [{ tool: 'rankings_list', params: {} }]);
await falls('string teams with an untyped team (Texas)', ROUTE('team_compare', { teams: 'Utah,Texas' }), 'compare Utah and BYU');
await falls('string teams with betting-ish junk part', ROUTE('team_compare', { teams: 'Utah,BYU,anything' }), 'compare Utah and BYU');
await falls('teams string: three names for a max-2 tool', ROUTE('team_compare', { teams: 'Utah, BYU, Utah vs Texas Tech' }), 'compare Utah and BYU and Texas Tech');
await falls('teams: more than the list max', ROUTE('tiebreak_explain', { conference: 'Big 12', teams: Array(9).fill('Utah') }), 'how does the Big 12 break ties for Utah');
await falls('n:"abc"', ROUTE('rankings_list', { n: 'abc' }), 'top 10 teams');
await falls('n:"100" (out of range)', ROUTE('rankings_list', { n: '100' }), 'top 100 teams');
await falls('n:"1e1"', ROUTE('rankings_list', { n: '1e1' }), 'top 10 teams');
await falls('n:"10.5"', ROUTE('rankings_list', { n: '10.5' }), 'top 10 teams');
await falls('enum values stay closed (aspect "Record " is rejected)', ROUTE('team_compare', { teams: ['Utah', 'BYU'], aspect: 'Record ' }), 'compare Utah and BYU');
// LOW (a): a param the tool does not have -> fall through
await falls('extra param conference on quality_wins (QA: Big 12 quality wins)', ROUTE('quality_wins', { conference: 'Big 12' }), 'which Big 12 teams have the most quality wins');
await falls('extra team param on rankings_list-like tool without it (slate_this_week team)', ROUTE('slate_this_week', { team: 'Utah' }), 'what games does Utah play this week');
await routed('empty / null / false extras are ignored', ROUTE('quality_wins', { team: 'Utah', conference: '', foo: null, bar: false, baz: [] }), 'Utah quality wins', [{ tool: 'quality_wins', params: { team: 'Utah' } }]);
// LOW (b): compare-style picks keep both teams
await falls('team_compare with one team', ROUTE('team_compare', { teams: ['Utah'] }), 'compare Utah and BYU');
await falls('path_compare with one team', ROUTE('path_compare', { teams: 'Utah', goal: 'playoff' }), 'compare Utah and BYU path to the playoff');
await falls('head_to_head, one team, no wins/losses view', ROUTE('head_to_head', { teams: ['Alabama'] }), 'Alabama vs Alabama');
await routed('head_to_head one team with view losses stays valid ("Who beat Alabama?")', ROUTE('head_to_head', { teams: ['Alabama'], view: 'losses' }), 'Who beat Alabama?', [{ tool: 'head_to_head', params: { teams: ['Alabama'], view: 'losses' } }]);
await chk('router2: team_compare with no teams stays rt:none (as in router1b)', async () => { const E = mk(ROUTE('team_compare', {}), ON); const r = await ask(E, 'Compare things', R); assert.equal(r.j.rt, 'none'); });
// prompt: array/number hint
await chk('router2: prompt tells the model teams is an ARRAY and n is a NUMBER, with a tiny example', async () => {
  const E = mk(ROUTE('team_snapshot', { team: 'Utah' }), ON); await ask(E, 'How is Utah doing?', R); const sys = JSON.parse(E.st.ai_calls[0][1]).messages[0].content;
  assert.match(sys, /teams is a JSON ARRAY of team names, e\.g\. "teams":\["Utah","BYU"\]/); assert.match(sys, /"n":10 \(never a string\)/); assert.match(sys, /\bteams=ARRAY of team names/); assert.match(sys, /n=NUMBER 1-25, only if typed/);
  assert.ok(sys.length < 9500, 'prompt length ' + sys.length); assert.ok(!/ccg_matchup|team_trend/.test(sys));
});
await chk('router2: only the 19 ids; dark tool names still rejected even with string params', async () => { for (const t of ['ccg_matchup', 'team_trend']) { const E = mk(ROUTE(t, { teams: 'Utah,BYU', team: 'Utah', n: '5' }), ON); const r = await ask(E, 'Utah vs BYU trend', R); assert.equal(r.j.rt, 'error', t); } });
// LOW (f): the Worker gate
await chk('router2: Worker refuses wintotal / wins over N evasions locally (no model call), flag on and off', async () => {
  const bad = ['BYU wintotal over 9.5', 'Utah wintotal over 9', 'BYU wintotals', 'BYU wins over 9', 'BYU wins over 9.5', 'BYU wins under 9.5', 'will BYU win over 9 games', 'Utah win total over 9.5', 'Utah win total o/u 9'];
  for (const over of [ON, {}]) for (const q of bad) { const E = mk(ROUTE('team_snapshot', { team: 'Utah' }), over); const r = await ask(E, q, R); assert.equal(r.j.source, 'local', q); assert.match(JSON.stringify(r.j.interpretation), /betting_or_gambling_request/, q); assert.equal(E.st.ai_calls.length, 0, q); }
});
await chk('router2: Worker still allows bare "Utah win total", "Utah wintotal" and normal questions', async () => {
  for (const q of ['Utah win total', 'Utah wintotal', 'who wins over 9 ranked teams', 'Utah wins over Texas', 'Who wins the Big 12?', 'How many wins will Utah finish with?', 'who has the most wins over top 25 teams', 'What does Utah need to win over BYU?']) { const E = mk(ROUTE('team_snapshot', { team: 'Utah' }), ON); const r = await ask(E, q, R); assert.notEqual(r.j.source, 'local', q); assert.ok(E.st.ai_calls.length >= 1, q); }
});
await chk('router2: model OUTPUT with a wintotal / wins over market string is refused, never routed', async () => { for (const out of [ROUTE('team_snapshot', { team: 'Utah (wintotal over 9.5)' }), '{"status":"none","note":"BYU wins over 9"}']) { const E = mk(out, ON); const r = await ask(E, 'How is Utah doing?', R); assert.equal(r.j.source, 'local'); assert.deepEqual(E.st.kinds, ['router']); } });
console.log(`${n} checks, ${bad} failed`); process.exit(bad ? 1 : 0);
