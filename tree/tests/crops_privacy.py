"""Crops for p2b: crops/privacy-{full,top,footer}-{320,390,1280}.png and crops/myteams-line-{320,390,430,1280}.png (the SHORT cookie line on My teams). python3 tests/crops_privacy.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=2 if w < 700 else 1); pg = ctx.new_page()
        pg.goto(BASE + "/privacy/"); pg.wait_for_selector("h1"); pg.wait_for_timeout(300)
        pg.screenshot(path=f"{CR}/privacy-full-{w}.png", full_page=True)
        pg.screenshot(path=f"{CR}/privacy-top-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 760 if w < 700 else 620})
        r = pg.evaluate("(() => { const r = document.querySelector('.ft').getBoundingClientRect(); return { y: r.top + scrollY, h: r.height } })()")   # document coordinates
        pg.screenshot(path=f"{CR}/privacy-footer-{w}.png", full_page=True, clip={"x": 0, "y": r["y"], "width": w, "height": r["h"]})
        ctx.close()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=2 if w < 700 else 1); pg = ctx.new_page()
        pg.goto(BASE + "/"); pg.wait_for_selector(".mt-ed"); pg.wait_for_selector(".mt-pv"); pg.wait_for_timeout(300)
        pg.locator("#my-teams").screenshot(path=f"{CR}/myteams-line-{w}.png")
        ctx.close()
    b.close()
srv.shutdown(); print("crops_privacy done")
