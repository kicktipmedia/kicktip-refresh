#!/usr/bin/env python3
"""Lane P4 build step (runs after the overlay copy and after lane B wrote data/tb/ccg-alive.json). It edits no existing site file; it only asserts that the two shipped data files agree with the tree:
  * data/tb/ccg-paths.json and data/tb/path-by-stage.json: each file under 160 KB, asof equal to sim-bundle as_of;
  * ccg-paths: one entry per team of ccg-alive, rules hash equal to ccg-alive's, letters only A H T N P U, own-game count equals ccg-alive 'left', consistent with ccg-alive status (out = all N, in = at least one path letter or a not-worked-out letter);
  * path-by-stage: n sums to the season count for every team, p <= n, b <= p, and p/b totals equal needs-by-record (same simulation run).
usage: build_lane.py --tree <built tree>"""
import argparse, json, os, sys
ap = argparse.ArgumentParser(); ap.add_argument('--tree', required=True); a = ap.parse_args(); T = os.path.abspath(a.tree)
def J(*p): return json.load(open(os.path.join(T, *p), encoding='utf8'))
bad = []
B = J('data', 'sim-bundle.json'); AL = J('data', 'tb', 'ccg-alive.json'); NB = J('data', 'tb', 'needs-by-record.json')
for f in ('ccg-paths.json', 'path-by-stage.json'):
    p = os.path.join(T, 'data', 'tb', f)
    if not os.path.exists(p): bad.append('missing data/tb/' + f); continue
    if os.path.getsize(p) >= 160 * 1024: bad.append('%s is %d bytes (limit 163840)' % (f, os.path.getsize(p)))
    if J('data', 'tb', f)['asof'] != B['as_of']: bad.append('%s asof %r != sim-bundle %r' % (f, J('data', 'tb', f)['asof'], B['as_of']))
if not bad:
    CP = J('data', 'tb', 'ccg-paths.json'); PS = J('data', 'tb', 'path-by-stage.json')
    if sorted(CP['confs']) != sorted(AL['confs']): bad.append('ccg-paths conferences differ from ccg-alive')
    for c, X in AL['confs'].items():
        if CP['rules'].get(c) != X['rules']['hash']: bad.append('%s: rules hash differs from ccg-alive' % c)
        tm = CP['confs'].get(c, {})
        if sorted(tm) != sorted(t['s'] for t in X['teams']): bad.append('%s: team list differs from ccg-alive' % c)
        for t in X['teams']:
            e = tm.get(t['s'])
            if not e: continue
            if len(e['o']) != t['left'] or len(e['t']) != t['left'] + 1: bad.append('%s/%s: own games %d / letters %d vs left %d' % (c, t['s'], len(e['o']), len(e['t']), t['left']))
            if set(e['t']) - set('AHTNPU'): bad.append('%s/%s: bad letters %s' % (c, t['s'], e['t']))
            if t['st'] == 'out' and set(e['t']) != {'N'}: bad.append('%s/%s: out but letters %s' % (c, t['s'], e['t']))
            if t['st'] == 'in' and set(e['t']) <= set('N'): bad.append('%s/%s: in the race but every letter is N: %s' % (c, t['s'], e['t']))
            if e['m'] is not None and e['t'][e['m']] not in 'AHTP': bad.append('%s/%s: minw %s does not point at a path letter' % (c, t['s'], e['m']))
            if e['m'] is not None and set(e['t'][:e['m']]) - set('N'): bad.append('%s/%s: minw %s but an earlier letter is not N' % (c, t['s'], e['m']))
            if (e['e'] == 1) != (not set(e['t']) & set('UP')): bad.append('%s/%s: exh flag disagrees with letters' % (c, t['s']))
    for s, e in PS['t'].items():
        if sum(e['n']) != PS['seasons']: bad.append('path-by-stage %s: n sums to %d' % (s, sum(e['n'])))
        if any(e['p'][z] > e['n'][z] or e['b'][z] > e['p'][z] for z in range(3)): bad.append('path-by-stage %s: p/b exceed n/p' % s)
        r = NB['byrec'].get(s)
        if r and (sum(e['p']) != sum(r['p']) or sum(e['b']) != sum(r['b'])): bad.append('path-by-stage %s: totals differ from needs-by-record' % s)
    if PS['seasons'] != 10000: bad.append('path-by-stage seasons %s' % PS['seasons'])
if bad:
    print('build_lane[P4] FAILED:\n - ' + '\n - '.join(bad[:30])); sys.exit(1)
print('build_lane[P4]: ccg-paths.json and path-by-stage.json ok, asof %s' % B['as_of'])
