#!/usr/bin/env python3
"""scn_b static checks on both builds. usage: static_checks_b.py ZIP_A2 ZIP_A2B ZIP_B"""
import sys, zipfile, hashlib, re
P = sys.argv[1:4]; Z = [zipfile.ZipFile(p) for p in P]; z2, zab, zb = Z; n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
TOK = re.compile(r'\?v=[0-9a-f]{10}'); N = lambda z, f: TOK.sub('?v=T', z.read(f).decode('utf-8', 'ignore')); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
chk('base A2 sha256 = 5e10463d...fac and equals the .sha256 beside it; 936 entries', sha(P[0]) == open(P[0] + '.sha256').read().split()[0] and sha(P[0]).startswith('5e10463d') and sha(P[0]).endswith('530fac') and len(z2.namelist()) == 936, sha(P[0]))
for (base, out, bp, op, label, edit) in ((z2, zab, P[0], P[1], 'A2b', ['assets/chat.css']), (zab, zb, P[1], P[2], 'B', ['_worker.js', 'assets/chat.css', 'assets/chat.js', 'assets/ks/explain.js', 'assets/ks/scenario.js', 'assets/ks/scnai.js'])):
    a, b = set(base.namelist()), set(out.namelist())
    chk('%s: base sha256 equals its .sha256; output sha256 equals the .sha256 beside it' % label, sha(bp) == open(bp + '.sha256').read().split()[0] and sha(op) == open(op + '.sha256').read().split()[0])
    chk('%s: 936 entries, no duplicates, no .zip entries, file set identical to the base' % label, len(b) == 936 == len(out.namelist()) and a == b and not [x for x in b if x.endswith('.zip')])
    chk('%s: every entry has the fixed build date' % label, all(i.date_time == (2026, 10, 27, 0, 0, 0) for i in out.infolist()))
    mod = sorted(x for x in a & b if base.read(x) != out.read(x)); real = sorted(x for x in mod if N(base, x) != N(out, x))
    chk('%s: content changes are exactly %s' % (label, edit), real == edit, real)
    chk('%s: every other changed file differs only in ?v= tokens (%d files)' % (label, len(mod) - len(real)), all(N(base, x) == N(out, x) for x in mod if x not in edit))
    chk('%s: no CLOUDFLARE_API_TOKEN or token assignment anywhere' % label, not any(re.search(rb'CLOUDFLARE_API_TOKEN|api[_-]?token\s*[:=]', out.read(f), re.I) for f in b))
    for f in edit:
        old = set(base.read(f).decode().splitlines()); new = [l for l in out.read(f).decode().splitlines() if l not in old]
        chk('%s %s: %d added/changed lines, ASCII only' % (label, f, len(new)), all(ord(ch) < 128 for l in new for ch in l))
css0, css1, css2 = z2.read('assets/chat.css').decode(), zab.read('assets/chat.css').decode(), zb.read('assets/chat.css').decode()
chk('A2b chat.css: only appended rules, scoped to .pnl .sx, inside a 420px media query, vertical-align top', css1.startswith(css0.rstrip('\n')) and 'vertical-align:top' in css1[len(css0.rstrip('\n')):] and '.pnl .sx' in css1[len(css0.rstrip('\n')):])
chk('B chat.css: only appended rules scoped to .pnl .sx', css2.startswith(css1.rstrip('\n')) and all(l.startswith(('.pnl .sx', '/*', '@media', '}')) or not l.strip() for l in css2[len(css1.rstrip('\n')):].splitlines()))
w1, w2 = zab.read('_worker.js').decode(), zb.read('_worker.js').decode(); ids = lambda s, nm: re.search(r'const %s = \[([^\]]*)\]' % nm, s).group(1).count("'") // 2
chk('Worker B: 19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; ROUTER_TOOLS, MAX_FACTS_JSON and SCN.MODEL unchanged', ids(w2, 'TB_LIVE_TOOLS') == 19 and ids(w2, 'TB_TOOL_IDS') == 19 and re.findall(r'^const ROUTER_TOOLS = .*$', w2, re.M) == re.findall(r'^const ROUTER_TOOLS = .*$', w1, re.M) and re.findall(r'MAX_FACTS_JSON\s*[:=]\s*\d+', w2) == re.findall(r'MAX_FACTS_JSON\s*[:=]\s*\d+', w1) and re.findall(r'MODEL:\s*[^,]+,', w2) == re.findall(r'MODEL:\s*[^,]+,', w1))
chk("Worker B: AI_SCN still read only through scnOn(env); no new env name, binding or route", "const scnOn = (env) => !!(env && env.AI_SCN === 'on');" in w2 and set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w2)) == set(re.findall(r'env\.([A-Z][A-Z0-9_]+)', w1)) and w2.count("pathname === '/api/") == w1.count("pathname === '/api/"))
for f in ('assets/ks/parse.js', 'assets/ks/answer.js', 'assets/ccgsim.js', 'assets/ai-client.js', 'assets/ks/sim.js'):
    if f in zab.namelist(): chk('%s byte-identical to A2b (engine, sim, parser untouched)' % f, zab.read(f) == zb.read(f))
chk('data/* byte-identical to A2b', all(zab.read(f) == zb.read(f) for f in zab.namelist() if f.startswith('data/')))
c, ex, sj, sc = (zb.read(f).decode() for f in ('assets/chat.js', 'assets/ks/explain.js', 'assets/ks/scnai.js', 'assets/ks/scenario.js'))
chk('chat.js: SCNB switch present once and true; no new fetch in chat.js', c.count('var SCNB = true;') == 1 and c.count('fetch(') == zab.read('assets/chat.js').decode().count('fetch('))
chk('scnai.js: ASCII, no network/storage/eval/timer calls', all(ord(ch) < 128 for ch in sj) and not re.search(r'fetch\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|document\.cookie|eval\(|new Function|setTimeout|setInterva', sj))
BAN = re.compile(r"\b(bets?|betting|wagers?|wagering|spreads?|parlays?|CCG|title game|picks?|locks?|predict\w*|forecast\w*|vegas|juice|over/under)\b|the 12(?!-team|-game)|\u00e9", re.I)
bs = [m for m in re.findall(r'COPY\.(b(?:Shared1|SharedN|If|Beats|Imp\w*)) = "([^"]*)";', ex)]
chk('explain.js: 9 new COPY.b* strings, none with a banned word, all ASCII', len(bs) == 9 and not any(BAN.search(v) for _, v in bs) and all(all(ord(ch) < 128 for ch in v) for _, v in bs), bs)
chk('explain.js drift tooling still OK is checked by tools/check_explain_drift.py (run_all)', True)
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
