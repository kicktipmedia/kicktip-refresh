"""Home (real build) and method-page crops at 320/390/430/1280 -> crops/odds-home-*.png, odds-method-lines-*.png. Fake clock as in odds_test.py."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
import datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops"
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 768, 1280):
        c = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1); pg = c.new_page(); pg.clock.set_fixed_time(dt.datetime(2026, 10, 25, 14, 0, tzinfo=dt.timezone.utc))
        pg.goto(BASE + "/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(600); pg.screenshot(path=f"{OUT}/odds-home-{w}.png")
        pg.goto(BASE + "/method/"); pg.wait_for_timeout(300)
        h = pg.locator("h2:has-text('lines'), h3:has-text('lines'), h2:has-text('Market'), h3:has-text('Market')").first
        if h.count(): h.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-80)"); pg.wait_for_timeout(150); pg.screenshot(path=f"{OUT}/odds-method-lines-{w}.png")
        c.close()
    b.close()
srv.shutdown()
