"""p2d crops into crops/ at 320/390/1280: /privacy/ Questions section, the storage table (Headline number row), the top of the page, and the header of a simulator page (signed out, bar closed + Menu open below 760px).
Also asserts the simulator page carries both sim5's code and the p2c header/account hooks. Static server (tests/serve.py), headless Playwright. python3 tests/crops_p2d.py"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
srv, BASE = serve.start(); bad = 0
def ok(n, c, d=""):
    global bad
    print(("ok   " if c else "FAIL ") + n, "" if c else d); bad += 0 if c else 1
SIM = "/conference/big-12/simulator/"
html = open(f"{ROOT}/build/site{SIM}index.html", encoding="utf-8").read()
ok("sim page loads sim5's ccgsim.js + ccgsim-ui.js + ccgsim.css", all(x in html for x in ("/assets/ccgsim.js?v=", "/assets/ccgsim-ui.js?v=", "/assets/ccgsim.css?v=")))
ok("sim page also carries the header kit + account hooks (hdr.css, hdr.js, myteams.js, account.js, myteams.css)", all(x in html for x in ("/assets/hdr.css?v=", "/assets/hdr.js?v=", "/assets/myteams.js?v=", "/assets/account.js?v=", "/assets/myteams.css?v=")))
ok("sim page footer has the Privacy link, header has My teams", '<a href="/privacy/">Privacy</a>' in html and "My teams" in html)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/privacy/"); pg.wait_for_selector("h1"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{CR}/privacy-top-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 900 if w < 700 else 700})
        bx = pg.evaluate("""()=>{const h=[...document.querySelectorAll('h2')].find(e=>e.textContent.trim()==='Questions');let b=h.getBoundingClientRect().bottom;let n=h.nextElementSibling;while(n&&n.tagName!=='H2'){b=n.getBoundingClientRect().bottom;n=n.nextElementSibling}
          const t=h.getBoundingClientRect().top+scrollY-14;return {x:0,y:t,width:innerWidth,height:b+scrollY-t+14}}""")
        pg.screenshot(path=f"{CR}/privacy-questions-{w}.png", full_page=True, clip=bx)
        bx = pg.evaluate("(i)=>{const r=document.querySelectorAll('.pvw')[i].getBoundingClientRect();return {x:0,y:r.top+scrollY-34,width:innerWidth,height:r.height+44}}", 0)
        pg.screenshot(path=f"{CR}/privacy-storage-table-{w}.png", full_page=True, clip=bx)
        q = pg.evaluate("()=>{const h=[...document.querySelectorAll('h2')].find(e=>e.textContent.trim()==='Questions');const s=h.nextElementSibling;return {a:[...s.querySelectorAll('a[href^=mailto]')].length,t:s.textContent,ov:document.documentElement.scrollWidth-innerWidth}}")
        ok(f"privacy@{w}: Questions shows the address once as text inside exactly one mailto link, no page overflow", q["a"] == 1 and "support@kicktipmedia.com" in q["t"] and q["ov"] <= 0 and not errs, (q, errs))
        ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + SIM); pg.wait_for_selector("header.hd"); pg.wait_for_timeout(700)
        st = pg.evaluate("()=>({bar:getComputedStyle(document.querySelector('header.hd')).position,h:document.querySelector('header.hd').getBoundingClientRect().height,lab:!!document.getElementById('lab'),ov:document.documentElement.scrollWidth-innerWidth,acct:!!document.querySelector('.ac-si,.ac-chip'),mt:!!document.querySelector('a[href=\"/#my-teams\"]')})")
        ok(f"sim@{w}: sticky header {st['h']}px, account control present, My teams link, simulator markup, no overflow, no JS error", st["bar"] == "sticky" and st["h"] in (56, 64) and st["acct"] and st["mt"] and st["lab"] and st["ov"] <= 0 and not errs, (st, errs))
        if w < 760:
            pg.screenshot(path=f"{CR}/sim-header-closed-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 70})
            pg.click("#kh-btn"); pg.wait_for_selector(".hd--open"); pg.wait_for_timeout(350); pg.screenshot(path=f"{CR}/sim-header-menu-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 470})
        else: pg.screenshot(path=f"{CR}/sim-header-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 90})
        ctx.close()
    b.close()
print("crops_p2d:", "FAIL" if bad else "ok", bad)
