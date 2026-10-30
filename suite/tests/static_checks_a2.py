#!/usr/bin/env python3
"""scn_a2 static checks. usage: static_checks_a2.py ZIP_A2 ZIP_A1B"""
import sys, zipfile, hashlib, re, os
z2, z1 = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
a, b = set(z1.namelist()), set(z2.namelist()); TOK = re.compile(r'\?v=[0-9a-f]{10}')
want = open(sys.argv[2] + '.sha256').read().split()[0]; got = hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest()
chk('base is A1b: 935 entries, sha256 equals the .sha256 beside it (%s...)' % got[:12], len(a) == 935 == len(z1.namelist()) and got == want)
chk('output 936 entries, no duplicates, no .zip entries, file set = base + assets/ks/scnai.js only', len(b) == 936 == len(z2.namelist()) and not [x for x in b if x.endswith('.zip')] and b - a == {'assets/ks/scnai.js'} and not (a - b))
chk('every entry has the fixed build date (2026-10-27 00:00:00)', all(i.date_time == (2026, 10, 27, 0, 0, 0) for i in z2.infolist()))
chk('output .sha256 file matches the zip', open(sys.argv[1] + '.sha256').read().split()[0] == hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())
EDIT = ['_worker.js', 'assets/ai-client.js', 'assets/ccgsim.js', 'assets/chat.css', 'assets/chat.js', 'assets/ks/explain.js']
mod = sorted(x for x in a & b if z1.read(x) != z2.read(x)); N = lambda z, f: TOK.sub('?v=T', z.read(f).decode('utf-8', 'ignore'))
chk('hand-edited files that differ in content: exactly _worker.js, ai-client.js, chat.js, chat.css, ks/explain.js (card chance copy), ccgsim.js (tie-section names)', sorted(x for x in mod if N(z1, x) != N(z2, x)) == EDIT, [x for x in mod if N(z1, x) != N(z2, x)])
other = [x for x in mod if x not in EDIT]
chk('every other changed file differs only in ?v= tokens (%d files)' % len(other), all(N(z1, x) == N(z2, x) for x in other))
same = ['assets/ks/parse.js', 'assets/ks/scenario.js', 'assets/ks/answer.js'] + sorted(x for x in a if x.startswith('data/'))
chk('parse.js, scenario.js, answer.js (the live tables keep >99.9%% and 0.0%%) and data/* byte-identical to A1b (%d files)' % len(same), all(z1.read(f) == z2.read(f) for f in same))
w0, w = z1.read('_worker.js').decode(), z2.read('_worker.js').decode(); ids = lambda s, nm: re.search(r'const %s = \[([^\]]*)\]' % nm, s).group(1).count("'") // 2
chk('19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; ROUTER_TOOLS line unchanged', ids(w, 'TB_LIVE_TOOLS') == 19 and ids(w, 'TB_TOOL_IDS') == 19 and re.findall(r'^const ROUTER_TOOLS = .*$', w, re.M) == re.findall(r'^const ROUTER_TOOLS = .*$', w0, re.M))
chk("AI_SCN is read only through scnOn(env) = (env.AI_SCN === 'on'); every other use of env.AI_SCN in the Worker is that exact comparison", "const scnOn = (env) => !!(env && env.AI_SCN === 'on');" in w and all(m.group(0).endswith("=== 'on'") for m in re.finditer(r"env\.AI_SCN(?!_CAP)\b( === 'on')?", w)) and len(re.findall(r"env\.AI_SCN(?!_CAP)\b", w)) == 1, re.findall(r".{20}env\.AI_SCN.{20}", w))
chk("ask-config: scn field appended after the router field, guarded by scnOn(env)", "if (ready && TB_ON.length && routerOn(env)) cfg.router = true;\n    if (ready && scnOn(env)) cfg.scn = true;" in w and "if (ready && TB_ON.length && routerOn(env)) cfg.router = true;" in w0)
chk('Worker: the scn route is entered only under scnOn(env); body limit stays ASK.MAX_BODY unless the flag is on', "scnOn(env) ? SCN.MAX_BODY : ASK.MAX_BODY" in w and "if (bodyMax !== ASK.MAX_BODY) { if (body.mode === 'scn') return await scnRoute(req, env, url, now, body);" in w)
chk('Worker: scn sub-cap 60 and the single-use ticket both exist; no new binding, secret name or service', 'DAY_CAP: 60' in w and 'askscn' in w and "'scnt:'" in w and not (set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w)) - set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w0)) - {'AI_SCN', 'AI_SCN_CAP_OVERRIDE'}), sorted(set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w)) - set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w0))))
chk('Worker: no CLOUDFLARE_API_TOKEN or other secret string anywhere in the tree', not any(re.search(rb'CLOUDFLARE_API_TOKEN|api[_-]?token\s*[:=]', z2.read(f), re.I) for f in b))
man = z2.read('assets/tb/manifest.js').decode()
chk('manifest: only ?v= tokens differ from A1b; ccg_matchup and team_trend still live:false', TOK.sub('', man) == TOK.sub('', z1.read('assets/tb/manifest.js').decode()) and all(re.search(r'"%s":\{"url"[^{}]*?"live":false' % t, man) for t in ('ccg_matchup', 'team_trend')))
sj = z2.read('assets/ks/scnai.js').decode(); c = z2.read('assets/chat.js').decode(); c0 = z1.read('assets/chat.js').decode(); ai = z2.read('assets/ai-client.js').decode(); ai0 = z1.read('assets/ai-client.js').decode()
chk('chat.js loads scnai.js with the real ?v= token (sha256[:10] of the file)', ('/assets/ks/scnai.js?v=' + hashlib.sha256(sj.encode()).hexdigest()[:10]) in c and '?v=0000000000' not in c)
chk('scnai.js: ASCII only; no network, storage, cookie, eval or timer calls', all(ord(ch) < 128 for ch in sj) and not re.search(r'fetch\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|document\.cookie|eval\(|new Function|setTimeout|setInterval', sj))
chk("chat.js: SCNAI switch is true, SCNAI_FALLBACK_LEAD false, SCNAI_MAX 3; scnWrite is defined once and called once; no new fetch in chat.js", 'var SCNAI = true, SCNAI_FALLBACK_LEAD = false, SCNAI_MAX = 3;' in c and c.count('scnWrite(f, B)') == 2 and c.count('if (f && card) scnWrite(f, B);') == 1 and c.count('fetch(') == c0.count('fetch('), (c.count('scnWrite(f, B)'), c.count('fetch('), c0.count('fetch(')))
chk("ai-client.js: exactly one new network call (the scn POST to /api/ask); scn honored only when ask-config said scn:true", ai.count('fetch(') == ai0.count('fetch(') + 1 and 'cfg.scn !== true' in ai and 'scn: j.scn === true' in ai and ai.count('"/api/') == ai0.count('"/api/') + 1, (ai.count('fetch('), ai0.count('fetch(')))
chk("ai-client.js: the scn body is only {mode, facts} + the bot-check token or a ticket (no typed text)", 'var body = { mode: "scn", facts: facts };' in ai and 'ask.text' not in ai[ai.index('function scn('):])
for f in EDIT:
    old = set(z1.read(f).decode().splitlines()); new = [l for l in z2.read(f).decode().splitlines() if l not in old]
    chk(f + ': %d added lines, ASCII only' % len(new), all(ord(ch) < 128 for l in new for ch in l))
B = re.compile(r"\b(bets?|betting|wagers?|wagering|spreads?|parlays?|CCG|title game|picks?|locks?|predict\w*|forecast\w*|vegas|juice|over/under)\b|the 12(?!-team|-game)|\u00e9", re.I)
chk('visitor-facing strings in scnai.js COPY contain no banned word', not any(B.search(v) for v in re.findall(r'COPY = \{(.*?)\};', sj, re.S)[0].split('",')), re.findall(r'COPY = \{(.*?)\};', sj, re.S)[0][:200])
css = z2.read('assets/chat.css').decode(); added = css[len(z1.read('assets/chat.css').decode()):] if css.startswith(TOK.sub('?v=T', z1.read('assets/chat.css').decode())[:0]) else ''
chk('chat.css: A2 rules appended after the A1b rules and scoped to .pnl .sx', css.startswith(z1.read('assets/chat.css').decode().rstrip('\n')) and all(l.startswith(('.pnl .sx', '/*', '@media', '}')) or not l.strip() for l in css[len(z1.read('assets/chat.css').decode().rstrip('\n')):].splitlines()))
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
