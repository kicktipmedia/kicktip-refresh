#!/usr/bin/env python3
"""Rootables numbers from the stored single-game what-if shards (copies of the LIVE files in live/data/...).
Usage: python3 compute.py           -> prints tables, writes data.json
Swing (gap) for team T, outcome M, game G = P(T reaches M | home side wins G) - P(T reaches M | away side wins G), absolute value, in percentage points.
Values are integer per-mille in the shards (0.1 point resolution), so every number below is exact to 0.1."""
import json, datetime as dt, sys
from zoneinfo import ZoneInfo
MT = ZoneInfo('America/Denver')
METRIC = {'cfp12': 'Make the 12', 'ccg': 'Reach the conference title game'}
THRESH = 10   # per-mille = 1.0 point
TEAMS = ('Utah Utes', 'BYU Cougars', 'Houston Cougars', 'LSU Tigers', 'Tennessee Volunteers')   # Utah + BYU = the two required examples; Houston = My teams 3rd card; LSU = bye-week example; Tennessee = 'nothing moves it 1.0 point' example
def base_dir(model): return 'live/data' + ('' if model == 'blend' else f'/m/{model}')
def load(model='blend'):
    b = base_dir(model) + '/whatif'; idx = json.load(open(b + '/index.json')); sh = {}
    for w, f in idx['shards'].items(): sh.update(json.load(open(f'{b}/{f}')))
    return idx, sh
def bundle(): return json.load(open('live/data/sim-bundle.json'))
def snap_utc(idx): return dt.datetime.strptime(idx['as_of'], '%Y-%m-%d %H:%M MT').replace(tzinfo=MT).astimezone(dt.timezone.utc)
def window_games(bun, snap, days=7):
    end = snap + dt.timedelta(days=days); out = {}
    for g in bun['games']:
        if not g.get('date'): continue
        d = dt.datetime.strptime(g['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc)
        if snap <= d <= end: out[g['id']] = d
    return out
def swings(idx, sh, team, metric, win):
    names = idx['team_names']; mi = idx['metrics'].index(metric); base = idx['baseline'][team][mi]; out = []
    for g in idx['games']:
        d = win.get(g['id']); e = sh.get(g['id'])
        if d is None or e is None: continue
        def val(k):
            for r in e[k]:
                if r[0] == team: return r[mi + 1]
            return base      # unlisted: moved < min_move_permille (3) on every metric -> equals baseline within 0.3 pt
        h, a = val('h'), val('a')
        if team in (g['h'], g['a']): continue   # Oct 31 (Jared): leave off the team's own game
        out.append(dict(id=g['id'], home=names[g['h']], away=names[g['a']], hid=g['h'], aid=g['a'], neutral=g['neutral'], kick_utc=d.strftime('%Y-%m-%dT%H:%MZ'),
                        kick_mt=d.astimezone(MT).strftime('%a %b %-d, %-I:%M %p MT'), base=base, home_wins=h, away_wins=a, gap=abs(h - a), own=team in (g['h'], g['a'])))
    out.sort(key=lambda r: (-r['gap'], r['kick_utc'], r['id'])); return out
def blend_block(idx, sh, win, t):
    # blended list (Oct 31): score = max(cfp12 gap, ccg gap); race = bigger (tie -> cfp12); 'title' never read
    P = {r['id']: r for r in swings(idx, sh, t, 'cfp12', win)}; C = {r['id']: r for r in swings(idx, sh, t, 'ccg', win)}; rows = []
    for i, p in P.items():
        c = C[i]; m, o, race = (c, p, 'ccg') if c['gap'] > p['gap'] else (p, c, 'cfp12')
        root = lambda r: r['hid'] if r['home_wins'] >= r['away_wins'] else r['aid']
        sec = None if o['gap'] < THRESH else dict(race='cfp12' if race == 'ccg' else 'ccg', v=o['gap'] if root(o) == root(m) else -o['gap'])
        rows.append(dict(id=i, score=m['gap'], race=race, root=root(m), cfp12=[p['home_wins'], p['away_wins']], ccg=[c['home_wins'], c['away_wins']], sec=sec, kick_utc=m['kick_utc'], home=m['home'], away=m['away']))
    rows.sort(key=lambda r: (-r['score'], r['kick_utc'], r['id'])); big = [r for r in rows if r['score'] >= THRESH]
    return dict(n_window=len(rows), n_big=len(big), n_hidden=len(rows) - len(big), top=big[:5])
def team_block(idx, sh, win, tm):
    t = idx['team_names'].index(tm); blk = {'team': tm, 'tid': t}
    for m in METRIC:
        rows = swings(idx, sh, t, m, win); big = [r for r in rows if r['gap'] >= THRESH]
        blk[m] = dict(baseline=idx['baseline'][t][idx['metrics'].index(m)], n_window=len(rows), n_big=len(big), n_hidden=len(rows) - len(big), top=big[:5])
    blk['blend'] = blend_block(idx, sh, win, t)
    return blk
if __name__ == '__main__':
    out = {}
    for model in ('blend', 'elo', 'eff'):
        idx, sh = load(model); bun = bundle(); snap = snap_utc(idx); win = window_games(bun, snap)
        out[model] = dict(as_of=idx['as_of'], seasons=idx['seasons'], model=idx['model'], n_games_window=len(win), teams={})
        for tm in TEAMS:
            out[model]['teams'][tm] = team_block(idx, sh, win, tm)
        print(model, idx['as_of'], 'seasons', idx['seasons'], 'games in window', len(win))
        for tm, blk in out[model]['teams'].items():
            for m in METRIC:
                x = blk[m]; print(f"  {tm:12} {METRIC[m]:34} base {x['baseline']/10:5.1f}  window {x['n_window']}  >=1.0: {x['n_big']}  hidden: {x['n_hidden']}")
                if model == 'blend':
                    for r in x['top']: print(f"      {r['kick_mt']:24} {r['away']} at {r['home']}: home wins {r['home_wins']/10}  away wins {r['away_wins']/10}  gap {r['gap']/10}")
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else 'data_noown.json', 'w'), indent=1)
