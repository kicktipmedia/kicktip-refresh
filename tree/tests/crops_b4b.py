"""Crops of the b4b changed items at 1280@1x and 390@2x -> crops-b4b/ (override dir: argv[1])"""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/" + (sys.argv[1] if len(sys.argv) > 1 else "crops-b4b"); os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
def shoot(b, w, s, path, name, sel, accepted=True, pad=12, checks=None):
    ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s)
    if accepted: ctx.add_init_script(ACC)
    pg = ctx.new_page(); pg.goto(BASE + path); pg.wait_for_timeout(700)
    el = pg.locator(sel).first; el.scroll_into_view_if_needed(); bb = el.bounding_box()
    pg.screenshot(path=f"{OUT}/{name}-{w}@{s}x.png", full_page=True, clip={"x": max(bb["x"] - pad, 0), "y": bb["y"] + pg.evaluate("scrollY") - pad, "width": min(bb["width"] + 2 * pad, w), "height": bb["height"] + 2 * pad})
    r = {}
    if checks: r = pg.evaluate(checks)
    ctx.close(); return r
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, s in ((1280, 1), (390, 2)):
        r = shoot(b, w, s, "/", "gate-note-links", "#gate .gnote", accepted=False, checks="Array.from(document.querySelectorAll('#gate .gnote a')).map(a=>{const r=a.getBoundingClientRect();return [a.textContent,Math.round(r.width),Math.round(r.height)]})"); print(w, "gate note links (text,w,h):", r)
        r = shoot(b, w, s, "/team/utah/", "team-breadcrumb", ".crumbs", checks="Array.from(document.querySelectorAll('.crumbs a')).map(a=>{const r=a.getBoundingClientRect();return [a.textContent,Math.round(r.width),Math.round(r.height)]})"); print(w, "breadcrumb:", r)
        shoot(b, w, s, "/conference/big-ten/", "bigten-source-note", "li:has-text('automated readers'), p:has-text('automated readers')")
        shoot(b, w, s, "/method/", "method-market-count", "li:has-text('games that have not started')")
        shoot(b, w, s, "/method/", "method-gate-sentence", "p:has-text('acceptance gate controls'), li:has-text('acceptance gate controls')")
        shoot(b, w, s, "/disclaimer/", "disclaimer-gate-sentence", "p:has-text('acceptance gate controls'), li:has-text('acceptance gate controls')")
        shoot(b, w, s, "/conference/acc/", "title-game-date", ".card:has(h2:text-is('Title game'))")
        shoot(b, w, s, "/playoff/", "playoff-sources-note", "p:has-text('Aug. 6, 2026 announcement')")
    b.close()
print(sorted(os.listdir(OUT)))
