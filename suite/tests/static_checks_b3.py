#!/usr/bin/env python3
"""scn_b3 static checks. usage: static_checks_b3.py ZIP_B2 ZIP_B3"""
import sys, zipfile, hashlib, re
P = sys.argv[1:3]; zb, z3 = [zipfile.ZipFile(p) for p in P]; n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
TOK = re.compile(r'\?v=[0-9a-f]{10}'); N = lambda z, f: TOK.sub('?v=T', z.read(f).decode('utf-8', 'ignore')); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
EDIT = ['_worker.js', 'assets/ks/explain.js']
chk('base B2 sha256 = 59bfc1a0...585d and equals the .sha256 beside it; 936 entries', sha(P[0]) == open(P[0] + '.sha256').read().split()[0] and sha(P[0]) == '59bfc1a01625e5fde52545385119a357a1e5f948459ea72883cec6bad743585d' and len(zb.namelist()) == 936)
chk('B3 sha256 equals the .sha256 beside it', sha(P[1]) == open(P[1] + '.sha256').read().split()[0])
a, b = set(zb.namelist()), set(z3.namelist())
chk('936 entries, no duplicates, no .zip entries, file set identical to B2', len(b) == 936 == len(z3.namelist()) and a == b and not [x for x in b if x.endswith('.zip')])
chk('every entry has the fixed build date', all(i.date_time == (2026, 10, 27, 0, 0, 0) for i in z3.infolist()))
mod = sorted(x for x in a & b if zb.read(x) != z3.read(x)); real = sorted(x for x in mod if N(zb, x) != N(z3, x))
chk('content changes are exactly %s' % EDIT, real == EDIT, real)
tokonly = [x for x in mod if x not in real]
chk('every other changed file differs only in ?v= tokens (%d files) and carries a changed token' % len(tokonly), all(N(zb, x) == N(z3, x) and set(TOK.findall(zb.read(x).decode('utf-8', 'ignore'))) != set(TOK.findall(z3.read(x).decode('utf-8', 'ignore'))) for x in tokonly))
h10 = lambda z, f: hashlib.sha256(z.read(f)).hexdigest()[:10]
chk('token cascade: chat.js carries explain.js\'s new token; every html file carries chat.js\'s new token (150 html + chat.js)', 'assets/chat.js' in tokonly and ('/assets/ks/explain.js?v=' + h10(z3, 'assets/ks/explain.js')) in z3.read('assets/chat.js').decode() and sorted(x for x in tokonly if x != 'assets/chat.js') == sorted(x for x in tokonly if x.endswith('.html')) and len(tokonly) == 151 and all(('/assets/chat.js?v=' + h10(z3, 'assets/chat.js')) in z3.read(x).decode('utf-8', 'ignore') for x in tokonly if x.endswith('.html')) and not any(('/assets/ks/explain.js?v=' + h10(zb, 'assets/ks/explain.js')) in z3.read(x).decode('utf-8', 'ignore') for x in b))
chk('assets/tb/manifest.js, data/*, scenario.js, scnai.js, ai-client.js, every other asset: byte-identical to B2', all(zb.read(x) == z3.read(x) for x in a if x not in EDIT and not x.endswith('.html') and x != 'assets/chat.js'))
chk('no CLOUDFLARE_API_TOKEN or token assignment anywhere', not any(re.search(rb'CLOUDFLARE_API_TOKEN|api[_-]?token\s*[:=]', z3.read(f), re.I) for f in b))
for f in EDIT:
    old = set(zb.read(f).decode().splitlines()); new = [l for l in z3.read(f).decode().splitlines() if l not in old]
    chk('%s: %d added/changed lines, ASCII only' % (f, len(new)), all(ord(ch) < 128 for l in new for ch in l))
w2, w3 = zb.read('_worker.js').decode().split('\n'), z3.read('_worker.js').decode().split('\n')
d = [i for i in range(len(w2)) if len(w2) == len(w3) and w2[i] != w3[i]]
chk('Worker: same line count, exactly 2 lines differ (the allowlist comment and the SCN_TEAMS line)', len(w2) == len(w3) and len(d) == 2, d)
chk('Worker: the SCN_TEAMS line differs only by San Jos\\u00e9 State -> San Jose State; only ASCII', len(d) == 2 and w2[d[1]].replace('"San Jos\\u00e9 State"', '"San Jose State"') == w3[d[1]] and '"San Jose State"' in w3[d[1]] and 'Jos\\u00e9' not in w3[d[1]])
W = z3.read('_worker.js').decode()
chk('Worker: SCN.MODEL 8b one line; TICKET_COUNTS true; AI_SCN dark unless "on"; DAY_CAP 60', len(re.findall(r"^  MODEL: '@cf/meta/llama-3\.1-8b-instruct-fp8',", W, re.M)) == 1 and 'TICKET_COUNTS: true,' in W and re.findall(r"scnOn = [^\n]*", zb.read('_worker.js').decode()) == re.findall(r"scnOn = [^\n]*", W) and 'DAY_CAP: 60' in W)
e2, e3 = zb.read('assets/ks/explain.js').decode(), z3.read('assets/ks/explain.js').decode()
chk('explain.js: COPY strings unchanged (bImpAll, bShared1, bSharedN identical to B2)', all(re.search(r'^\s*COPY\.%s = .*$' % k, e2, re.M).group(0) == re.search(r'^\s*COPY\.%s = .*$' % k, e3, re.M).group(0) for k in ('bImpAll', 'bShared1', 'bSharedN')))
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
