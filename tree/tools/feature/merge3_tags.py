import sys,os,re,subprocess,shutil
# 3-way merge layer L onto M (base B), tag-split + ?v= token-normalized. Tokens re-bumped afterwards.
B,L,M=sys.argv[1:4]
V=re.compile(r'\?v=[0-9a-f]{10}')
def split(s): return V.sub('?v=TOKEN0000',s).replace('>','>\x02\n')
def join(s): return s.replace('>\x02\n','>')
conf=[]
for d,_,fs in os.walk(L):
  for f in fs:
    lp=os.path.join(d,f); r=os.path.relpath(lp,L); bp=os.path.join(B,r); mp=os.path.join(M,r)
    if not os.path.exists(bp):
      if os.path.exists(mp) and open(mp,'rb').read()!=open(lp,'rb').read(): conf.append('NEW '+r)
      else: os.makedirs(os.path.dirname(mp),exist_ok=True); shutil.copy(lp,mp)
      continue
    lb=open(lp,'rb').read(); bb=open(bp,'rb').read()
    if lb==bb: continue
    mb=open(mp,'rb').read()
    if mb==bb: open(mp,'wb').write(lb); continue
    if not r.endswith(('.html','.js','.css')): conf.append('BIN '+r); continue
    t=[split(x.decode('utf-8')) for x in (mb,bb,lb)]
    if t[1]==t[2]: continue
    for n,x in zip(('/tmp/m3a','/tmp/m3b','/tmp/m3c'),t): open(n,'w',encoding='utf-8').write(x)
    rc=subprocess.run(['git','merge-file','-p','-L','merged','-L','base','-L','layer','/tmp/m3a','/tmp/m3b','/tmp/m3c'],capture_output=True)
    out=join(rc.stdout.decode('utf-8'))
    open(mp,'w',encoding='utf-8').write(out)
    if rc.returncode: conf.append('CONF %d %s'%(rc.returncode,r))
print('\n'.join(conf)); print('conflicts',len(conf))
