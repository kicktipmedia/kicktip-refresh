"""rev2 crops -> crops-rev2/. BEFORE = before-site-samedata (b9f: deployed dom1 code on the same data), AFTER = build/site. python3 tests/crops_rev2.py"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-rev2"; os.makedirs(OUT, exist_ok=True)
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
BACC = "localStorage.setItem('kicktip_gate', JSON.stringify({v:'2026-10-23-v2',t:Date.now()})); sessionStorage.setItem('kicktip_gate_visit','1');"
n = 0
def shot(pg, name, sel=None, full=False):
    global n
    if sel: el = pg.locator(sel).first; el.scroll_into_view_if_needed(); pg.wait_for_timeout(150); el.screenshot(path=f"{OUT}/{name}.png")
    else: pg.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    n += 1
with sync_playwright() as p:
    b = p.chromium.launch()
    # BEFORE (same-data b9f, its own accepted gate version)
    srv, BASE = serve.start(f"{ROOT}/before-site-samedata")
    for W, S in ((320, 2), (390, 2), (1280, 1)):
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(BACC); pg = c.new_page()
        pg.goto(BASE + "/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(900); shot(pg, f"home-before-{W}")
        if W == 390:
            pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(900); shot(pg, "team-utah-before-390")
        c.close()
    srv.shutdown()
    srv, BASE = serve.start(f"{ROOT}/build/site")
    for W, S in ((320, 2), (390, 2), (1280, 1)):
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page()
        # home default (top of page, then the model card in 3 states)
        pg.goto(BASE + "/"); pg.wait_for_selector("[data-mdl]"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_timeout(500)
        shot(pg, f"home-default-{W}"); shot(pg, f"card-closed-{W}", "[data-mdl]")
        pg.click("[data-why]"); pg.wait_for_timeout(200); shot(pg, f"card-whats-this-open-{W}", "[data-mdl]"); pg.click("[data-why]")
        pg.click("[data-more]"); pg.wait_for_timeout(200); shot(pg, f"card-more-expanded-{W}", "[data-mdl]")
        pg.click("[data-m=elo]"); pg.wait_for_selector("[data-model=elo]"); pg.wait_for_timeout(500); shot(pg, f"card-elo-selected-more-open-{W}", "[data-mdl]")
        pg.click("[data-why]"); pg.wait_for_timeout(200); shot(pg, f"card-elo-whats-this-open-{W}", "[data-mdl]")
        pg.reload(); pg.wait_for_selector("[data-model=elo]"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_timeout(500); shot(pg, f"home-elo-picked-restored-{W}")
        if W == 390:
            pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("[data-model=elo]"); pg.wait_for_timeout(900); shot(pg, "team-utah-elo-390")
        c.close()
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page()
        if W == 390:
            pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(900); shot(pg, "team-utah-default-390")
        pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector("#field tbody tr"); pg.wait_for_timeout(700)
        shot(pg, f"bracket-cue-under-bracket-{W}", "#bracket .bkcue"); shot(pg, f"bracket-card-{W}", "#bracket"); shot(pg, f"bracket-cue-field-card-{W}", ".card:has(#field)")
        for slug in ("american", "conference-usa"):
            pg.goto(BASE + f"/conference/{slug}/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(600)
            loc = pg.locator("main :text('other public rating systems')").first
            if loc.count(): loc.scroll_into_view_if_needed(); pg.wait_for_timeout(150); pg.screenshot(path=f"{OUT}/conf-{slug}-other-systems-{W}.png"); globals()['n'] += 1
        c.close()
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=S); pg = c.new_page()
        pg.goto(BASE + "/method/"); pg.wait_for_timeout(500); shot(pg, f"method-models-{W}", "#models"); 
        pg.goto(BASE + "/method/"); shot(pg, f"method-changed-{W}", "#changed")
        pg.goto(BASE + "/disclaimer/"); pg.wait_for_timeout(500); shot(pg, f"disclaimer-page-{W}", full=True)
        pg.evaluate("localStorage.clear(); sessionStorage.clear()"); pg.goto(BASE + "/"); pg.wait_for_timeout(700); shot(pg, f"gate-{W}")
        c.close()
    srv.shutdown(); b.close()
print(n, "crops")
