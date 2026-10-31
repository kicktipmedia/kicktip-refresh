#!/usr/bin/env python3
"""confmerge regression test (Oct 31, 5:29 PM MT inputs): conference pages with the site-only kc block after the standings table.
Fixture: live (siteF 3c6470a7, unbaked), S0 (275633f9 = 028b011a for these pages), S1 (pipeline 17:29), post-fixed like apply_data.
usage: confmerge_test.py [old_merge3.py]  -> exit 0 on PASS"""
import json,os,re,subprocess,sys,tempfile,shutil
H=os.path.dirname(os.path.abspath(__file__)); FX=H+'/fixtures/confmerge_1729'; M3=os.path.join(H,'..','tools','merge3.py')
FM=json.dumps([["Sat, Oct 31, 2026, 9:30 AM MT","Sat, Oct 31, 2026, 5:29 PM MT"],["Oct 31, 2026, 9:30 AM MT","Oct 31, 2026, 5:29 PM MT"],["Oct 31, 9:30 AM MT","Oct 31, 5:29 PM MT"],["2026-10-31 09:30 MT","2026-10-31 17:29 MT"]])
sys.path.insert(0,os.path.dirname(M3)); fail=0
def ok(c,m):
    global fail; print(('ok   ' if c else 'FAIL ')+m); fail+=0 if c else 1
def run(m3,live,s0,s1):
    td=tempfile.mkdtemp(); out=td+'/out'; shutil.copytree(live,out); r=subprocess.run([sys.executable,m3,live,s0,s1,out,td+'/r.json',FM],capture_output=True,text=True)
    return json.load(open(td+'/r.json')),out
TOK=re.compile(r'\?v=[0-9a-f]{10}')
def tb(t): i=t.find('<tbody',t.find('<table')); return t[i:t.find('</tbody>',i)+8]
def gcl(t):
    i=t.find('<div class="gcl">'); d=0
    for m in re.finditer(r'<div\b|</div>',t[i:]):
        d+=1 if m.group(0)!='</div>' else -1
        if d==0: return t[i:i+m.end()]
def kc(t): i=t.find('<p class="kc-key"'); return t[i:t.find('<div class="card"><h2>Remaining',i)]
def stamp(t,i): return t.replace('9:30 AM MT','<T>').replace('5:29 PM MT','<T>').replace('09:30','<T>').replace('17:29','<T>')
pages=sorted(os.listdir(FX+'/live/conference'))
if len(sys.argv)>1:
    r,_=run(sys.argv[1],FX+'/live',FX+'/s0',FX+'/s1'); ok(len(r['conflict'])==3,'regression reproduced with the old merge3: '+str(r['conflict']))
r,out=run(M3,FX+'/live',FX+'/s0',FX+'/s1')
ok(r['conflict']==[],'new merge3: no conflict (%d merged)'%len(r['merged'])); ok(sorted(r.get('resolved',{}))==['conference/%s/index.html'%p for p in pages],'resolver used on '+str(len(r.get('resolved',{}))))
for p in pages:
    f='/conference/%s/index.html'%p; L=open(FX+'/live'+f).read(); S0=open(FX+'/s0'+f).read(); S1=open(FX+'/s1'+f).read(); O=open(out+f).read()
    ok(TOK.sub('',tb(O))==TOK.sub('',tb(S1)) and TOK.sub('',gcl(O))==TOK.sub('',gcl(S1)),p+': standings rows + games list = S1')
    ok(kc(O)==kc(L) and kc(L).count('kc-list')==1,p+': site-only kc block byte-identical to live')
    # everything else: L with S0->S1 applied. Mask both regions; every remaining line that differs from live must differ S0->S1 too (data)
    def mask(t): t=t.replace(tb(t),'<TB>').replace(gcl(t),'<GCL>'); return TOK.sub('',t).replace('><','>\n<').split('\n')
    lo,ll,l0,l1=mask(O),mask(L),set(mask(S0)),set(mask(S1))
    import difflib
    bad=[x for x in difflib.unified_diff(ll,lo,n=0,lineterm='') if x[:1]=='+' and not x.startswith('+++') and x[1:] not in l1]
    ok(not bad,p+': outside the regions only S1 (data) lines changed'+(' BAD '+str(bad[:2]) if bad else ''))
# synthetic: live edited inside the standings -> the resolver must not touch that region
td=tempfile.mkdtemp()
for s in ('live','s0','s1'): shutil.copytree(FX+'/'+s,td+'/'+s)
f=td+'/live/conference/acc/index.html'; t=open(f).read(); i=t.find('<td',t.find('<tbody')); open(f,'w').write(t[:i]+'<td class="x">live</td>'+t[i:])
r2,_=run(M3,td+'/live',td+'/s0',td+'/s1'); ok(any('acc' in x and 'r0 live-edited' in x for x in r2.get('resolver_skipped',[])),'live edit inside a region: resolver skips it '+str(r2.get('resolver_skipped')))
print('CONFMERGE_TEST','FAIL %d'%fail if fail else 'PASS'); sys.exit(1 if fail else 0)
