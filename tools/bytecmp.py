#!/usr/bin/env python3
"""bytecmp.py <site_dir> <base_url> : GET every static file (Accept */*, cache-bust, follow redirects), compare bytes. exit 1 on any mismatch."""
import sys,os,urllib.request,concurrent.futures as cf,time
S,U=sys.argv[1],sys.argv[2].rstrip('/'); bust=str(int(time.time()))
fs=[os.path.relpath(os.path.join(d,f),S) for d,_,x in os.walk(S) for f in x]
fs=[f for f in fs if f not in ('_worker.js','_headers','_redirects','_routes.json') and f!='404.html']
def get(f):
    p='/'+f; p=p[:-10] if p.endswith('/index.html') else p
    req=urllib.request.Request(U+p+('&' if '?' in p else '?')+'cb='+bust,headers={'Accept':'*/*','User-Agent':'kt-bytecmp'})
    for i in range(3):
        try:
            b=urllib.request.urlopen(req,timeout=30).read(); loc=open(os.path.join(S,f),'rb').read()
            if b==loc: return f,True
            # Cloudflare zone email obfuscation removes <!--email_off--> wrappers on custom domains only
            n=loc.replace(b'<!--email_off-->',b'').replace(b'<!--/email_off-->',b'')
            return f,(b==n) or 'MISMATCH'
        except Exception as e: err=str(e); time.sleep(1)
    return f,'ERR '+err
with cf.ThreadPoolExecutor(12) as ex: r=list(ex.map(get,fs))
bad=[x for x in r if x[1] is not True]
print(U,'files',len(r),'match',len(r)-len(bad),'mismatch',len(bad)); [print(' ',b) for b in bad[:15]]
sys.exit(1 if bad else 0)
