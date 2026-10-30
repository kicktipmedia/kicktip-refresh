"""b5/c1 crops at 1280@1x and 390@2x -> crops-b5/ (override dir: argv[1]): the b4 page set, plus the logo placements, credit and the initials fallback."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/" + (sys.argv[1] if len(sys.argv) > 1 else "crops-b5"); os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
PAGES = [("home", "/"), ("conference-big12", "/conference/big-12/"), ("team-utah", "/team/utah/"), ("playoff", "/playoff/"), ("method", "/method/")]
def card(h): return f'xpath=//h2[normalize-space()="{h}"]/..'
# name, path, locator(s): first..last element, the crop spans from the top of the first to the bottom of the last
EL = [("conference-hero-tabs", "/conference/big-12/", [".hero", "nav.tabs"]), ("conference-standings", "/conference/big-12/", [card("Standings")]),
      ("conference-key-games", "/conference/big-12/", [card("Remaining conference games")]), ("home-conference-cards", "/", ["section#conferences"]),
      ("home-top-chances", "/", [card("Top chances to make the 12")]), ("playoff-header", "/playoff/", [".hero"]), ("playoff-bracket", "/playoff/", [card("Bracket if the season ended today")]),
      ("playoff-field", "/playoff/", [card("The field")]), ("team-utah-header", "/team/utah/", [".hero"]), ("team-utah-games", "/team/utah/", [card("Remaining games")]), ("footer-credit", "/team/utah/", ["footer.ft"]),
      ("method-credit-line", "/method/", ["li:has-text('courtesy of ESPN')"])]
def clipshot(pg, name, sels, pad=10):
    first = pg.locator(sels[0]).first; last = pg.locator(sels[-1]).first; first.scroll_into_view_if_needed()
    a, z = first.bounding_box(), last.bounding_box(); sy = pg.evaluate("scrollY"); w = pg.viewport_size["width"]
    y0 = a["y"] + sy - pad; y1 = z["y"] + sy + z["height"] + pad; x0 = max(min(a["x"], z["x"]) - pad, 0); x1 = min(max(a["x"] + a["width"], z["x"] + z["width"]) + pad, w)
    pg.screenshot(path=name, full_page=True, clip={"x": x0, "y": max(y0, 0), "width": x1 - x0, "height": min(y1 - y0, 9000)})
def settle(pg):
    pg.wait_for_timeout(900)
    for y in range(0, pg.evaluate("document.body.scrollHeight"), 500): pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(40)
    pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(500)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, s in ((1280, 1), (390, 2)):
        h = 900 if w == 1280 else 1400
        for name, path in PAGES:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page()
            pg.goto(BASE + path); settle(pg); pg.set_viewport_size({"width": w, "height": (1500 if w == 1280 else 1700)}); pg.wait_for_timeout(200)
            pg.screenshot(path=f"{OUT}/{name}-{w}@{s}x.png"); ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(700)
        el = pg.locator("section.sec", has_text="State sites").first; el.scroll_into_view_if_needed(); el.screenshot(path=f"{OUT}/home-state-sites-{w}@{s}x.png"); ctx.close()
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(600)
        pg.screenshot(path=f"{OUT}/gate-{w}@{s}x.png")
        pg.locator("#gate .gnote").screenshot(path=f"{OUT}/gate-dialog-note-{w}@{s}x.png")
        pg.check("#gate input[type=checkbox]"); pg.screenshot(path=f"{OUT}/gate-checked-{w}@{s}x.png"); ctx.close()
        for name, path, sels in EL:
            ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + path); settle(pg)
            clipshot(pg, f"{OUT}/{name}-{w}@{s}x.png", sels); ctx.close()
        # fallback: block every logo file so each tile shows its initials/abbreviation
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page()
        pg.route("**/assets/logos/**", lambda r: r.fulfill(status=404, body="")); pg.goto(BASE + "/conference/big-12/"); settle(pg)
        clipshot(pg, f"{OUT}/fallback-initials-standings-{w}@{s}x.png", [".hero", card("Standings")]); ctx.close()
    b.close()
print(len(os.listdir(OUT)), sorted(os.listdir(OUT)))
