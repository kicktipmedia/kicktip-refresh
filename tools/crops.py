import sys,asyncio,os
from playwright.async_api import async_playwright
base,out=sys.argv[1].rstrip('/'),sys.argv[2]; os.makedirs(out,exist_ok=True)
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for name,path in (('home','/'),('byu','/team/byu/')):
      pg=await b.new_page(viewport={'width':390,'height':844},device_scale_factor=2); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
      await pg.goto(base+path+'?cb=1',wait_until='networkidle'); await pg.wait_for_timeout(1000)
      await pg.screenshot(path=f'{out}/{name}-390-top.png')
      await pg.screenshot(path=f'{out}/{name}-390-full.png',full_page=True)
      t=await pg.evaluate("()=>document.body.innerText")
      import re
      print(name,'errs',errs,'| asof hits',re.findall(r'(?:Updated|pulled:|last checked)[^\n.]{0,40}',t)[:3])
      if name=='byu':
        for k in ('playoff','championship','bye'):
          print('  ',[l for l in t.split('\n') if k in l.lower() and '%' in l][:3])
      await pg.close()
    await b.close()
asyncio.run(m())
