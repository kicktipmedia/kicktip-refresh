"""b4c crops -> crops-b4c/: gate note (and whole dialog) at 1280, 1024, 390, 320; method bullets."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-b4c"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1280, 1024, 390, 320):
        s = 2 if w < 600 else 1
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(500)
        pg.locator("#gate .gnote").screenshot(path=f"{OUT}/gate-note-{w}@{s}x.png"); pg.locator("#gate .dlg").screenshot(path=f"{OUT}/gate-dialog-{w}@{s}x.png"); ctx.close()
    for w, s in ((1280, 1), (390, 2)):
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + "/method/"); pg.wait_for_timeout(500)
        pg.locator("h2:text-is('The simulation') + ul").screenshot(path=f"{OUT}/method-simulation-bullets-{w}@{s}x.png")
        pg.locator("li:has-text('games that have not started')").first.screenshot(path=f"{OUT}/method-market-bullet-{w}@{s}x.png"); ctx.close()
    b.close()
print(sorted(os.listdir(OUT)))
