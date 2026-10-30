// In-memory stand-in for a D1 binding. It answers ONLY the exact SQL strings exported by the Worker (worker._t.SQL), so a test fails if the Worker runs any statement it did not declare;
// tests/d1_schema_test.py runs those same strings against real SQLite with the real migrations, so the two together cover semantics + syntax.
export function makeDB(SQL) {
  const db = { users: [], teams: [], rate: new Map(), nextId: 1, log: [], failNext: false };
  function run(sql, a) {
    db.log.push(sql);
    if (db.failNext) { db.failNext = false; throw new Error('forced D1 failure'); }
    switch (sql) {
      case SQL.upsertUser: { let u = db.users.find((x) => x.google_sub === a[0]); if (u) { u.email = a[1]; u.display_name = a[2]; } else { u = { id: db.nextId++, google_sub: a[0], email: a[1], display_name: a[2], created_at: a[3], sess_ver: 1 }; db.users.push(u); } return { first: { id: u.id, sess_ver: u.sess_ver }, rows: [] }; }
      case SQL.userById: { const u = db.users.find((x) => x.id === a[0]); return { first: u ? { id: u.id, email: u.email, display_name: u.display_name, sess_ver: u.sess_ver } : null, rows: [] }; }
      case SQL.teams: { const rows = db.teams.filter((t) => t.user_id === a[0]).sort((x, y) => x.position - y.position).map((t) => ({ slug: t.slug, lead: t.lead })); return { first: rows[0] || null, rows }; }
      case SQL.clearTeams: db.teams = db.teams.filter((t) => t.user_id !== a[0]); return { first: null, rows: [] };
      case SQL.addTeam: { if (db.teams.some((t) => t.user_id === a[0] && t.slug === a[1])) throw new Error('UNIQUE'); db.teams.push({ user_id: a[0], slug: a[1], lead: a[2], position: a[3], added_at: a[4] }); return { first: null, rows: [] }; }
      case SQL.bumpSess: { const u = db.users.find((x) => x.id === a[0]); if (u) u.sess_ver++; return { first: null, rows: [] }; }
      case SQL.deleteUser: db.users = db.users.filter((u) => u.id !== a[0]); db.teams = db.teams.filter((t) => t.user_id !== a[0]); return { first: null, rows: [] };
      case SQL.rate: { const key = a[0] + '|' + a[1]; const r = db.rate.get(key) || { n: 0, exp: a[2] }; r.n++; db.rate.set(key, r); return { first: { n: r.n }, rows: [] }; }
      case SQL.sweep: for (const [k, v] of db.rate) if (v.exp < a[0]) db.rate.delete(k); return { first: null, rows: [] };
      default: throw new Error('undeclared SQL: ' + sql);
    }
  }
  db.prepare = (sql) => { let args = []; const st = { bind(...x) { args = x; return st; }, async first() { return run(sql, args).first; }, async all() { return { results: run(sql, args).rows }; }, async run() { run(sql, args); return { success: true }; }, _exec: () => run(sql, args) }; return st; };
  db.batch = async (stmts) => { const snap = { teams: db.teams.slice(), users: db.users.slice() }; try { return stmts.map((s) => { s._exec(); return { success: true }; }); } catch (e) { db.teams = snap.teams; db.users = snap.users; throw e; } };
  return db;
}
const b64u = (o) => Buffer.from(typeof o === 'string' ? o : JSON.stringify(o)).toString('base64url');
// Mock Google token endpoint. Checks PKCE (S256 of code_verifier must equal the challenge the auth request carried), the redirect URI and the client credentials, then returns an ID token built from `claims`.
export function makeGoogle(opts) {
  const g = { codes: new Map(), calls: [], nextClaims: null, fail: false, issue(authUrl, claims) { const u = new URL(authUrl), code = 'code-' + Math.random().toString(36).slice(2); g.codes.set(code, { challenge: u.searchParams.get('code_challenge'), nonce: u.searchParams.get('nonce'), claims }); return code; } };
  g.fetch = async (url, init) => {
    g.calls.push(String(url));
    if (String(url) !== 'https://oauth2.googleapis.com/token') throw new Error('unexpected outbound fetch: ' + url);
    if (g.fail) return new Response('{"error":"server_error"}', { status: 500 });
    const p = new URLSearchParams(init.body), c = g.codes.get(p.get('code'));
    const bad = () => new Response('{"error":"invalid_grant"}', { status: 400 });
    if (!c || p.get('client_id') !== opts.clientId || p.get('client_secret') !== opts.clientSecret || p.get('redirect_uri') !== 'https://kicktipmedia.com/api/auth/google/callback' || p.get('grant_type') !== 'authorization_code') return bad();
    const { createHash } = await import('node:crypto');
    if (createHash('sha256').update(p.get('code_verifier') || '').digest('base64url') !== c.challenge) return bad();
    g.codes.delete(p.get('code'));   // single use
    const now = Math.floor(Date.now() / 1000), claims = Object.assign({ iss: 'https://accounts.google.com', aud: opts.clientId, sub: '1000000001', email: 'sam@example.com', email_verified: true, name: 'Sam Rivera', nonce: c.nonce, iat: now, exp: now + 3600 }, c.claims || {});
    return new Response(JSON.stringify({ access_token: 'x', token_type: 'Bearer', id_token: b64u({ alg: 'RS256' }) + '.' + b64u(claims) + '.sig' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  return g;
}
