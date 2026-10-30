"""v6a crops: BEFORE = a base zip extracted to a dir (default before-site-dom1/ = deployed dom1; before-site-samedata/ = b9f, dom1 code on the same data as v6a), AFTER = build/site, accepted state. python3 tests/crops_v6a.py [before_dir] [out_dir]"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BEF = sys.argv[1] if len(sys.argv) > 1 else "before-site-dom1"; OUT = f"{ROOT}/" + (sys.argv[2] if len(sys.argv) > 2 else "crops"); os.makedirs(OUT, exist_ok=True)
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
PAGES = [("home", "/", "#top12"), ("conf-big12", "/conference/big-12/", "main"), ("team-utah", "/team/utah/", "main"), ("playoff", "/playoff/", "main"), ("method", "/method/", "main")]
SECT = [("method-models", "/method/", "#models"), ("method-accuracy", "/method/", "#accuracy"), ("method-changed", "/method/", "#changed")]
n = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, site in (("before", f"{ROOT}/{BEF}"), ("after", f"{ROOT}/build/site")):
        srv, BASE = serve.start(site)
        for W, S in ((320, 2), (390, 2), (1280, 1)):
            c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page()
            todo = PAGES + (SECT if tag == "after" else [])
            for name, path, sel in todo:
                pg.goto(BASE + path)
                if not path.startswith("/method"): pg.wait_for_selector("main[data-loaded]")
                pg.wait_for_timeout(900)
                if sel == "main": pg.screenshot(path=f"{OUT}/{name}-{tag}-{W}.png", full_page=(name in ("method",)) )
                else:
                    el = pg.locator(sel).first; el.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
                    if name == "home": pg.screenshot(path=f"{OUT}/{name}-{tag}-{W}.png", full_page=False, clip=None) if False else el.screenshot(path=f"{OUT}/{name}-{tag}-{W}.png")
                    else: el.screenshot(path=f"{OUT}/{name}-{tag}-{W}.png")
                n += 1
            if tag == "after":   # alternate model selected (after acceptance only), control visible
                pg.goto(BASE + "/"); pg.wait_for_selector("[data-mdl]"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_timeout(300); pg.screenshot(path=f"{OUT}/home-after-top-default-{W}.png"); n += 1
                for mid in ("msm", "elo"):
                    pg.goto(BASE + "/"); pg.wait_for_selector("[data-mdl]"); pg.wait_for_selector("#top12 tbody tr"); (pg.click("[data-more]") if mid == "elo" else None); pg.click(f"[data-m={mid}]"); pg.wait_for_selector(f"[data-model={mid}]"); pg.wait_for_timeout(500)
                    pg.screenshot(path=f"{OUT}/home-after-{mid}-{W}.png"); n += 1
            c.close()
        # before the gate is accepted: modal, no model numbers; (after only)
        if tag == "after":
            for W in (390, 1280):
                c = b.new_context(viewport={"width": W, "height": 900}); pg = c.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(700); pg.screenshot(path=f"{OUT}/home-after-gate-{W}.png"); n += 1; c.close()
        srv.shutdown()
    b.close()
print(n, "crops")
