// Offline tests for the accounts Worker (build/site/_worker.js): mock D1 + mock Google. Run: node tests/worker_test.mjs
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import { pathToFileURL, fileURLToPath } from 'node:url';
import { makeDB, makeGoogle } from './mockd1.mjs';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ktw-')); const wfile = path.join(tmp, 'worker.mjs'); fs.copyFileSync(path.join(root, 'build/site/_worker.js'), wfile);
const W = (await import(pathToFileURL(wfile).href)).default, T = W._t;
let pass = 0, fail = 0; const bad = [];
function ok(c, m) { if (c) pass++; else { fail++; bad.push(m); console.log('FAIL', m); } }
const CID = 'cid.apps.example', CSEC = 'csecret', SS = 'x'.repeat(48), ORIGIN = 'https://kicktipmedia.com';
const google = makeGoogle({ clientId: CID, clientSecret: CSEC }); globalThis.fetch = google.fetch;
function mkEnv() { return { DB: makeDB(T.SQL), GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: CSEC, SESSION_SECRET: SS, ASSETS: { fetch: async (r) => new Response('asset:' + new URL(r.url).pathname) } }; }
let ip = 0; const nextIp = () => '203.0.113.' + (++ip);
const call = (env, method, p, o = {}) => W.fetch(new Request(ORIGIN + p, { method, headers: Object.assign({ 'CF-Connecting-IP': o.ip || '198.51.100.1' }, o.headers || {}), body: o.body }), env);
const jar = (res) => Object.fromEntries((res.headers.getSetCookie ? res.headers.getSetCookie() : []).map((c) => [c.split('=')[0], c]));
const val = (c) => c.split(';')[0].split('=').slice(1).join('=');
const slugs = [...T.TEAM_SLUGS];
async function signIn(env, claims, ipx) {
  const s = await call(env, 'GET', '/api/auth/google/start?r=/team/' + slugs[0] + '/', { ip: ipx || nextIp() });
  const loc = new URL(s.headers.get('Location')), oc = jar(s)[T.OAUTH_COOKIE];
  const code = google.issue(loc.href, claims);
  const cb = await call(env, 'GET', '/api/auth/google/callback?code=' + code + '&state=' + loc.searchParams.get('state'), { headers: { Cookie: T.OAUTH_COOKIE + '=' + val(oc) } });
  const sc = jar(cb)[T.SESSION_COOKIE];
  return { s, loc, oc, cb, sc, cookie: sc ? T.SESSION_COOKIE + '=' + val(sc) : '' };
}
const PUT = (env, cookie, body, h = {}) => call(env, 'PUT', '/api/teams', { headers: Object.assign({ Cookie: cookie, Origin: ORIGIN, 'Content-Type': 'application/json' }, h), body: typeof body === 'string' ? body : JSON.stringify(body) });

// ---- unconfigured: nothing breaks, sign-in just reports it
{ const none = { DB: null }; let r = await call(none, 'GET', '/api/auth/session'); let j = await r.json(); ok(r.status === 200 && j.configured === false && j.signedIn === false, 'unconfigured session -> configured:false');
  r = await call(none, 'GET', '/api/auth/google/start'); ok(r.status === 302 && r.headers.get('Location') === '/?signin=error', 'unconfigured start -> redirect to /?signin=error, never raw JSON (D4)');
  const half = Object.assign(mkEnv(), { GOOGLE_CLIENT_SECRET: '' }); j = await (await call(half, 'GET', '/api/auth/session')).json(); ok(j.configured === false, 'missing one secret -> configured:false');
  const short = Object.assign(mkEnv(), { SESSION_SECRET: 'short' }); j = await (await call(short, 'GET', '/api/auth/session')).json(); ok(j.configured === false, 'SESSION_SECRET under 32 chars -> not configured');
  r = await call(none, 'GET', '/team/x/'); ok(r.status === 404, 'non-api path with no ASSETS -> 404 (no crash)'); }
// ---- routing
{ const env = mkEnv(); let r = await call(env, 'GET', '/some/page/'); ok(await r.text() === 'asset:/some/page/', 'non-/api paths go to ASSETS');
  r = await call(env, 'GET', '/api/nope'); ok(r.status === 404, 'unknown api route 404'); r = await call(env, 'DELETE', '/api/teams'); ok(r.status === 405, 'wrong method 405');
  r = await call(env, 'GET', '/api/auth/session'); ok(r.headers.get('Cache-Control') === 'no-store', 'api responses are no-store'); }
// ---- start: state + PKCE + cookie attributes, open-redirect hardening, 10/hr cap
{ const env = mkEnv(); const r = await call(env, 'GET', '/api/auth/google/start?r=/conference/big-12/', { ip: nextIp() });
  ok(r.status === 302, 'start redirects'); const u = new URL(r.headers.get('Location'));
  ok(u.origin + u.pathname === 'https://accounts.google.com/o/oauth2/v2/auth', 'redirect goes to Google authorization endpoint');
  ok(u.searchParams.get('client_id') === CID && u.searchParams.get('redirect_uri') === ORIGIN + '/api/auth/google/callback', 'client id + exact redirect_uri');
  ok(u.searchParams.get('response_type') === 'code' && u.searchParams.get('code_challenge_method') === 'S256' && (u.searchParams.get('code_challenge') || '').length >= 43, 'PKCE S256 challenge present');
  ok((u.searchParams.get('state') || '').length >= 40 && (u.searchParams.get('nonce') || '').length >= 20, 'state and nonce are long random values');
  ok(u.searchParams.get('scope') === 'openid email profile', 'scope is openid email profile only');
  const c = jar(r)[T.OAUTH_COOKIE]; ok(c && /Secure/.test(c) && /HttpOnly/.test(c) && /SameSite=Lax/.test(c) && /Path=\//.test(c) && !/Domain=/i.test(c) && /Max-Age=600/.test(c), '__Host- state cookie attributes (Secure, HttpOnly, Lax, Path=/, no Domain, 10 min)');
  ok(c.startsWith('__Host-'), 'state cookie has the __Host- prefix');
  const a = await call(env, 'GET', '/api/auth/google/start', { ip: nextIp() }), b = await call(env, 'GET', '/api/auth/google/start', { ip: nextIp() });
  ok(new URL(a.headers.get('Location')).searchParams.get('state') !== new URL(b.headers.get('Location')).searchParams.get('state'), 'state is different every time');
  for (const bad of ['//evil.example', 'https://evil.example/', '/\\evil.example', '/a/../b', 'javascript:alert(1)', '/x?y=1', '/' + 'a'.repeat(300), '/a//b']) ok(T.safePath(bad) === '/', 'safePath rejects ' + bad.slice(0, 30));
  ok(T.safePath('/team/utah/') === '/team/utah/' && T.safePath('/') === '/', 'safePath keeps normal site paths');
  const x = await call(env, 'GET', '/api/auth/google/start', { ip: nextIp(), headers: { 'Sec-Fetch-Site': 'cross-site' } }); ok(x.status === 403, 'start refuses a cross-site request');
  const same = '192.0.2.9'; let codes = []; for (let i = 0; i < 12; i++) codes.push((await call(env, 'GET', '/api/auth/google/start', { ip: same })).status);
  ok(codes.slice(0, 10).every((s) => s === 302) && codes[10] === 429 && codes[11] === 429, 'sign-in start capped at 10 per hour per visitor (11th and 12th get 429): ' + codes.join(','));
  const other = await call(env, 'GET', '/api/auth/google/start', { ip: '192.0.2.77' }); ok(other.status === 302, 'a different visitor is not affected by the cap'); }
// ---- callback: happy path, then every way to fail
{ const env = mkEnv(); const t = await signIn(env, {});
  ok(t.cb.status === 302 && t.cb.headers.get('Location') === '/team/' + slugs[0] + '/?signin=ok', 'callback success redirects back to the page with ?signin=ok');
  ok(t.sc && /Secure/.test(t.sc) && /HttpOnly/.test(t.sc) && /SameSite=Lax/.test(t.sc) && /Path=\//.test(t.sc) && !/Domain=/i.test(t.sc) && t.sc.startsWith('__Host-kt_session=') && /Max-Age=2592000/.test(t.sc), '__Host- session cookie attributes');
  ok(/Max-Age=0/.test(jar(t.cb)[T.OAUTH_COOKIE] || ''), 'state cookie is cleared after the callback');
  ok(env.DB.users.length === 1 && env.DB.users[0].google_sub === '1000000001' && env.DB.users[0].email === 'sam@example.com' && env.DB.users[0].display_name === 'Sam Rivera', 'user row holds sub, email, name');
  ok(Object.keys(env.DB.users[0]).sort().join() === 'created_at,display_name,email,google_sub,id,sess_ver', 'user row has no other fields');
  const sj = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: t.cookie } })).json(); ok(sj.signedIn && sj.email === 'sam@example.com' && sj.initial === 'S' && sj.cap === 50, 'session endpoint reports the user, initial and cap 50');
  const again = await signIn(env, {}); ok(env.DB.users.length === 1 && again.sc, 'signing in again re-uses the same user (keyed on google sub)');
  // session cookie signing
  const v = val(jar(t.cb)[T.SESSION_COOKIE]); const flip = v.slice(0, -2) + (v.slice(-2) === 'AA' ? 'BB' : 'AA');
  let j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + flip } })).json(); ok(!j.signedIn, 'tampered signature -> signed out');
  const parts = v.split('.'); const forged = parts[0] + '.' + Buffer.from(JSON.stringify({ u: 1, ver: 1, exp: 9999999999 })).toString('base64url') + '.' + parts[2];
  j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + forged } })).json(); ok(!j.signedIn, 'forged payload with old signature -> signed out');
  const otherSecret = await T.seal('y'.repeat(48), { u: 1, ver: 1, exp: 9999999999 }); j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + otherSecret } })).json(); ok(!j.signedIn, 'cookie signed with another secret -> signed out');
  const old = await T.seal(SS, { u: 1, ver: 1, exp: 1000 }); j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + old } })).json(); ok(!j.signedIn, 'expired session -> signed out');
  for (const junk of ['', 'abc', 'v1..', 'v1.a.b.c', 'v2.a.b', 'x'.repeat(2000), '%%%', 'v1.' + 'a'.repeat(10) + '.']) { j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + junk } })).json(); ok(!j.signedIn, 'junk cookie "' + junk.slice(0, 12) + '" -> signed out, no crash'); }
  const nullBody = await T.seal(SS, null); ok((await T.unseal(SS, nullBody)) === null, 'sealed null is rejected');
  const un = await T.seal(SS, { u: 'x', ver: 1, exp: 9999999999 }); j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: T.SESSION_COOKIE + '=' + un } })).json(); ok(!j.signedIn, 'session with non-integer user id -> signed out');
  env.DB.users[0].sess_ver = 2; j = await (await call(env, 'GET', '/api/auth/session', { headers: { Cookie: t.cookie } })).json(); ok(!j.signedIn, 'bumping sess_ver revokes existing sessions'); }
{ // state / CSRF / replay / denial / bad tokens
  const env = mkEnv(); const start = async () => { const s = await call(env, 'GET', '/api/auth/google/start', { ip: nextIp() }); return { loc: new URL(s.headers.get('Location')), oc: val(jar(s)[T.OAUTH_COOKIE]) }; };
  const cbk = (q, oc) => call(env, 'GET', '/api/auth/google/callback?' + q, { headers: oc ? { Cookie: T.OAUTH_COOKIE + '=' + oc } : {} });
  let a = await start(); let code = google.issue(a.loc.href, {});
  let r = await cbk('code=' + code + '&state=WRONG', a.oc); ok(r.headers.get('Location').includes('signin=error') && !jar(r)[T.SESSION_COOKIE], 'wrong state -> error, no session');
  r = await cbk('code=' + code + '&state=' + a.loc.searchParams.get('state'), ''); ok(r.headers.get('Location').includes('signin=error') && !jar(r)[T.SESSION_COOKIE], 'missing state cookie (login CSRF) -> error');
  const b = await start(); r = await cbk('code=' + code + '&state=' + a.loc.searchParams.get('state'), b.oc); ok(r.headers.get('Location').includes('signin=error'), 'state cookie from another start -> error');
  const tamp = a.oc.slice(0, -3) + 'AAA'; r = await cbk('code=' + code + '&state=' + a.loc.searchParams.get('state'), tamp); ok(r.headers.get('Location').includes('signin=error'), 'tampered state cookie -> error');
  r = await cbk('code=' + code + '&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=ok'), 'right state + cookie -> ok (control)');
  r = await cbk('code=' + code + '&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error'), 'replaying the same code is refused by Google (single use) -> error');
  a = await start(); r = await cbk('error=access_denied&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=cancelled'), 'access_denied -> cancelled');
  a = await start(); r = await cbk('error=server_error&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error'), 'other provider error -> error');
  a = await start(); r = await cbk('state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error'), 'no code -> error');
  a = await start(); code = google.issue(a.loc.href, {}); r = await cbk('code=' + code + 'zzz&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error'), 'unknown code -> error (Google rejects)');
  a = await start(); google.fail = true; r = await cbk('code=' + google.issue(a.loc.href, {}) + '&state=' + a.loc.searchParams.get('state'), a.oc); google.fail = false; ok(r.headers.get('Location').includes('signin=error'), 'token endpoint 500 -> error');
  const claimCases = [['wrong audience', { aud: 'other' }], ['wrong issuer', { iss: 'https://evil.example' }], ['expired token', { exp: 100 }], ['wrong nonce', { nonce: 'nope' }], ['unverified email', { email_verified: false }], ['no sub', { sub: '' }], ['non-string email', { email: 5 }], ['bad email', { email: 'not-an-email' }]];
  for (const [n, cl] of claimCases) { a = await start(); r = await cbk('code=' + google.issue(a.loc.href, cl) + '&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error') && !jar(r)[T.SESSION_COOKIE], 'ID token with ' + n + ' -> error, no session'); }
  ok(env.DB.users.length === 1, 'only the one valid sign-in created a user (' + env.DB.users.length + ')');
  const exp = await T.seal(SS, { s: 'S', v: 'V', n: 'N', r: '/', t: Date.now() - 11 * 60000 }); r = await cbk('code=c&state=S', exp); ok(r.headers.get('Location').includes('signin=error'), 'state cookie older than 10 minutes -> error');
  const ev = await T.seal(SS, { s: 'S', v: 'V', n: 'N', r: '//evil.example', t: Date.now() }); r = await cbk('error=access_denied&state=S', ev); ok(r.headers.get('Location') === '/?signin=cancelled', 'open-redirect value stored in state cookie falls back to /');
  a = await start(); env.DB.failNext = true; r = await cbk('code=' + google.issue(a.loc.href, {}) + '&state=' + a.loc.searchParams.get('state'), a.oc); ok(r.headers.get('Location').includes('signin=error'), 'D1 failure during sign-in -> error, not a 500'); }
// ---- teams: Origin check, validation, caps, rate limit
{ const env = mkEnv(); const t = await signIn(env, {}); const C = t.cookie;
  let r = await call(env, 'GET', '/api/teams'); ok(r.status === 401, 'GET /api/teams signed out -> 401');
  r = await call(env, 'PUT', '/api/teams', { headers: { Origin: ORIGIN, 'Content-Type': 'application/json' }, body: '{"teams":[]}' }); ok(r.status === 401, 'PUT signed out -> 401');
  r = await call(env, 'PUT', '/api/teams', { headers: { Cookie: C, 'Content-Type': 'application/json' }, body: '{"teams":[]}' }); ok(r.status === 403, 'PUT without Origin -> 403');
  r = await PUT(env, C, { teams: [] }, { Origin: 'https://evil.example' }); ok(r.status === 403, 'PUT from another origin -> 403');
  r = await PUT(env, C, { teams: [] }, { Origin: ORIGIN + '.evil.example' }); ok(r.status === 403, 'PUT from a look-alike origin -> 403');
  r = await PUT(env, C, { teams: [] }, { Origin: 'http://kicktipmedia.com' }); ok(r.status === 403, 'PUT from http origin -> 403');
  r = await call(env, 'GET', '/api/teams', { headers: { Cookie: C, 'Sec-Fetch-Site': 'cross-site' } }); ok(r.status === 403, 'GET with cross-site Sec-Fetch-Site -> 403');
  const [a, b2, c3] = slugs; r = await PUT(env, C, { teams: [a, b2, c3], lead: { [a]: 'c', [c3]: 'w' } }); let j = await r.json(); ok(r.status === 200 && j.teams.join() === [a, b2, c3].join() && j.lead[a] === 'c' && j.lead[b2] === 'p' && j.lead[c3] === 'w', 'valid save stores order + lead (default p)');
  j = await (await call(env, 'GET', '/api/teams', { headers: { Cookie: C } })).json(); ok(j.teams.join() === [a, b2, c3].join() && j.lead[c3] === 'w' && j.cap === 50, 'GET returns what was saved');
  r = await PUT(env, C, { teams: [c3, a] }); j = await r.json(); ok(j.teams.join() === [c3, a].join() && env.DB.teams.length === 2, 'PUT replaces the whole list');
  const sets = (n) => slugs.slice(0, n);
  r = await PUT(env, C, { teams: sets(50) }); ok(r.status === 200 && env.DB.teams.length === 50, '50 teams accepted (the cap)');
  r = await PUT(env, C, { teams: sets(51) }); j = await r.json(); ok(r.status === 409 && j.error === 'cap' && j.cap === 50 && env.DB.teams.length === 50, '51 teams rejected 409 and the stored list is untouched');
  const cases = [['unknown slug', { teams: ['not-a-team'] }, 400], ['slug with path chars', { teams: ['../x'] }, 400], ['uppercase', { teams: [a.toUpperCase()] }, 400], ['constructor', { teams: ['constructor'] }, 400], ['__proto__', { teams: ['__proto__'] }, 400], ['duplicate', { teams: [a, a] }, 400], ['non-string', { teams: [1] }, 400], ['object entry', { teams: [{ a: 1 }] }, 400], ['teams not array', { teams: 'abc' }, 400], ['missing teams', {}, 400], ['extra field', { teams: [], admin: true }, 400], ['lead bad code', { teams: [a], lead: { [a]: 'x' } }, 400], ['lead key not in list', { teams: [a], lead: { [b2]: 'p' } }, 400], ['lead is array', { teams: [a], lead: [] }, 400], ['lead non-string', { teams: [a], lead: { [a]: 1 } }, 400], ['body is array', [], 400], ['body null', null, 400], ['body number', 5, 400]];
  for (const [n, body, st] of cases) { r = await PUT(env, C, body); ok(r.status === st, 'malformed: ' + n + ' -> ' + st + ' (got ' + r.status + ')'); }
  r = await PUT(env, C, '{"teams":[}'); ok(r.status === 400, 'malformed JSON -> 400'); r = await PUT(env, C, '{"teams":[],"lead":{"__proto__":{"p":1}}}'); ok(r.status === 400, '__proto__ lead key rejected');
  ok(({}).p === undefined, 'no prototype pollution');
  r = await PUT(env, C, '{"teams":[]}', { 'Content-Type': 'text/plain' }); ok(r.status === 415, 'wrong content type -> 415'); r = await PUT(env, C, '{"teams":["' + 'a'.repeat(9000) + '"]}'); ok(r.status === 413, 'oversized body -> 413');
  ok(env.DB.teams.length === 50, 'rejected requests never changed the stored list');
  env.DB.failNext = false; await PUT(env, C, { teams: [a] }); env.DB.log.length = 0; const before = env.DB.teams.slice(); const origBatch = env.DB.batch; env.DB.batch = async () => { throw new Error('x'); }; r = await PUT(env, C, { teams: [b2] }); env.DB.batch = origBatch; ok(r.status === 500 && env.DB.teams.length === before.length, 'store failure -> 500 JSON, list untouched');
  // rate limit: 60 saves per hour per user (the ones above already counted); count exactly from a fresh user
  const env2 = mkEnv(); const t2 = await signIn(env2, { sub: '2000000002', email: 'lee@example.com', name: '' }); let ok60 = 0, first429 = 0; for (let i = 1; i <= 62; i++) { const rr = await PUT(env2, t2.cookie, { teams: [slugs[i % 5]] }); if (rr.status === 200) ok60++; else if (!first429) first429 = i; }
  ok(ok60 === 60 && first429 === 61, 'saves capped at 60 per hour: ' + ok60 + ' ok, first refusal at #' + first429);
  const sj = await (await call(env2, 'GET', '/api/auth/session', { headers: { Cookie: t2.cookie } })).json(); ok(sj.initial === 'L', 'initial falls back to the email when there is no display name'); }
// ---- merge (server side of A4): union of device + account lists, account lead wins, cap respected
{ const env = mkEnv(); const t = await signIn(env, {}); const [a, b, c, d] = slugs;
  await PUT(env, t.cookie, { teams: [a, b], lead: { [a]: 'w' } });
  const server = await (await call(env, 'GET', '/api/teams', { headers: { Cookie: t.cookie } })).json(); const device = { teams: [b, c, d], lead: { [b]: 'c', [c]: 'b' } };
  const add = device.teams.filter((s) => !server.teams.includes(s)); const lead = Object.assign({}, device.lead, server.lead); const teams = server.teams.concat(add).slice(0, 50);
  const r = await PUT(env, t.cookie, { teams, lead: Object.fromEntries(Object.entries(lead).filter(([k]) => teams.includes(k))) }); const j = await r.json();
  ok(j.teams.join() === [a, b, c, d].join() && j.lead[a] === 'w' && j.lead[b] === 'p' && j.lead[c] === 'b', 'merge keeps the account order first, adds device teams, keeps lead choices'); }
// ---- logout + delete
{ const env = mkEnv(); let t = await signIn(env, {}); let r = await call(env, 'POST', '/api/auth/logout'); ok(r.status === 403, 'logout without Origin -> 403 (no cross-site logout)');
  r = await call(env, 'POST', '/api/auth/logout', { headers: { Origin: ORIGIN, Cookie: t.cookie } }); ok(r.status === 200 && /Max-Age=0/.test(jar(r)[T.SESSION_COOKIE] || ''), 'logout clears the cookie'); r = await call(env, 'GET', '/api/auth/logout'); ok(r.status === 405, 'logout is POST only');
  t = await signIn(env, {}, nextIp()); /* logout now revokes the old cookie, so sign in again */
  await PUT(env, t.cookie, { teams: [slugs[0]] });
  r = await call(env, 'POST', '/api/account/delete', { headers: { Cookie: t.cookie } }); ok(r.status === 403, 'delete without Origin -> 403');
  r = await call(env, 'POST', '/api/account/delete', { headers: { Cookie: t.cookie, Origin: ORIGIN } }); ok(r.status === 200 && env.DB.users.length === 0 && env.DB.teams.length === 0, 'delete removes the user and every saved team');
  r = await call(env, 'GET', '/api/auth/session', { headers: { Cookie: t.cookie } }); ok(!(await r.json()).signedIn, 'the old cookie no longer works after delete');
  const e3 = mkEnv(); const codes = []; for (let i = 0; i < 5; i++) { const s = await signIn(e3, { sub: 's' + i, email: 'u' + i + '@example.com' }, nextIp()); const rr = await call(e3, 'POST', '/api/account/delete', { ip: '192.0.2.50', headers: { Cookie: s.cookie, Origin: ORIGIN } }); codes.push(rr.status); }
  ok(codes.join() === '200,200,200,429,429', 'delete capped at 3 per day: ' + codes.join(',')); }
// ---- D2: logout revokes the session server side (sess_ver bump); D4: /start never answers raw JSON when D1 or its tables are missing
{ const env = mkEnv(); const a = await signIn(env, {}, nextIp()), b = { cookie: a.cookie };
  const v0 = env.DB.users[0].sess_ver; let r = await call(env, 'GET', '/api/auth/session', { headers: { Cookie: a.cookie } }); ok((await r.json()).signedIn, 'D2: signed in before logout');
  r = await call(env, 'POST', '/api/auth/logout', { headers: { Origin: ORIGIN, Cookie: a.cookie } });
  ok(r.status === 200 && env.DB.users[0].sess_ver === v0 + 1 && env.DB.log.includes(T.SQL.bumpSess), 'D2: logout bumps users.sess_ver by one');
  r = await call(env, 'GET', '/api/auth/session', { headers: { Cookie: b.cookie } }); ok(!(await r.json()).signedIn, 'D2: the logged-out cookie, replayed, is rejected (revoked server side, not just cleared in the browser)');
  r = await call(env, 'GET', '/api/teams', { headers: { Cookie: b.cookie } }); ok(r.status === 401, 'D2: the replayed cookie cannot read teams either (' + r.status + ')');
  const again = await call(env, 'POST', '/api/auth/logout', { headers: { Origin: ORIGIN, Cookie: b.cookie } }); ok(again.status === 200 && env.DB.users[0].sess_ver === v0 + 1, 'D2: logging out twice with the dead cookie does not bump again, still clears it');
  const nocookie = await call(env, 'POST', '/api/auth/logout', { headers: { Origin: ORIGIN } }); ok(nocookie.status === 200, 'D2: logout with no session is a harmless 200');
  // forced failure on the UPDATE: the cookie must NOT be cleared and the caller is told
  const e3 = mkEnv(); const s3 = await signIn(e3, {}, nextIp()); const prep = e3.DB.prepare.bind(e3.DB);
  e3.DB.prepare = (sql) => { const st = prep(sql); if (sql === T.SQL.bumpSess) { const run = st.bind.bind(st); st.bind = (...x) => { const b2 = run(...x); b2.run = async () => { throw new Error('forced'); }; return b2; }; } return st; };
  const f = await call(e3, 'POST', '/api/auth/logout', { headers: { Origin: ORIGIN, Cookie: s3.cookie } }); ok(f.status === 500 && !(jar(f)[T.SESSION_COOKIE]), 'D2: if the revoke fails, 500 and the cookie is not cleared (never claims signed out while the session works)'); }
{ const env = mkEnv(); env.DB.failNext = true; const r = await call(env, 'GET', '/api/auth/google/start', { ip: nextIp() }); ok(r.status === 302 && r.headers.get('Location') === '/?signin=error', 'D4: D1 failing (tables missing) -> redirect to /?signin=error, not raw JSON 500');
  const e2 = mkEnv(); delete e2.GOOGLE_CLIENT_ID; const r2 = await call(e2, 'GET', '/api/auth/google/start', { ip: nextIp() }); ok(r2.status === 302 && r2.headers.get('Location') === '/?signin=error', 'D4: missing secret -> redirect to /?signin=error');
  const e3 = mkEnv(); e3.DB.prepare = () => { throw new Error('no such table: rate_limits'); }; const r3 = await call(e3, 'GET', '/api/auth/google/start', { ip: nextIp() }); ok(r3.status === 302 && r3.headers.get('Location') === '/?signin=error', 'D4: prepare() throwing -> redirect');
  const r4 = await call(mkEnv(), 'GET', '/api/auth/session'); ok(r4.headers.get('content-type').includes('json'), 'D4: the session probe still answers JSON'); }
// ---- shipped file hygiene
{ const src = fs.readFileSync(path.join(root, 'build/site/_worker.js'), 'utf8'); ok(!/__TEAM_SLUGS__/.test(src), 'placeholder replaced'); ok(T.TEAM_SLUGS.size >= 130, 'team list injected (' + T.TEAM_SLUGS.size + ')');
  ok(!/console\.(log|error)/.test(src), 'no console output that could leak tokens'); ok(!/localStorage|document\./.test(src), 'no browser APIs'); }
console.log(`worker_test: ${pass} pass, ${fail} fail`); process.exit(fail ? 1 : 0);
