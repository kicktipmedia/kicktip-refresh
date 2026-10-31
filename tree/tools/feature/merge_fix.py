#!/usr/bin/env python3
"""Merge fixes (idempotent): python3 merge_fix.py <site>. Runs after trim+polish+nojs merge, BEFORE bake_static.js."""
import sys,os,re,glob
S=sys.argv[1]; n={}
def ed(rel,pairs,must=True):
    p=os.path.join(S,rel); s=open(p,encoding='utf-8').read(); o=s
    for a,b in pairs:
        if a in s: s=s.replace(a,b)
        elif must and b not in s: raise SystemExit('anchor missing in %s: %r'%(rel,a[:80]))
    if s!=o: open(p,'w',encoding='utf-8').write(s); n[rel]=1
# 1) Lab: one visible not-a-betting line per state = the gate's 'Not a betting site'
ed('assets/chat.js',[
 ("var REQ = '<span class=\"req\">Simulation analysis, not betting advice</span>';","var REQ = '';   /* merge: in-card banner dropped (one line per state: the gate's 'Not a betting site') */"),
 ("<span class=\"lab\">Simulation analysis, not betting advice</span>","<span class=\"lab\">Simulation analysis</span>"),
 ("hidden><p class=\"rn\">KickTip is not a betting site.</p>' + '<p class=\"rn rtai\">","hidden><p class=\"rn rtai\">"),
 ("We don\\'t give betting advice or recommendations.","We don\\'t give advice or recommendations."),
 ("esc(AI_SHORT) + '</p>' + RUNTERMS + '<p class=\"lcr\">","esc(AI_SHORT) + '</p>' + '<p class=\"rn\">Information only. Don&#39;t make decisions based on this material. <a href=\"/disclaimer/\">Full terms</a></p>' + '<p class=\"lcr\">"),
])
# trim renamed 'prediction page' -> 'chances page' on /method/; keep the explain_site snippet in sync (drift check)
ed('assets/tb/explain_site.js',[('The model control at the top of each prediction page','The model control at the top of each chances page')])
# 4) Rootables footer: no year
ed('assets/rootables.js',[("return MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + m[1] + ', ' + ((h + 11)","return MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + ((h + 11)")])
# polish pc-st JS stamp duplicates the baked kt-upd stamp (stamp.js): drop it so JS on == JS off
ed('assets/polish.js',[("    var st = D.querySelector('[data-pc-asof]');\n    if (st && W.fetch) fetch('/data/tile-data.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) { st.textContent = stamp(j && j.as_of); }, function () { st.textContent = ''; });\n","")])
for p in glob.glob(os.path.join(S,'**/*.html'),recursive=True):
    s=open(p,encoding='utf-8').read(); o=s
    s=s.replace('<p class="pc-st" data-pc-asof></p>','')
    # polish revb baked stamps outside bk markers -> back to the bake anchor; bake_static.js re-bakes them with stamp.js
    s=re.sub(r'(<span class="kt-asof" data-asof="[^"]*">)(?!<!--bk)[^<]*(</span>)',lambda m:m[1]+'recently'+m[2],s)
    if s!=o: open(p,'w',encoding='utf-8').write(s); n['html']=n.get('html',0)+1
print('merge_fix',n)
