"""Crops (not full pages) of key pages at 1280@1x and 390@2x -> crops-b3/"""
import sys, os, re; sys.path.insert(0, "/workspace/kicktip/tests")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
JOBS = [("home", "/", 1500, 1500), ("conference-big12", "/conference/big-12/", 1700, 1700), ("team-utah", "/team/utah/", 1500, 1500), ("playoff", "/playoff/", 1700, 1700), ("method", "/method/", 1300, 1300)]
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, s in ((1280, 1), (390, 2)):
        h = 900 if w == 1280 else 1400
        for name, path, h1, h2 in JOBS:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page()
            pg.goto(BASE + path); pg.wait_for_timeout(700)
            pg.set_viewport_size({"width": w, "height": (1500 if w == 1280 else 1700)}); pg.wait_for_timeout(200)
            pg.screenshot(path=f"{ROOT}/crops-b3/{name}-{w}@{s}x.png"); ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(700)
        el = pg.locator("section.sec", has_text="State sites").first; el.scroll_into_view_if_needed(); el.screenshot(path=f"{ROOT}/crops-b3/home-state-sites-{w}@{s}x.png"); ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(600)
        pg.screenshot(path=f"{ROOT}/crops-b3/gate-{w}@{s}x.png")
        pg.check("#gate input[type=checkbox]"); pg.screenshot(path=f"{ROOT}/crops-b3/gate-checked-{w}@{s}x.png"); ctx.close()
    b.close()
print(sorted(os.listdir(f"{ROOT}/crops-b3")))
