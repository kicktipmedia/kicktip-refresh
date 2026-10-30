"""Crops for the CCG label + definition line. home / conference / team (top: tiles + definition) at 390 and 1280, team Rootables after Run at 320/390/1280. python3 tests/crops_ccg.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); C = f"{ROOT}/crops"; os.makedirs(C, exist_ok=True)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
        if w in (390, 1280):
            for n, u, sel in (("home", "/", "#top12"), ("conference", "/conference/big-12/", "table"), ("team-chances", "/team/utah/", ".tiles")):
                pg.goto(BASE + u); pg.wait_for_timeout(1200); pg.evaluate("document.fonts.ready")
                el = pg.locator(sel).first; sec = pg.locator("section.sec", has=el).first
                sec.screenshot(path=f"{C}/ccg-{n}-{w}.png")
            pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(1000)
            card = pg.locator(".card", has=pg.locator("#paths")).first; card.screenshot(path=f"{C}/ccg-team-paths-{w}.png")
        pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(800); pg.click("#rootables [data-run]"); pg.wait_for_selector("#rootables[data-rb=on]:not([aria-busy])", timeout=10000); pg.wait_for_timeout(400)
        pg.evaluate("() => { const k = document.getElementById('kpill'); if (k) k.style.display = 'none'; }")
        pg.locator("#rootables").screenshot(path=f"{C}/ccg-rootables-{w}.png")
        pg.click("[data-outcome=ccg]"); pg.wait_for_timeout(300); pg.locator("#rootables").screenshot(path=f"{C}/ccg-rootables-ccg-{w}.png")
        ctx.close()
    b.close()
print("ok")
