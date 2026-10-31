#!/usr/bin/env python3
"""Polish (merged build): re-derive the static chances-card subtitle on team pages from the page's own record text, so a data refresh
never leaves a stale record. Idempotent, pure, no network:  python3 polish_refresh.py <site_dir>
  <p class="pc-sub">{Conference} · {overall}, {conf} conference</p>   (Independents: '{Conference} · {overall}')"""
import sys,os,re,glob,html
S=sys.argv[1]; n=0
for p in sorted(glob.glob(os.path.join(S,'team/*/index.html'))):
    s=open(p,encoding='utf-8').read()
    if '<p class="pc-sub">' not in s: continue
    cm=re.search(r'<p class="crumbs"><a href="/conference/[^"]+/">(.*?)</a></p>',s); conf=html.unescape(cm.group(1)) if cm else 'Independents'
    rm=re.search(r'Conference record (\d+-\d+), overall (\d+-\d+)\.',s)
    if rm: sub='%s \u00b7 %s, %s conference'%(conf,rm.group(2),rm.group(1))
    else:
        om=re.search(r'Overall record (\d+-\d+)\.',s); sub='%s \u00b7 %s'%(conf,om.group(1)) if om else conf
    t=re.sub(r'<p class="pc-sub">[^<]*</p>','<p class="pc-sub">%s</p>'%html.escape(sub),s,count=1)
    if t!=s: open(p,'w',encoding='utf-8').write(t); n+=1
print('polish_refresh: pc-sub updated on',n,'team pages')
