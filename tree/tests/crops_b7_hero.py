"""b7 hero crops: python3 tests/crops_b7_hero.py -> crops-b7/hero-{team,home}-{390,1280}.png"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-b7"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for W, S in ((390, 2), (1280, 1)):
        for nm, path in (("team", "/team/utah/"), ("home", "/"), ("conf", "/conference/big-12/"), ("playoff", "/playoff/"), ("404", "/404.html")):
            c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + path); pg.wait_for_timeout(500)
            pg.locator(".hero").first.screenshot(path=f"{OUT}/hero-{nm}-{W}.png"); c.close()
    b.close()
srv.shutdown(); print("ok")
