#!/usr/bin/env python3
"""KickTip polish: HTML part. Idempotent, anchor-based; run on any site dir (e.g. after merging the no-JS or trim builds):
   python3 apply_polish.py <site_dir>
Touches index.html (hero how-to strip + css/js links) and team/*/index.html (chances card + css/js links). Asset tokens are fixed afterwards by bump.py."""
import sys,os,re,glob,html
S=sys.argv[1]
MARK='data-polish="1"'
LINKS='<link rel="stylesheet" href="/assets/tc.css?v=0000000000"><link rel="stylesheet" href="/assets/polish.css?v=0000000000" data-polish="1">'
JS='<script src="/assets/polish.js?v=0000000000" defer></script>'
def once(s,a,b,n=1):
    assert s.count(a)==n,(a[:80],s.count(a)); return s.replace(a,b)
def head(s,after_css):
    s=once(s,after_css,after_css+LINKS)
    k=re.search(r'<script src="/assets/kt\.js\?v=[0-9a-f]{10}" defer></script>',s).group(0)
    return once(s,k,k+JS)
NB='\u00a0'
def home(p):
    s=open(p,encoding='utf-8').read()
    if MARK in s: return False
    s=head(s,re.search(r'<link rel="stylesheet" href="/assets/top25\.css\?v=[0-9a-f]{10}">',s).group(0))
    s=once(s,'<h1>Your&nbsp;team. Your&nbsp;chances. Your&nbsp;postseason&nbsp;path.</h1>','<h1>Where does your team&nbsp;stand?</h1>')
    a=re.search(r'<p class="tt-a">.*?</p><p class="pk-lead">.*?</p>',s).group(0)
    q='Utah and BYU each lose one more game'
    strip=('<p class="ph-pos">College football playoff simulator from the Mtn&nbsp;Sports&nbsp;Media&nbsp;team.</p>'
      '<ol class="ph-how" aria-label="How to use KickTip">'
      '<li><span class="ph-n" aria-hidden="true">1</span><div><b>Choose a team</b><span>Any FBS team, from Utah to Utah&nbsp;State.</span></div></li>'
      '<li><span class="ph-n" aria-hidden="true">2</span><div><b>See their chances</b><span>Conference championship and 12&#8209;team playoff, from 10,000&nbsp;simulations.</span></div></li>'
      '<li><span class="ph-n" aria-hidden="true">3</span><div><b>Try a What If</b><span>Change a result and watch the chances&nbsp;move.</span></div></li>'
      '</ol><p class="ph-ex"><a class="ph-chip" href="/?wi='+q.replace(' ','+')+'#what-if" data-ph-q="'+q+'">'
      '<img src="/assets/logos/32/254.png" srcset="/assets/logos/32/254.png 1x, /assets/logos/64/254.png 2x" alt="" width="22" height="22" decoding="async">'
      '<img src="/assets/logos/32/252.png" srcset="/assets/logos/32/252.png 1x, /assets/logos/64/252.png 2x" alt="" width="22" height="22" decoding="async">'
      '<span>Utah and BYU each lose one more&nbsp;game</span></a></p>'
      )
    s=once(s,a,strip)
    open(p,'w',encoding='utf-8').write(s); return True
def team(p):
    s=open(p,encoding='utf-8').read()
    if MARK in s: return False
    s=head(s,re.search(r'<link rel="stylesheet" href="/assets/kt\.css\?v=[0-9a-f]{10}">',s).group(0))
    slug=os.path.basename(os.path.dirname(p))
    name=html.unescape(re.search(r'<h1>(.*?)</h1>',s).group(1))
    cm=re.search(r'<p class="crumbs"><a href="/conference/[^"]+/">(.*?)</a></p>',s)
    conf=html.unescape(cm.group(1)) if cm else 'Independents'
    rm=re.search(r'Conference record (\d+-\d+), overall (\d+-\d+)\.',s)
    if rm: sub='%s \u00b7 %s, %s conference'%(conf,rm.group(2),rm.group(1))
    else:
        om=re.search(r'Overall record (\d+-\d+)\.',s); sub='%s \u00b7 %s'%(conf,om.group(1)) if om else conf
    lm=re.search(r'<span class="lg s80" aria-hidden="true"><img src="/assets/logos/500/(\d+)\.png"',s)
    lg=('<span class="pc-lg" aria-hidden="true"><img src="/assets/logos/64/%s.png" alt="" width="40" height="40" decoding="async"></span>'%lm.group(1)) if lm else ''
    cf=conf.replace(' ','&nbsp;')
    LAB={'c':'Reach the %s championship'%cf,'w':'Win the %s'%cf,'p':'Make the 12&#8209;team playoff','b':'First&#8209;round bye'}
    m=re.search(r'<h2>Chances</h2><div class="tiles">(.*?)</div></div><p class="note">(.*?)</p>',s)
    tiles=re.findall(r'<div class="tile">(<b data-tile="(\w)">.*?</b>)<span>.*?</span></div>',m.group(1))
    th=''.join('<div class="tile">%s<span>%s</span><span class="pc-bar" aria-hidden="true"><span></span></span></div>'%(b,LAB[k]) for b,k in tiles)
    more=''
    pa='<div class="card"><h2>Paths to the conference championship game</h2>'
    if pa in s:
        i=s.index(pa); j=s.index('</table></div></div>',i)+len('</table></div></div>')
        inner=s[i+len(pa):j-len('</div>')]
        s=s[:i]+s[j:]
        more='<details class="pc-more"><summary>Show all by conference record</summary><div class="pc-mb">'+inner+'</div></details>'
    new=('<h2>%s chances</h2><div class="pc tc-%s"><div class="pc-tm">%s<div><p class="pc-nm">%s</p><p class="pc-sub">%s</p></div></div>'
         '<div class="tiles pc-g">%s</div><p class="note pc-nt">%s</p><p class="pc-st" data-pc-asof></p>%s</div>')%(html.escape(name),slug,lg,html.escape(name),html.escape(sub),th,m.group(2),more)
    s=s[:m.start()]+new+s[m.end():]
    open(p,'w',encoding='utf-8').write(s); return True
n=home(os.path.join(S,'index.html'))
t=sum(team(p) for p in sorted(glob.glob(os.path.join(S,'team/*/index.html'))))
print('home',n,'teams',t)
