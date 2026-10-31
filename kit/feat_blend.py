import json,re,glob,sys
D=sys.argv[1]; b=json.load(open(D+'/data/sim-bundle.json')); conf={c['code']:c['name'] for c in b['confs']}; tm={t['g']:t for t in b['teams'] if t.get('g')}
n=0
for p in glob.glob(D+'/team/*/index.html'):
    s=open(p,encoding='utf-8').read(); g=p.split('/')[-2]; t=tm.get(g,{}); noccg='data-noccg="1"' in s
    cn=conf.get(t.get('c'),'')
    ph='playoff chances' if noccg or not cn else f'playoff and {cn} championship chances'
    s2=re.sub(r'(<p class="rb-sub">Who to cheer for this week, for [^<]*?(?:\u2019|&#8217;)s )chance to make the 12-team playoff field\.</p>', lambda m: m.group(1)+ph+'.</p>', s, count=1)
    if s2!=s: n+=1; open(p,'w',encoding='utf-8').write(s2)
print('rb-sub blended',n)
