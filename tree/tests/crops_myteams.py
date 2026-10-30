"""Crops for the My teams build (phase 1) into crops/myteams-*.png at 320/390/430/1280. python3 tests/crops_myteams.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
srv, BASE = serve.start()
def go(pg, u, sel):
    pg.goto(BASE + u); pg.wait_for_selector(sel); pg.wait_for_timeout(500)
def shot(pg, name, w, loc=None, clip_top=None):
    path = f"{CR}/myteams-{name}-{w}.png"
    if loc is not None: pg.locator(loc).screenshot(path=path)
    else: pg.screenshot(path=path)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
        go(pg, "/", ".mt-ed")
        shot(pg, "header-empty", w, "header, .tb >> nth=0") if False else pg.screenshot(path=f"{CR}/myteams-header-signedout-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 330 if w < 700 else 200})
        shot(pg, "empty", w, "#my-teams")
        pg.click(".mt-chip[data-t=byu]"); pg.click("[data-more]"); pg.click(".mt-chip[data-t=utah]"); pg.click(".mt-chip[data-t=kansas]"); pg.select_option("#mtl-utah", "c")
        shot(pg, "editor-filled-save-line", w, "#my-teams")
        pg.click("[data-save]"); pg.wait_for_selector(".mt-c"); pg.locator(".mt-c .mt-kv").nth(5).wait_for(); pg.wait_for_timeout(300)
        shot(pg, "filled", w, "#my-teams")
        pg.screenshot(path=f"{CR}/myteams-header-count-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 330 if w < 700 else 200})
        # list stars
        pg.locator(".tw.tk-n").first.scroll_into_view_if_needed(); pg.wait_for_selector(".mt-ls")
        box = pg.locator(".mt-ln").first.bounding_box(); pg.screenshot(path=f"{CR}/myteams-list-stars-{w}.png", clip={"x": 0, "y": max(0, box["y"] - 70), "width": w, "height": 520})
        # cap
        pg.goto(BASE + "/"); pg.wait_for_selector(".mt-c"); pg.click("[data-edit]")
        for c in pg.eval_on_selector_all("#mtconf option", "o=>o.map(x=>x.value)"):
            if "10 of 10" in pg.inner_text(".mt-count"): break
            pg.select_option("#mtconf", c)
            if pg.locator("[data-more][aria-expanded=false]").count(): pg.click("[data-more]")
            for s in pg.eval_on_selector_all(".mt-chip[data-t]", "e=>e.map(x=>x.dataset.t)"):
                if "10 of 10" in pg.inner_text(".mt-count"): break
                if pg.get_attribute(f".mt-chip[data-t={s}]", "aria-pressed") == "false" and pg.get_attribute(f".mt-chip[data-t={s}]", "aria-disabled") != "true": pg.click(f".mt-chip[data-t={s}]")
        pg.click(".mt-chip[aria-pressed=false]", force=True); shot(pg, "cap-message", w, "#my-teams .mt-ed")
        pg.click("[data-cancel]")
        # team page
        go(pg, "/team/ohio-state/", ".mt-sv"); pg.screenshot(path=f"{CR}/myteams-team-save-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 760 if w < 700 else 520})
        pg.click(".mt-sv"); pg.screenshot(path=f"{CR}/myteams-team-saved-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 760 if w < 700 else 520})
        # keyboard focus on a chip
        go(pg, "/", ".mt-c"); pg.click("[data-clear]"); pg.screenshot(path=f"{CR}/myteams-clear-confirm-{w}.png", clip={"x": 0, "y": max(0, pg.locator('#my-teams').bounding_box()["y"] - 4), "width": w, "height": 330})
        ctx.close()
        # blocked storage
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
        pg.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
        go(pg, "/", ".mt-ed"); pg.click(".mt-chip[data-t=byu]"); pg.click("[data-save]"); pg.wait_for_selector(".mt-c"); pg.wait_for_timeout(400); shot(pg, "blocked-storage", w, "#my-teams")
        ctx.close()
        # keyboard focus ring
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); go(pg, "/", ".mt-ed"); pg.focus(".mt-chip[data-t=byu]"); pg.keyboard.press("Tab"); pg.keyboard.press("Shift+Tab"); shot(pg, "focus-chip", w, "#my-teams .mt-chips")
        ctx.close()
    b.close()
print(sorted(os.listdir(CR))[:3], len([f for f in os.listdir(CR) if f.startswith("myteams-")]), "crops")
