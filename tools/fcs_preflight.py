#!/usr/bin/env python3
"""fcs_preflight.py <site_dir>: exit 1 if the data live rootables.js / og cards / tile-data consume would show a non-FBS side.
Mirrors rootables.js: games from data/whatif/index.json that have a shard, kickoff within 7 days of index.as_of, not started."""
import json,sys,datetime,re
R=sys.argv[1]; ix=json.load(open(R+'/data/whatif/index.json')); b=json.load(open(R+'/data/sim-bundle.json'))
by={t['n']:t for t in b['teams'] if t.get('n')}; names=ix['team_names']
m=re.match(r'(\d{4}-\d\d-\d\d) (\d\d):(\d\d)',ix['as_of']); asof=datetime.datetime.fromisoformat(m.group(1)+'T'+m.group(2)+':'+m.group(3)+':00-06:00' if 'MT' in ix['as_of'] else ix['as_of'])
kick={str(g.get('id')):g.get('date') for g in b.get('games',[])}
bad=[]
for g in ix['games']:
    if str(g['week']) not in ix['shards']: continue
    sides=[names[g['h']],names[g['a']]]
    if all((by.get(s) or {}).get('g') for s in sides): continue
    k=kick.get(str(g['id'])); kd=datetime.datetime.fromisoformat(k.replace('Z','+00:00')) if k else None
    within=kd is not None and asof<=kd<=asof+datetime.timedelta(days=7)
    bad.append((within,g['week'],sides,k))
win=[x for x in bad if x[0]]
for x in bad: print(('IN 7-DAY WINDOW ' if x[0] else 'later           ')+'week %s %s vs %s kick %s'%(x[1],x[2][0],x[2][1],x[3]))
td=json.load(open(R+'/data/tile-data.json')); tr=sum(1 for t in td['teams'].values() for r in t.get('r',[]) if not (by.get(next((n for n in by if (by[n].get('s') or n)==r['a']),''),{}) or {}).get('g') or 'FCS' in r['a']+r['x'])
print('tile-data rows naming a non-FBS side:',tr)
import glob; og=[p for p in glob.glob(R+'/og/rootables/*.json')+glob.glob(R+'/data/og-cards.json') if 'FCS opponent' in open(p).read()]
print('og card data mentioning FCS opponent:',og)
import subprocess,os
# filtered output: the SITE's own assets/rootables.js compute() (team pages, share cards, baked HTML) for every FBS team
u=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','tree','tests','fbsfilter_unit.js')
p=subprocess.run(['node',u,R,os.path.join(R,'assets/rootables.js')],capture_output=True,text=True); print(p.stdout.strip()); rows_ok=p.returncode==0
def rbsec(t):
    i=t.find('id="rootables"'); return t[i:t.find('</section>',i)] if i>=0 else ''
html=[q for q in glob.glob(R+'/team/*/index.html') if 'FCS opponent' in rbsec(open(q).read())]
print('team pages with FCS opponent after #rootables (baked rootables card only):',len(html),html[:3])
print('note: non-FBS game in the 7-day window:',bool(win),'(allowed only because the computed rows above exclude it)')
fail=(not rows_ok) or tr or og or html
print('PREFLIGHT','FAIL' if fail else 'PASS'); sys.exit(1 if fail else 0)
