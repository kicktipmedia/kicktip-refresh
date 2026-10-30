#!/usr/bin/env python3
"""The MSM Rankings (MSM Top 25), v3. ESPN public JSON only. Conference-blind: no conference data goes into any rating.
No polls, rankings, betting lines or preseason priors. Ratings measure team strength; no score or spread predictions."""
import os, json, urllib.request, csv, sys, random, math, numpy as np
from concurrent.futures import ThreadPoolExecutor
YEAR=int(sys.argv[1]) if len(sys.argv)>1 else 2026
RIDGE=0.3; K=28.0; S=14.0; GARBAGE=25; REC_MIN=0.75; H2H_GAP=1.0
W={'resume':0.60,'control':0.25,'eff':0.15}; W_SOR=0.7; W_COLLEY=0.3; BENCH_RANK=25
B="https://site.api.espn.com/apis/site/v2/sports/football/college-football/"
CACHE=f"cache_{YEAR}"; os.makedirs(CACHE,exist_ok=True)
def get(u,cache=None):
    if cache and os.path.exists(cache): return json.load(open(cache))
    err=None
    for _ in range(3):
        try: d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30)); break
        except Exception as e: err=e
    else: raise err
    if cache: json.dump(d,open(cache,'w'))
    return d
fbs={}; conf={}   # conf used ONLY in the post-hoc audit
st=get(f"https://site.api.espn.com/apis/v2/sports/football/college-football/standings?group=80&season={YEAR}")
def walk(x,cn):
    if isinstance(x,dict):
        if isinstance(x.get('team'),dict) and 'id' in x['team']: fbs[x['team']['id']]=x['team']['displayName']; conf[x['team']['id']]=cn
        for v in x.values(): walk(v,cn)
    elif isinstance(x,list):
        for v in x: walk(v,cn)
for c in st['children']: walk(c,c.get('abbreviation',c.get('name')))
games={}
for wk in range(1,17):
    for e in get(B+f"scoreboard?groups=80&week={wk}&year={YEAR}&seasontype=2&limit=400").get('events',[]):
        c=e['competitions'][0]
        if not c['status']['type']['completed']: continue
        h=[x for x in c['competitors'] if x['homeAway']=='home'][0]; a=[x for x in c['competitors'] if x['homeAway']=='away'][0]
        games[e['id']]=dict(id=e['id'],date=e['date'][:10],home=h['team']['id'],away=a['team']['id'],hn=h['team']['displayName'],an=a['team']['displayName'],
            hs=int(h['score']),as_=int(a['score']),neutral=c.get('neutralSite',False))
G=sorted(games.values(),key=lambda g:g['date'])
def box(g):
    try: d=get(B+f"summary?event={g['id']}",f"{CACHE}/{g['id']}.json")
    except Exception: return
    s={}
    for t in d.get('boxscore',{}).get('teams',[]):
        v={x['name']:x['displayValue'] for x in t['statistics']}
        try: s[t['team']['id']]=dict(yds=int(v['totalYards']),plays=int(v['rushingAttempts'])+int(v['completionAttempts'].split('/')[1].split('-')[-1]))
        except Exception: pass
    dr={}
    for x in d.get('drives',{}).get('previous',[]):
        tid=x.get('team',{}).get('id'); dr[tid]=dr.get(tid,0)+1
    for tid in s: s[tid]['drives']=dr.get(tid,0)
    g['box']=s
    q3=(0,0)   # score (home,away) at end of 3rd quarter from scoring plays
    for p in d.get('scoringPlays',[]):
        if p['period']['number']<=3: q3=(int(p['homeScore']),int(p['awayScore']))
    g['q3']=q3 if d.get('scoringPlays') is not None else None
with ThreadPoolExecutor(12) as ex: list(ex.map(box,G))
json.dump(G,open(f'games_v3_{YEAR}.json','w'))
FCS='FCS'; key=lambda i: i if i in fbs else FCS
teams=sorted(fbs)+[FCS]; ix={t:k for k,t in enumerate(teams)}; n=len(teams)
dates=sorted(set(g['date'] for g in G)); d0,d1=dates[0],dates[-1]
import datetime as dt
D=lambda s: dt.date.fromisoformat(s)
span=max(1,(D(d1)-D(d0)).days)
for g in G: g['w']=REC_MIN+(1-REC_MIN)*(D(g['date'])-D(d0)).days/span   # recency: oldest 0.75, newest 1.0
f=lambda m: math.copysign(K*(1-math.exp(-abs(m)/S)),m)   # diminishing returns, no hard cap
def control(g):
    fin=g['hs']-g['as_']; q=g.get('q3')
    if q is None: return f(fin)
    q3m=q[0]-q[1]
    if abs(q3m)>=GARBAGE and (q3m>0)==(fin>0): fin=q3m   # garbage-time filter: ignore 4th quarter of decided games
    return 0.5*f(q3m)+0.5*f(fin)                          # game control: how far ahead through 3 qtrs + finish
def wridge(rows,y,w,free=1):
    X=np.array(rows);y=np.array(y);Wt=np.array(w);P=np.eye(X.shape[1])*RIDGE
    for k in range(free): P[-1-k,-1-k]=0
    return np.linalg.solve(X.T@(X*Wt[:,None])+P,X.T@(Wt*y))
R=[];Y=[];Wg=[]
for g in G:
    r=np.zeros(n+1); r[ix[key(g['home'])]]+=1; r[ix[key(g['away'])]]-=1; r[n]=0 if g['neutral'] else 1
    R.append(r); Y.append(control(g)); Wg.append(g['w'])
bm=wridge(R,Y,Wg); strength=bm[:n]; hfa=bm[n]
# win-probability scale fitted from our own games (logistic on strength difference)
diff=np.array([strength[ix[key(g['home'])]]-strength[ix[key(g['away'])]]+(0 if g['neutral'] else hfa) for g in G]); win=np.array([g['hs']>g['as_'] for g in G])
def ll(s): p=1/(1+np.exp(-diff/s)); p=np.clip(p,1e-6,1-1e-6); return np.sum(win*np.log(p)+(~win)*np.log(1-p))
SIG=max(np.arange(2,30,0.25),key=ll)
F=[ix[t] for t in fbs]
bench=sorted(strength[F],reverse=True)[BENCH_RANK-1]
# Strength of Record: wins above what a typical #25 team would get vs the same opponents at the same sites
sor={t:0.0 for t in fbs}; opp={t:[] for t in fbs}; rec={t:[0,0] for t in fbs}; h2h={}
for g in G:
    for t,o,won,side in ((g['home'],g['away'],g['hs']>g['as_'],1),(g['away'],g['home'],g['as_']>g['hs'],-1)):
        if t not in fbs: continue
        edge=0 if g['neutral'] else side*hfa
        p=1/(1+math.exp(-(bench-strength[ix[key(o)]]+edge)/SIG))
        sor[t]+=(1 if won else 0)-p; opp[t].append(o); rec[t][0 if won else 1]+=1
        if won: h2h[(t,o)]=h2h.get((t,o),0)+1
C=2*np.eye(n); b=np.ones(n)
for g in G:
    h,a=ix[key(g['home'])],ix[key(g['away'])]
    if h==a: continue
    C[h,h]+=1;C[a,a]+=1;C[h,a]-=1;C[a,h]-=1
    w_,l_=(h,a) if g['hs']>g['as_'] else (a,h); b[w_]+=.5; b[l_]-=.5
colley=np.linalg.solve(C,b)
def adj(statfn):
    R=[];Y=[];Wt=[]
    for g in G:
        bx=g.get('box',{})
        for o,d,home in ((g['home'],g['away'],1),(g['away'],g['home'],-1)):
            v=statfn(g,o,bx)
            if v is None: continue
            r=np.zeros(2*n+2); r[ix[key(o)]]=1; r[n+ix[key(d)]]=-1; r[2*n]=0 if g['neutral'] else home; r[2*n+1]=1
            R.append(r);Y.append(v);Wt.append(g['w'])
    bb=wridge(R,Y,Wt,2); return bb[:n]+bb[n:2*n]
ypp=lambda g,o,bx: bx[o]['yds']/bx[o]['plays'] if o in bx and bx[o]['plays']>20 else None
ppd=lambda g,o,bx: (g['hs'] if o==g['home'] else g['as_'])/bx[o]['drives'] if o in bx and bx[o].get('drives',0)>=5 else None
zf=lambda v:(v-v[F].mean())/v[F].std()
eff=(zf(adj(ypp))+zf(adj(ppd)))/2
sor_v=np.zeros(n); 
for t in fbs: sor_v[ix[t]]=sor[t]
resume=W_SOR*zf(sor_v)+W_COLLEY*zf(colley)
comp=W['resume']*zf(resume)+W['control']*zf(strength)+W['eff']*zf(eff)
rating=comp*10+50
order=sorted(fbs,key=lambda t:-rating[ix[t]])
# head-to-head tiebreak (CFP-style): adjacent teams within H2H_GAP rating points; head-to-head winner goes ahead
swaps=[]
for _ in range(3):
    for k in range(len(order)-1):
        a,b_=order[k],order[k+1]
        if rating[ix[a]]-rating[ix[b_]]<=H2H_GAP and h2h.get((b_,a),0)>h2h.get((a,b_),0):
            order[k],order[k+1]=b_,a; swaps.append(f"{fbs[b_]} over {fbs[a]}")
# SOS played / remaining (display only)
sos={t:np.mean([rating[ix[key(o)]] for o in opp[t]]) for t in fbs}
def sched(t): return t,get(B+f"teams/{t}/schedule?season={YEAR}",f"{CACHE}/sched_{t}.json")
with ThreadPoolExecutor(12) as ex: Sd=dict(ex.map(sched,list(fbs)))
rem={};espn_done={}
for t,d in Sd.items():
    fut=[];done=0
    for e in d.get('events',[]):
        c=e['competitions'][0]
        if c['status']['type']['completed']: done+=1; continue
        o=[x['team']['id'] for x in c['competitors'] if x['team']['id']!=t]
        if o: fut.append(rating[ix[key(o[0])]])
    rem[t]=np.mean(fut) if fut else np.nan; espn_done[t]=done
rk=lambda d:{t:i+1 for i,t in enumerate(sorted(d,key=lambda t:-(d[t] if not np.isnan(d[t]) else -1e9)))}
sr,rr=rk(sos),rk(rem)
hdr=['rank','team','record','msm_rating','sor_wins_above_top25','colley','game_control_pts','eff_z','sos_played','sos_played_rank','remaining_sos','remaining_sos_rank']
rows=[[k,fbs[t],f"{rec[t][0]}-{rec[t][1]}",round(rating[ix[t]],1),round(sor[t],2),round(colley[ix[t]],3),round(strength[ix[t]],1),round(eff[ix[t]],2),round(sos[t],1),sr[t],round(rem[t],1),rr[t]] for k,t in enumerate(order,1)]
for fn,rs in ((f'msm_all_v3_{YEAR}.csv',rows),(f'msm_top25_v3_{YEAR}_published.csv',rows[:25])):
    with open(fn,'w',newline='') as fh: w=csv.writer(fh); w.writerow(hdr); w.writerows(rs)
aud=[f"games={len(G)} fbs_teams={len(fbs)} home_edge={hfa:.2f} win_prob_scale={SIG} top25_benchmark_strength={bench:.2f} q3_missing={sum(1 for g in G if g.get('q3') is None)} box_missing={sum(1 for g in G if len(g.get('box',{}))<2)}",
     f"garbage-time filtered games={sum(1 for g in G if g.get('q3') and abs(g['q3'][0]-g['q3'][1])>=GARBAGE)}", f"FCS pool rating={rating[ix[FCS]]:.1f}",
     f"head-to-head swaps: {swaps or 'none'}"]
mism=[(fbs[t],len(opp[t]),espn_done[t]) for t in fbs if len(opp[t])!=espn_done[t]]
aud.append(f"completeness (all teams vs ESPN team schedules): {mism or 'all match'}")
random.seed(YEAR+3); samp=random.sample(sorted(fbs),10)
aud.append("spot-check 10 random: "+", ".join(f"{fbs[t]} {len(opp[t])}/{espn_done[t]}" for t in samp))
# conference residual audit, two scales: (a) game-control units (v3 strength model) (b) capped-21 points for comparison with v2
pred=lambda g: strength[ix[key(g['home'])]]-strength[ix[key(g['away'])]]+(0 if g['neutral'] else hfa)
res={}
for g in G:
    h,a=g['home'],g['away']
    if h in fbs and a in fbs and conf[h]!=conf[a]:
        r=control(g)-pred(g); res.setdefault(conf[h],[]).append(r); res.setdefault(conf[a],[]).append(-r)
aud.append("conference audit (mean residual, game-control pts, non-conference FBS games; reported, not corrected):")
for c in sorted(res): aud.append(f"  {c:10s} resid={np.mean(res[c]):+.2f} n={len(res[c])}")
open(f'audit_v3_{YEAR}.txt','w').write("\n".join(aud)); print("\n".join(aud))
