#!/bin/bash
# Rebuild the wkfinal1 hotfix zip on top of any live base zip (use when Production moved since the QA'd build).
# usage: tools/hotfix/wkfinal1_build.sh <live base zip> <new empty out dir>   -> <out>/site, <out>/kicktip-site-wkfinal1.zip, prints sha256
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); Z=$(realpath "$1"); O=$(realpath -m "$2"); [ ! -e "$O" ] || [ -z "$(ls -A "$O")" ] || { echo "out dir not empty"; exit 2; }
mkdir -p "$O/site" "$O/base"; (cd "$O/base" && unzip -q "$Z"); (cd "$O/site" && unzip -q "$Z")
grep -q 'wkfinal1' "$O/site/assets/ccgsim-ui.js" && { echo "base already has wkfinal1"; exit 3; }
python3 "$H/wkfinal1_patch.py" "$O/site/assets/ccgsim-ui.js"; node --check "$O/site/assets/ccgsim-ui.js"
python3 "$H/../../tree/tools/restamp.py" "$O/site" "$O/base" | tail -2
python3 - "$O/base" "$O/site" <<'P'
import os,re,sys
b,s=sys.argv[1:3]; TOK=re.compile(r'\?v=[0-9a-f]{10}'); ch=[]
fs=sorted(os.path.relpath(os.path.join(d,f),s) for d,_,ff in os.walk(s) for f in ff)
assert fs==sorted(os.path.relpath(os.path.join(d,f),b) for d,_,ff in os.walk(b) for f in ff), 'file list changed'
for r in fs:
    x=open(os.path.join(b,r),'rb').read(); y=open(os.path.join(s,r),'rb').read()
    if x==y: continue
    ch.append(r)
    if r!='assets/ccgsim-ui.js': assert r.endswith('.html') and TOK.sub('?v=0',x.decode())==TOK.sub('?v=0',y.decode()), 'not token-only: '+r
print('changed', len(ch), 'files: assets/ccgsim-ui.js + %d html (token only)' % (len(ch)-1))
P
python3 - "$O/site" "$O/kicktip-site-wkfinal1.zip" <<'P'
import zipfile,os,sys
src,out=sys.argv[1],sys.argv[2]
fs=sorted(os.path.relpath(os.path.join(d,f),src) for d,_,ff in os.walk(src) for f in ff)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in fs:
        zi=zipfile.ZipInfo(rel,(2026,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16; z.writestr(zi,open(os.path.join(src,rel),'rb').read())
P
rm -rf "$O/base"; sha256sum "$O/kicktip-site-wkfinal1.zip"
