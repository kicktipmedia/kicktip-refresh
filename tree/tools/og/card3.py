# KickTip Rootables share card rev 3 (SHARE-SPEC 1b18d56c; Creative card_rev3.py.bak 5b2d7e61, one change: neutral site = 'vs' as on the page). Bold board. Caps: wide 5 (+N more line), tall 8.
import asyncio,json,os
from playwright.async_api import async_playwright
CHARTER='KickTip is not a betting site.'
def lum(h):
  c=[int(h[i:i+2],16)/255 for i in (1,3,5)];c=[x/12.92 if x<=.03928 else ((x+.055)/1.055)**2.4 for x in c];return .2126*c[0]+.7152*c[1]+.0722*c[2]
def ratio(a,b):x,y=sorted([lum(a),lum(b)]);return (y+.05)/(x+.05)
def fill(c): return c if ratio(c,'#FFFFFF')>=4.5 else '#121519'
# rootables-fix: rows = main band + a why strip (chip + one-line why); both logos in identical white circular slots (SL), img = LG centered (object-fit:contain)
S={'og':dict(W=1200,H=630,CAP=3,BAND=84,TS=40,MK=50,HP=28,FOOT=54,FF=22,RH=148,RHM=148,GAP=8,LG=52,SL=64,WY=64,WF=20,TP='6px 14px',PANEL=380,RL=18,NF=30,ON=26,KF=21,TG=18,GL=20,GF=42),   # rev d: wide = 3 rows + '+N more', larger type
   'portrait':dict(W=1080,H=1350,CAP=8,BAND=100,TS=50,MK=60,HP=28,FOOT=54,FF=21,RH=142,RHM=142,GAP=5,LG=56,SL=70,WY=60,WF=17,TP='6px 14px',PANEL=380,RL=17,NF=26,ON=23,KF=19,TG=17,GL=18,GF=40)}   # rev c: why strip holds 2 lines
def order(gs):
  out,seen=[],set()
  for g in sorted(gs,key=lambda g:(-g['gain'],g['ko'])):
    k=(g['away']['id'],g['home']['id'])
    if k not in seen: seen.add(k); out.append(g)
  return out
nb=lambda s:s.replace(' ','&nbsp;')
def kt(g):   # Creative r3 blocker: every row shows the real date, as on the page: 'Sat Oct 31 &middot; 1:45 PM MT' / 'Sat Nov 14 &middot; time TBD' (entity separator, no literal U+00A0)
  if 'day' not in g: return nb(g['when'])
  t=nb(g['time'])+'<span class="mt">&nbsp;MT</span>' if g.get('time') else 'time&nbsp;TBD'
  return nb(g['day'])+' &middot; '+t
import html as _h,re as _re
esc=lambda t:_h.escape(t,quote=False)
first=lambda t:(_re.match(r'.*?(?<!\bNo)[.!?](?=\s|$)',t) or [t])[0]   # one tight line: the first sentence of the home why
rk=lambda t:f'#{t["rank"]}&nbsp;' if t.get('rank') else ''
# rev f: logo centering. Every logo slot (.dc) is snapped to whole CSS pixels so the white disc/ring and the logo raster share one center
# (via relative left/top, not transform, so the disc paints snapped like the img). Flex centering left the tall-card opponent discs on y.5: the disc painted snapped, the logo did not, so logos sat 0.5-0.6px low).
SNAP="document.querySelectorAll('.dc').forEach(function(d){var r=d.getBoundingClientRect();d.style.position='relative';d.style.left=(Math.round(r.left)-r.left)+'px';d.style.top=(Math.round(r.top)-r.top)+'px'})"
def html(d,sz):
  s=S[sz]; allg=order(d['games']); gs=allg[:s['CAP']]; extra=len(allg)-len(gs)
  rh=s['RHM'] if extra else s['RH']; disc=s['SL']
  css=f'''*{{box-sizing:border-box;margin:0}}body{{font-family:"Noto Sans",system-ui,sans-serif;background:#F1F3F4;color:#121519;width:{s['W']}px;height:{s['H']}px;overflow:hidden;display:flex;flex-direction:column}}
.hd{{background:#121519;height:{s['BAND']}px;padding:0 {s['HP']}px;display:flex;align-items:center;justify-content:space-between;flex:none}}
.hd h1{{color:#F1F3F4;font:900 {s['TS']}px/1 "Noto Sans";text-transform:uppercase}}.hd img{{height:{s['MK']}px}}
.bd{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:{s['GAP']}px;padding:0 {s['HP']}px}}
.r{{height:{rh}px;flex:none;display:grid;grid-template-columns:{s['PANEL']}px minmax(0,1fr) auto;grid-template-rows:minmax(0,1fr) {s['WY']}px;background:#fff;border:2px solid #C9CED3;border-radius:14px;overflow:hidden}}
.pn{{box-shadow:inset 0 0 0 3px #121519,inset 0 0 0 6px #fff;border-radius:12px 0 0 0;width:{s['PANEL']}px;flex:none;background:var(--f);display:flex;align-items:center;gap:14px;padding:0 16px}}
.dc{{width:{disc}px;height:{disc}px;border-radius:50%;background:#fff;display:grid;place-items:center;flex:none;line-height:0;padding:0}}.dc img{{display:block;width:{s['LG']}px;height:{s['LG']}px;object-fit:contain;object-position:50% 50%;margin:0}}.op .dc{{box-shadow:inset 0 0 0 2px #7A848E}}
.pn .rl{{color:#fff;font:800 {s['RL']}px/1 "Noto Sans";text-transform:uppercase;letter-spacing:.08em}}.pn .nm{{color:#fff;font:900 {s['NF']}px/1.1 "Noto Sans";white-space:nowrap;margin-top:4px}}
.op{{flex:1;min-width:0;display:flex;align-items:center;gap:12px;padding:0 16px}}
.op .on{{font:700 {s['ON']}px/1.1 "Noto Sans";color:#4C5560;white-space:nowrap}}.op .on b{{color:#121519}}.op .kt{{font:600 {s['KF']}px/1.2 "Noto Sans";color:#4C5560;margin-top:4px;white-space:nowrap}}
.tg{{flex:none;font:700 {s['TG']}px/1 "Noto Sans";padding:{s['TP']};border-radius:999px;white-space:nowrap;border:2px solid #4C5560;color:#4C5560;background:#fff}}
.wy{{grid-column:1/-1;display:flex;align-items:center;gap:14px;padding:0 14px;background:#F1F3F4;border-top:1px solid #DDE1E4;min-width:0}}.wt{{flex:1;min-width:0;white-space:normal;overflow:hidden;max-height:calc(2 * 1.2em);font:400 {s['WF']}px/1.2 "Noto Sans";color:#4C5560}}.wt b{{color:#121519;font-weight:700}}.tg.po{{background:#121519;border-color:#121519;color:#fff}}
.gn{{display:flex;flex-direction:column;justify-content:center;align-items:flex-end;padding-right:20px;min-width:{180 if sz=='og' else 210}px}}.gn span{{font:700 {s['GL']}px/1 "Noto Sans";color:#4C5560}}.gn b{{font:900 {s['GF']}px/1.05 "Noto Sans";white-space:nowrap;font-variant-numeric:tabular-nums;margin-top:4px}}
.mid{{min-width:0;display:flex;align-items:center}}
.kmt{{display:none}}.nomt .mt{{display:none}}.nomt .kmt{{display:inline}}.more{{font:700 {s['KF']}px "Noto Sans";color:#4C5560;text-align:center}}
.emp{{background:#fff;border:2px solid #C9CED3;border-radius:14px;padding:48px;text-align:center}}.emp p{{font:800 {s['NF']+6}px/1.3 "Noto Sans"}}.emp small{{display:block;margin-top:16px;font:600 {s['KF']+2}px "Noto Sans";color:#4C5560}}
.ft{{height:{s['FOOT']}px;flex:none;display:flex;align-items:center;justify-content:space-between;padding:0 {s['HP']}px;font:600 {s['FF']}px "Noto Sans";color:#4C5560;border-top:2px solid #DDE1E4}}'''
  rows=''
  for g in gs:
    rs,os_=g[g['root']],g['home' if g['root']=='away' else 'away']
    at='vs' if g.get('neutral') else ('at' if g['root']=='away' else 'vs')  # root away plays at home team; root home hosts
    tag=f'<span class="tg {"po" if g["race"]=="Playoff" else ""}">{nb(g["race"])}</span>'
    mid=f'<div class="mid"><div class="op"><span class="dc"><img src="../logos/{os_["id"]}.png" alt=""></span><div><div class="on">{at} <b>{rk(os_)}{nb(os_["name"])}</b></div><div class="kt">{kt(g)}</div></div></div></div>'
    rows+=f'<div class="r"><div class="pn" style="--f:{fill(g["color"])}"><span class="dc"><img src="../logos/{rs["id"]}.png" alt=""></span><div><div class="rl">Root for</div><div class="nm">{rk(rs)}{nb(rs["name"])}</div></div></div>{mid}<div class="gn"><span>{d["team"]}&nbsp;gain</span><b>+{g["gain"]:.1f}&nbsp;pts</b></div><div class="wy">{tag}<span class="wt"><b>Why:</b> <span class="wx">{esc(g.get("why",""))}</span></span></div></div>'
  kmt='<span class="kmt"> &middot; Kickoff times&nbsp;MT</span>'   # shown only when the fit pass shortens '1:45 PM MT' to '1:45 PM' (Creative r3: keep MT)
  if extra: rows+=f'<div class="more">+{extra}&nbsp;more at kicktipmedia.com{kmt}</div>'
  elif gs: rows+=f'<div class="more kmt">Kickoff times&nbsp;MT</div>'
  if d.get('fallback'): rows=f'<div class="emp"><p>See this week&#39;s {d["team"]} Rootables at kicktipmedia.com</p><small>Every game, updated with the latest data</small></div>'   # og_cards overflow fallback: no rows, no claim
  elif not gs: rows=f'<div class="emp"><p>No other games this week move {d["team"]}\'s chances by&nbsp;much.</p><small>See every game at kicktipmedia.com</small></div>'
  st=f'<span>Updated {d["asof"]}</span>' if d.get('asof') else '<span></span>'
  return f'<html><head><meta charset=utf-8><style>{css}</style></head><body onload="{SNAP}"><div class="hd"><h1>{d["team"]} Rootables</h1><img src="../kt_header.png" alt="KickTip"></div><div class="bd">{rows}</div><div class="ft">{st}<span>{CHARTER}</span><span>kicktipmedia.com</span></div></body></html>',len(gs),extra
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
