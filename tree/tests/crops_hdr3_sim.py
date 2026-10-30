"""Simulator + playoff crops with the header: python3 tests/crops_hdr3_sim.py [outdir] -> crops-hdr3/sim-<slug>-<w>-<state>.png, playoff-<w>-<state>.png
States: top, scrolled (mirror bar #ccgc pinned under the header at top = --kt-bar-h), menu (Menu open while the mirror bar is showing; 320/390 only), 1280 gets scrolled only."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/crops-hdr3"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start(os.environ.get("KT_SITE"))
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in (320, 390, 1280):
        H = 844 if W < 500 else 800; c = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
        for slug in ("big-12", "pac-12"):
            pg.goto(f"{BASE}/conference/{slug}/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(500)
            pg.screenshot(path=f"{OUT}/sim-{slug}-{W}-top.png")
            pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(500); pg.screenshot(path=f"{OUT}/sim-{slug}-{W}-scrolled.png")
            if W < 760: pg.click("#kh-btn"); pg.wait_for_timeout(350); pg.screenshot(path=f"{OUT}/sim-{slug}-{W}-menu.png"); pg.keyboard.press("Escape")
            print(slug, W, pg.evaluate("() => ({bar: getComputedStyle(document.documentElement).getPropertyValue('--kt-bar-h'), hd: document.querySelector('header.hd').getBoundingClientRect().height, ccgc: document.getElementById('ccgc').getBoundingClientRect().top, on: document.getElementById('ccgc').classList.contains('on')})"))
        pg.goto(BASE + "/playoff/"); pg.wait_for_timeout(1200); pg.screenshot(path=f"{OUT}/playoff-{W}-top.png")
        pg.evaluate("window.scrollTo(0, 700)"); pg.wait_for_timeout(350); pg.screenshot(path=f"{OUT}/playoff-{W}-scrolled.png")
        if W < 760: pg.click("#kh-btn"); pg.wait_for_timeout(350); pg.screenshot(path=f"{OUT}/playoff-{W}-menu.png"); pg.keyboard.press("Escape")
        c.close()
    b.close()
srv.shutdown(); print("sim crops done", OUT)
