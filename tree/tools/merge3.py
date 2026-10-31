#!/usr/bin/env python3
"""3-way merge: live (L) + delta S0->S1.  usage: merge3.py L S0 S1 OUT ; copies L to OUT first (done by caller), writes merged files.
Only touches files where S0 != S1 (byte). JSON: leaf-wise 3-way with conflict list; text: git merge-file."""
import sys, os, json, subprocess, tempfile, shutil, re
L, S0, S1, OUT = sys.argv[1:5]
def walk(t): return sorted(os.path.relpath(os.path.join(d,f),t) for d,_,x in os.walk(t) for f in x)
def rd(p): return open(p,'rb').read() if os.path.exists(p) else None
changed=[]; 
for f in sorted(set(walk(S0))|set(walk(S1))):
    a,b=rd(S0+'/'+f),rd(S1+'/'+f)
    if a!=b: changed.append(f)
TOK=re.compile(r'\?v=[0-9a-f]{10}'); REF=re.compile(r'((?:/assets|/data)/[A-Za-z0-9_./-]+?\.(?:js|css|json|png|svg|webp|ico))\?v=([0-9a-f]{10})'); REF2=re.compile(r'((?:/assets|/data)/[A-Za-z0-9_./-]+?\.(?:js|css|json|png|svg|webp|ico))\?v=X')
SKIP={'assets/lg.js'}; MANUAL={'method/index.html'}
GM={}
for _f in walk(L):
    if _f.endswith('.html'):
        for m in REF.finditer(open(L+'/'+_f,encoding='utf-8').read()): GM.setdefault(m.group(1),m.group(2))
PAIRS=[tuple(x) for x in json.loads(sys.argv[6])] if len(sys.argv)>6 else [('Sat, Oct 24, 2026, 11:58 PM MT','Tue, Oct 27, 2026, 5:58 PM MT'),('Oct 24, 2026, 11:58 PM MT','Oct 27, 2026, 5:58 PM MT'),('Oct 24, 11:58 PM MT','Oct 27, 5:58 PM MT'),('2026-10-24 23:58 MT','2026-10-27 17:58 MT')]
def pre(b,new):
    t=b.decode('utf-8')
    for i,(o,n) in enumerate(PAIRS): t=t.replace(n if new else o,'@@ASOF%d@@'%i)
    return t.encode('utf-8')
def post(t):
    for i,(o,n) in enumerate(PAIRS): t=t.replace('@@ASOF%d@@'%i,n)
    return t.replace('effectively eliminated (<0.05%)','under 0.05% chance')
rep={'skipped':[],'taken':[], 'merged':[], 'conflict':[], 'missing_live':[], 'json_conflicts':{}}
def jm(l,a,b,path,conf):
    if a==b: return l
    if l==a: return b
    if isinstance(l,dict) and isinstance(a,dict) and isinstance(b,dict):
        out={}
        for k in list(l)+[k for k in b if k not in l]:
            lv=l.get(k,'\0'); av=a.get(k,'\0'); bv=b.get(k,'\0')
            if k not in l:
                if k in a: continue          # deleted in live: keep deleted
                out[k]=b[k]; continue        # added by S1 only
            if k not in b and k in a: 
                continue                     # S1 deleted (e.g. game went final): data wins over live presentation edit
            out[k]=jm(l[k],a.get(k),b.get(k),path+'/'+k,conf) if k in a and k in b else lv
        return out
    if isinstance(l,list) and isinstance(a,list) and isinstance(b,list) and len(l)==len(a)==len(b):
        return [jm(x,y,z,path+'[%d]'%i,conf) for i,(x,y,z) in enumerate(zip(l,a,b))]
    if l is None: return None            # live deliberately suppresses this leaf (e.g. hidden spread)
    if isinstance(a,str) and isinstance(b,str): return b   # S1 data string wins; live relabels re-applied in post()
    conf.append((path,l,a,b)); return l
def anchored(l,a,b):
    import difflib
    lt,at,bt=l.decode('utf-8'),a.decode('utf-8'),b.decode('utf-8'); bad=[]
    tk=lambda s:[m for m in re.finditer(r'\d+(?:[.,]\d+)*|\w+|\s+|.',s,re.S)]
    ta,tb=tk(at),tk(bt)
    ops=[o for o in difflib.SequenceMatcher(None,[m.group(0) for m in ta],[m.group(0) for m in tb],autojunk=False).get_opcodes() if o[0]!='equal']
    sp=[]
    for op,i1,i2,j1,j2 in ops:
        ca=(ta[i1].start() if i1<len(ta) else len(at), ta[i2-1].end() if i2>i1 else (ta[i1].start() if i1<len(ta) else len(at)))
        cb=(tb[j1].start() if j1<len(tb) else len(bt), tb[j2-1].end() if j2>j1 else (tb[j1].start() if j1<len(tb) else len(bt)))
        if sp and ca[0]-sp[-1][1]<60: sp[-1]=[sp[-1][0],ca[1],sp[-1][2],cb[1]]
        else: sp.append([ca[0],ca[1],cb[0],cb[1]])
    for a1,a2,b1,b2 in reversed(sp):
        done=False
        for k in (12,24,40,80,160,320):
            pre_,suf=at[max(0,a1-k):a1],at[a2:a2+k]
            if lt.count(pre_+at[a1:a2]+suf)==1:
                lt=lt.replace(pre_+at[a1:a2]+suf,pre_+bt[b1:b2]+suf); done=True; break
        if not done:
            na=re.findall(r'\d+(?:\.\d+)?',at[a1:a2]); nb=re.findall(r'\d+(?:\.\d+)?',bt[b1:b2])
            numonly=len(na)==len(nb)>0 and re.sub(r'\d+(?:\.\d+)?','#',at[a1:a2])==re.sub(r'\d+(?:\.\d+)?','#',bt[b1:b2])
            if numonly:
                ctx=at[max(0,a1-40):a1]; w=re.findall(r'[A-Za-z]{3,}',ctx)[-2:]
                rx=r'(?<![\d.])'+r'[^<]{1,140}?'.join(re.escape(x) for x in na)+r'(?![\d])'
                ms=list(re.finditer(rx,lt))
                if len(ms)==1:
                    s=ms[0].group(0)
                    for x,y in zip(na,nb): s=s.replace(x,'\0'+y,1)
                    lt=lt[:ms[0].start()]+s.replace('\0','')+lt[ms[0].end():]; rep.setdefault('numeric_fallback',[]).append(at[a1:a2]+' -> '+bt[b1:b2]); continue
                if not ms and not any(x in lt for x in [at[max(0,a1-60):a1]]) and w and not all(x in lt for x in w): rep.setdefault('absent_in_live',[]).append(repr(at[max(0,a1-60):a2+20])); continue
                if not ms and at[max(0,a1-60):a1] not in lt: rep.setdefault('absent_in_live',[]).append(repr(at[max(0,a1-60):a2+20])); continue
            if numonly:   # per-number fallback: each old number with its S0 right-hand context must be unique in live
                ok=True; nl=lt; pos=a1
                for x,y in zip(na,nb):
                    k=at.index(x,pos); pos=k+len(x); ctx=at[pos:pos+24]
                    c=nl.count(x+ctx)
                    if c!=1: ok=False; break
                    nl=nl.replace(x+ctx,y+ctx)
                if ok: lt=nl; rep.setdefault('numeric_fallback',[]).append('per-number '+at[a1:a2]+' -> '+bt[b1:b2]); continue
            bad.append(repr(at[max(0,a1-30):a2+30]))
    return lt.encode('utf-8'),bad
STALE_GAP=b'<td data-c="gap"><span class="lk">Loading</span></td>'
CNT=re.compile(rb'Right now that is \d+ of the \d+ games that have not started')
def livefix(f,l,a):
    """Live-only leftovers that the templates can never reproduce (Oct 31 refreshfix):
    games/index.html: stray <td data-c="gap"> cells left in a few live rows after the Gap column was removed (header has no Gap column);
    method/index.html: the 'Right now that is N of the M games' count is pipeline data; live's stale value is replaced by S0's so S1 applies."""
    if f=='games/index.html' and STALE_GAP not in a and STALE_GAP in l:
        rep.setdefault('livefix',[]).append(f+' stray gap cells: %d'%l.count(STALE_GAP)); l=l.replace(STALE_GAP,b'')
    if f=='method/index.html':
        m=CNT.search(a)
        if m and CNT.search(l) and m.group(0) not in l:
            rep.setdefault('livefix',[]).append(f+' count '+CNT.search(l).group(0).decode()+' -> S0'); l=CNT.sub(lambda _:m.group(0),l,count=1)
    return l
for f in changed:
    lp=L+'/'+f
    if not os.path.exists(lp): rep['missing_live'].append(f); continue
    l,a,b=rd(lp),rd(S0+'/'+f),rd(S1+'/'+f)
    if a is None or b is None: rep['conflict'].append(f+' (only in one of S0/S1)'); continue
    l=livefix(f,l,a)
    if l==a: open(OUT+'/'+f,'wb').write(b); rep['taken'].append(f); continue
    if f.endswith('.json'):
        conf=[]; m=jm(json.loads(pre(l,0)),json.loads(pre(a,0)),json.loads(pre(b,1)),'',conf)
        if conf: rep['json_conflicts'][f]=conf
        s=post(json.dumps(m,separators=(',',':'),ensure_ascii=False))
        open(OUT+'/'+f,'w').write(s); rep['merged'].append(f); continue
    if f in SKIP: rep['skipped'].append(f); continue
    if f in MANUAL:
        m,bad=anchored(pre(l,0),pre(a,0),pre(b,1))
        if bad: rep['conflict'].append(f+' anchored: '+'; '.join(bad[:5])); continue
        open(OUT+'/'+f,'wb').write(post(m.decode('utf-8')).encode('utf-8')); rep['merged'].append(f); continue
    ish=f.endswith('.html')
    def nz(c,new=0):
        t=pre(c,new).decode('utf-8')
        if ish: t=TOK.sub('?v=X',t).replace('><','>\n@@<'); t='\n\u00a7\n'.join(t.split('\n'))
        return t.encode('utf-8')
    with tempfile.TemporaryDirectory() as td:
        for n,c in (('l',l),('a',a),('b',b)): open(td+'/'+n,'wb').write(nz(c,1 if n=='b' else 0))
        r=subprocess.run(['git','merge-file','-p','--diff3','-L','live','-L','s0','-L','s1',td+'/l',td+'/a',td+'/b'],capture_output=True)
        if r.returncode>0 and f not in MANUAL:
            t0=r.stdout.decode('utf-8'); n=[0]
            def res(m):
                if m.group(3)=='' and m.group(2)!='': n[0]+=1; return ''   # S1 deleted a block that live had edited: accept deletion
                return m.group(0)
            t1=re.sub(r'<<<<<<< live\n(.*?)\|\|\|\|\|\|\| s0\n(.*?)=======\n(.*?)>>>>>>> s1\n',lambda m: res(re.match(r'(?s)(.*)',m.group(0)) and type('M',(),{'group':lambda self,i,m=m:{0:m.group(0),1:m.group(1),2:m.group(2),3:m.group(3)}[i]})()),t0,flags=re.S)
            if '<<<<<<< live' not in t1:
                r=subprocess.CompletedProcess([],0,t1.encode('utf-8'),b''); rep.setdefault('deletions_accepted',{})[f]=n[0]
        if r.returncode==0:
            t=r.stdout.decode('utf-8')
            if ish:
                t=t.replace('\n\u00a7\n','\n').replace('>\n@@<','><')
                lt=l.decode('utf-8'); lm={}
                for m in REF.finditer(lt): lm.setdefault(m.group(1),m.group(2))
                t=REF2.sub(lambda m: m.group(1)+'?v='+lm.get(m.group(1),GM.get(m.group(1),'X')),t)
                assert '?v=X' not in t, f
            t=post(t)
            open(OUT+'/'+f,'w',encoding='utf-8').write(t); rep['merged'].append(f)
        else: rep['conflict'].append(f+' rc=%d'%r.returncode)
json.dump(rep,open(sys.argv[5] if len(sys.argv)>5 else '/dev/stdout','w'),indent=1,default=str)
print({k:(len(v)) for k,v in rep.items()})
