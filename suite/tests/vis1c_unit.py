#!/usr/bin/env python3
"""vis1c vs vis1b: content changes only in assets/tb/tb.css (vis1c.css appended) and assets/tb/conf_vs_conf.js (vis1c.js inserted before the module.exports line); no copy strings change. usage: vis1c_unit.py VIS1B_TREE VIS1C_TREE CSS JS"""
import os, re, sys
A, B, CSS, JS = sys.argv[1:5]; n = bad = 0
def ck(ok, k):
    global n, bad; n += 1; bad += (not ok); print(('PASS ' if ok else 'FAIL ') + k)
TOK = re.compile(rb'\?v=[0-9a-f]{10}')
W = lambda r: {os.path.relpath(os.path.join(d, f), r) for d, _, fs in os.walk(r) for f in fs}
fa, fb = W(A), W(B); ck(fa == fb and len(fa) == 952, 'same 952 paths')
ch = [p for p in sorted(fa) if TOK.sub(b'', open(os.path.join(A, p), 'rb').read()) != TOK.sub(b'', open(os.path.join(B, p), 'rb').read())]
ck(ch == ['assets/tb/conf_vs_conf.js', 'assets/tb/tb.css'], 'content changes only in conf_vs_conf.js + tb.css: %s' % ch)
rd = lambda r, p: open(os.path.join(r, p), encoding='utf-8').read()
c = open(CSS, encoding='utf-8').read(); j = open(JS, encoding='utf-8').read()
ck(rd(B, 'assets/tb/tb.css') == rd(A, 'assets/tb/tb.css').rstrip('\n') + '\n' + c, 'tb.css = vis1b tb.css + vis1c.css appended')
anc = '  if (typeof module !== "undefined" && module.exports) module.exports = TB;\n'
a = rd(A, 'assets/tb/conf_vs_conf.js'); b = rd(B, 'assets/tb/conf_vs_conf.js')
ck(a.count(anc) == 1 and b == a.replace(anc, j + anc), 'conf_vs_conf.js = vis1b + vis1c.js inserted before module.exports')
rules = [l for l in c.splitlines() if l and not l.startswith('/*')]
ck(all(all(s.strip().startswith('.ac.tbox[data-tool="conf_vs_conf"]') for s in l.split('{')[0].split(',')) for l in rules), 'every new selector scoped to conf_vs_conf card')
ck('content:' not in c and 'display:none' not in c and 'visibility' not in c, 'CSS adds or hides no text')
ck('.ac.tbox[data-tool="conf_vs_conf"] table.ba' in j and 'tbox-x' in j and 'tbox-more' in j, 'JS scoped selector + toggled classes')
jc = re.sub(r'/\*.*?\*/|//[^\n]*', '', j, flags=re.S); lits = re.findall(r'"([^"\\]*)"|\'([^\'\\]*)\'', jc); lits = [x or y for x, y in lits]
ck(all(re.fullmatch(r'[\w\-\s\.\[\]="]*', s) or s.startswith('.ac.tbox') for s in lits), 'JS adds no copy text: %s' % lits)
ck('innerHTML' not in j and 'textContent' not in j and 'eval(' not in j and 'style.' not in j, 'no DOM text writes / inline style (CSP)')
for p in ('assets/tb/card.js', '_worker.js'): ck(open(os.path.join(A, p), 'rb').read() == open(os.path.join(B, p), 'rb').read(), p + ' byte-identical')
bw = re.compile(r'\b(bet|bets|wager\w*|parlay\w*|spread|CCG)\b|title game|the 12\b', re.I)
ck(not bw.search(c + j), 'no banned words in added code')
print('%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
