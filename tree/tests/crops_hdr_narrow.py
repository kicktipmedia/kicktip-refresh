"""Narrow-viewport crops -> crops-hdr3b/narrow-<name>-<open|closed>.png (home). 160x284 DPR2; zoom200-320 = a 320px phone at 200% browser zoom = 160 CSS px wide at DPR4; 200, 240, 296 DPR2."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-hdr3b"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start(os.environ.get("KT_SITE"))
CASES = [("160x284", 160, 284, 2), ("zoom200-320", 160, 284, 4), ("200x356", 200, 356, 2), ("240x427", 240, 427, 2), ("296x526", 296, 526, 2)]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, W, H, dpr in CASES:
        c = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=dpr); pg = c.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(700)
        pg.screenshot(path=f"{OUT}/narrow-{name}-closed.png"); pg.click("#kh-btn"); pg.wait_for_timeout(350); pg.screenshot(path=f"{OUT}/narrow-{name}-open.png"); c.close()
    b.close()
srv.shutdown(); print("done", OUT)
