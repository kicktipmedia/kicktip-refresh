#!/usr/bin/env python3
# scn_b4 static checks: B3 zip vs B4 zip. usage: python3 tests/static_checks_b4.py B3_ZIP B4_ZIP
import sys, zipfile, hashlib, re
TOK = re.compile(r'\?v=[0-9a-f]{10}'); n = bad = 0
def chk(k, c):
    global n, bad; n += 1; print(('PASS ' if c else 'FAIL ') + k); bad += (not c)
za, zb = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); A = {x: za.read(x) for x in za.namelist()}; B = {x: zb.read(x) for x in zb.namelist()}
chk('B3 base sha asserted', hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest() == '6b633c7d910a28d2843142404a009e6603b9fa985ec4dd829eefc984fd676e00')
chk('936 entries, same file set, no .zip entries', len(B) == 936 and sorted(A) == sorted(B) and not [x for x in B if x.lower().endswith('.zip')])
ch = sorted(x for x in B if A[x] != B[x]); content = [x for x in ch if TOK.sub('?v=0', A[x].decode('utf-8', 'replace')) != TOK.sub('?v=0', B[x].decode('utf-8', 'replace'))]
chk('content changes are exactly _worker.js and assets/ai-client.js: %s' % content, content == ['_worker.js', 'assets/ai-client.js'])
tok = [x for x in ch if x not in content]
def refs(s): return set(re.findall(r'([\w./-]+\.(?:js|css))\?v=[0-9a-f]{10}', s))
okc = True; cascade = {'ai-client.js'}
for x in tok:
    a, b = A[x].decode(), B[x].decode(); da = set(re.findall(r'[\w./-]+\?v=[0-9a-f]{10}', a)) ^ set(re.findall(r'[\w./-]+\?v=[0-9a-f]{10}', b))
    names = {d.split('?')[0].split('/')[-1] for d in da}
    if not names or not names <= {'ai-client.js', 'chat.js', 'ctile.js', 'manifest.js'}: okc = False; print('  unexpected token change in', x, names)
chk('token-only files (%d) only restamp ai-client.js or the files that load it (chat.js, ctile.js)' % len(tok), okc)
w = B['_worker.js'].decode(); chk('Worker: SCN.MODEL 70b, AI_TIMEOUT_MS 8000, MAX_OUT_TOKENS 220, 8b still in MODELS', "  MODEL: '@cf/meta/llama-3.3-70b-instruct-fp8-fast'," in w and 'AI_TIMEOUT_MS: 8000' in w and 'MAX_OUT_TOKENS: 220' in w and "MODELS: ['@cf/meta/llama-3.3-70b-instruct-fp8-fast', '@cf/meta/llama-3.1-8b-instruct-fp8']" in w)
chk('ai-client: SCN_WAIT_MS 9000', 'var SCN_WAIT_MS = 9000' in B['assets/ai-client.js'].decode())
chk('ASCII only in the changed files', all(all(ord(c) < 128 for c in l) for x in content for l in set(B[x].decode().splitlines()) - set(A[x].decode().splitlines())))
print('%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
