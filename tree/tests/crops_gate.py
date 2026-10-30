"""Crops for the run-gate build into crops/. Clock-independent. python3 tests/crops_gate.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
srv, BASE = serve.start()
def card(pg, name, sel="#rootables"):
    pg.locator(sel).scroll_into_view_if_needed(); pg.evaluate("()=>{const k=document.getElementById('kpill'); if(k) k.style.display='none'}"); pg.locator(sel).screenshot(path=f"{CR}/{name}.png")
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("#rootables[data-rb=idle]"); pg.wait_for_timeout(800)
        pg.screenshot(path=f"{CR}/rootables-before-run-banner-{w}.png")                     # top of the page: banner + header
        card(pg, f"rootables-before-run-{w}")
        pg.click("#rootables [data-run]"); pg.wait_for_selector("#rootables[data-rb=on]:not([aria-busy])", timeout=15000); pg.wait_for_timeout(500)
        card(pg, f"rootables-after-run-{w}")
        pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=f"{CR}/rootables-after-run-banner-{w}.png")
        ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(1500); pg.screenshot(path=f"{CR}/home-{w}.png"); ctx.close()
    for w in (390, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(1500)
        pg.click("#kpill"); pg.wait_for_timeout(700); pg.screenshot(path=f"{CR}/ask-panel-open-{w}.png")
        pg.locator(".q").first.click(); pg.wait_for_timeout(200); pg.screenshot(path=f"{CR}/ask-panel-filled-{w}.png")
        pg.click("#kform .snd"); pg.wait_for_selector(".ba", timeout=20000); pg.wait_for_timeout(600); pg.screenshot(path=f"{CR}/ask-panel-answer-{w}.png")
        ctx.close()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page(); pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(1500)
    t = pg.locator("table:has(th:has-text('Market line'))").first; t.scroll_into_view_if_needed(); pg.evaluate("()=>{const k=document.getElementById('kpill'); if(k) k.style.display='none'}")
    pg.locator(".card:has(table th:has-text('Market line'))").first.screenshot(path=f"{CR}/gamecard-lines-1280.png")
    b.close()
