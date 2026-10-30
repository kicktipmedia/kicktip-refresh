"""p2c variant: pixel-compare the CLOSED 56px bar (y 0-56) of two builds at every width below 760 (header3b vs p2c must be identical there: Sign in / My teams live inside the Menu panel) and, at 760+, the bar minus its nav (brand + pill region). Usage: python3 tests/hdr_pixel_p2c.py <header3b site> <p2c site>"""
import sys, os, io; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
sa, ba = serve.start(sys.argv[1]); sb, bb = serve.start(sys.argv[2]); bad = 0; n = 0
def shot(pg, base, path, W, menu):
    pg.goto(base + path); pg.wait_for_timeout(500)
    if menu: pg.click("#kh-btn"); pg.wait_for_timeout(350)
    return Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": (W if W < 760 else 300), "height": 56}))).convert("RGB")
with sync_playwright() as p:
    for eng in ("chromium", "webkit"):
        b = getattr(p, eng).launch()
        for W in (300, 320, 359, 360, 375, 390, 414, 600, 759, 760, 1024, 1101, 1280):
            c = b.new_context(viewport={"width": W, "height": 800}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
            for path in ("/", "/playoff/", "/conference/big-12/simulator/"):
                for menu in (False,):
                    x, y = shot(pg, ba, path, W, menu), shot(pg, bb, path, W, menu); n += 1
                    if ImageChops.difference(x, y).getbbox(): bad += 1; print("DIFF", eng, path, W, "menu" if menu else "top", ImageChops.difference(x, y).getbbox())
            c.close()
        b.close()
print(f"hdr_pixel_p2c: {n} comparisons, {bad} differ"); sys.exit(1 if bad else 0)
