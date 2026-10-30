#!/usr/bin/env python3
"""Build data/ranks.json for 'How {Team} ranks nationally' from NCAA.com FBS team stats (NCAA-only v1).
Usage: build_ranks.py --teams pred-teams.json --out data/ranks.json [--cache DIR] [--offline] [--map-report PATH]
Exit 2 on any fetch/parse/column/mapping/count failure; the old ranks.json is then left untouched (last-good)."""
import argparse, json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ncaa_base as B, time
_f = B.fetch
def _polite(url, cache, offline):
    if not offline: time.sleep(1.2)
    return _f(url, cache, offline)
B.fetch = _polite

# SPEC §2/§5 fixed order. dir is informational (NCAA's rank already encodes direction).
CATS = [
 ('so', 27,  'Scoring offense',          'PPG', 'f1',  'high'),
 ('sd', 28,  'Scoring defense',          'Avg', 'f1',  'low'),
 ('to', 21,  'Total offense',            'YPG', 'f1',  'high'),
 ('td', 22,  'Total defense',            'YPG', 'f1',  'low'),
 ('po', 25,  'Passing offense',          'YPG', 'f1',  'high'),
 ('ro', 23,  'Rushing offense',          'YPG', 'f1',  'high'),
 ('tm', 29,  'Turnover margin',          'Avg', 'pm2', 'high'),
 ('t3', 699, 'Third-down conversion %',  'Pct', 'pct', 'high'),
 ('sk', 466, 'Sacks (by defense)',       'Avg', 'f2',  'high'),
]
MIN_N = 130

def fail(msg):
    print('RANKS FAIL:', msg, file=sys.stderr); raise SystemExit(2)

def conf_ranks(rows_by_team, conf_of):
    """Conf place = 1 + number of conference members with a strictly better NCAA national rank.
    Tied (T-) when another member shares the same national rank AND NCAA marked them tied."""
    out = {}
    by_conf = {}
    for kt, (rk, t) in rows_by_team.items():
        c = conf_of.get(kt)
        if c and c != 'independents': by_conf.setdefault(c, []).append((kt, rk, t))
    for c, mem in by_conf.items():
        for kt, rk, t in mem:
            place = 1 + sum(1 for _, r2, _ in mem if r2 < rk)
            tied = t and any(k2 != kt and r2 == rk for k2, r2, _ in mem)
            out[kt] = (place, int(bool(tied)), len(mem))
    return out

def build(teams_path, cache, offline):
    KT = json.load(open(teams_path, encoding='utf-8'))['teams']
    byname = {B.norm(v['n']): k for k, v in KT.items()}; byname.update({k: k for k in KT})
    def kt_of(row): sl = row['_slug']; return B.ALIAS.get(sl) or byname.get(sl) or byname.get(B.norm(row['_name']))
    conf_of = {k: v['cs'] for k, v in KT.items()}
    cats, teams, thrus, ups, unm = [], {}, set(), set(), {}
    for k, cid, label, col, fmt, d in CATS:
        rows, u, th = B.scrape('current', dict(id=cid), cache, offline, (col, 'G'))
        ups |= u; thrus |= th
        n = len(rows)
        if n < MIN_N: fail('cat %d only %d rows' % (cid, n))
        seen, nat = set(), {}
        for row in rows:
            kt = kt_of(row)
            if kt not in KT: unm[row['_slug']] = row['_name']; continue
            if kt in seen: fail('duplicate team %s in cat %d' % (kt, cid))
            seen.add(kt)
            v = B.num(row[col])
            if v is None: fail('bad value %r for %s cat %d' % (row[col], kt, cid))
            nat[kt] = (row['_r'], row['_t'], v)
        cr = conf_ranks({kt: (r, t) for kt, (r, t, _) in nat.items()}, conf_of)
        for kt, (r, t, v) in nat.items():
            c = cr.get(kt)
            teams.setdefault(kt, {})[k] = [r, t, v] + ([c[0], c[1], c[2]] if c else [])
        cats.append(dict(k=k, id=cid, l=label, f=fmt, d=d, n=n))
    if unm: fail('unmapped NCAA teams %s' % unm)
    missing = sorted(set(KT) - set(teams))
    if missing: fail('KickTip teams with no NCAA row %s' % missing)
    if len(teams) != len(KT): fail('team count %d != %d' % (len(teams), len(KT)))
    thru = sorted(x for x in thrus if x)
    if not thru: fail('no Through games stamp')
    th = max(datetime.datetime.strptime(x, '%A, %B %d, %Y') for x in thru).strftime('%Y-%m-%d')
    names = {k: ('Miami (FL)' if k == 'miami' else v['n']) for k, v in KT.items()}
    confs = {v['cs']: v['cn'] for v in KT.values()}
    return dict(v=1, src='NCAA.com', thru=th, cats=cats, nm=names, cf={k: conf_of[k] for k in KT}, cn=confs,
                t={k: teams[k] for k in sorted(teams)})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--teams', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--cache', default=None); ap.add_argument('--offline', action='store_true')
    a = ap.parse_args()
    if a.cache: os.makedirs(a.cache, exist_ok=True)
    try:
        out = build(a.teams, a.cache, a.offline)
    except SystemExit as e:
        if e.code == 2: raise
        print('RANKS FAIL:', e, file=sys.stderr); raise SystemExit(2)
    s = json.dumps(out, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + '.tmp'; open(tmp, 'w', encoding='utf-8').write(s); os.replace(tmp, a.out)
    print('RANKS OK teams=%d cats=%d n=%s thru=%s bytes=%d' % (len(out['t']), len(out['cats']), [c['n'] for c in out['cats']], out['thru'], len(s.encode())))

if __name__ == '__main__': main()
