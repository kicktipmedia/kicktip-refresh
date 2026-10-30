/* KickTip Media - accounts Worker (Cloudflare Pages "advanced mode": this file ships as _worker.js at the zip root; _routes.json sends ONLY /api/* here, so pages and assets stay static).
   Bindings (Pages project > Settings): D1 database bound as DB; secrets GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET. Any missing -> sign-in reports "not configured" and nothing else changes.
   Flow: authorization code + PKCE (S256) + state + nonce, redirect_uri https://kicktipmedia.com/api/auth/google/callback. The code is exchanged server to server over HTTPS and the ID token comes straight from Google's token endpoint (claims verified: iss, aud, exp, nonce, email_verified). No script from any third party is ever loaded.
   Session: stateless HMAC-SHA-256 signed value in a __Host- cookie (Secure, HttpOnly, SameSite=Lax, Path=/), 30 days, revoked by bumping users.sess_ver: logout does that (one tap signs the account out on EVERY device, because the value is stateless and there is no per-device session row), and deleting the account removes the row. Unsafe methods require Origin === https://kicktipmedia.com.
   Stored: google sub, email, optional display name, created_at, followed teams + lead choice. Nothing else. */
const ORIGIN = 'https://kicktipmedia.com';
const REDIRECT_URI = ORIGIN + '/api/auth/google/callback';
const SESSION_COOKIE = '__Host-kt_session', OAUTH_COOKIE = '__Host-kt_oauth';
const SESSION_TTL = 30 * 86400, OAUTH_TTL = 600, CAP_ACCOUNT = 50;
const EMAIL_LINK_TTL_SECONDS = __EMAIL_LINK_TTL_SECONDS__;   /* phase 3 (not used by any route yet): magic-link lifetime, single use; ONE value, set in src/site_config.py and injected by build.py */
const LIMITS = { signin: [10, 3600], save: [60, 3600], del: [3, 86400] };   /* [max, window seconds] */
const TEAM_SLUGS = new Set(__TEAM_SLUGS__);
const LEADS = new Set(['p', 'c', 'w', 'b']);
const SLUGRE = /^[a-z0-9][a-z0-9-]{0,47}$/;
const SQL = {
  upsertUser: 'INSERT INTO users(google_sub,email,display_name,created_at) VALUES(?1,?2,?3,?4) ON CONFLICT(google_sub) DO UPDATE SET email=excluded.email, display_name=excluded.display_name RETURNING id, sess_ver',
  userById: 'SELECT id, email, display_name, sess_ver FROM users WHERE id=?1',
  teams: 'SELECT slug, lead FROM saved_teams WHERE user_id=?1 ORDER BY position',
  clearTeams: 'DELETE FROM saved_teams WHERE user_id=?1',
  addTeam: 'INSERT INTO saved_teams(user_id,slug,lead,position,added_at) VALUES(?1,?2,?3,?4,?5)',
  bumpSess: 'UPDATE users SET sess_ver=sess_ver+1 WHERE id=?1',
  deleteUser: 'DELETE FROM users WHERE id=?1',
  rate: 'INSERT INTO rate_limits(k,w,n,exp) VALUES(?1,?2,1,?3) ON CONFLICT(k,w) DO UPDATE SET n=n+1 RETURNING n',
  sweep: 'DELETE FROM rate_limits WHERE exp<?1'
};
const enc = new TextEncoder(), dec = new TextDecoder();

/* ---------- small helpers ---------- */
function b64u(buf) { let s = ''; const a = new Uint8Array(buf); for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function unb64u(s) { s = String(s).replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const bin = atob(s), a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return a; }
function rnd(n) { return b64u(crypto.getRandomValues(new Uint8Array(n))); }
const hkey = (secret) => crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
async function sign(secret, text) { return b64u(await crypto.subtle.sign('HMAC', await hkey(secret), enc.encode(text))); }
async function verifySig(secret, text, sig) { try { return await crypto.subtle.verify('HMAC', await hkey(secret), unb64u(sig), enc.encode(text)); } catch (e) { return false; } }
async function seal(secret, obj) { const p = 'v1.' + b64u(enc.encode(JSON.stringify(obj))); return p + '.' + await sign(secret, p); }
async function unseal(secret, tok) {   /* -> object or null (bad shape, bad signature, bad JSON) */
  if (typeof tok !== 'string' || tok.length > 1024) return null; const parts = tok.split('.'); if (parts.length !== 3 || parts[0] !== 'v1') return null;
  if (!(await verifySig(secret, parts[0] + '.' + parts[1], parts[2]))) return null;
  try { const o = JSON.parse(dec.decode(unb64u(parts[1]))); return o && typeof o === 'object' ? o : null; } catch (e) { return null; }
}
function cookies(req) { const o = {}; (req.headers.get('Cookie') || '').split(';').forEach((c) => { const i = c.indexOf('='); if (i > 0) o[c.slice(0, i).trim()] = c.slice(i + 1).trim(); }); return o; }
function setCookie(name, value, maxAge) { return `${name}=${value}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=${maxAge}`; }
const SEC = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'" };
function json(obj, status, extra) { const h = new Headers(Object.assign({ 'Content-Type': 'application/json; charset=utf-8', Vary: 'Cookie' }, SEC, extra || {})); return new Response(JSON.stringify(obj), { status: status || 200, headers: h }); }
function redirect(url, cookiesToSet) { const h = new Headers(Object.assign({ Location: url }, SEC)); (cookiesToSet || []).forEach((c) => h.append('Set-Cookie', c)); return new Response(null, { status: 302, headers: h }); }
const configured = (env) => !!(env && env.DB && env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET && env.SESSION_SECRET && String(env.SESSION_SECRET).length >= 32);
function safePath(r) { return typeof r === 'string' && r.length <= 200 && /^\/[A-Za-z0-9\-._~\/]*$/.test(r) && r.indexOf('//') < 0 && r.indexOf('..') < 0 ? r : '/'; }
function sameOriginRead(req) { const f = req.headers.get('Sec-Fetch-Site'); return !f || f === 'same-origin' || f === 'none'; }
function originOk(req) { return req.headers.get('Origin') === ORIGIN; }
const clean = (s, max) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f<>]/g, '').trim().slice(0, max);

/* ---------- rate limit (fixed window in D1; key is a keyed hash, never an address) ---------- */
async function hit(env, kind, who, now) {
  const [max, win] = LIMITS[kind], w = Math.floor(now / 1000 / win), k = kind + ':' + (await sign(env.SESSION_SECRET, 'rl|' + who)).slice(0, 22);
  const r = await env.DB.prepare(SQL.rate).bind(k, w, Math.floor(now / 1000) + win * 2).first();
  if (r && r.n === 1 && now % 20 === 0) { try { await env.DB.prepare(SQL.sweep).bind(Math.floor(now / 1000)).run(); } catch (e) { /* sweeping is housekeeping only */ } }
  return !!r && r.n <= max;
}
const visitor = (req) => req.headers.get('CF-Connecting-IP') || req.headers.get('X-Forwarded-For') || 'unknown';

/* ---------- session ---------- */
async function currentUser(req, env, now) {
  const tok = cookies(req)[SESSION_COOKIE]; if (!tok) return null; const s = await unseal(env.SESSION_SECRET, tok);
  if (!s || !Number.isInteger(s.u) || !Number.isInteger(s.ver) || !Number.isFinite(s.exp) || s.exp * 1000 < now) return null;
  const u = await env.DB.prepare(SQL.userById).bind(s.u).first(); if (!u || u.sess_ver !== s.ver) return null; return u;
}
const initial = (u) => (clean(u.display_name, 80) || u.email || '?').trim().charAt(0).toUpperCase() || '?';
const dropCookies = () => [setCookie(SESSION_COOKIE, '', 0)];

/* ---------- handlers ---------- */
const toError = () => redirect('/?signin=error');   /* the Sign in button is a full-page navigation, so every failure of /start that is OUR fault lands on the page with the sheet's error message, never on raw JSON */
async function start(req, env, url, now) {
  if (!configured(env)) return toError();
  if (!sameOriginRead(req)) return json({ error: 'cross_site' }, 403);
  let allowed; try { allowed = await hit(env, 'signin', visitor(req), now); } catch (e) { return toError(); }   /* D1 unreachable or migrations not applied */
  if (!allowed) return json({ error: 'rate_limited' }, 429, { 'Retry-After': '3600' });
  const state = rnd(32), verifier = rnd(32), nonce = rnd(24), r = safePath(url.searchParams.get('r'));
  const challenge = b64u(await crypto.subtle.digest('SHA-256', enc.encode(verifier)));
  const cookie = setCookie(OAUTH_COOKIE, await seal(env.SESSION_SECRET, { s: state, v: verifier, n: nonce, r, t: now }), OAUTH_TTL);
  const q = new URLSearchParams({ client_id: env.GOOGLE_CLIENT_ID, redirect_uri: REDIRECT_URI, response_type: 'code', scope: 'openid email profile', state, nonce, code_challenge: challenge, code_challenge_method: 'S256', prompt: 'select_account' });
  return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + q.toString(), [cookie]);
}
async function callback(req, env, url, now) {
  if (!configured(env)) return json({ error: 'not_configured' }, 503);
  const jar = cookies(req), o = await unseal(env.SESSION_SECRET, jar[OAUTH_COOKIE]), kill = setCookie(OAUTH_COOKIE, '', 0);
  const back = (kind, r) => redirect((r || '/') + '?signin=' + kind, [kill]);
  if (!o || typeof o.s !== 'string' || typeof o.v !== 'string' || typeof o.n !== 'string' || !Number.isFinite(o.t) || now - o.t > OAUTH_TTL * 1000 || o.t > now + 60000) return back('error', '/');
  const r = safePath(o.r), qs = url.searchParams;
  if (qs.get('state') !== o.s) return back('error', r);                    /* CSRF / replay: state must match the one bound to this browser */
  if (qs.get('error')) return back(qs.get('error') === 'access_denied' ? 'cancelled' : 'error', r);
  const code = qs.get('code'); if (!code || code.length > 2048) return back('error', r);
  let tok;
  try {
    const resp = await fetch('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ code, client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, redirect_uri: REDIRECT_URI, grant_type: 'authorization_code', code_verifier: o.v }).toString() });
    if (!resp.ok) return back('error', r); tok = await resp.json();
  } catch (e) { return back('error', r); }
  const claims = parseIdToken(tok && tok.id_token, env.GOOGLE_CLIENT_ID, o.n, now); if (!claims) return back('error', r);
  let u;
  try { u = await env.DB.prepare(SQL.upsertUser).bind(claims.sub, claims.email, claims.name || null, Math.floor(now / 1000)).first(); } catch (e) { return back('error', r); }
  if (!u) return back('error', r);
  return finishSignIn(env, u, r, now, [kill]);
}
/* Every sign-in method ends here: given a users row, issue the session cookie and send the person back. (Phase 3 email-link sign-in calls this too; see NOTES-myteams-p2.md.) */
async function finishSignIn(env, u, r, now, extraCookies) {
  const session = setCookie(SESSION_COOKIE, await seal(env.SESSION_SECRET, { u: u.id, ver: u.sess_ver, exp: Math.floor(now / 1000) + SESSION_TTL }), SESSION_TTL);
  return redirect(r + '?signin=ok' + (r === '/' ? '#my-teams' : ''), (extraCookies || []).concat([session]));
}
function parseIdToken(t, clientId, nonce, now) {   /* the token arrived from Google's token endpoint over TLS; claims are still checked */
  if (typeof t !== 'string' || t.length > 8192) return null; const p = t.split('.'); if (p.length !== 3) return null; let c;
  try { c = JSON.parse(dec.decode(unb64u(p[1]))); } catch (e) { return null; }
  if (!c || typeof c !== 'object') return null;
  if (c.iss !== 'https://accounts.google.com' && c.iss !== 'accounts.google.com') return null;
  const aud = Array.isArray(c.aud) ? c.aud : [c.aud]; if (aud.indexOf(clientId) < 0) return null;
  if (!Number.isFinite(c.exp) || c.exp * 1000 < now - 60000) return null;
  if (c.nonce !== nonce) return null;
  if (c.email_verified !== true && c.email_verified !== 'true') return null;
  if (typeof c.sub !== 'string' || !c.sub || c.sub.length > 64 || typeof c.email !== 'string') return null;
  const email = clean(c.email, 254).toLowerCase(); if (!/^[^\s@]+@[^\s@]+$/.test(email)) return null;
  return { sub: c.sub, email, name: clean(c.name, 80) };
}
async function session(req, env, now) {
  if (!configured(env)) return json({ configured: false, signedIn: false });
  if (!sameOriginRead(req)) return json({ error: 'cross_site' }, 403);
  const u = await currentUser(req, env, now);
  if (!u) return json({ configured: true, signedIn: false }, 200, cookies(req)[SESSION_COOKIE] ? { 'Set-Cookie': dropCookies()[0] } : {});
  return json({ configured: true, signedIn: true, email: u.email, name: u.display_name || '', initial: initial(u), cap: CAP_ACCOUNT });
}
async function logout(req, env, now) {
  if (!originOk(req)) return json({ error: 'origin' }, 403);
  const u = await currentUser(req, env, now).catch(() => 'err');   /* a valid session: revoke it server side (every cookie signed with the old sess_ver stops working). No valid session: just clear the cookie. */
  if (u === 'err') return json({ error: 'store_failed' }, 500);
  if (u) { try { await env.DB.prepare(SQL.bumpSess).bind(u.id).run(); } catch (e) { return json({ error: 'store_failed' }, 500); } }   /* if the revoke fails the cookie is NOT cleared and the visitor is told, so "signed out" is never claimed while the session still works */
  return json({ ok: true }, 200, { 'Set-Cookie': dropCookies()[0] });
}
async function getTeams(req, env, now) {
  if (!sameOriginRead(req)) return json({ error: 'cross_site' }, 403);
  const u = await currentUser(req, env, now); if (!u) return json({ error: 'signed_out' }, 401);
  const rows = (await env.DB.prepare(SQL.teams).bind(u.id).all()).results || [];
  return json({ teams: rows.map((r) => r.slug), lead: Object.fromEntries(rows.map((r) => [r.slug, r.lead])), cap: CAP_ACCOUNT });
}
function validateTeams(b) {   /* -> {teams, lead} or {error} ; rejects (never repairs) anything malformed */
  if (!b || typeof b !== 'object' || Array.isArray(b)) return { error: 'bad_body' };
  const keys = Object.keys(b); if (keys.some((k) => k !== 'teams' && k !== 'lead')) return { error: 'bad_body' };
  if (!Array.isArray(b.teams)) return { error: 'bad_body' };
  if (b.teams.length > CAP_ACCOUNT) return { error: 'cap', cap: CAP_ACCOUNT };
  const seen = new Set();
  for (const s of b.teams) { if (typeof s !== 'string' || !SLUGRE.test(s) || !TEAM_SLUGS.has(s)) return { error: 'bad_team' }; if (seen.has(s)) return { error: 'duplicate' }; seen.add(s); }
  const lead = b.lead === undefined ? {} : b.lead;
  if (!lead || typeof lead !== 'object' || Array.isArray(lead)) return { error: 'bad_body' };
  for (const k of Object.keys(lead)) { if (!seen.has(k) || typeof lead[k] !== 'string' || !LEADS.has(lead[k])) return { error: 'bad_lead' }; }
  return { teams: b.teams, lead };
}
async function putTeams(req, env, now) {
  if (!originOk(req)) return json({ error: 'origin' }, 403);
  const u = await currentUser(req, env, now); if (!u) return json({ error: 'signed_out' }, 401);
  if (!(await hit(env, 'save', 'u' + u.id, now))) return json({ error: 'rate_limited' }, 429, { 'Retry-After': '3600' });
  if (!/^application\/json\b/i.test(req.headers.get('Content-Type') || '')) return json({ error: 'bad_type' }, 415);
  const len = Number(req.headers.get('Content-Length') || 0); if (len > 8192) return json({ error: 'too_large' }, 413);
  let text; try { text = await req.text(); } catch (e) { return json({ error: 'bad_body' }, 400); }
  if (text.length > 8192) return json({ error: 'too_large' }, 413);
  let body; try { body = JSON.parse(text); } catch (e) { return json({ error: 'bad_json' }, 400); }
  const v = validateTeams(body); if (v.error) return json({ error: v.error, cap: v.cap }, v.error === 'cap' ? 409 : 400);
  const ts = Math.floor(now / 1000), stmts = [env.DB.prepare(SQL.clearTeams).bind(u.id)];
  v.teams.forEach((s, i) => stmts.push(env.DB.prepare(SQL.addTeam).bind(u.id, s, v.lead[s] || 'p', i, ts)));
  try { await env.DB.batch(stmts); } catch (e) { return json({ error: 'store_failed' }, 500); }
  return json({ teams: v.teams, lead: Object.fromEntries(v.teams.map((s) => [s, v.lead[s] || 'p'])), cap: CAP_ACCOUNT });
}
async function deleteAccount(req, env, now) {
  if (!originOk(req)) return json({ error: 'origin' }, 403);
  const u = await currentUser(req, env, now); if (!u) return json({ error: 'signed_out' }, 401);
  if (!(await hit(env, 'del', visitor(req), now))) return json({ error: 'rate_limited' }, 429, { 'Retry-After': '86400' });
  try { await env.DB.batch([env.DB.prepare(SQL.clearTeams).bind(u.id), env.DB.prepare(SQL.deleteUser).bind(u.id)]); } catch (e) { return json({ error: 'store_failed' }, 500); }
  return json({ ok: true }, 200, { 'Set-Cookie': dropCookies()[0] });
}

const ROUTES = {
  '/api/auth/google/start': { GET: (q, e, u, n) => start(q, e, u, n) },
  '/api/auth/google/callback': { GET: (q, e, u, n) => callback(q, e, u, n) },
  '/api/auth/session': { GET: (q, e, u, n) => session(q, e, n) },
  '/api/auth/logout': { POST: (q, e, u, n) => logout(q, e, n) },
  '/api/teams': { GET: (q, e, u, n) => getTeams(q, e, n), PUT: (q, e, u, n) => putTeams(q, e, n) },
  '/api/account/delete': { POST: (q, e, u, n) => deleteAccount(q, e, n) }
};
const worker = {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env && env.ASSETS ? env.ASSETS.fetch(request) : new Response('Not found', { status: 404 });   /* _routes.json keeps these away; this is the safety net */
    const route = ROUTES[url.pathname.replace(/\/+$/, '')];
    if (!route) return json({ error: 'not_found' }, 404);
    const h = route[request.method];
    if (!h) return json({ error: 'method' }, 405, { Allow: Object.keys(route).join(', ') });
    const isStart = url.pathname.replace(/\/+$/, '') === '/api/auth/google/start';
    if (!env || !env.DB || !env.SESSION_SECRET) { return url.pathname === '/api/auth/session' ? json({ configured: false, signedIn: false }) : isStart ? toError() : json({ error: 'not_configured' }, 503); }
    try { return await h(request, env, url, Date.now()); } catch (e) { return isStart ? toError() : json({ error: 'server' }, 500); }
  },
  _t: { SQL, validateTeams, parseIdToken, seal, unseal, safePath, configured, CAP_ACCOUNT, EMAIL_LINK_TTL_SECONDS, LIMITS, TEAM_SLUGS, ORIGIN, SESSION_COOKIE, OAUTH_COOKIE }   /* test hooks; not routes */
};
export default worker;
