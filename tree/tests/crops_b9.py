"""b9 bracket crops: python3 tests/crops_b9.py -> crops-b9/*.png (accepted: full + by-round + scrolled; before the gate; no-JS)."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-b9"; os.makedirs(OUT, exist_ok=True)
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
srv, BASE = serve.start(); n = 0
def shot(pg, name, sel="#bracket"):
    el = pg.locator(sel); el.scroll_into_view_if_needed(); pg.wait_for_timeout(250); el.screenshot(path=f"{OUT}/{name}.png")
with sync_playwright() as p:
    b = p.chromium.launch()
    for W, S in ((320, 2), (390, 2), (1280, 1)):
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(600)
        shot(pg, f"bracket-full-{W}"); n += 1
        if W < 1280:
            pg.evaluate("document.querySelector('#bracket .bkw').scrollLeft = 300"); pg.wait_for_timeout(200); shot(pg, f"bracket-full-scrolled-{W}"); n += 1
            pg.evaluate("document.querySelector('#bracket .bkw').scrollLeft = 9999"); pg.wait_for_timeout(200); shot(pg, f"bracket-full-scrolled-end-{W}"); n += 1
            pg.click("[data-bkview=rounds]"); pg.wait_for_timeout(200); shot(pg, f"bracket-byround-{W}"); n += 1
        c.close()
    # before the gate is accepted (modal open) and with no JS: bracket skeleton only, no teams, no numbers
    for W in (390, 1280):
        c = b.new_context(viewport={"width": W, "height": 900}); pg = c.new_page(); pg.goto(BASE + "/playoff/"); pg.wait_for_timeout(500)
        pg.evaluate("document.getElementById('gate').hidden = true"); shot(pg, f"bracket-before-gate-{W}"); n += 1; c.close()
        c = b.new_context(viewport={"width": W, "height": 900}, java_script_enabled=False); pg = c.new_page(); pg.goto(BASE + "/playoff/"); shot(pg, f"bracket-nojs-{W}"); n += 1; c.close()
    b.close()
srv.shutdown(); print(n, "crops")
