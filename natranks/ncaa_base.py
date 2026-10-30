#!/usr/bin/env python3
"""Build data/brag.json for the KickTip 'Bragging rights' tile from NCAA.com FBS team stat rankings.
Usage: build_brag_data.py [--teams PATH/pred-teams.json] [--out data/brag.json] [--cache DIR] [--offline]
Re-runnable: fetches every page of each fixed category, maps NCAA school names to KickTip slugs,
keeps each team's 2 best and 2 worst national ranks. Exit 2 if a fetch/parse fails or <130 teams map
(so an auto-refresh keeps the old file instead of shipping a bad one)."""
import argparse, json, os, re, sys, time, urllib.request, datetime, html as H
ROOT = 'https://www.ncaa.com/stats/football/fbs/'
BASE = ROOT + 'current/team/'
# Fixed category set. k=key, id=NCAA stat id, val=column shown, fmt, a/b=raw columns for the Why? line
CATS = [
 dict(k='so', id=27,  l='Points per game',              val='PPG',    fmt='f1',  a='Pts',  b='G',  fam='scoring'),
 dict(k='sd', id=28,  l='Points allowed per game',      val='Avg',    fmt='f1',  a='Pts',  b='G',  fam='scoring'),
 dict(k='to', id=21,  l='Total yards per game',         val='YPG',    fmt='f0',  a='YDS',  b='G',  fam='offy'),
 dict(k='ro', id=23,  l='Rushing yards per game',       val='YPG',    fmt='f0',  a='Rush Yds', b='G', fam='offy'),
 dict(k='po', id=25,  l='Passing yards per game',       val='YPG',    fmt='f0',  a='Pass Yds', b='G', fam='offy'),
 dict(k='td', id=22,  l='Yards allowed per game',       val='YPG',    fmt='f0',  a='YDS',  b='G',  fam='defy'),
 dict(k='rd', id=24,  l='Rushing yards allowed per game', val='YPG',  fmt='f0',  a='Opp Rush Yds', b='G', fam='defy'),
 dict(k='t3', id=699, l='Third-down conversions',       val='Pct',    fmt='pct', a='3rd Conv', b='3rd Att', fam='third'),
 dict(k='d3', id=701, l='Opponent third-down rate',     val='Pct',    fmt='pct', a='Opp 3rd Conv', b='Opp 3rd Att', fam='third'),
 dict(k='sa', id=468, l='Sacks allowed per game',       val='Avg',    fmt='f2',  a='Opp Sacks', b='G', fam='sacks'),
 dict(k='sk', id=466, l='Sacks per game',               val='Avg',    fmt='f2',  a='Sacks', b='G', fam='sacks'),
 dict(k='tm', id=29,  l='Turnover margin per game',     val='Avg',    fmt='pm2', a='Margin', b='G', fam='to'),
 dict(k='pn', id=697, l='Penalties per game',           val='PenPerGame', fmt='f1', a='Penalties', b='G', fam='pen'),
 dict(k='rz', id=703, l='Red-zone scoring',             val='Pct',    fmt='pct', a='RZScores', b='RZAtt', fam='rz'),
]
SEASONS = [2023, 2024, 2025]   # 2022 archive pages have no table (Creative VERIFY); trends = these + current
ALIAS = {'miami-fl':'miami','miami-oh':'miami-oh','army':'army','hawaii':'hawaii','fiu':'florida-international',
 'app-state':'app-state','ulm':'ul-monroe','la-monroe':'ul-monroe','louisiana':'louisiana','southern-miss':'southern-miss',
 'texas-am':'texas-a-m','ole-miss':'ole-miss','nc-state':'nc-state','san-jose-st':'san-jose-state','massachusetts':'massachusetts',
 'uconn':'uconn','ucf':'ucf','smu':'smu','tcu':'tcu','lsu':'lsu','byu':'byu','usc':'usc','ucla':'ucla','unlv':'unlv','utep':'utep',
 'utsa':'utsa','uab':'uab','pittsburgh':'pittsburgh','sam-houston-st':'sam-houston','sam-houston':'sam-houston','middle-tenn':'middle-tennessee',
 'western-ky':'western-kentucky','western-mich':'western-michigan','eastern-mich':'eastern-michigan','central-mich':'central-michigan',
 'northern-ill':'northern-illinois','fla-atlantic':'florida-atlantic','ga-southern':'georgia-southern','coastal-caro':'coastal-carolina',
 'south-fla':'south-florida','boston-college':'boston-college','east-carolina':'east-carolina','north-dakota-st':'north-dakota-state',
 'sacramento-st':'sacramento-state','kennesaw-st':'kennesaw-state','jacksonville-st':'jacksonville-state','new-mexico-st':'new-mexico-state',
 'appalachian-st':'app-state','louisiana-monroe':'ul-monroe','ul-monroe':'ul-monroe','southern-california':'usc','north-carolina-st':'nc-state'}

def fetch(url, cache, offline):
    fn = os.path.join(cache, re.sub(r'\W', '_', url.split('/fbs/')[1]) + '.html') if cache else None
    if offline and fn and os.path.exists(fn): return open(fn, encoding='utf-8').read()
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (KickTip stats refresh)'})
            t = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            if fn: open(fn, 'w', encoding='utf-8').write(t)
            return t
        except Exception as e:
            err = e; time.sleep(2 + 3 * i)
    raise SystemExit('fetch failed %s: %s' % (url, err))

def parse(t):
    hd = [H.unescape(x).strip() for x in re.findall(r'<th>(.*?)</th>', t)]
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', t, re.S):
        tds = re.findall(r'<td>(.*?)</td>', tr, re.S)
        if len(tds) != len(hd) or not tds: continue
        m = re.search(r'href="/schools/([^"]+)"[^>]*>([^<]*)<', tds[1])
        if not m: continue
        cells = [H.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in tds]
        rows.append(dict(zip(hd, cells), _slug=m.group(1), _name=H.unescape(m.group(2)).strip()))
    up = re.search(r'Last updated</em>\s*<em class="placeholder">([^<]+)</em>', t)
    th = re.search(r'Through games</em>\s*<em class="placeholder">([^<]+)</em>', t)
    nxt = re.search(r'stats-pager__li--next"><a href="([^"]+)"', t)
    return hd, rows, (up.group(1).strip() if up else None), (th.group(1).strip() if th else None), nxt

def num(s):
    s = s.replace(',', '').strip()
    try: return float(s)
    except ValueError: return None

def norm(s): return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('&', '').replace(' st.', ' state').replace('é', 'e').replace("'", '')).strip('-')

def scrape(season, c, cache, offline, need):
    """All rows of one category/season with NCAA ranks resolved ('-' = tied with the row above)."""
    rows, ups, ths = [], set(), set(); page = 1; url = ROOT + '%s/team/%d' % (season, c['id'])
    while url:
        t = fetch(url, cache, offline); hd, r, up, th, nxt = parse(t)
        if not r: raise SystemExit('no rows parsed: ' + url)
        for col in need:
            if col not in hd: raise SystemExit('column %r missing on %s (%s)' % (col, url, hd))
        rows += r; ups.add(up); ths.add(th); page += 1
        url = (ROOT + '%s/team/%d/p%d' % (season, c['id'], page)) if nxt and page < 6 else None
    last = None
    for i, row in enumerate(rows):
        rk = row['Rank']; tie = rk == '-'
        if tie: rk = last
        else:
            rk = int(rk); last = rk
            if i + 1 < len(rows) and rows[i + 1]['Rank'] == '-': tie = True
        row['_r'] = rk; row['_t'] = int(tie)
    return rows, ups, ths

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--teams', default='/workspace/kicktip-home7/ship7d/site/data/pred-teams.json')
    ap.add_argument('--out', default=os.path.join(here, 'data', 'brag.json'))
    ap.add_argument('--cache', default=os.path.join(here, 'cache', 'pages'))
    ap.add_argument('--offline', action='store_true', help='reuse cached current-season pages')
    ap.add_argument('--report', default=os.path.join(here, 'data', 'brag-map.json'))
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    KT = json.load(open(a.teams, encoding='utf-8'))['teams']
    byname = {norm(v['n']): k for k, v in KT.items()}; byname.update({k: k for k in KT})
    def kt_of(row): sl = row['_slug']; return ALIAS.get(sl) or byname.get(sl) or byname.get(norm(row['_name']))
    stats, ups, ths, unm, sizes = {}, set(), set(), {}, {}
    for ci, c in enumerate(CATS):
        rows, u, th = scrape('current', c, a.cache, a.offline, (c['val'], c['a'], c['b'], 'G'))
        ups |= u; ths |= th; c['_n'] = len(rows)
        # prior seasons: archives are static, always served from cache once fetched; matched by NCAA team name
        hist = {}
        for yr in SEASONS:
            hr, _, _ = scrape(yr, c, a.cache, True, ())
            sizes[yr] = max(sizes.get(yr, 0), len(hr))
            for row in hr: hist.setdefault(row['_name'], {})[yr] = [row['_r'], row['_t']]
        c['_top'] = rows
        for row in rows:
            kt = kt_of(row)
            if kt not in KT: unm[row['_slug']] = row['_name']; continue
            hs = hist.get(row['_name'], {})
            tr = [hs.get(yr) for yr in SEASONS]
            stats.setdefault(kt, {})[c['k']] = dict(ci=ci, r=row['_r'], t=row['_t'], v=num(row[c['val']]), a=num(row[c['a']]), b=num(row[c['b']]),
                g=num(row['G']), n=len(rows), tr=tr, ok=sum(1 for x in tr if x) >= 2)
    up = sorted(x for x in ups if x)[-1]
    asof = datetime.datetime.strptime(up, '%A, %B %d, %Y %I:%M %p').strftime('%Y-%m-%dT%H:%M:00-04:00')  # NCAA stamps are US Eastern
    teams, hidden = {}, []
    for kt, st in sorted(stats.items()):
        g = max((s['g'] or 0) for s in st.values())
        if g < 4: teams[kt] = 0; hidden.append(kt); continue
        key = lambda s: (s['r'] / s['n'], s['ci'])   # current-season rank only; history never affects selection
        def choose(cands, excl):
            out, fams = [], set()
            for s in cands:
                if s['ci'] in excl or CATS[s['ci']]['fam'] in fams: continue
                out.append(s); fams.add(CATS[s['ci']]['fam'])
                if len(out) == 2: break
            return out
        best = choose(sorted(st.values(), key=key), set())
        worst = choose(sorted(st.values(), key=lambda s: (-s['r'] / s['n'], s['ci'])), {s['ci'] for s in best})
        def pack(s, good):
            above = 0
            if good and s['r'] <= 3 and s['r'] > 1:
                above = [kt_of(r) or r['_name'] for r in CATS[s['ci']]['_top'] if r['_r'] < s['r']]
            return [s['ci'], s['r'], s['t'], s['v'], s['a'], s['b'], s['g'], above, s['tr'] if s['ok'] else 0]
        teams[kt] = [pack(s, True) for s in best] + [pack(s, False) for s in worst]
    names = {k: KT[k]['n'] for k in KT}
    out = dict(v=2, src='NCAA.com', asof=asof, thru=sorted(x for x in ths if x)[-1], n=max(c['_n'] for c in CATS), yrs=SEASONS + [int(asof[:4])],
               cats=[[c['k'], c['l'], c['fmt'], c['id']] for c in CATS], nm={k: names[k] for k in sorted(teams)}, t=teams)
    missing = sorted(set(KT) - set(teams))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    s = json.dumps(out, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    json.dump(dict(mapped=len(teams), kt_total=len(KT), ncaa_unmapped=unm, kt_missing=missing, hidden_lt4_games=hidden, season_sizes=sizes,
                   no_trend_any=sorted(k for k, v in teams.items() if v and not any(p[8] for p in v))), open(a.report, 'w'), indent=1, sort_keys=True)
    print('teams', len(teams), 'of', len(KT), 'unmapped', unm, 'kt missing', missing, 'hidden', hidden, 'sizes', sizes, 'bytes', len(s.encode()))
    if len(teams) < 130: raise SystemExit(2)
    tmp = a.out + '.tmp'; open(tmp, 'w', encoding='utf-8').write(s); os.replace(tmp, a.out)

if __name__ == '__main__': main()
