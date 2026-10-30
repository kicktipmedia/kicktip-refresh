#!/usr/bin/env python3
"""usage: static_checks9.py ZIP9 ZIP8B"""
import sys, zipfile, hashlib, re
z9, z8 = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
a, b = set(z8.namelist()), set(z9.namelist())
chk('base is toolbox8b: 931 entries, sha aa41c0f3...', len(a) == 931 and hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest().startswith('aa41c0f3c9450871'))
chk('output 928 entries, no duplicates, no .zip entries', len(b) == 928 == len(z9.namelist()) and not [x for x in b if x.endswith('.zip')])
chk('added none; removed = 3 whatif w8 shards', not (b - a) and len(a - b) == 3 and all(x.endswith('whatif/w8.json') for x in a - b), (b - a, a - b))
chk('_worker.js byte-identical', z9.read('_worker.js') == z8.read('_worker.js'))
w = z9.read('_worker.js').decode(); ids = lambda nm: re.search(r'const %s = \[([^\]]*)\]' % nm, w).group(1).count("'") // 2
chk('19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS', ids('TB_LIVE_TOOLS') == 19 and ids('TB_TOOL_IDS') == 19)
mod = sorted(x for x in a & b if z8.read(x) != z9.read(x)); nh = [x for x in mod if not x.endswith('.html')]
chk('modified: 165 html + 53 other = 218', len(mod) == 218 and len(nh) == 53, (len(mod), len(nh)))
SRC = ['assets/rootables.js', 'assets/tb/head_to_head.js', 'assets/tb/matcher.js', 'assets/tb/rules/schedule_strength.js', 'assets/tb/schedule_strength.js', 'assets/tb/slate_this_week.js', 'assets/tb/team_compare.js', 'assets/tb/team_schedule.js']
chk('all 8 Part 2 source files changed', all(x in mod for x in SRC))
odd = [x for x in nh if x not in SRC and not re.match(r'data/|assets/tb/(manifest|hook)\.js|assets/chat\.js|assets/(kt|lg|search|tile)', x)]
chk('other modified non-html files are data/ or token carriers', not odd, odd)
BAN = re.compile(r"\b(bets?|betting|wagers?|wagering|spreads?|parlays?|ccg|title game)\b|\bthe 12(?!-team)\b", re.I)
for f in SRC:
    old = set(z8.read(f).decode().splitlines()); ch = '\n'.join(l for l in z9.read(f).decode().splitlines() if l not in old)
    ch = re.sub(r'ccg-sim|ccg-alive|ccg_rules_verified', '', ch); ch = '\n'.join(l for l in ch.split('\n') if not (re.search(r'spread', l) and re.search(r'BENIGN|WT_|OU|gate', l))) if f.endswith('matcher.js') else ch
    m = BAN.search(ch); chk(f + ': changed lines clean of banned words / non-ASCII', not m and all(ord(c) < 128 or c == '\u00b7' for c in ch), m and ch[max(0, m.start() - 40):m.end() + 40])
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
