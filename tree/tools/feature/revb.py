#!/usr/bin/env python3
"""KickTip polish rev b (Creative fixes 1-4). Idempotent: python3 revb.py <site_dir>
1 exact as-of stamps: static kt-asof text 'recently' -> 'Oct 29, 10:13 PM MT' baked from data-asof; JS (pk.js, asof.js) formats the same exact stamp, never relative.
2 chip: nbsp through 'lose one more game' (CSS left-align in polish.css).
3 chances: restore the First-round bye tile (pred-teams.json has b for all 138 teams; kt.js teamTiles already fills data-tile=b).
4 rootables footnote in percent."""
import sys,os,re,glob
S=sys.argv[1]
MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
def fmt(ps):
    m=re.fullmatch(r'(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)',ps or '')
    if not m: return ''
    mo,d,h=int(m[2]),int(m[3]),int(m[4])
    if not(1<=mo<=12 and 1<=d<=31 and h<=23 and int(m[5])<=59): return ''
    return '%s&nbsp;%d, %d:%s&nbsp;%s&nbsp;MT'%(MON[mo-1],d,(h+11)%12+1,m[5],'AM' if h<12 else 'PM')
n=[0,0,0,0]
for p in glob.glob(os.path.join(S,'**/*.html'),recursive=True):
    s=open(p,encoding='utf-8').read(); o=s
    def rep(mm):
        f=fmt(mm[1]); return '<span class="kt-asof" data-asof="%s">%s</span>'%(mm[1],f)
    s=re.sub(r'<span class="kt-asof" data-asof="([^"]*)">recently</span>',rep,s)
    # home: hide the freshness line when the stamp is empty
    s=s.replace('<p class="pk-fresh">Updated <span class="kt-asof" data-asof="" ></span></p>','')
    s=re.sub(r'<p class="pk-fresh">Updated <span class="kt-asof" data-asof="[^"]*"></span></p>','',s)
    s=s.replace('<span>Utah and BYU each lose one more&nbsp;game</span>','<span>Utah and BYU each lose&nbsp;one&nbsp;more&nbsp;game</span>')
    if '/team/' in p.replace(os.sep,'/') and 'data-tile="b"' not in s:
        a=re.search(r'(<div class="tile"><b data-tile="p">&ndash;</b><span>Make the 12&#8209;team playoff</span><span class="pc-bar" aria-hidden="true"><span></span></span></div>)',s)
        if a:
            s=s[:a.end()]+'<div class="tile"><b data-tile="b">&ndash;</b><span>First&#8209;round bye</span><span class="pc-bar" aria-hidden="true"><span></span></span></div>'+s[a.end():]; n[2]+=1
    if s!=o: open(p,'w',encoding='utf-8').write(s); n[0]+=1
# JS
FMT=("function ktStamp(ps) { /* 'YYYY-MM-DD HH:MM' (MT) -> 'Oct\\u00a029, 10:13\\u00a0PM\\u00a0MT'; '' if unreadable. Exact stamp, never relative (Jared, Oct 30). */\n"
     "    var m = /^(\\d{4})-(\\d\\d)-(\\d\\d) (\\d\\d):(\\d\\d)(?: MT)?$/.exec(String(ps || '').trim()); if (!m) return '';\n"
     "    var mo = +m[2], d = +m[3], h = +m[4]; if (mo < 1 || mo > 12 || d < 1 || d > 31 || h > 23 || +m[5] > 59) return '';\n"
     "    return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][mo - 1] + '\\u00a0' + d + ', ' + ((h + 11) % 12 + 1) + ':' + m[5] + '\\u00a0' + (h < 12 ? 'AM' : 'PM') + '\\u00a0MT';\n  }")
p=os.path.join(S,'assets/pk.js'); s=open(p,encoding='utf-8').read()
if 'ktStamp' not in s:
    i=s.index('  function ttAge(ps) {'); j=s.index("    return r + ' ago';\n  }\n",i)+len("    return r + ' ago';\n  }\n")
    s=s[:i]+'  '+FMT+'\n  function ttAge(ps) { if (ps === undefined) ps = pageStamp(); return ps ? ktStamp(ps) : \'\'; }   /* name kept for callers; now the exact stamp */\n'+s[j:]
    s=s.replace("function ktAsof() { [].forEach.call(D.querySelectorAll('.kt-asof[data-asof]'), function (x) { var r = ttAge(x.getAttribute('data-asof')); if (r) x.textContent = r; }); }",
      "function ktAsof() { [].forEach.call(D.querySelectorAll('.kt-asof[data-asof]'), function (x) { var r = ttAge(x.getAttribute('data-asof')); if (r) { if (x.textContent !== r) x.textContent = r; } else { var f = x.closest('.pk-fresh'); if (f) f.hidden = true; } }); }")
    assert 'f.hidden = true' in s
    s=s.replace("ktAsof(); W.setInterval(ktAsof, 60000);","ktAsof();")
    open(p,'w',encoding='utf-8').write(s); n[3]+=1
p=os.path.join(S,'assets/asof.js')
open(p,'w',encoding='utf-8').write("""/* KickTip exact "last updated" stamps: <span class="kt-asof" data-asof="YYYY-MM-DD HH:MM"> (MT) -> "Oct 29, 10:13 PM MT".
   The same text is baked into the HTML at build time, so no-JS readers see it too. Never relative ("ago"/"recently"). No storage, no network. */
(function () {
  'use strict';
  """+FMT+"""
  function run() { [].forEach.call(document.querySelectorAll('.kt-asof[data-asof]'), function (x) { var r = ktStamp(x.getAttribute('data-asof')); if (r && x.textContent !== r) x.textContent = r; }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
""")
p=os.path.join(S,'assets/rootables.js'); s=open(p,encoding='utf-8').read()
for a,b in [("by less than 1.0 point are not shown","by less than 1% are not shown"),
            ("games that move this by 1.0 point or more.","games that move this by 1% or more."),
            ("moves this by less than 1.0 point and is not shown.","moves this by less than 1% and is not shown."),
            ("move this by less than 1.0 point and are not shown.","move this by less than 1% and are not shown."),
            ("No game this week moves this by 1.0 point or more.","No game this week moves this by 1% or more.")]:
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s)
p=os.path.join(S,'assets/polish.css'); s=open(p,encoding='utf-8').read()
if 'revb' not in s:
    s+="\n/* revb: chip left-aligned (Creative); home stamp on ink stays light for contrast */\nmain[data-page=home] .hero a.ph-chip,.ph-chip{justify-content:flex-start;text-align:left}\n.pk-fresh[hidden]{display:none}\n"
    open(p,'w',encoding='utf-8').write(s)
print('html changed',n[0],'bye tiles',n[2],'pk',n[3])
