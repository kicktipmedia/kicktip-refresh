#!/usr/bin/env python3
"""Writes <site>/data/msm-rankings.json for /playoff/ from the same published MSM Top 25 CSV that feeds /rankings/.
Usage: python3 playoff_data.py <site_dir> [edition label]
Ranks 1-25 come from msm_top25_v3_2026_published.csv (exactly what /rankings/ shows); 26+ from msm_all_v3_2026.csv.
Conference map: conf_2026.json (ESPN standings, display only; the rankings stay conference-blind)."""
import csv, json, sys, os, datetime
D=os.path.dirname(os.path.abspath(__file__))
site=sys.argv[1]; ed=sys.argv[2] if len(sys.argv)>2 else 'first edition'
conf=json.load(open(os.path.join(D,'conf_2026.json')))
pub=list(csv.DictReader(open(os.path.join(D,'msm_top25_v3_2026_published.csv'))))
allr=list(csv.DictReader(open(os.path.join(D,'msm_all_v3_2026.csv'))))
seen={r['team'] for r in pub}; rows=pub+[r for r in allr if r['team'] not in seen]
out=[]
for i,r in enumerate(rows,1):
    c=conf[r['team']]
    out.append({'r':i,'n':r['team'],'s':c['loc'],'rec':r['record'],'c':c['conf'],'id':c.get('id','')})
p=os.path.join(D,'msm_top25_v3_2026_published.csv')
upd=datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat()
os.makedirs(os.path.join(site,'data'),exist_ok=True)
json.dump({'edition':ed,'updated':upd,'teams':out},open(os.path.join(site,'data','msm-rankings.json'),'w'),separators=(',',':'))
print('wrote',len(out),'teams, updated',upd)

# --- next103: Playoff Picture summary lines (same rules as /playoff-v102b.js). Rewrites text between <!--po--> and <!--/po--> markers.
P4=['acc','big10','big12','sec'];G6=['American','usa','midam','mwest','pac12','belt']
def field(T):
    auto={}
    for c in P4:
        t=next((x for x in T if x['c']==c),None)
        if t: auto[t['n']]=1
    g=next((x for x in T if x['c'] in G6),None)
    if g: auto[g['n']]=1
    nd=next((x for x in T if x['c']=='ind' and x['s']=='Notre Dame' and x['r']<=12),None)
    if nd: auto[nd['n']]=1
    F=[x for x in T if x['n'] in auto]
    for x in T:
        if len(F)<12 and x['n'] not in auto: F.append(x)
    F.sort(key=lambda x:x['r'])
    F=[x for x in F if x['r']<=12 or x['n'] not in auto]+[x for x in F if x['r']>12 and x['n'] in auto]
    out=[x for x in T if x not in F]
    return F,out
def status(T,F,out,name):
    t=next(x for x in T if x['n']==name)
    if t in F: return f"{t['s']} No. {F.index(t)+1} seed"
    k=out.index(t)+1
    o={1:'first',2:'2nd',3:'3rd'}.get(k,f'{k}th')
    return f"{t['s']} {o} team out" if k<=8 else None
import re as _re
T=out; F,OUT=field(T)
parts=[s for s in (status(T,F,OUT,n) for n in ['BYU Cougars','Utah Utes','Utah State Aggies']) if s]
home='Playoff Picture: '+' · '.join(parts)
card='If the season ended today: '+', '.join(parts)+'. See the full 12-team field.'
for rel,txt in [('index.html',home),('rankings/index.html',card)]:
    f=os.path.join(site,rel)
    if os.path.exists(f):
        h=open(f).read();h2=_re.sub(r'<!--po-->.*?<!--/po-->','<!--po-->'+txt+'<!--/po-->',h,flags=_re.S)
        if h2!=h: open(f,'w').write(h2);print('updated',rel,':',txt)
