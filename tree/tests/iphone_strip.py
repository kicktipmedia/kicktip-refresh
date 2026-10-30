"""iPhone-emulated top-strip crops: Playwright WebKit (iPhone profiles) with the safe-area insets emulated (env(safe-area-inset-top)=59px, bottom=34px, by rewriting the env() calls in kt.css/chat.css as they are served; real iOS Safari/Chrome chrome can not be driven headless) plus a drawn 59px status-bar overlay (clock text only, transparent, like iOS with viewport-fit=cover). Asserts every pixel of the column at x=40px from y=0 to the bottom of the header is the one graphite rgb(38,43,49) (banner border line excepted). Writes crops/iphone-safearea-*.png. python3 tests/iphone_strip.py"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
srv, BASE = serve.start(); fails = 0
OVER = "(()=>{const d=document.createElement('div');d.style.cssText='position:fixed;left:0;top:0;right:0;height:59px;z-index:99999;pointer-events:none;color:#fff;font:600 16px -apple-system,Arial;display:flex;justify-content:space-between;align-items:flex-end;padding:0 28px 8px';d.innerHTML='<span>8:34</span><span>5G &#9646;&#9646;&#9646;</span>';document.body.appendChild(d)})()"
def fix(route):
    r = route.fetch(); body = r.text().replace("env(safe-area-inset-top,0px)", "59px").replace("env(safe-area-inset-bottom,0px)", "34px")
    route.fulfill(response=r, body=body)
with sync_playwright() as p:
    for eng, dev, tag in ((p.webkit, "iPhone 14", "390"), (p.webkit, "iPhone 14 Pro Max", "430")):
        b = eng.launch(); ctx = b.new_context(**p.devices[dev]); pg = ctx.new_page()
        pg.route(re.compile(r".*/assets/(kt|chat)\.css.*"), fix)
        for name, path in (("home", "/"), ("team", "/team/utah/")):
            pg.goto(BASE + path); pg.wait_for_timeout(1500)
            vp = pg.evaluate("document.querySelector('meta[name=viewport]').content"); w = pg.evaluate("innerWidth")
            col = pg.evaluate("""()=>{const g=e=>getComputedStyle(e).backgroundColor;return {html:getComputedStyle(document.documentElement).backgroundImage,body:g(document.body),tb:g(document.querySelector('.tb')),hd:g(document.querySelector('.hd')),tbTop:document.querySelector('.tb').getBoundingClientRect().top,tbPad:getComputedStyle(document.querySelector('.tb')).paddingTop,hdBottom:document.querySelector('.hd').getBoundingClientRect().bottom}}""")
            pg.evaluate(OVER); pg.wait_for_timeout(200)
            f = f"{CR}/iphone-safearea-{tag}-{name}.png"; pg.screenshot(path=f)
            im = Image.open(f).convert("RGB"); sc = im.size[0] / w; hb = int(col["hdBottom"] * sc)
            bad = [y for y in range(0, hb - 2) if im.getpixel((40, y)) != (38, 43, 49) and not (abs(y / sc - (59 + 8 + 8 + 19)) < 4)]
            # the 1px translucent line under the banner is the only allowed lighter row
            line = [y for y in range(0, hb - 2) if im.getpixel((40, y)) != (38, 43, 49)]
            ok = col["tbPad"] == "59px" and col["body"] == "rgb(38, 43, 49)" and col["tb"] == col["hd"] == "rgb(38, 43, 49)" and "viewport-fit=cover" in vp and col["tbTop"] == 0 and len(line) <= 3
            print(("PASS" if ok else "FAIL"), tag, name, vp, col, "non-graphite rows in the x=40 column:", line)
            fails += (not ok)
        ctx.close(); b.close()
sys.exit(1 if fails else 0)
