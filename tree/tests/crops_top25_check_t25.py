import sys, os, datetime as dt; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = dt.datetime(2026, 10, 25, 14, 0, tzinfo=dt.timezone.utc)
def shoot(site, w, path, full):
    srv, base = serve.start(site)
    with sync_playwright() as p:
        b = p.chromium.launch(); c = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1); pg = c.new_page(); pg.clock.set_fixed_time(T)
        pg.goto(base + "/top25/"); pg.wait_for_selector("main[data-loaded='1']"); pg.wait_for_timeout(1200); pg.screenshot(path=path, full_page=full); b.close()
    srv.shutdown()
for w in (320, 390, 430, 1280):
    shoot("/tmp/top25_x", w, f"/tmp/ot25/t25base-{w}.png", True)
    shoot(f"{ROOT}/build/site", w, f"{ROOT}/crops/odds-t25-top25-{w}.png", True)
    a = Image.open(f"/tmp/ot25/t25base-{w}.png").convert("RGB"); bb = Image.open(f"{ROOT}/crops/odds-t25-top25-{w}.png").convert("RGB")
    h = min(a.height, bb.height); d = ImageChops.difference(a.crop((0, 0, a.width, h)), bb.crop((0, 0, bb.width, h))); bbx = d.getbbox()
    print(w, "sizes", a.size, bb.size, "diff bbox", bbx, "(diff only in footer if y >= %d)" % (min(a.height, bb.height) - 400))
