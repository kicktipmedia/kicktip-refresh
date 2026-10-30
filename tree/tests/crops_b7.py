"""b7 sticky-column crops: python3 tests/crops_b7.py before|after  -> crops-b7/{before,after}-<page>-<table>-<w>.png (scrolled sideways so content slides under the sticky columns)"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-b7"; os.makedirs(OUT, exist_ok=True)
LAB = sys.argv[1]
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
PAGES = (("home", "/"), ("conf-big12", "/conference/big-12/"), ("team-utah", "/team/utah/"), ("playoff", "/playoff/"))
srv, BASE = serve.start(); n = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for W, S in ((390, 2), (1280, 1)):
        for nm, path in PAGES:
            c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + path); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(500)
            tws = pg.locator(".tw.tk-n, .tw.tk-g"); 
            for i in range(tws.count()):
                el = tws.nth(i); el.scroll_into_view_if_needed(); pg.wait_for_timeout(100)
                pg.evaluate("(i) => { const e = document.querySelectorAll('.tw.tk-n, .tw.tk-g')[i]; e.scrollLeft = Math.min(e.scrollWidth - e.clientWidth, 150); }", i); pg.wait_for_timeout(150)
                bb = el.bounding_box()
                if not bb: continue
                pg.screenshot(path=f"{OUT}/{LAB}-{nm}-t{i}-{W}.png", full_page=True, clip={"x": max(bb["x"], 0), "y": bb["y"] + pg.evaluate("window.scrollY"), "width": min(bb["width"], W), "height": min(bb["height"], 330)}); n += 1
            c.close()
    b.close()
srv.shutdown(); print(n, "crops", LAB)
