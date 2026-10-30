"""Crops of /top25/ for Creative: crops/top25-<shot>-<width>.png at 320/390/430/1280. python3 tests/crops_top25.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        pg = b.new_context(viewport={"width": w, "height": 900}).new_page(); pg.goto(BASE + "/top25/"); pg.wait_for_selector("main[data-t25]"); pg.wait_for_timeout(600)
        pg.screenshot(path=f"{OUT}/top25-top-{w}.png")
        pg.evaluate("document.getElementById('kpill').style.display='none'")   # the floating pill would cover element shots; the page itself is unchanged
        pg.locator("xpath=//ol[@id='t25l']/ancestor::div[contains(@class,'card')][1]").screenshot(path=f"{OUT}/top25-list-{w}.png")
        pg.locator(".t25-run").screenshot(path=f"{OUT}/top25-run-{w}.png")
        if pg.evaluate("!document.getElementById('t25out').hidden"): pg.locator("#t25out").screenshot(path=f"{OUT}/top25-outside-{w}.png")
        if w < 700:
            li = pg.locator("#t25l > li").nth(1); li.locator(".t25-chv").click(); li.screenshot(path=f"{OUT}/top25-expanded-{w}.png")
        else:
            pg.locator("#t25").screenshot(path=f"{OUT}/top25-expanded-{w}.png", clip=None) if False else pg.locator("#t25 tbody tr").nth(1).screenshot(path=f"{OUT}/top25-row-{w}.png")
    b.close()
print(sorted(os.listdir(OUT)))
