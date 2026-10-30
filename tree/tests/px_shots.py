"""Full-page screenshots of the 7 page types at 320/390/430/1280, normal (900 high) and tall (2400 high) windows, into an out dir. Used for the before/after pixel diff of the top-strip colour-chain change. python3 tests/px_shots.py OUTDIR"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
T = {"home": "/", "team": "/team/utah/", "conf": "/conference/big-12/", "playoff": "/playoff/", "method": "/method/", "disc": "/disclaimer/", "404": "/nope-404/"}
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for h in (900, 2400):
        for w in (320, 390, 430, 1280):
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            for n, u in T.items():
                pg.goto(BASE + u); pg.wait_for_timeout(900); pg.evaluate("document.fonts.ready")
                pg.screenshot(path=f"{out}/{n}-{w}-{h}.png", full_page=True)
            ctx.close()
    b.close()
