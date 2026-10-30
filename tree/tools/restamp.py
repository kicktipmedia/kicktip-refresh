# Restamp every /assets/<file>?v=<10hex> token (html + js + css refs) to sha256(file)[:10]; repeat until stable; then verify. Run LAST, after every asset edit.
import re,os,glob,hashlib,sys
R=sys.argv[1].rstrip('/') if len(sys.argv)>1 else '/workspace/hub/kicktip-whatif-group-1026/lab-tree'
B=sys.argv[2].rstrip('/') if len(sys.argv)>2 else '/workspace/hub/kicktip-whatif-group-1026/base-home3'

def h10(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:10]
pat=re.compile(r'(/assets/[A-Za-z0-9._/-]+?)\?v=([0-9a-f]{10})')
files=[f for f in glob.glob(R+'/**/*',recursive=True) if f.endswith(('.html','.js','.css')) and os.path.isfile(f)]
for it in range(6):
    changed=0
    for f in files:
        t=open(f,encoding='utf-8').read()
        def sub(m):
            p=R+m.group(1)
            if not os.path.exists(p): return m.group(0)
            return m.group(1)+'?v='+h10(p)
        t2=pat.sub(sub,t)
        if t2!=t: open(f,'w',encoding='utf-8').write(t2); changed+=1
    if not changed: break
bad=0;n=0;tok={}
for f in files:
    for m in pat.finditer(open(f,encoding='utf-8').read()):
        p=R+m.group(1)
        if not os.path.exists(p): continue
        n+=1; tok[m.group(1)]=m.group(2)
        if h10(p)!=m.group(2): bad+=1; print('BAD',f,m.group(1))
print('refs',n,'bad',bad,'iterations',it+1)
# list assets whose token changed vs base
for a,t in sorted(tok.items()):
    bp=B+a
    if os.path.exists(bp) and h10(bp)!=t: print('NEW TOKEN %-28s %s -> %s'%(a,h10(bp),t))
assert bad==0, 'restamp left %d stale tokens' % bad
