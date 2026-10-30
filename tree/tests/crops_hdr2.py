"""Header crops -> crops-hdr2/<page>-<w>-<state>.png. python3 tests/crops_hdr2.py [outdir]. Pages: home, conference (big-12), playoff, top25 (long table). States: top (banner visible), scrolled (bar pinned), menu (open, <760 only), anchor (after tapping Conferences on home), ask (Ask panel open)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/crops-hdr2"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start(os.environ.get("KT_SITE"))
PAGES = {"home": "/", "conference": "/conference/big-12/", "playoff": "/playoff/", "top25": "/top25/"}
def settle(pg):
    pg.wait_for_timeout(450)
    if pg.locator("main[data-gated]").count():
        try: pg.wait_for_selector("main[data-loaded]", timeout=4000)
        except Exception: pass
    pg.wait_for_timeout(300)
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in (320, 390, 1024, 1101, 1280):
        H = 844 if W < 500 else 800; c = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
        for name, path in PAGES.items():
            N = lambda s: f"{OUT}/{name}-{W}-{s}.png"
            pg.goto(BASE + path); settle(pg); pg.screenshot(path=N("top"))
            if name == "top25":   # long list: a table from 760px up, a card list below it (the table is display:none there) -> scroll into the list either way
                pg.evaluate("() => { const t = document.getElementById('t25'), r = t.getBoundingClientRect(); const y = r.height ? r.top + scrollY - 72 : t.closest('.card').getBoundingClientRect().top + scrollY + 900; window.scrollTo(0, y) }")
            else: pg.evaluate("window.scrollTo(0, 700)")
            pg.wait_for_timeout(350); pg.screenshot(path=N("scrolled"))
            if W < 760:
                pg.click("#kh-btn"); pg.wait_for_timeout(350); pg.screenshot(path=N("menu")); pg.keyboard.press("Escape")
        pg.goto(BASE + "/"); settle(pg)
        if W < 760: pg.click("#kh-btn"); pg.wait_for_timeout(250)
        pg.locator(".hd .nav a", has_text="Conferences").click(); pg.wait_for_timeout(900); pg.screenshot(path=f"{OUT}/home-{W}-anchor.png")
        pg.goto(BASE + "/conference/big-12/"); settle(pg); pg.evaluate("window.scrollTo(0, 600)"); pg.wait_for_timeout(250); pg.click("#kpill"); pg.wait_for_timeout(600); pg.screenshot(path=f"{OUT}/conference-{W}-ask.png")
        c.close()
    b.close()
srv.shutdown(); print("crops done", OUT)
