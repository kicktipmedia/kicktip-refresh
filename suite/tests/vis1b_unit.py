#!/usr/bin/env python3
"""vis1b vs vis1: only assets/tb/tb.css changes in content (vis1b.css appended, scoped to conf_vs_conf); every other file is identical once ?v= tokens are stripped. usage: vis1b_unit.py VIS1_TREE VIS1B_TREE CSS_FILE"""
import os, re, sys
A, B, CSS = sys.argv[1:4]; n = bad = 0
def ck(ok, k):
    global n, bad; n += 1; bad += (not ok); print(('PASS ' if ok else 'FAIL ') + k)
TOK = re.compile(rb'\?v=[0-9a-f]{10}')
fa = {os.path.relpath(os.path.join(d, f), A) for d, _, fs in os.walk(A) for f in fs}; fb = {os.path.relpath(os.path.join(d, f), B) for d, _, fs in os.walk(B) for f in fs}
ck(fa == fb and len(fa) == 952, 'same 952 paths')
ch = [p for p in sorted(fa) if TOK.sub(b'', open(os.path.join(A, p), 'rb').read()) != TOK.sub(b'', open(os.path.join(B, p), 'rb').read())]
ck(ch == ['assets/tb/tb.css'], 'content change only in assets/tb/tb.css: %s' % ch)
a = open(os.path.join(A, 'assets/tb/tb.css'), encoding='utf-8').read(); b = open(os.path.join(B, 'assets/tb/tb.css'), encoding='utf-8').read(); c = open(CSS, encoding='utf-8').read()
ck(b == a.rstrip('\n') + '\n' + c, 'tb.css = vis1 tb.css + vis1b.css appended')
rules = [l for l in c.splitlines() if l and not l.startswith('/*')]
ck(all(all(s.strip().startswith('.ac.tbox[data-tool="conf_vs_conf"]') for s in l.split('{')[0].split(',')) for l in rules), 'every new selector is scoped to the conf_vs_conf card')
ck('content:' not in c and 'display:none' not in c and 'visibility' not in c, 'CSS adds or hides no text')
for p in ('assets/tb/conf_vs_conf.js', 'assets/tb/card.js', '_worker.js'): ck(open(os.path.join(A, p), 'rb').read() == open(os.path.join(B, p), 'rb').read(), p + ' byte-identical (no string change)')
print('%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
