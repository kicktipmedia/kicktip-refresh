"""Crops of the lines UI at 320/390/430/1280 -> crops/odds/. Fake browser clock (see odds_test.py)."""
import sys, os, re, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops/odds"; os.makedirs(OUT, exist_ok=True)
GAMES = json.load(open(f"{ROOT}/build/site/data/pred-games.json"))["g"]; LINES = json.load(open(f"{ROOT}/build/site/data/pred-lines.json"))["l"]
NL = [k for k, v in GAMES.items() if k not in LINES and v[0] is not None][0]
T_OPEN = dt.datetime(2026, 10, 25, 14, 0, tzinfo=dt.timezone.utc); T_CLOSED = dt.datetime(2026, 10, 26, 12, 0, tzinfo=dt.timezone.utc)   # 8:00 AM MT Oct 25 (ESPN pull read 1:32 AM MT) / 6:00 AM MT Oct 26 (> 24 h)
srv, BASE = serve.start()
def ctx(b, w, t):
    c = b.new_context(viewport={"width": w, "height": 900 if w < 1000 else 800}, device_scale_factor=1)
    pg = c.new_page(); pg.clock.set_fixed_time(t); return c, pg
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 768, 1280):
        # D1 / D2: team page games, collapsed and open, with a line
        c, pg = ctx(b, w, T_OPEN); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); art = pg.locator('[data-gk="georgia~florida"]').first
        btn = art.locator(".gbt")
        if btn.get_attribute("aria-expanded") == "true": btn.click()
        pg.wait_for_timeout(150); art.screenshot(path=f"{OUT}/D1-collapsed-{w}.png")
        btn.click(); pg.wait_for_timeout(150); art.screenshot(path=f"{OUT}/D2-open-{w}.png"); c.close()
        # D3: no market line
        c, pg = ctx(b, w, T_OPEN); pg.goto(BASE + "/team/" + NL.split("~")[0] + "/"); pg.wait_for_selector(f'[data-gk="{NL}"] .gbt'); art = pg.locator(f'[data-gk="{NL}"]').first; btn = art.locator(".gbt")
        if btn.get_attribute("aria-expanded") == "false": btn.click()
        pg.wait_for_timeout(150); art.screenshot(path=f"{OUT}/D3-nomarket-{w}.png"); c.close()
        # D4: closed
        c, pg = ctx(b, w, T_CLOSED); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); art = pg.locator('[data-gk="georgia~florida"]').first; btn = art.locator(".gbt")
        if btn.get_attribute("aria-expanded") == "false": btn.click()
        pg.wait_for_timeout(150); art.screenshot(path=f"{OUT}/D4-closed-{w}.png"); c.close()
        # slate page
        c, pg = ctx(b, w, T_OPEN); pg.goto(BASE + "/games/"); pg.wait_for_selector("[data-slate] [data-gk] .gbt, [data-slate] tr[data-gk] [data-c=mk] .nm", state="attached"); pg.wait_for_timeout(300)
        pg.locator("[data-slate-ctl]").scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-60)"); pg.screenshot(path=f"{OUT}/slate-{w}.png"); c.close()
        # horizontal overflow check on lines pages
        c, pg = ctx(b, w, T_OPEN); 
        for path in ("/games/", "/team/georgia/", "/conference/big-12/"):
            pg.goto(BASE + path); pg.wait_for_selector(".gbt", state="attached"); pg.wait_for_timeout(200)
            sw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"); print(w, path, "scrollWidth/innerWidth", sw, "OVERFLOW" if sw[0] > sw[1] else "ok")
        c.close()
    b.close()
srv.shutdown()
