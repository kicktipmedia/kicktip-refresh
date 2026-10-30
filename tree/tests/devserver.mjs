// Local HTTPS harness for the phase-2 browser tests: serves build/site with the _headers CSP, runs build/site/_worker.js for /api/*, with mock D1 and mock Google.
// Test-only control routes live under /__test/ (this file is never shipped). Usage: node tests/devserver.mjs PORT
import https from 'node:https'; import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import { pathToFileURL, fileURLToPath } from 'node:url';
import { makeDB, makeGoogle } from './mockd1.mjs';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..'), site = path.join(root, 'build/site'), port = Number(process.argv[2] || 8443);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ktdev-')); fs.copyFileSync(path.join(site, '_worker.js'), path.join(tmp, 'w.mjs'));
const W = (await import(pathToFileURL(path.join(tmp, 'w.mjs')).href)).default, T = W._t;
const CID = 'cid.apps.example', CSEC = 'csecret';
const google = makeGoogle({ clientId: CID, clientSecret: CSEC }); globalThis.fetch = google.fetch;
const db = makeDB(T.SQL), env = { DB: db, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: CSEC, SESSION_SECRET: 's'.repeat(48), ASSETS: null };
const live = { configured: true, gmode: 'ok', gclaims: {} };
const csp = (fs.readFileSync(path.join(site, '_headers'), 'utf8').match(/Content-Security-Policy: (.*)/) || [])[1];
const MIME = { html: 'text/html; charset=utf-8', js: 'text/javascript', css: 'text/css', json: 'application/json', png: 'image/png', jpg: 'image/jpeg', svg: 'image/svg+xml', woff2: 'font/woff2', ico: 'image/x-icon', xml: 'application/xml', txt: 'text/plain', webmanifest: 'application/manifest+json' };
function staticFile(p) {
  let f = path.join(site, decodeURIComponent(p.split('?')[0])); if (!f.startsWith(site)) return null;
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html'); else if (!fs.existsSync(f) && fs.existsSync(f + '/index.html')) f += '/index.html';
  return fs.existsSync(f) && fs.statSync(f).isFile() ? f : null;
}
const server = https.createServer({ key: fs.readFileSync('/tmp/kt-dev.key'), cert: fs.readFileSync('/tmp/kt-dev.crt') }, async (req, res) => {
  const u = new URL(req.url, 'https://kicktipmedia.com');
  if ((req.headers.host || '').startsWith('accounts.google.com')) {   // stand-in for Google's consent page: bounces straight back to the callback (the browser maps this host to this server; real Google is never contacted)
    if (!u.pathname.startsWith('/o/oauth2/')) { res.statusCode = 404; res.end(); return; }
    const st = u.searchParams.get('state'); const cb = 'https://kicktipmedia.com/api/auth/google/callback?';
    res.statusCode = 302; res.setHeader('Location', cb + (live.gmode === 'deny' ? 'error=access_denied&state=' + encodeURIComponent(st) : 'code=' + encodeURIComponent(google.issue('https://accounts.google.com' + req.url, live.gclaims)) + '&state=' + encodeURIComponent(st))); res.end(); return;
  }
  if (u.pathname.startsWith('/__test/')) {
    res.setHeader('Content-Type', 'application/json');
    if (u.pathname === '/__test/issue') { const claims = JSON.parse(u.searchParams.get('claims') || '{}'); res.end(JSON.stringify({ code: google.issue(u.searchParams.get('url'), claims) })); return; }
    if (u.pathname === '/__test/state') { res.end(JSON.stringify({ users: db.users, teams: db.teams, rate: db.rate.size })); return; }
    if (u.pathname === '/__test/google') { live.gmode = u.searchParams.get('mode') || 'ok'; live.gclaims = JSON.parse(u.searchParams.get('claims') || '{}'); res.end('{"ok":true}'); return; }
    if (u.pathname === '/__test/config') { live.configured = u.searchParams.get('on') !== '0'; res.end('{"ok":true}'); return; }
    if (u.pathname === '/__test/reset') { db.users.length = 0; db.teams.length = 0; db.rate.clear(); db.nextId = 1; live.configured = true; live.gmode = 'ok'; live.gclaims = {}; google.fail = false; res.end('{"ok":true}'); return; }
    if (u.pathname === '/__test/seed') { const b = JSON.parse(u.searchParams.get('b')); db.teams.push(...b.teams.map((s, i) => ({ user_id: b.user_id, slug: s, lead: (b.lead || {})[s] || 'p', position: i, added_at: 1 }))); res.end('{"ok":true}'); return; }
    res.statusCode = 404; res.end('{}'); return;
  }
  if (u.pathname.startsWith('/api/')) {
    const chunks = []; for await (const c of req) chunks.push(c); const body = Buffer.concat(chunks);
    const h = new Headers(); for (const [k, v] of Object.entries(req.headers)) { if (Array.isArray(v)) v.forEach((x) => h.append(k, x)); else h.set(k, v); } h.set('CF-Connecting-IP', '127.0.0.1');
    const r = await W.fetch(new Request(u.href, { method: req.method, headers: h, body: ['GET', 'HEAD'].includes(req.method) ? undefined : body, redirect: 'manual' }), live.configured ? env : { DB: null });
    res.statusCode = r.status; r.headers.forEach((v, k) => { if (k !== 'set-cookie') res.setHeader(k, v); }); const sc = r.headers.getSetCookie(); if (sc.length) res.setHeader('Set-Cookie', sc);
    res.end(Buffer.from(await r.arrayBuffer())); return;
  }
  const f = staticFile(u.pathname);
  if (!f) { res.statusCode = 404; res.setHeader('Content-Type', MIME.html); res.end(fs.readFileSync(path.join(site, '404.html'))); return; }
  res.setHeader('Content-Type', MIME[f.split('.').pop()] || 'application/octet-stream'); res.setHeader('Content-Security-Policy', csp); res.setHeader('X-Content-Type-Options', 'nosniff');
  res.end(fs.readFileSync(f));
});
server.listen(port, '127.0.0.1', () => console.log('listening ' + port));
