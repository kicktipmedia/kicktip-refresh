#!/usr/bin/env python3
"""Exporter for data/tb/history.json (Set 3c, tool #25 team_history), seasons 2021-2025 only (O-H1).
  python3 gen_history.py --pipeline <pipeline root with data/store/prior/{games,teams,cfp}_{yr}.json and data/ref/conf_2026.json> --bundle <site data/sim-bundle.json> --out <data/tb/history.json>
Free source only: the pipeline's own store/prior files (already written by the pipeline; no network, no new source).
Records: every game in games_{yr} (regular season and conference championship games; the prior files carry no bowl or playoff games).
  A season is counted for a team only when teams_{yr} puts it in an FBS conference (or the FBS independents): a team that was FCS that season has no record row (its FCS games are not in the file).
Conference membership by season: teams_{yr}.conf (ESPN group id) mapped to KickTip conference codes. conf_ok[yr] is false when any FBS team that season has no mapped conference;
  the tool then keeps conference rows (champions, conference by season) dark for that season. Nothing is guessed from the 2026 list.
Conference champions: the one game per conference in December between two members of that conference that ESPN does not mark as a conference game (cc false) = the conference championship game.
  Every conference with a conference championship game must have exactly one per season, otherwise that season's champ rows are left out (champ_ok false).
Playoff trips: cfp_{yr}.teams. Seasons whose cfp file lists no teams are not covered (cfp_seasons lists only the covered ones).
Series rows s["a|b"] (slugs sorted): every game between two current FBS teams: [season - 2000, 0 if a won else 1, winner points, loser points], oldest first. No dates.
Fail closed: any assert stops the export (nothing written). Size: under 160 KB (160,000 bytes), asserted."""
import argparse, json, os, collections
ap = argparse.ArgumentParser(); ap.add_argument('--pipeline', required=True); ap.add_argument('--bundle', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
P = os.path.join(a.pipeline, 'data', 'store', 'prior'); SEASONS = [2021, 2022, 2023, 2024, 2025]
conf26 = json.load(open(os.path.join(a.pipeline, 'data', 'ref', 'conf_2026.json')))
B = json.load(open(a.bundle)); T = B['teams']; FCS = B['fcs']
byname = {t['n']: i for i, t in enumerate(T)}
slug_of = {}
for full, v in conf26.items():
    assert full in byname, full; slug_of[str(v['id'])] = T[byname[full]]['g']
assert len(slug_of) == 138
GROUP = {'1': 'acc', '4': 'big12', '5': 'big10', '8': 'sec', '9': 'pac12', '12': 'usa', '15': 'midam', '17': 'mwest', '37': 'belt', '151': 'American', '18': 'ind'}
codes = {c['code']: c for c in B['confs']}; assert set(GROUP.values()) <= set(codes), set(GROUP.values()) - set(codes)
t = collections.defaultdict(lambda: {'conf': {}, 'rec': {}, 'cfp': [], 'champ': []})
s = collections.defaultdict(list); conf_ok = {}; champ_ok = {}; champ = {}; cfp_seasons = []
for yr in SEASONS:
    TM = json.load(open(os.path.join(P, 'teams_%d.json' % yr))); G = json.load(open(os.path.join(P, 'games_%d.json' % yr))); CF = json.load(open(os.path.join(P, 'cfp_%d.json' % yr)))
    ids = [g['id'] for g in G]; assert len(ids) == len(set(ids)), 'duplicate game ids %d' % yr
    fbs = {k: GROUP[v['conf']] for k, v in TM.items() if v.get('conf') in GROUP}   # FBS that season (ESPN id -> KickTip code)
    mine = {k: c for k, c in fbs.items() if k in slug_of}                          # current FBS teams that were FBS that season
    conf_ok[yr] = all(k in fbs for k in slug_of if k in TM and TM[k].get('conf') in GROUP) and len(fbs) >= 120
    for k, c in mine.items(): t[slug_of[k]]['conf'][str(yr)] = c
    W = collections.Counter(); L = collections.Counter(); ccg = collections.defaultdict(list)
    for g in sorted(G, key=lambda g: (g['date'], g['id'])):
        h, w, hs, as_ = str(g['home']), str(g['away']), g['hs'], g['as_']
        assert isinstance(hs, int) and isinstance(as_, int) and hs != as_, 'bad score %s' % g['id']
        win, los = (h, w) if hs > as_ else (w, h); ws, ls = max(hs, as_), min(hs, as_)
        W[win] += 1; L[los] += 1
        if h in fbs and w in fbs and fbs[h] == fbs[w] and fbs[h] != 'ind' and not g['cc'] and g['date'][5:7] == '12': ccg[fbs[h]].append(slug_of.get(win))
        if h in slug_of and w in slug_of:
            sa, sb = sorted((slug_of[h], slug_of[w])); s[sa + '|' + sb].append([yr - 2000, 0 if slug_of[win] == sa else 1, ws, ls])
    for k in mine: t[slug_of[k]]['rec'][str(yr)] = [W[k], L[k]]
    size = collections.Counter(fbs.values()); want = sorted(c for c in size if c != 'ind' and size[c] >= 8)   # a conference of 2 (Pac-12 in 2024-25) plays no conference championship game
    champ_ok[yr] = conf_ok[yr] and sorted(ccg) == want and all(len(v) == 1 and v[0] for v in ccg.values())
    if champ_ok[yr]:
        champ[str(yr)] = {c: v[0] for c, v in sorted(ccg.items())}
        for c, v in ccg.items(): t[v[0]]['champ'].append(yr)
    if CF.get('teams'):
        cfp_seasons.append(yr)
        for k in CF['teams']:
            if k in slug_of: t[slug_of[k]]['cfp'].append(yr)
out = {'asof': B['as_of'], 'seasons': SEASONS, 'cfp_seasons': cfp_seasons, 'conf_ok': {str(y): conf_ok[y] for y in SEASONS}, 'champ_ok': {str(y): champ_ok[y] for y in SEASONS},
       'doc': 'Set 3c team history, seasons 2021-2025. t[slug]: conf (season -> KickTip conference code, from that season\'s membership), rec (season -> [wins, losses], regular season and conference championship games; bowl and playoff games are not in the source), cfp (playoff seasons, covered seasons only: cfp_seasons), champ (conference champion seasons). champ[season][conf] = champion. s["a|b"] (a < b) = [season - 2000, winner (0 = a, 1 = b), winner points, loser points]. Source: the KickTip pipeline prior-season files.',
       't': {k: t[k] for k in sorted(t)}, 'champ': champ, 's': {k: s[k] for k in sorted(s)}}
txt = json.dumps(out, separators=(',', ':'), sort_keys=False) + '\n'
assert len(txt.encode()) < 160 * 1000, "history.json is %d bytes (cap: under 160 KB)" % len(txt.encode())
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); open(a.out, 'w').write(txt)
print('history.json %d bytes; teams %d; series %d; cfp seasons %s; conf_ok %s; champ_ok %s' % (len(txt.encode()), len(out['t']), len(out['s']), cfp_seasons, out['conf_ok'], out['champ_ok']))
