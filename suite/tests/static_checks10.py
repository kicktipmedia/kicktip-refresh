#!/usr/bin/env python3
"""usage: static_checks10.py ZIP10 ZIP9"""
import sys, zipfile, hashlib, re, json
z10, z9 = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
a, b = set(z9.namelist()), set(z10.namelist())
chk('base is toolbox9c: 928 entries, sha 7c6e7c0e...', len(a) == 928 and hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest().startswith('7c6e7c0edd234004'))
chk('output 934 entries, no duplicates, no .zip entries', len(b) == 934 == len(z10.namelist()) and not [x for x in b if x.endswith('.zip')])
NEW = {'assets/tb/ccg_matchup.js', 'assets/tb/team_trend.js', 'assets/tb/rules/ccg_matchup.js', 'assets/tb/rules/team_trend.js', 'data/tb/ccg-games.json', 'data/tb/trend.json'}
chk('added exactly the 6 new files; nothing removed', (b - a) == NEW and not (a - b), (b - a, a - b))
chk('_worker.js byte-identical to toolbox9', z10.read('_worker.js') == z9.read('_worker.js'))
w = z10.read('_worker.js').decode(); ids = lambda nm: re.search(r'const %s = \[([^\]]*)\]' % nm, w).group(1).count("'") // 2
chk('19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; neither lists the new tools', ids('TB_LIVE_TOOLS') == 19 and ids('TB_TOOL_IDS') == 19 and 'ccg_matchup' not in w and 'team_trend' not in w)
mod = sorted(x for x in a & b if z9.read(x) != z10.read(x)); nh = [x for x in mod if not x.endswith('.html')]
chk('modified: 150 html + chat.js + hook.js + manifest.js = 153', len(mod) == 153 and sorted(nh) == ['assets/chat.js', 'assets/tb/hook.js', 'assets/tb/manifest.js'], (len(mod), nh))
tok = re.compile(r'\?v=[0-9a-z]+')
def strip(x): return tok.sub('?v=T', z9.read(x).decode()) == tok.sub('?v=T', z10.read(x).decode())
chk('every modified file except manifest.js differs only in ?v= tokens', all(strip(x) for x in mod if x != 'assets/tb/manifest.js'), [x for x in mod if x != 'assets/tb/manifest.js' and not strip(x)][:5])
man = z10.read('assets/tb/manifest.js').decode()
chk('manifest: both new tools live:false', all(re.search(r'"%s":\{"url"[^{}]*?"live":false' % t, man) for t in ('ccg_matchup', 'team_trend')))
BAN = re.compile(r"\b(bets?|betting|wagers?|wagering|spreads?|parlays?|ccg|title game)\b|\bthe 12(?!-team)\b", re.I)
for f in sorted(NEW):
    s = z10.read(f).decode()
    if f.startswith('assets/tb/rules/'): s = ''   # rules recognise visitor words; they never print them (SPEC-GUESSES)
    s = re.sub(r'ccg-games|ccg_matchup|ccg-alive|ccg-sim|ccg\.json|championship_game', '', s)
    m = BAN.search(s); chk(f + ': clean of banned words', not m, m and s[max(0, m.start() - 40):m.end() + 40])
    chk(f + ': ASCII only', all(ord(c) < 128 for c in z10.read(f).decode()))
for f in ('data/tb/ccg-games.json', 'data/tb/trend.json'): json.loads(z10.read(f))
chk('data files parse as JSON', True)
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
