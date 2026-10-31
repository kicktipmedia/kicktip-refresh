#!/usr/bin/env python3
"""Set every /assets/<file>?v=XXXXXXXXXX to sha256(file)[:10]; loop until stable (tokens inside js/css change hashes)."""
import os,re,hashlib,sys
S=sys.argv[1]; os.chdir(S)
R=re.compile(r'/(assets/[A-Za-z0-9_./-]+)\?v=([0-9A-Za-z]{10})')
files=sorted(os.path.join(d,f)[2:] for d,_,fs in os.walk('.') for f in fs if f.endswith(('.html','.js','.css')))
for it in range(8):
  ch=0; H={}
  for f in files:
    s=open(f,encoding='utf-8',errors='surrogateescape').read()
    def r(m):
      a=m[1]
      if not os.path.exists(a): raise SystemExit('missing asset '+a+' in '+f)
      if a not in H: H[a]=hashlib.sha256(open(a,'rb').read()).hexdigest()[:10]
      return '/'+a+'?v='+H[a]
    t=R.sub(r,s)
    if t!=s: open(f,'w',encoding='utf-8',errors='surrogateescape').write(t); ch+=1
  if not ch: print('tokens stable after',it); break
else: raise SystemExit('tokens not stable')
