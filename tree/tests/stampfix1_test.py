"""stampfix1: as-of restamp must not touch the spreads stamp or kickoff labels that share the old as-of minute; merge3 heals a live spreads stamp
that differs from S0 (Nov 14 2026 runs 43653016423/43655772002 failed: method/index.html anchored conflict). python3 tests/stampfix1_test.py"""
import os, re, sys, json, datetime, subprocess, tempfile
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'); src = open(T + '/apply_data.py').read(); ns = {}
exec('import re,datetime\n' + src[src.index('def forms'):src.index('def run(cmd')], ns); fails = []
F0, F1 = ns['forms']('2026-11-14 15:00 MT'), ns['forms']('2026-11-14 15:37 MT')
t = '<b>Game results last pulled:</b> Sat, Nov 14, 2026, 3:00 PM MT. <b>Spreads last read:</b> Nov 14, 2026, 3:00 PM MT. <div class="gtag">Sat Nov 14, 3:00 PM MT</div> Data as of Nov 14, 3:00 PM MT. data-asof="2026-11-14 15:00"'
o = ns['restamp_text'](t, F0, F1)
if 'pulled:</b> Sat, Nov 14, 2026, 3:37 PM MT' not in o or 'Data as of Nov 14, 3:37 PM MT' not in o or 'data-asof="2026-11-14 15:37"' not in o: fails.append('as-of not restamped: ' + o)
if 'Spreads last read:</b> Nov 14, 2026, 3:00 PM MT.' not in o or 'gtag">Sat Nov 14, 3:00 PM MT' not in o: fails.append('protected span changed: ' + o)
if [f for f in F0[:5] if f in ns['unprot'](o)]: fails.append('left-check would fire')
d = tempfile.mkdtemp(); body = '<p><b>Game results last pulled:</b> Sat, Nov 14, 2026, {a} MT. <b>Spreads last read:</b> Nov 14, 2026, {s} MT. All times are Mountain Time.</p>'
for k, a, s in (('L', '3:37 PM', '3:37 PM'), ('A', '3:37 PM', '3:00 PM'), ('B', '4:24 PM', '4:24 PM'), ('O', '3:37 PM', '3:37 PM')):
    os.makedirs(f'{d}/{k}/method'); open(f'{d}/{k}/method/index.html', 'w').write(body.format(a=a, s=s))
P = json.dumps([[F, G] for F, G in zip(ns['forms']('2026-11-14 15:37 MT')[:4], ns['forms']('2026-11-14 16:24 MT')[:4])])
subprocess.run([sys.executable, T + '/merge3.py', f'{d}/L', f'{d}/A', f'{d}/B', f'{d}/O', f'{d}/rep.json', P], check=True, capture_output=True)
r = json.load(open(f'{d}/rep.json')); out = open(f'{d}/O/method/index.html').read()
if r['conflict'] or 'Spreads last read:</b> Nov 14, 2026, 4:24 PM MT.' not in out: fails.append('merge3: %s %s' % (r['conflict'], out))
print('4 checks, %d failed' % len(fails)); [print('FAIL', f) for f in fails]; sys.exit(1 if fails else 0)
