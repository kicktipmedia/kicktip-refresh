// Shared offline mocks: in-memory D1 (answers ONLY the SQL the Worker declares), mock Workers AI, mock Turnstile siteverify. Nothing leaves this machine.
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import { pathToFileURL } from 'node:url';
export async function loadWorker(tree, flag) {   // flag: array of tool ids -> rewrites the shipped `const TB_LIVE_TOOLS = [];` in a TEMP COPY (the shipped file is never edited)
  let src = fs.readFileSync(path.join(tree, '_worker.js'), 'utf8');
  if (flag && flag.length) { const re = /const TB_LIVE_TOOLS = \[[^\]]*\];/; if (!re.test(src)) throw new Error('tree has no TB_LIVE_TOOLS switch'); const ids = flag[0] === 'none' ? [] : flag; src = src.replace(re, 'const TB_LIVE_TOOLS = ' + JSON.stringify(ids) + ';'); const re2 = /const TB_TOOL_IDS = \[[^\]]*\];/; if (!re2.test(src)) throw new Error('tree has no TB_TOOL_IDS'); const known = JSON.parse(re2.exec(src)[0].slice('const TB_TOOL_IDS = '.length, -1).replace(/'/g, '"')); src = src.replace(re2, 'const TB_TOOL_IDS = ' + JSON.stringify(Array.from(new Set(known.concat(ids)))) + ';'); }   // toolbox6: the new tools are dark, so the flag fixture edits BOTH lists (a later real flip must too)   // toolbox5: the shipped list is full; --flag overrides it (flag 'none' = empty list = OFF)
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tb5w-')), f = path.join(tmp, 'worker.mjs'); fs.writeFileSync(f, src);
  return (await import(pathToFileURL(f).href)).default;
}
export function makeEnv(W, o = {}) {
  const SQLS = Object.assign({}, W._t.SQL, W._tb ? { tbc: W._tb.TB_SQL } : {});
  const db = { rows: new Map(), log: [], fail: false };
  const kind = (sql) => sql === SQLS.tbc ? 'tb' : sql === SQLS.askf ? 'askf' : sql === SQLS.rate ? 'rate' : sql === SQLS.sweep ? 'sweep' : 'other';
  db.prepare = (sql) => { let a = []; const s = {
    bind(...x) { a = x; return s; },
    async first() { db.log.push({ k: kind(sql), sql, a }); if (db.fail) throw new Error('D1 down'); if (sql === SQLS.rate) { const key = a[0] + '|' + a[1], r = db.rows.get(key) || { n: 0, exp: a[2] }; r.n++; db.rows.set(key, r); return { n: r.n }; } throw new Error('undeclared first() SQL ' + sql); },
    async run() { db.log.push({ k: kind(sql), sql, a }); if (db.fail) throw new Error('D1 down');
      if (sql === SQLS.sweep) { for (const [k, v] of db.rows) if (v.exp < a[0]) db.rows.delete(k); return {}; }
      const fam = sql === SQLS.askf ? 'askf:' : sql === SQLS.tbc ? 'tb:' : null;
      if (fam) { const [k, w, exp, max, gmax] = a, key = k + '|' + w; let g = 0; for (const [kk, v] of db.rows) if (kk.startsWith(fam) && kk.endsWith('|' + w)) g += v.n;
        const r = db.rows.get(key); if (g >= gmax && !r) return {}; if (r) { if (r.n < max) r.n++; } else db.rows.set(key, { n: 1, exp }); return {}; }
      throw new Error('undeclared run() SQL ' + sql); } }; return s; };
  const st = { ai_calls: [], siteverify: [] };
  const ai = { run: async (model, input) => { st.ai_calls.push([model, JSON.stringify(input)]); return { response: JSON.stringify({ v: 1, mode: 'home', status: 'ok', scenarios: [{ label: 'A', wins_out: ['BYU Cougars'] }] }) }; } };
  const env = Object.assign({ KT_ENV: 'preview', DB: db, SESSION_SECRET: 'x'.repeat(48), AI_ENABLED: 'on', AI: ai, TURNSTILE_SECRET: '1x0000000000000000000000000000000AA', TURNSTILE_SITEKEY: '1x00000000000000000000AA' }, o);
  return { env, db, st };
}
let installed = null;
export function installFetch(st) {   // mock Turnstile siteverify; any other outbound fetch is an error
  if (!installed) installed = globalThis.fetch;
  globalThis.fetch = async (url, init) => { if (String(url) === 'https://challenges.cloudflare.com/turnstile/v0/siteverify') { const p = new URLSearchParams(init.body); st.siteverify.push(Object.fromEntries(p)); return Response.json((p.get('response') && p.get('response') !== 'bad') ? { success: true, 'error-codes': [], hostname: 'example.com', metadata: { result_with_testing_key: true } } : { success: false, 'error-codes': ['invalid-input-response'] }); } throw new Error('unexpected outbound fetch ' + url); };
}
export const ORIGIN = 'https://kicktipmedia.com';
