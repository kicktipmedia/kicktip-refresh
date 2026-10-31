"""merged rev b2 (Creative condition a): with the Lab open, the scrim is lighter over the page-banner strip only, so the dimmed banner text keeps >= 4.5:1.
Idempotent: python3 revb2_fix.py <site>"""
import sys,os
S=sys.argv[1]
JS=r"""
/* merged revb2 (kt-tbcut): the Lab scrim is lighter over the on-screen page banner strip (contrast >= 4.5:1). Sets --kt-tb0/--kt-tb1 (px, relative to the scrim box). */
(function () { var D = document, W = window, R = D.documentElement, q = 0;
  function upd() { q = 0; var t = 0, b = 0; [].forEach.call(D.querySelectorAll('.tb'), function (x) { var r = x.getBoundingClientRect(); if (r.height > 0 && r.bottom > 0 && r.top < W.innerHeight && !b) { t = Math.max(0, r.top); b = Math.min(W.innerHeight, r.bottom); } });
    var sc = D.querySelector('.scrim'), o = sc ? sc.getBoundingClientRect().top : 0; if (b) { t -= o; b -= o; }   /* mask coords are relative to the scrim box */
    R.style.setProperty('--kt-tb0', t + 'px'); R.style.setProperty('--kt-tb1', b + 'px'); }
  function req() { if (!q) { q = 1; (W.requestAnimationFrame || setTimeout)(upd); } }
  W.addEventListener('scroll', req, { passive: true }); W.addEventListener('resize', req);
  if (W.MutationObserver) new MutationObserver(function () { req(); setTimeout(upd, 450); }).observe(R, { attributes: true, childList: true, subtree: true, attributeFilter: ['class'] });
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', upd); else upd(); })();
"""
M='linear-gradient(to bottom,#000 0,#000 var(--kt-tb0,0px),rgba(0,0,0,.36) var(--kt-tb0,0px),rgba(0,0,0,.36) var(--kt-tb1,0px),#000 var(--kt-tb1,0px))'
CSS=f"\n/* merged revb2 (kt-tbcut): scrim alpha over the banner strip ~0.20 instead of 0.55 (0.55 x 0.36) */\nhtml body.kt-tbv .scrim{{-webkit-mask-image:{M};mask-image:{M}}}\n"
def rw(p,add,mark='kt-tbcut'):
  p=os.path.join(S,p); s=open(p).read()
  if mark not in s: open(p,'w').write(s.rstrip('\n')+'\n'+add.lstrip('\n')); print('patched',p)
rw('assets/chat.js',JS); rw('assets/chat.css',CSS)
# Creative condition b: the chances-card team logo (span.pc-lg, added by the merge/POLISH; not on live d2d2ea00) is removed. The hero logo (live, same file+bytes) stays.
import re,glob
n=0
for f in glob.glob(os.path.join(S,'team/*/index.html')):
  s=open(f).read(); t=re.sub(r'<span class="pc-lg" aria-hidden="true"><img [^>]*></span>','',s)
  if t!=s: open(f,'w').write(t); n+=1
print('pc-lg removed from',n,'team pages')
