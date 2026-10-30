"""c1r1d sanity crop: one real answer at 390 (data refreshed to 5:55 PM MT; visuals unchanged)."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch(); c = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("#kpill:not([hidden])")
    pg.click("#kpill"); pg.wait_for_selector(".q"); pg.fill("#kask", "What if Utah Utes lose to Houston?"); pg.click("#kform .snd"); pg.wait_for_selector(".ba", timeout=90000); pg.wait_for_function("!document.querySelector('.prog')", timeout=90000); pg.wait_for_timeout(400)
    pg.screenshot(path=f"{ROOT}/crops/c1r1d/390-answer-refresh1955-data.png"); pg.locator("#kbd").evaluate("e => e.scrollTop = e.scrollHeight"); pg.wait_for_timeout(300); pg.screenshot(path=f"{ROOT}/crops/c1r1d/390-answer-refresh1955-data-bottom.png"); b.close()
srv.shutdown()
