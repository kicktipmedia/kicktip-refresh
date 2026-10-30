"""Pixel-compare two builds' header at widths >= 300 (header3 vs header3b must be identical there): python3 tests/hdr_pixel_same.py <siteA> <siteB>"""
import sys, os, io; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
sa, ba = serve.start(sys.argv[1]); sb, bb = serve.start(sys.argv[2]); bad = 0; n = 0
def shot(pg, base, path, W, menu):
    pg.goto(base + path); pg.wait_for_timeout(500)
    if menu: pg.click("#kh-btn"); pg.wait_for_timeout(350)
    return Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": W, "height": 520}))).convert("RGB")
with sync_playwright() as p:
    for eng in ("chromium", "webkit"):
        b = getattr(p, eng).launch()
        for W in (300, 320, 359, 360, 375, 390, 414, 600, 759, 760, 1024, 1101, 1280):
            c = b.new_context(viewport={"width": W, "height": 800}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
            for path in ("/", "/playoff/", "/conference/big-12/simulator/"):
                for menu in ((False, True) if W < 760 else (False,)):
                    x, y = shot(pg, ba, path, W, menu), shot(pg, bb, path, W, menu); n += 1
                    if ImageChops.difference(x, y).getbbox(): bad += 1; print("DIFF", eng, path, W, "menu" if menu else "top", ImageChops.difference(x, y).getbbox())
            c.close()
        b.close()
print(f"hdr_pixel_same: {n} comparisons, {bad} differ"); sys.exit(1 if bad else 0)
