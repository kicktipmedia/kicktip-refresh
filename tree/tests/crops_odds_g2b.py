"""g2b: slate table rows (incl. 'Market line not posted yet.') at 768/1024/1280 -> crops/odds-lines-slate-table-*.png"""
import sys, os, datetime as dt; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (768, 1024, 1280):
        c = b.new_context(viewport={"width": w, "height": 700}); pg = c.new_page(); pg.clock.set_fixed_time(dt.datetime(2026, 10, 25, 14, 0, tzinfo=dt.timezone.utc))
        pg.goto(BASE + "/games/"); pg.wait_for_selector(".gt tbody tr", state="attached"); pg.wait_for_timeout(400)
        pg.locator(".gt thead").scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-30)"); pg.wait_for_timeout(200); pg.screenshot(path=f"{ROOT}/crops/odds-lines-slate-table-{w}.png"); c.close()
    b.close()
srv.shutdown()
