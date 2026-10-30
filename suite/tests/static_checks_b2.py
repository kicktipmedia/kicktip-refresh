#!/usr/bin/env python3
"""scn_b2 static checks. usage: static_checks_b2.py ZIP_B ZIP_B2"""
import sys, zipfile, hashlib, re
P = sys.argv[1:3]; zb, z2 = [zipfile.ZipFile(p) for p in P]; n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
TOK = re.compile(r'\?v=[0-9a-f]{10}'); N = lambda z, f: TOK.sub('?v=T', z.read(f).decode('utf-8', 'ignore')); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
EDIT = ['_worker.js', 'assets/chat.js', 'assets/ks/explain.js', 'assets/ks/scenario.js']
chk('base B sha256 = 25186170...df31 and equals the .sha256 beside it; 936 entries', sha(P[0]) == open(P[0] + '.sha256').read().split()[0] and sha(P[0]) == '251861703fbd8cc2ce9d55b344213b73770635d2ee7f47cd148e3f2dc4b1df31' and len(zb.namelist()) == 936)
chk('B2 sha256 equals the .sha256 beside it', sha(P[1]) == open(P[1] + '.sha256').read().split()[0])
a, b = set(zb.namelist()), set(z2.namelist())
chk('936 entries, no duplicates, no .zip entries, file set identical to B', len(b) == 936 == len(z2.namelist()) and a == b and not [x for x in b if x.endswith('.zip')])
chk('every entry has the fixed build date', all(i.date_time == (2026, 10, 27, 0, 0, 0) for i in z2.infolist()))
mod = sorted(x for x in a & b if zb.read(x) != z2.read(x)); real = sorted(x for x in mod if N(zb, x) != N(z2, x))
chk('content changes are exactly %s' % EDIT, real == EDIT, real)
chk('every other changed file differs only in ?v= tokens (%d files) and carries a changed token' % (len(mod) - len(real)), all(N(zb, x) == N(z2, x) and set(TOK.findall(zb.read(x).decode('utf-8', 'ignore'))) != set(TOK.findall(z2.read(x).decode('utf-8', 'ignore'))) for x in mod if x not in EDIT))
chk('assets/tb/manifest.js, data/*, every other asset: byte-identical to B', all(zb.read(x) == z2.read(x) for x in a if x not in EDIT and not x.endswith('.html')) )
chk('no CLOUDFLARE_API_TOKEN or token assignment anywhere', not any(re.search(rb'CLOUDFLARE_API_TOKEN|api[_-]?token\s*[:=]', z2.read(f), re.I) for f in b))
for f in EDIT:
    old = set(zb.read(f).decode().splitlines()); new = [l for l in z2.read(f).decode().splitlines() if l not in old]
    chk('%s: %d added/changed lines, ASCII only' % (f, len(new)), all(ord(ch) < 128 for l in new for ch in l))
w1, w2 = zb.read('_worker.js').decode(), z2.read('_worker.js').decode(); ids = lambda s, nm: re.search(r'const %s = \[([^\]]*)\]' % nm, s).group(1).count("'") // 2
chk('Worker: 19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; ROUTER_TOOLS and MAX_FACTS_JSON unchanged', ids(w2, 'TB_LIVE_TOOLS') == 19 and ids(w2, 'TB_TOOL_IDS') == 19 and re.findall(r'^const ROUTER_TOOLS = .*$', w1, re.M) == re.findall(r'^const ROUTER_TOOLS = .*$', w2, re.M) and re.findall(r'MAX_FACTS_JSON[^\n;]*', w1) == re.findall(r'MAX_FACTS_JSON[^\n;]*', w2))
chk('Worker: SCN.MODEL is the 8b id in ONE line, 70b still in SCN.MODELS, TICKET_COUNTS true', len(re.findall(r"^  MODEL: '@cf/meta/llama-3\.1-8b-instruct-fp8',", w2, re.M)) == 1 and "'@cf/meta/llama-3.3-70b-instruct-fp8-fast'" in re.search(r'MODELS: \[[^\]]*\]', w2).group(0) and re.search(r'^  TICKET_COUNTS: true,', w2, re.M))
chk('Worker: AI_SCN still dark unless exactly "on"; DAY_CAP 60 unchanged', re.findall(r"scnOn = [^\n]*", w1) == re.findall(r"scnOn = [^\n]*", w2) and 'DAY_CAP: 60' in w2)
c1, c2 = zb.read('assets/chat.js').decode(), z2.read('assets/chat.js').decode()
chk('chat.js: SCNIMPALL one-line switch; the new card is behind KTAI.scnOn()', c2.count('var SCNIMPALL = true;') == 1 and 'KTAI.scnOn' in c2)
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
