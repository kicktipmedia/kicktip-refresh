# KickTip Rootables share card rev 3 (SHARE-SPEC 1b18d56c; Creative card_rev3.py.bak 5b2d7e61, one change: neutral site = 'vs' as on the page). Bold board. Caps: wide 5 (+N more line), tall 8.
import asyncio,json,os
from playwright.async_api import async_playwright
CHARTER='KickTip is not a betting site.'
def lum(h):
  c=[int(h[i:i+2],16)/255 for i in (1,3,5)];c=[x/12.92 if x<=.03928 else ((x+.055)/1.055)**2.4 for x in c];return .2126*c[0]+.7152*c[1]+.0722*c[2]
def ratio(a,b):x,y=sorted([lum(a),lum(b)]);return (y+.05)/(x+.05)
def fill(c): return c if ratio(c,'#FFFFFF')>=4.5 else '#121519'
S={'og':dict(W=1200,H=630,CAP=5,BAND=84,TS=40,MK=50,HP=28,FOOT=54,FF=22,RH=88,RHM=78,GAP=8,LG=64,PANEL=360,RL=20,NF=26,ON=22,KF=20,TG=22,GL=20,GF=40),
   'portrait':dict(W=1080,H=1350,CAP=8,BAND=130,TS=58,MK=72,HP=32,FOOT=66,FF=24,RH=132,RHM=132,GAP=8,LG=80,PANEL=400,RL=22,NF=30,ON=26,KF=22,TG=22,GL=22,GF=52)}
def order(gs):
  out,seen=[],set()
  for g in sorted(gs,key=lambda g:(-g['gain'],g['ko'])):
    k=(g['away']['id'],g['home']['id'])
    if k not in seen: seen.add(k); out.append(g)
  return out
nb=lambda s:s.replace(' ','&nbsp;')
rk=lambda t:f'#{t["rank"]}&nbsp;' if t.get('rank') else ''
def html(d,sz):
  s=S[sz]; allg=order(d['games']); gs=allg[:s['CAP']]; extra=len(allg)-len(gs)
  rh=s['RHM'] if extra else s['RH']; disc=s['LG']+(8 if sz=='og' else 12)
  css=f'''*{{box-sizing:border-box;margin:0}}body{{font-family:"Noto Sans",system-ui,sans-serif;background:#F1F3F4;color:#121519;width:{s['W']}px;height:{s['H']}px;overflow:hidden;display:flex;flex-direction:column}}
.hd{{background:#121519;height:{s['BAND']}px;padding:0 {s['HP']}px;display:flex;align-items:center;justify-content:space-between;flex:none}}
.hd h1{{color:#F1F3F4;font:900 {s['TS']}px/1 "Noto Sans";text-transform:uppercase}}.hd img{{height:{s['MK']}px}}
.bd{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:{s['GAP']}px;padding:0 {s['HP']}px}}
.r{{height:{rh}px;flex:none;display:flex;align-items:stretch;background:#fff;border:2px solid #C9CED3;border-radius:14px;overflow:hidden}}
.pn{{width:{s['PANEL']}px;flex:none;background:var(--f);display:flex;align-items:center;gap:14px;padding:0 16px}}
.dc{{width:{disc}px;height:{disc}px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}}.dc img{{width:{s['LG']}px;height:{s['LG']}px}}
.pn .rl{{color:#fff;font:800 {s['RL']}px/1 "Noto Sans";text-transform:uppercase;letter-spacing:.08em}}.pn .nm{{color:#fff;font:900 {s['NF']}px/1.1 "Noto Sans";white-space:nowrap;margin-top:4px}}
.op{{flex:1;min-width:0;display:flex;align-items:center;gap:12px;padding:0 16px}}.op img{{width:{s['LG']}px;height:{s['LG']}px;flex:none}}
.op .on{{font:700 {s['ON']}px/1.1 "Noto Sans";color:#4C5560;white-space:nowrap}}.op .on b{{color:#121519}}.op .kt{{font:600 {s['KF']}px/1.2 "Noto Sans";color:#4C5560;margin-top:4px;white-space:nowrap}}
.tg{{align-self:center;font:700 {s['TG']}px/1 "Noto Sans";padding:7px 12px;border-radius:999px;white-space:nowrap;border:2px solid #4C5560;color:#4C5560;background:#fff;margin-right:16px}}{'.mid .tg{{margin-left:16px;align-self:flex-start}}' if sz=='portrait' else ''}.tg.po{{background:#121519;border-color:#121519;color:#fff}}
.gn{{display:flex;flex-direction:column;justify-content:center;align-items:flex-end;padding-right:20px;min-width:{180 if sz=='og' else 210}px}}.gn span{{font:700 {s['GL']}px/1 "Noto Sans";color:#4C5560}}.gn b{{font:900 {s['GF']}px/1.05 "Noto Sans";white-space:nowrap;font-variant-numeric:tabular-nums;margin-top:4px}}
.mid{{flex:1;min-width:0;display:flex;{'flex-direction:column;justify-content:center;align-items:flex-start;gap:10px' if sz=='portrait' else 'align-items:center'}}}
.more{{font:700 {s['KF']}px "Noto Sans";color:#4C5560;text-align:center}}
.emp{{background:#fff;border:2px solid #C9CED3;border-radius:14px;padding:48px;text-align:center}}.emp p{{font:800 {s['NF']+6}px/1.3 "Noto Sans"}}.emp small{{display:block;margin-top:16px;font:600 {s['KF']+2}px "Noto Sans";color:#4C5560}}
.ft{{height:{s['FOOT']}px;flex:none;display:flex;align-items:center;justify-content:space-between;padding:0 {s['HP']}px;font:600 {s['FF']}px "Noto Sans";color:#4C5560;border-top:2px solid #DDE1E4}}'''
  rows=''
  for g in gs:
    rs,os_=g[g['root']],g['home' if g['root']=='away' else 'away']
    at='vs' if g.get('neutral') else ('at' if g['root']=='away' else 'vs')  # root away plays at home team; root home hosts
    tag=f'<span class="tg {"po" if g["race"]=="Playoff" else ""}">{nb(g["race"])}</span>'
    mid=f'<div class="mid"><div class="op"><img src="../logos/{os_["id"]}.png" alt=""><div><div class="on">{at} <b>{rk(os_)}{nb(os_["name"])}</b></div><div class="kt">{nb(g["when"])}</div></div></div>{tag}</div>'
    rows+=f'<div class="r"><div class="pn" style="--f:{fill(g["color"])}"><span class="dc"><img src="../logos/{rs["id"]}.png" alt=""></span><div><div class="rl">Root for</div><div class="nm">{rk(rs)}{nb(rs["name"])}</div></div></div>{mid}<div class="gn"><span>{d["team"]}&nbsp;gain</span><b>+{g["gain"]:.1f}&nbsp;pts</b></div></div>'
  if extra: rows+=f'<div class="more">+{extra}&nbsp;more at kicktipmedia.com</div>'
  if not gs: rows=f'<div class="emp"><p>No other games this week move {d["team"]}\'s chances by&nbsp;much.</p><small>See every game at kicktipmedia.com</small></div>'
  st=f'<span>Updated {d["asof"]}</span>' if d.get('asof') else '<span></span>'
  return f'<html><head><meta charset=utf-8><style>{css}</style></head><body><div class="hd"><h1>{d["team"]} Rootables</h1><img src="../kt_header.png" alt="KickTip"></div><div class="bd">{rows}</div><div class="ft">{st}<span>{CHARTER}</span><span>kicktipmedia.com</span></div></body></html>',len(gs),extra
JOBS=[('byu_sample','og'),('byu_sample','portrait'),('empty_byu_sample','og'),('empty_byu_sample','portrait')]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for f,sz in JOBS:
      d=json.load(open(f'share/{f}.json')); h,n,x=html(d,sz); name=f'share/card3_{f}_{sz}'
      open(name+'.html','w').write(h)
      pg=await b.new_page(viewport={'width':S[sz]['W'],'height':S[sz]['H']})
      await pg.goto('file://'+os.path.abspath(name+'.html')); await pg.wait_for_timeout(300)
      m=await pg.evaluate('''()=>{const bd=document.querySelector('.bd');const im=[...document.querySelectorAll('.r img')].map(i=>i.getBoundingClientRect().width);
        return {sw:document.documentElement.scrollWidth,bd_over:bd.scrollHeight-bd.clientHeight,row_over:[...document.querySelectorAll('.r,.pn,.op,.mid')].filter(e=>e.scrollWidth>e.clientWidth+1).length,logo_px:[...new Set(im)]}}''')
      m['row_over_ids']=await pg.evaluate("[...document.querySelectorAll('.r,.pn,.op,.mid')].filter(e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1).map(e=>e.className)");print(name,'rows',n,'more',x,m)
      await pg.screenshot(path=f'crops/share3_{f}_{sz}.png')
    await b.close()
if __name__=='__main__': asyncio.run(main())
