"""rev2b gate crops -> crops-rev2b/ (default state: gate open, storage line visible). python3 tests/crops_rev2b.py"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); O = f"{R}/crops-rev2b"; os.makedirs(O, exist_ok=True)
srv, BASE = serve.start(f"{R}/build/site")
with sync_playwright() as p:
    b = p.chromium.launch()
    for W, S in ((320, 2), (390, 2), (1280, 1)):
        c = b.new_context(viewport={"width": W, "height": 800}, device_scale_factor=S); pg = c.new_page(); pg.goto(BASE + "/"); pg.wait_for_selector("#gate:not([hidden])"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{O}/gate-{W}.png"); pg.locator("#gate .dlg").screenshot(path=f"{O}/gate-dialog-{W}.png")
        print(W, pg.evaluate("() => { const d = document.querySelector('#gate .dlg').getBoundingClientRect(); return [Math.round(d.height), innerHeight, document.querySelector('#gate .dlg').scrollHeight > document.querySelector('#gate .dlg').clientHeight] }"))
        c.close()
    b.close()
srv.shutdown()
