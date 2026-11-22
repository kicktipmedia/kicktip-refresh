#!/usr/bin/env python3
"""Team remaining-games card: last in-progress game goes final (run 44992101679).

At live a97d531e / as_of 2026-11-21 18:59 MT, four Pac-12 pages still had their last
remaining game In progress: Colorado State at Fresno State (401860918) and Washington
State at Texas State (401860920). The next refresh's S1 replaced each Remaining games
card with build.py's empty sentinel ("No regular-season games remain in our schedule
data."). Live had already dropped the ionly disclaimer and reworded the FCS note in
that card, so git merge-file conflicted (apply_data exit 16). The resolver takes S1's
sentinel only in that exhausted-card case and stays fail-closed otherwise.

usage: python3 tests/team_rem_final_test.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, 'fixtures', 'team_rem_final')
M3 = os.path.join(HERE, '..', 'tools', 'merge3.py')
TEAMS = {
    'colorado-state': {
        'opp': 'fresno-state', 'note': 'Away', 'result': 'L 42-49',
        'old': 'Conference record 1-5, overall 3-7',
        'new': 'Conference record 1-6, overall 3-8',
        'espn': '401860918', 'final': '42-49',
    },
    'fresno-state': {
        'opp': 'colorado-state', 'note': 'Home', 'result': 'W 49-42',
        'old': 'Conference record 2-4, overall 5-5',
        'new': 'Conference record 3-4, overall 6-5',
        'espn': '401860918', 'final': '49-42',
    },
    'texas-state': {
        'opp': 'washington-state', 'note': 'Home', 'result': 'W 42-14',
        'old': 'Conference record 4-2, overall 6-4',
        'new': 'Conference record 5-2, overall 7-4',
        'espn': '401860920', 'final': '42-14',
    },
    'washington-state': {
        'opp': 'texas-state', 'note': 'Away', 'result': 'L 14-42',
        'old': 'Conference record 1-5, overall 2-8',
        'new': 'Conference record 1-6, overall 2-9',
        'espn': '401860920', 'final': '14-42',
    },
}
EMPTY = '<div class="card"><h2>Remaining games</h2><p>No regular-season games remain in our schedule data.</p></div>'
fail = 0

def ok(c, m):
    global fail
    print(('ok   ' if c else 'FAIL ') + m)
    fail += 0 if c else 1

def remcard_span(t):
    i = t.find('<div class="card"><h2>Remaining games</h2>')
    if i < 0:
        return None
    d = 0
    for m in re.finditer(r'<div\b|</div>', t[i:]):
        d += 1 if m.group(0) != '</div>' else -1
        if d == 0:
            return (i, i + m.end())
    return None

def make_s1(s0_root, dst):
    for slug, meta in TEAMS.items():
        src = os.path.join(s0_root, 'team', slug, 'index.html')
        t = open(src, encoding='utf-8').read()
        sp = remcard_span(t)
        if not sp:
            raise SystemExit('no remaining card in s0 %s' % slug)
        t = t[:sp[0]] + EMPTY + t[sp[1]:]
        name = ' '.join(w.capitalize() if w != 'state' else 'State' for w in meta['opp'].split('-'))
        row = ('<tr><td>Sat Nov 21</td><td><a class="tl" href="/team/%s/">%s</a>'
               '<span class="note">%s</span></td><td><b>Final</b> &middot; %s</td></tr>'
               % (meta['opp'], name, meta['note'], meta['result']))
        t = t.replace('<tbody>', '<tbody>' + row, 1)
        if meta['old'] not in t:
            raise SystemExit('old record missing in s0 %s' % slug)
        t = t.replace(meta['old'], meta['new'], 1)
        outp = os.path.join(dst, 'team', slug, 'index.html')
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        open(outp, 'w', encoding='utf-8').write(t)

def run_merge3(path, live, s0, s1):
    td = tempfile.mkdtemp(prefix='remfinal_')
    out = os.path.join(td, 'out')
    shutil.copytree(live, out)
    rep = os.path.join(td, 'r.json')
    r = subprocess.run([sys.executable, path, live, s0, s1, out, rep], capture_output=True, text=True)
    report = json.load(open(rep)) if os.path.isfile(rep) else {}
    return report, out, r

def unfixed_copy():
    src = open(M3, encoding='utf-8').read()
    # Drop only this PR's resolver so the test still reproduces on a tarball (no git show).
    start = src.find('    # Team pages: when the last remaining game goes final')
    end = src.find('    def nz(c,new=0):')
    if start < 0 or end < 0 or end < start:
        raise SystemExit('could not strip TEAM rem resolver')
    src = src[:start] + src[end:]
    if 'KTRREM' in src:
        raise SystemExit('strip failed: KTRREM still present')
    td = tempfile.mkdtemp(prefix='m3old_')
    path = os.path.join(td, 'merge3.py')
    open(path, 'w', encoding='utf-8').write(src)
    return path

# --- build trees ---
live = os.path.join(FX, 'live')
s0 = os.path.join(FX, 's0')
td = tempfile.mkdtemp(prefix='remfinal_s1_')
s1 = os.path.join(td, 's1')
make_s1(s0, s1)

old = unfixed_copy()
r_old, _, _ = run_merge3(old, live, s0, s1)
conf_old = r_old.get('conflict') or []
want = ['team/%s/index.html rc=1' % s for s in TEAMS]
ok(sorted(conf_old) == sorted(want), 'unfixed merge3 conflicts on the four exhausted team pages: %s' % conf_old)

r, out, proc = run_merge3(M3, live, s0, s1)
ok(proc.returncode == 0, 'fixed merge3 process rc=0, got %s %s' % (proc.returncode, (proc.stderr or '')[-200:]))
ok((r.get('conflict') or []) == [], 'fixed merge3: no conflicts %s' % r.get('conflict'))
resolved = r.get('resolved') or {}
ok(sorted(resolved) == sorted('team/%s/index.html' % s for s in TEAMS),
   'resolver used on the four team pages: %s' % resolved)

for slug, meta in TEAMS.items():
    rel = 'team/%s/index.html' % slug
    o = open(os.path.join(out, rel), encoding='utf-8').read()
    ok(EMPTY in o, '%s: remaining-games card is the exhausted sentinel' % slug)
    ok('In progress' not in o, '%s: in-progress last-check line is gone' % slug)
    ok('<b>Final</b> &middot; %s' % meta['result'] in o, '%s: results include Final %s' % (slug, meta['result']))
    ok(meta['new'] in o, '%s: record updated to %s' % (slug, meta['new']))
    # live chrome outside the remaining card must survive (What If / chances heading)
    L = open(os.path.join(live, rel), encoding='utf-8').read()
    if 'What if for' in L:
        ok('What if for' in o, '%s: live What If chrome kept' % slug)

# Fail-closed: S1 is not the exhausted sentinel (game still remaining) and live/s0/s1 all
# disagree inside the card — merge-file must still report a conflict.
td2 = tempfile.mkdtemp(prefix='remfinal_fc_')
for side in ('live', 's0', 's1'):
    shutil.copytree(os.path.join(FX, 'live') if side == 'live' else (s0 if side == 's0' else s1),
                    os.path.join(td2, side))
# Restore a remaining card on S1 so it is NOT exhausted, but change the in-progress score
# differently from a live-only edit, so merge-file conflicts.
def patch(path, fn):
    t = open(path, encoding='utf-8').read()
    open(path, 'w', encoding='utf-8').write(fn(t))

p_live = os.path.join(td2, 'live/team/colorado-state/index.html')
p_s0 = os.path.join(td2, 's0/team/colorado-state/index.html')
p_s1 = os.path.join(td2, 's1/team/colorado-state/index.html')
# s1 starts as exhausted; copy s0 remaining card back, then edit the score three ways
s0_html = open(p_s0, encoding='utf-8').read()
sp = remcard_span(s0_html)
card = s0_html[sp[0]:sp[1]]
s1_html = open(p_s1, encoding='utf-8').read()
sp1 = remcard_span(s1_html)
# S1: still in progress, different last-check score
s1_card = card.replace('Colorado State 14, Fresno State 28', 'Colorado State 21, Fresno State 35')
open(p_s1, 'w', encoding='utf-8').write(s1_html[:sp1[0]] + s1_card + s1_html[sp1[1]:])
# Live: still in progress, a different last-check score (a live-only edit of the data)
live_html = open(p_live, encoding='utf-8').read()
spl = remcard_span(live_html)
live_card = live_html[spl[0]:spl[1]].replace('Colorado State 14, Fresno State 28', 'Colorado State 17, Fresno State 31')
open(p_live, 'w', encoding='utf-8').write(live_html[:spl[0]] + live_card + live_html[spl[1]:])
r_fc, _, _ = run_merge3(M3, os.path.join(td2, 'live'), os.path.join(td2, 's0'), os.path.join(td2, 's1'))
fc = r_fc.get('conflict') or []
ok(any('team/colorado-state/index.html' in x for x in fc),
   'fail-closed: live-edited in-progress score still conflicts when S1 is not exhausted: %s' % fc)

print('%d failed' % fail)
sys.exit(1 if fail else 0)
