#!/usr/bin/env python3
"""build_tile_data.py: writes data/tile-data.json for the home tiles (What if + Who to root for), all FBS teams in pred-teams.json.

usage: build_tile_data.py <tree> [--now ISO8601] [--out FILE]
  <tree>  site tree (reads data/pred-teams.json, data/whatif/index.json + data/whatif/w<N>.json shards, data/sim-bundle.json)
  --now   reference time for "not started yet". Default = the data stamp (whatif/index.json as_of), so the output is deterministic for a given data set.
          The page itself drops any game whose kickoff has passed in the visitor's clock, so a later "now" is never required.
  --out   default <tree>/data/tile-data.json
Faithful Python port of assets/rootables.js (buildGames, compute, whenShort, mtMs) as run by Creative's prototype-data/compute.js, with two differences:
  * per team it keeps the top 5 rootables rows and the next up-to-3 unstarted games (the page shows 3 / 1 and skips any that have started in its own clock);
  * numbers are kept as integers (per-mille) and the page formats them (whole percent in What if cells, one decimal in rootables points).
No network, no Odds API, no secrets: reads only the published data files above."""
import sys, os, json, datetime, re
from zoneinfo import ZoneInfo

MT = ZoneInfo('America/Denver'); UTC = datetime.timezone.utc
MS7 = 7 * 864000 * 100  # 7 days in ms
DAY = 864000 * 100
THRESH, MAXROWS, NEXTN = 10, 5, 3
WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def mt_ms(stamp):  # '2026-10-24 23:58 MT' -> UTC ms (DST aware)
    m = re.match(r'^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d) MT$', stamp or '')
    if not m: return None
    d = datetime.datetime(*map(int, m.groups()), tzinfo=MT)
    return int(d.timestamp() * 1000)

def is_tba(iso): return iso[11:] in ('04:00Z', '05:00Z')
def parse_kick(iso):
    s = iso[:16] + ':00Z' if len(iso) == 17 else iso
    try: return int(datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp() * 1000)
    except ValueError: return None

def when_short(kick, tba):  # 'Sat Oct 31 · 1:30 PM MT'; TBA day = the placeholder's UTC calendar date + 'time TBA'
    if tba:
        d = datetime.datetime.fromtimestamp(kick / 1000, UTC)
        return '%s %s %d \u00B7 time TBA' % (WD[d.weekday()], MON[d.month - 1], d.day)
    d = datetime.datetime.fromtimestamp(kick / 1000, MT)
    h = d.hour % 12 or 12
    return '%s %s %d \u00B7 %d:%02d %s MT' % (WD[d.weekday()], MON[d.month - 1], d.day, h, d.minute, 'AM' if d.hour < 12 else 'PM')

def build_games(index, bundle):
    by = {g['id']: g for g in index['games']}; out = []
    for b in bundle.get('games') or []:
        g = by.get(b['id'])
        if not g or not b.get('date'): continue
        k = parse_kick(b['date'])
        if k is None: continue
        out.append(dict(id=g['id'], week=g['week'], h=g['h'], a=g['a'], neutral=bool(g.get('neutral')), kick=k, tba=is_tba(b['date']), ip=bool(b.get('ip'))))
    return out

def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'): sys.exit(__doc__)
    tree = os.path.abspath(a[0]); now_arg = out = None
    i = 1
    while i < len(a):
        if a[i] == '--now': now_arg = a[i + 1]; i += 2
        elif a[i] == '--out': out = a[i + 1]; i += 2
        else: sys.exit('unknown arg ' + a[i])
    D = os.path.join(tree, 'data')
    ld = lambda p: json.load(open(os.path.join(D, p), encoding='utf-8'))
    index, bundle, pred = ld('whatif/index.json'), ld('sim-bundle.json'), ld('pred-teams.json')['teams']
    as_of_ms = mt_ms(index['as_of'])
    if as_of_ms is None: sys.exit('whatif/index.json as_of is not in the form YYYY-MM-DD HH:MM MT: %r' % index.get('as_of'))
    if now_arg:
        now = int(datetime.datetime.fromisoformat(now_arg).timestamp() * 1000)
    else: now = as_of_ms
    games = build_games(index, bundle)
    shards = {w: ld('whatif/' + f) for w, f in index['shards'].items()}
    def shard(w, gid): return (shards.get(str(w)) or {}).get(gid)
    by = {t['n']: t for t in bundle['teams'] if t.get('n')}
    names = index['team_names']; metrics = index['metrics']; base = index['baseline']
    def name_of(i): t = by[names[i]]; return t.get('s') or t['n']
    def started(g): return now > (g['kick'] + DAY if g['tba'] else g['kick'])
    def chance(g, side, tn, col):
        s = shard(g['week'], g['id']); l = (s or {}).get(side) or []
        for r in l:
            if r[0] == tn: return r[col]
        return base[tn][col - 1]
    teams = {}
    for tn, full in enumerate(names):
        t = by.get(full)
        if not t or not t.get('g') or t['g'] not in pred or tn >= len(base): continue
        pt = pred[t['g']]
        metric = 'cfp12' if (pt['p'] >= 0.01 or pt.get('c') is None) else 'ccg'
        col = metrics.index(metric) + 1
        # --- rootables (rootables.js compute)
        rows = []; end = as_of_ms + MS7
        for g in games:
            if g['ip'] or g['kick'] > end or started(g): continue
            if not shard(g['week'], g['id']): continue
            pH, pA = chance(g, 'h', tn, col), chance(g, 'a', tn, col)
            own = g['h'] == tn or g['a'] == tn
            rows.append(dict(id=g['id'], g=g, pH=pH, pA=pA, gap=abs(pH - pA), own=own,
                             root=g['h'] if pH >= pA else g['a'], other=g['a'] if pH >= pA else g['h']))
        big = [r for r in rows if r['gap'] >= THRESH]
        big.sort(key=lambda r: (-r['gap'], r['g']['kick'], r['id']))
        roots = [{'a': name_of(r['root']), 'x': name_of(r['other']), 'g': r['gap'], 'k': r['g']['kick'], 't': int(r['g']['tba']),
                  'd': when_short(r['g']['kick'], r['g']['tba']), 'o': int(r['own'])} for r in big[:MAXROWS]]
        # --- next games with a what-if shard, soonest first; stops at the first game without a shard
        mine = sorted([g for g in games if (g['h'] == tn or g['a'] == tn) and not g['ip'] and not started(g)], key=lambda g: g['kick'])
        nxt = []
        for g in mine[:NEXTN]:
            if not shard(g['week'], g['id']): break
            home = g['h'] == tn
            pH, pA = chance(g, 'h', tn, col), chance(g, 'a', tn, col)
            nxt.append({'o': name_of(g['a'] if home else g['h']), 'h': 2 if g['neutral'] else (1 if home else 0), 'k': g['kick'], 't': int(g['tba']),
                        'd': when_short(g['kick'], g['tba']), 'w': pH if home else pA, 'l': pA if home else pH})
        teams[t['g']] = {'m': metric, 'b': base[tn][col - 1], 'n': nxt, 'r': roots}
    doc = {'v': 1, 'as_of': index['as_of'], 'seasons': index.get('seasons'), 'teams': teams}
    out = out or os.path.join(D, 'tile-data.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='') as f: json.dump(doc, f, separators=(',', ':'), ensure_ascii=False, sort_keys=False); f.write('\n')
    print('tile-data.json: %d teams, as_of %s, %d bytes -> %s' % (len(teams), index['as_of'], os.path.getsize(out), out))

if __name__ == '__main__': main()
