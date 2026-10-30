"""Sticky header checks + crops. python3 tests/hdr_test.py [outdir]. Build variant comes from the built site (KT_HDR=p|q at build time). Writes tests/last_hdr_test.json."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/crops-hdr"; os.makedirs(OUT, exist_ok=True)
res = {"failures": [], "n": 0, "info": {}}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["failures"].append(f"{name} {detail}")
srv, BASE = serve.start(os.environ.get("KT_SITE"))
PAGES = ["/", "/playoff/", "/top25/", "/conference/big-12/", "/method/", "/team/alabama/", "/games/", "/disclaimer/"]
WIDTHS = (320, 359, 360, 390, 430, 759, 760, 768, 1100, 1101, 1280)
def settle(pg):
    pg.wait_for_timeout(350)
    if pg.locator("main[data-gated]").count():
        try: pg.wait_for_selector("main[data-loaded]", timeout=4000)
        except Exception: pass
    pg.wait_for_timeout(250)
def rect(pg, sel): return pg.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height}; }", sel)
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in WIDTHS:
        H = 844 if W < 500 else 800
        c = b.new_context(viewport={"width": W, "height": H}); pg = c.new_page(); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        compact = W <= 759; q = None
        for path in PAGES:
            pg.goto(BASE + path); settle(pg); tag = f"{path}@{W}"
            q = pg.evaluate("document.querySelector('header.hd').classList.contains('hd--q')")
            ok(f"{tag}: banner text still on the page", "KickTip is not a betting site." in pg.locator(".tb").inner_text())
            ok(f"{tag}: html.hdjs set before paint", pg.evaluate("document.documentElement.classList.contains('hdjs')"))
            sw = pg.evaluate("[document.documentElement.scrollWidth, document.body.scrollWidth, innerWidth]")
            ok(f"{tag}: no sideways scroll at top", sw[0] <= sw[2] and sw[1] <= sw[2], str(sw))
            ok(f"{tag}: html/body overflow-x clip", pg.evaluate("[getComputedStyle(document.documentElement).overflowX, getComputedStyle(document.body).overflowX]") == ["clip", "clip"])
            ok(f"{tag}: header sticky", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).position") == "sticky")
            hb = rect(pg, "header.hd"); want = (52 if (q and W <= 759) else 56) if W <= 1100 else 64
            ok(f"{tag}: bar height {want}", abs(hb["h"] - want) <= 1, str(hb))
            tb = rect(pg, ".tb"); ok(f"{tag}: banner is above the bar in flow", tb["b"] <= hb["t"] + 1, f"{tb} {hb}")
            if compact:   # one row: nothing overlaps or leaves the screen
                parts = [rect(pg, s) for s in (".hd .brand", ".hd .tog")] + ([rect(pg, ".hd .khb")] if not q else [])
                ok(f"{tag}: bar items fit one row, in order, inside the screen", all(a["r"] <= bb["l"] + 0.5 for a, bb in zip(parts, parts[1:])) and parts[-1]["r"] <= W + 0.5 and all(abs((x["t"] + x["b"]) / 2 - hb["h"] / 2 - hb["t"]) < 12 for x in parts), str(parts))
                if not q:
                    bt = rect(pg, ".hd .khb"); ok(f"{tag}: Menu button 48x48", abs(bt["h"] - 48) <= 1 and bt["w"] >= 47.5, str(bt)); pt = rect(pg, ".hd .tog"); ok(f"{tag}: pill 34px tall", abs(pt["h"] - 34) <= 1, str(pt)); ok(f"{tag}: Menu right edge 10px from screen edge", abs(W - bt["r"] - 10) <= 1, str(bt))
                    ok(f"{tag}: nav hidden while menu closed", not pg.locator(".hd .nav a").first.is_visible())
            else:
                ok(f"{tag}: desktop shows 5 inline links (Home, Conferences, Playoff Picture, My teams, Method) + pill + the Sign in control", pg.locator(".hd .nav a:visible").count() == 5 and pg.locator(".hd .nav .ac-si").count() + pg.locator(".hd .nav .ac-chip").count() == 1 and pg.locator(".hd .tog").is_visible() and not pg.locator(".hd .khb").is_visible())
            # scrolled: bar pinned, banner gone
            ok(f"{tag}: no shadow at page top", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).boxShadow") == "none")
            pg.evaluate("window.scrollTo(0, 1600)"); pg.wait_for_timeout(400)
            ok(f"{tag}: shadow once stuck", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).boxShadow") != "none")
            ok(f"{tag}: pinned at top after scroll", abs(rect(pg, "header.hd")["t"]) <= 1, str(rect(pg, "header.hd")))
            ok(f"{tag}: banner scrolled away", rect(pg, ".tb")["b"] < 0)
            sw = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]"); ok(f"{tag}: no sideways scroll when scrolled", sw[0] <= sw[1], str(sw))
            pg.evaluate("window.scrollTo(0, 0)")
        # menu behaviour (variant P, compact)
        if compact and not q:
            pg.goto(BASE + "/playoff/"); settle(pg); tag = f"menu@{W}"
            pg.evaluate("window.scrollTo(0, 700)"); pg.wait_for_timeout(200)
            pg.click("#kh-btn"); pg.wait_for_timeout(250)
            ok(f"{tag}: opening moves focus into the panel, onto the first link (Home)", pg.evaluate("document.activeElement.closest('#kh-panel') !== null && document.activeElement.textContent.trim() === 'Home' && document.activeElement === document.querySelector('#kh-panel a[href]')"), pg.evaluate("document.activeElement.id || document.activeElement.textContent.trim().slice(0,20)"))
            pg.keyboard.press("Tab"); ok(f"{tag}: Tab from the first link goes to the second (Conferences)", pg.evaluate("document.activeElement.textContent.trim()") == "Conferences"); pg.keyboard.press("Shift+Tab"); pg.keyboard.press("Shift+Tab"); ok(f"{tag}: Shift+Tab from the first link reaches the Menu/Close button (trap order)", pg.evaluate("document.activeElement.id") == "kh-btn"); pg.keyboard.press("Tab")
            ok(f"{tag}: aria-expanded true + nav visible", pg.get_attribute("#kh-btn", "aria-expanded") == "true" and pg.locator(".hd .nav a").first.is_visible())
            hs = pg.evaluate("[...document.querySelectorAll('.hd .nav a')].map(a => Math.round(a.getBoundingClientRect().height))"); ok(f"{tag}: five link rows >= 52px", len(hs) == 5 and min(hs) >= 52, str(hs))
            ok(f"{tag}: current page cue present", pg.evaluate("getComputedStyle(document.querySelector('.hd .nav a[aria-current=page]'), '::after').content") == '"Current page"')
            ok(f"{tag}: body scroll locked", pg.evaluate("getComputedStyle(document.documentElement).overflow") == "hidden")
            y0 = pg.evaluate("scrollY"); pg.mouse.wheel(0, 500); pg.wait_for_timeout(200); ok(f"{tag}: page does not scroll under open menu", pg.evaluate("scrollY") == y0)
            full = pg.locator(".hd .khn a"); ok(f"{tag}: Full disclaimer link >= 44px", full.is_visible() and full.bounding_box()["height"] >= 43.5)
            # focus trap: Tab through everything, never leaves
            pg.focus("#kh-btn"); seen = []
            for _ in range(8):
                pg.keyboard.press("Tab"); seen.append(pg.evaluate("document.activeElement.id || document.activeElement.textContent.trim().slice(0,18)"))
            ok(f"{tag}: Tab stays inside Menu + panel links", all(x in ("kh-btn", "Home", "Conferences", "Playoff Picture", "My teams", "Method", "Sign in", "Full disclaimer") for x in seen), str(seen))
            pg.keyboard.press("Shift+Tab"); pg.focus("#kh-btn"); pg.keyboard.press("Shift+Tab"); ok(f"{tag}: Shift+Tab from Menu wraps to the last link", pg.evaluate("document.activeElement.textContent.trim()") == "Full disclaimer")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
            ok(f"{tag}: Esc closes and returns focus to Menu", pg.get_attribute("#kh-btn", "aria-expanded") == "false" and pg.evaluate("document.activeElement.id") == "kh-btn")
            pg.click("#kh-btn"); pg.wait_for_timeout(150); pg.mouse.click(W // 2, H - 130); pg.wait_for_timeout(150)
            ok(f"{tag}: tapping the scrim closes", pg.get_attribute("#kh-btn", "aria-expanded") == "false")
            ok(f"{tag}: lock released", pg.evaluate("getComputedStyle(document.documentElement).overflow") != "hidden")
            # Ask panel covers the bar, menu closes when Ask opens
            pg.click("#kh-btn"); pg.wait_for_timeout(100); pg.click("#kpill"); pg.wait_for_timeout(350)
            ok(f"{tag}: Ask opens and the menu closes", pg.get_attribute("#kh-btn", "aria-expanded") == "false" and pg.locator("#kp").is_visible())
            top = pg.evaluate("(() => { const e = document.elementFromPoint(innerWidth - 60, 28); return e ? (e.closest('#kp') ? 'kp' : e.closest('.scrim') ? 'scrim' : e.id || e.className || e.tagName) : null })()")
            ok(f"{tag}: Ask panel/scrim sits above the bar", top in ("kp", "scrim") or (isinstance(top, str) and top.startswith("scrim")), str(top))
        # anchor jump
        pg.goto(BASE + "/"); settle(pg); tag = f"anchor@{W}"
        if compact and not q: pg.click("#kh-btn"); pg.wait_for_timeout(150)
        pg.locator(".hd .nav a", has_text="Conferences").click(); pg.wait_for_timeout(700)
        t = rect(pg, "#conferences"); hb = rect(pg, "header.hd")
        ok(f"{tag}: #conferences lands clear of the bar", t is not None and t["t"] >= hb["b"] - 1, f"{t} {hb}")
        if compact and not q: ok(f"{tag}: menu closed after tapping a link", pg.get_attribute("#kh-btn", "aria-expanded") == "false")
        ok(f"@{W}: no console errors (CSP etc.)", not errs, str(errs[:2]))
        res["info"][W] = {"variant": "q" if q else "p"}
        c.close()
    b.close()
srv.shutdown()
json.dump(res, open(f"{ROOT}/tests/last_hdr_test.json", "w"), indent=1)
print(f"hdr_test: {res['n']} checks, {len(res['failures'])} failures"); [print(" FAIL", f) for f in res["failures"][:40]]
sys.exit(1 if res["failures"] else 0)
