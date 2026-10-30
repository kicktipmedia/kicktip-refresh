"""chip crops -> crops/. WITH chips: build/site-chipdemo (fixture snapshots, tests/chip_fixture.py); WITHOUT: build/site (real build, no previous day). python3 tests/crops_chip.py"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops"; os.makedirs(OUT, exist_ok=True)
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
n = 0
def shot(pg, name, sel=None):
    global n
    if sel: el = pg.locator(sel).first; el.scroll_into_view_if_needed(); pg.wait_for_timeout(150); el.screenshot(path=f"{OUT}/{name}.png")
    else: pg.screenshot(path=f"{OUT}/{name}.png")
    n += 1
def ready(pg, sel="#top12 tbody tr"): pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector(sel); pg.wait_for_timeout(600)
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in (320, 390, 430, 1280):
        S = 2 if W < 1000 else 1
        def ctx(): c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); return c
        # WITHOUT chips (real build): home Top 12 + team page
        srv, BASE = serve.start(f"{ROOT}/build/site"); c = ctx(); pg = c.new_page()
        pg.goto(BASE + "/"); ready(pg); shot(pg, f"home-nochip-{W}", "section:has(#top12)") if pg.locator("section:has(#top12)").count() else shot(pg, f"home-nochip-{W}")
        pg.goto(BASE + "/team/utah/"); ready(pg, "main[data-loaded]"); shot(pg, f"team-utah-nochip-{W}"); c.close(); srv.shutdown()
        # WITH chips (fixture)
        srv, BASE = serve.start(f"{ROOT}/build/site-chipdemo"); c = ctx(); pg = c.new_page()
        pg.goto(BASE + "/"); ready(pg); sec = "section:has(#top12)" if pg.locator("section:has(#top12)").count() else None
        shot(pg, f"home-chips-{W}", sec) if sec else shot(pg, f"home-chips-{W}")
        pg.locator(".mv").first.click(); pg.wait_for_selector(".mvpop:not([hidden])"); pg.wait_for_timeout(200); pg.locator(".mvpop").scroll_into_view_if_needed(); pg.wait_for_timeout(150); shot(pg, f"home-chip-popover-{W}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150); pg.keyboard.press("Tab"); pg.locator(".mv").nth(2).focus(); pg.wait_for_timeout(150)   # keyboard focus ring on a chip
        pg.locator(".mv").nth(2).scroll_into_view_if_needed(); pg.wait_for_timeout(150); shot(pg, f"home-chip-focus-ring-{W}", ".tw.tk-n")
        pg.goto(BASE + "/conference/big-12/"); ready(pg, "main[data-loaded] table"); shot(pg, f"conf-big12-chips-{W}")
        pg.locator(".mv[data-mv=utah]").click(); pg.wait_for_selector(".mvpop:not([hidden])"); pg.wait_for_timeout(200); shot(pg, f"conf-big12-popover-driver-utah-{W}")
        pg.keyboard.press("Escape"); pg.locator(".mv[data-mv=byu]").click(); pg.wait_for_timeout(200); shot(pg, f"conf-big12-popover-fallback-byu-{W}")
        pg.keyboard.press("Escape")
        pg.goto(BASE + "/team/utah/"); ready(pg, "main[data-loaded]"); shot(pg, f"team-utah-chipday-{W}")
        # model-change day (elo fixture has an older version): chips off, no note
        pg.goto(BASE + "/?model=elo"); ready(pg); shot(pg, f"home-model-change-day-elo-{W}")
        # dark-table simulation (the site has no dark table today): inject .on-dark on the Top 12 table's wrapper and a dark background
        pg.goto(BASE + "/"); ready(pg)
        pg.evaluate("(()=>{const t=document.querySelector('#top12');let w=t.closest('.tw')||t.parentElement;w.classList.add('on-dark');t.style.background='#121519';t.style.color='#fff';t.querySelectorAll('th,td').forEach(x=>{x.style.background='#121519';x.style.color='#fff'});t.querySelectorAll('a').forEach(x=>x.style.color='#fff')})()")
        pg.keyboard.press("Tab"); pg.locator(".mv").nth(1).focus(); pg.wait_for_timeout(150); shot(pg, f"dark-sim-focus-{W}", ".tw.tk-n")
        pg.locator(".mv").first.click(); pg.wait_for_timeout(200); pg.evaluate("window.scrollBy(0,-120)"); pg.wait_for_timeout(150); shot(pg, f"dark-sim-open-{W}")
        c.close(); srv.shutdown()
    b.close()
print(n, "crops")
