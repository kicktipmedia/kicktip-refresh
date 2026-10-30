#!/usr/bin/env python3
"""Exporter for data/tb/team-stats.json (Set 3b, tool #26 team_stats). Run in the refresh step right after sim-bundle.json is written.
  python3 gen_team_stats.py --pipeline <pipeline root with data/store/games_rated.json, data/ref/conf_2026.json> --bundle <site data/sim-bundle.json> --out <data/tb/team-stats.json>
No new source and no network: totals are summed from the pipeline's own games_rated.json (scores plus ESPN box yds/plays), the file the refresh already wrote.
Fail-closed: every game must map to a sim-bundle team pair and the scores must equal sim-bundle.played exactly (same run), otherwise nothing is written.
t[slug]   = totals in games against FBS teams (vs_fbs:true); all[slug] = totals in all games (FCS opponents included).
Fields: g games counted, pf/pa points for/against, yds/ya yards gained/allowed, pl/pla plays run/faced, nb games left out because their box data is missing (not counted anywhere else).
Rates (per game, per play, margin) are computed in the browser. Nothing here ships (tools/ is never copied into a build)."""
import argparse, json, os, collections
ap = argparse.ArgumentParser(); ap.add_argument('--pipeline', required=True); ap.add_argument('--bundle', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
G = json.load(open(os.path.join(a.pipeline, 'data', 'store', 'games_rated.json')))
conf = json.load(open(os.path.join(a.pipeline, 'data', 'ref', 'conf_2026.json')))
B = json.load(open(a.bundle)); T = B['teams']; FCS = B['fcs']
byname = {t['n']: i for i, t in enumerate(T)}
idmap = {}
for full, v in conf.items():
    assert full in byname, 'conf_2026 team not in the bundle: ' + full
    idmap[str(v['id'])] = byname[full]
assert len(idmap) == len(T) - 1 == 138, 'FBS team count'
def ix(espn): return idmap.get(str(espn), FCS)
# fail closed: the games file must be this bundle's run (same played rows: home, away, scores)
want = collections.Counter(tuple(p[:4]) for p in B['played'])
have = collections.Counter((ix(g['home']), ix(g['away']), g['hs'], g['as_']) for g in G)
assert want == have, 'games_rated.json does not match sim-bundle.played (not this bundle\'s run): %d vs %d rows, %d differ' % (sum(want.values()), sum(have.values()), sum((want - have).values()) + sum((have - want).values()))
Z = lambda: {'g': 0, 'pf': 0, 'pa': 0, 'yds': 0, 'ya': 0, 'pl': 0, 'pla': 0, 'nb': 0}
fbs = {i: Z() for i in range(len(T)) if i != FCS}; alls = {i: Z() for i in fbs}
def okbox(b, k): v = (b or {}).get(str(k)); return isinstance(v, dict) and isinstance(v.get('yds'), int) and isinstance(v.get('plays'), int) and v['plays'] > 0
for g in sorted(G, key=lambda g: (g['date'], g['id'])):
    h, w = ix(g['home']), ix(g['away'])
    for me, op, ek, eo, pf, pa in ((h, w, g['home'], g['away'], g['hs'], g['as_']), (w, h, g['away'], g['home'], g['as_'], g['hs'])):
        if me == FCS: continue
        good = okbox(g.get('box'), ek) and okbox(g.get('box'), eo)
        for tgt in ([fbs[me], alls[me]] if op != FCS else [alls[me]]):
            if not good: tgt['nb'] += 1; continue
            tgt['g'] += 1; tgt['pf'] += pf; tgt['pa'] += pa
            tgt['yds'] += g['box'][str(ek)]['yds']; tgt['ya'] += g['box'][str(eo)]['yds']; tgt['pl'] += g['box'][str(ek)]['plays']; tgt['pla'] += g['box'][str(eo)]['plays']
slug = lambda i: T[i]['g']
out = {'v': 1, 'asof': B['as_of'], 'vs_fbs': True, 'n': len(fbs),
       'doc': 'Set 3b team-stats. t[slug] = season totals in games against FBS teams; all[slug] = totals in all games (FCS opponents included). g games, pf/pa points for/against, yds/ya yards gained/allowed, pl/pla plays run/faced, nb games left out for missing box data. Raw numbers, not adjusted for opponents. Source: the KickTip pipeline games file (scores and box totals).',
       't': {slug(i): fbs[i] for i in sorted(fbs, key=slug)}, 'all': {slug(i): alls[i] for i in sorted(alls, key=slug)}}
json.dump(out, open(a.out, 'w'), separators=(',', ':'))
print('wrote', a.out, os.path.getsize(a.out), 'bytes teams', len(fbs), 'games', len(G))
