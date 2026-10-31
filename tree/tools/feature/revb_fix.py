#!/usr/bin/env python3
"""merged rev b fixes on a siteMerged copy. Idempotent. python3 revb_fix.py <site>"""
import sys,os,re,glob
S=sys.argv[1]; log={}
def rw(rel,f):
    p=os.path.join(S,rel); s=open(p,encoding='utf-8').read(); n=f(s)
    if n!=s: open(p,'w',encoding='utf-8').write(n); log.setdefault(f.__name__,[]).append(rel)
OLD='Information only; make no decision based on this material.'; NEW='Information only. Don&#39;t make decisions based on this material.'
NEWJS="Information only. Don&#39;t make decisions based on this material."
# 2) banner wording: page banners (.tb) and header menu (.khn) only; legal body sentences untouched
def banner(s):
    s=re.sub(r'(<div class="tb[^"]*" role="note"[^>]*><div class="w">(?:<p>)?<b>KickTip is not a betting site\.</b> )'+re.escape(OLD),lambda m:m[1]+NEW,s)
    s=re.sub(r'(<p class="khn"><b>KickTip is not a betting site\.</b> )'+re.escape(OLD),lambda m:m[1]+NEW,s)
    return s
# 5) explainer
EX_OLD=('<b>How to read the spread and expected margin.</b> Each spread names the favorite and the points ESPN lists it as winning by, with a minus sign: '
 'Utah −3.0 means Utah is the favorite by 3.0. KickTip\'s expected margin is our own number from the model, shown as the team KickTip favors and the points, '
 'for example “Utah by 3.5” (rounded to 0.5 on the page). The spread is shown with the time it was read (MT) and only when ESPN has listed one. Neither number is a recommendation. Information only.')
EX_NEW=('<b>How to read these numbers.</b> The ESPN spread shows the team ESPN expects to win and by how many points, with a minus sign: '
 'Utah −3.0 means ESPN has Utah winning by 3.0. KickTip\'s expected margin is our own number from the model: the team KickTip expects to win and by how many points, '
 'for example “Utah by 3.5” (rounded to 0.5 on the page). The ESPN spread is shown with the time it was read (MT) and only when ESPN has posted one. Neither number is a recommendation. Information only.')
FCS_OLD='Games against FCS opponents are counted in the simulation but have no spread or expected margin.'
FCS_NEW='Games against FCS opponents are counted in the simulation but have no ESPN spread or expected margin.'
def explainer(s): return s.replace(EX_OLD,EX_NEW).replace(FCS_OLD,FCS_NEW)
for p in sorted(glob.glob(os.path.join(S,'**/*.html'),recursive=True)):
    r=os.path.relpath(p,S); rw(r,banner); rw(r,explainer)
def acct(s): return s.replace("'<b>KickTip is not a betting site.</b> "+OLD+"'","'<b>KickTip is not a betting site.</b> "+NEWJS+"'")
rw('assets/account.js',acct)
# 1) gate: the Lab gate drops '· Not a betting site' while a page banner (.tb) is on screen; keeps it otherwise (never zero)
JS=r"""
/* merged revb: exactly one visible 'not a betting site' line. While any page banner (.tb) is on screen, body gets kt-tbv and the Lab gate
   hides its '· Not a betting site' (chat.css); with no banner in view the gate keeps it. */
(function () { var D = document, W = window, on = {}, n = 0;
  function set() { D.body && D.body.classList.toggle('kt-tbv', n > 0); }
  function go() { var b = D.querySelectorAll('.tb'); if (!b.length || !W.IntersectionObserver) return;
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { var i = e.target.__ktb; var v = e.isIntersecting && e.intersectionRect.height > 0; if (v && !on[i]) { on[i] = 1; n++; } else if (!v && on[i]) { on[i] = 0; n--; } }); set(); });
    [].forEach.call(b, function (x, i) { x.__ktb = i + 1; io.observe(x); }); }
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', go); else go(); })();
"""
def chat(s): return s if 'kt-tbv' in s else s.rstrip('\n')+'\n'+JS.lstrip('\n')
rw('assets/chat.js',chat)
CSS="\n/* merged revb: page banner on screen -> the Lab gate drops its own '· Not a betting site' (one visible line) */\nhtml body.kt-tbv .pnl .rtx .rt1 .rtnb,html body.kt-tbv .rtx .rt1 .rtnb{display:none!important}\n"
def css(s): return s if 'kt-tbv' in s else s+CSS
rw('assets/chat.css',css)
for k,v in log.items(): print(k,len(v),v[:4])
# 3) /games/ CLS: at <=359px the banner text wraps to 3 lines in the fallback font during the font swap, then 2 -> page shift. Reserve 3 lines there.
KTC="\n/* merged revb: reserve the banner's 3-line fallback height at <=359px so the font swap does not shift the page (games CLS) */\n@media (max-width:359px){.tb .w{min-height:74px}}\n"
def ktcss(s): return s if 'merged revb: reserve' in s else s+KTC
rw('assets/kt.css',ktcss)
print('kt.css',log.get('ktcss'))
