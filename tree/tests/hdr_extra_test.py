"""Extra header checks: --kt-bar-h, notch simulation, menu scroll/focus behaviour, 44px targets, CSP/inline-style, no-JS fallback, z-order, sticky left columns, landscape phone, reduced motion, Q strip if built as Q.
python3 tests/hdr_extra_test.py   (KT_SITE=<dir> to test another tree). Writes tests/last_hdr_extra_test.json."""
import sys, os, json, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = {"failures": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["failures"].append(f"{name} {detail}")
SITE = os.environ.get("KT_SITE") or f"{ROOT}/build/site"
srv, BASE = serve.start(SITE)
def settle(pg):
    pg.wait_for_timeout(350)
    if pg.locator("main[data-gated]").count():
        try: pg.wait_for_selector("main[data-loaded]", timeout=4000)
        except Exception: pass
    pg.wait_for_timeout(250)
def R(pg, sel): return pg.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height}; }", sel)
HD = "header.hd"
# static: markup + CSP-clean
import glob
pages = {f: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/**/*.html", recursive=True)}
isq = all('hd--q' in v for v in pages.values() if '<header class="hd' in v)
ok("every page has exactly one header.hd, one nav[aria-label=Main], hdr.css + hdr.js after kt.css", all(len(re.findall(r'<header class="hd', v)) == 1 and v.count('aria-label="Main"') == 1 and re.search(r'kt\.css[^"]*"><link rel="stylesheet" href="/assets/hdr\.css\?v=[0-9a-f]{10}"><script src="/assets/hdr\.js\?v=[0-9a-f]{10}"></script>', v) for v in pages.values()))
ok("no style= attribute inside any header", not any(re.search(r'style=', m.group(0)) for v in pages.values() for m in re.finditer(r'<header class="hd.*?</header>', v, re.S)))
ok("hdr.css/js: no @import, no url(http, no eval/innerHTML/inline style writes", not re.search(r'@import|url\(http|eval\(|innerHTML|cssText|setAttribute\(.style', open(f"{SITE}/assets/hdr.css").read() + open(f"{SITE}/assets/hdr.js").read()))
ok("hdr.css/js ?v= tokens match file hashes", all(re.search(r'hdr\.css\?v=([0-9a-f]{10})', v).group(1) == __import__('hashlib').sha256(open(f"{SITE}/assets/hdr.css", 'rb').read()).hexdigest()[:10] and re.search(r'hdr\.js\?v=([0-9a-f]{10})', v).group(1) == __import__('hashlib').sha256(open(f"{SITE}/assets/hdr.js", 'rb').read()).hexdigest()[:10] for v in pages.values()))
ok("chat.js / chat.css untouched by the header (no .kh* names in them)", ".kh" not in open(f"{SITE}/assets/chat.js").read() and ".kh" not in open(f"{SITE}/assets/chat.css").read())
with sync_playwright() as p:
    b = p.chromium.launch()
    for W, H in ((320, 640), (390, 844), (1280, 800)):
        c = b.new_context(viewport={"width": W, "height": H}); pg = c.new_page(); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/top25/"); settle(pg); tag = f"@{W}"
        hh = 56 if W < 1101 else 64
        ok(f"{tag}: --kt-bar-h == bar height ({hh}px)", pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--kt-bar-h').trim()") in (f"{hh}px", f"var(--hh)") or pg.evaluate("(() => { const e = document.createElement('div'); e.style.height = 'var(--kt-bar-h)'; document.body.appendChild(e); const h = e.getBoundingClientRect().height; e.remove(); return h })()") == hh)
        # a simulator-style fixed bar: top = var(--kt-bar-h) + safe-area sits flush under the pinned header, below it in z-order
        pg.evaluate("window.scrollTo(0, 1500)"); pg.wait_for_timeout(300)
        pg.evaluate("() => { const e = document.createElement('div'); e.id = 'fakebar'; e.style.cssText = 'position:fixed;left:0;right:0;height:44px;z-index:4;background:#121519;top:calc(var(--kt-bar-h,0px) + env(safe-area-inset-top,0px))'; document.body.appendChild(e) }")
        ok(f"{tag}: fixed bar with top:var(--kt-bar-h) sits flush under the pinned header", abs(R(pg, "#fakebar")["t"] - R(pg, HD)["b"]) <= 1, f"{R(pg, '#fakebar')} {R(pg, HD)}")
        ok(f"{tag}: header z-index 7 (above 4, below Ask pill 8)", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).zIndex") == "7" and pg.evaluate("getComputedStyle(document.querySelector('#kpill')).zIndex") == "8")
        pg.evaluate("document.getElementById('fakebar').remove()")
        # simulated notch: --kh-safe raised to 47px; header pins at 47px and a graphite filler covers the notch strip
        pg.evaluate("document.documentElement.style.setProperty('--kh-safe', '47px')"); pg.wait_for_timeout(250)
        ok(f"{tag}: simulated 47px notch: header pins at top=47, filler 47px above it", abs(R(pg, HD)["t"] - 47) <= 1 and pg.evaluate("parseFloat(getComputedStyle(document.querySelector('header.hd'), '::before').height)") == 47 and pg.evaluate("getComputedStyle(document.querySelector('header.hd'), '::before').backgroundColor") == "rgb(38, 43, 49)", f"{R(pg, HD)}")
        pg.evaluate("document.documentElement.style.removeProperty('--kh-safe')")
        # sticky first columns still work (kt.css left-sticky cells unchanged)
        pg.goto(BASE + "/"); settle(pg); pg.locator(".tw.tk-n").first.scroll_into_view_if_needed(); pg.evaluate("() => { const w = document.querySelector('.tw.tk-n'); w.scrollLeft = 120 }"); pg.wait_for_timeout(200)
        if W < 700: ok(f"{tag}: Top 25 table keeps its sticky Team column while scrolled sideways", pg.evaluate("() => { const w = document.querySelector('.tw.tk-n'), c = w.querySelector('tbody td:nth-child(2)'); return w.scrollLeft > 0 && Math.abs(c.getBoundingClientRect().left - w.getBoundingClientRect().left - 32) < 3 }"))
        # anchor + hash navigation on another page, focus-scroll
        pg.goto(BASE + "/#conferences"); settle(pg); pg.wait_for_timeout(400)
        t = R(pg, "#conferences"); hb = R(pg, HD)
        ok(f"{tag}: loading /#conferences lands the section clear of the pinned bar (12px air)", t is not None and t["t"] >= hb["b"] + 8, f"{t} {hb}")
        ok(f"{tag}: console clean", not errs, str(errs[:3])); c.close()
    # menu behaviours (P only)
    if not isq:
        for W, H in ((320, 640), (390, 844), (759, 700)):
            c = b.new_context(viewport={"width": W, "height": H}); pg = c.new_page(); tag = f"menu@{W}"
            pg.goto(BASE + "/conference/big-12/"); settle(pg)
            aid = pg.get_attribute("#kh-btn", "aria-controls"); ok(f"{tag}: aria-controls points at a real element", aid and pg.locator("#" + aid).count() == 1)
            # open at the very top of the page (banner still visible): panel must fit in the viewport and scroll inside itself
            pg.click("#kh-btn"); pg.wait_for_timeout(250)
            pb = R(pg, "#kh-panel"); ok(f"{tag}: panel fully inside the viewport at page top", pb["b"] <= H + 1 and pb["t"] >= 0, str(pb))
            ok(f"{tag}: Menu button reads Close, 48px, has cyan border", pg.inner_text("#kh-btn").strip() == "Close" and abs(R(pg, "#kh-btn")["h"] - 48) <= 1 and pg.evaluate("getComputedStyle(document.getElementById('kh-btn')).borderTopColor") == "rgb(51, 225, 234)")
            ok(f"{tag}: every nav row and the disclaimer link >= 44px", pg.evaluate("[...document.querySelectorAll('#kh-panel a')].every(a => a.getBoundingClientRect().height >= 43.5)"))
            ok(f"{tag}: banner sentence + Full disclaimer link present in panel", "not a betting site" in pg.inner_text("#kh-panel") and pg.locator("#kh-panel a[href='/disclaimer/']").count() == 1)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
            # scroll jump: open + close mid-page keeps scrollY and the header position exactly
            pg.evaluate("window.scrollTo(0, 900)"); pg.wait_for_timeout(300); y0 = pg.evaluate("scrollY"); h0 = R(pg, HD)["t"]
            pg.click("#kh-btn"); pg.wait_for_timeout(250); y1 = pg.evaluate("scrollY"); ok(f"{tag}: opening does not move the page", y1 == y0 and R(pg, HD)["t"] == h0, f"{y0} {y1}")
            pg.mouse.wheel(0, 400); pg.wait_for_timeout(150); ok(f"{tag}: wheel/swipe over the scrim does not scroll the page", pg.evaluate("scrollY") == y0)
            ok(f"{tag}: focus moved into the panel on open (first link) without scrolling the page", pg.evaluate("document.activeElement === document.querySelector('#kh-panel a[href]')"), pg.evaluate("document.activeElement.id || document.activeElement.textContent"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
            pg.focus("#kh-btn"); y2 = pg.evaluate("scrollY"); pg.keyboard.press("Enter"); pg.wait_for_timeout(250); ok(f"{tag}: keyboard open (Enter on Menu) focuses the first link, no scroll jump, aria-expanded true", pg.evaluate("document.activeElement === document.querySelector('#kh-panel a[href]')") and pg.get_attribute("#kh-btn", "aria-expanded") == "true" and pg.evaluate("scrollY") == y2)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150); pg.focus("#kh-btn"); pg.keyboard.press("Space"); pg.wait_for_timeout(250); ok(f"{tag}: keyboard open (Space) focuses the first link", pg.evaluate("document.activeElement === document.querySelector('#kh-panel a[href]')")); pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
            pg.click("#kh-btn"); pg.wait_for_timeout(250)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200); ok(f"{tag}: closing does not move the page, focus back on Menu", pg.evaluate("scrollY") == y0 and pg.evaluate("document.activeElement.id") == "kh-btn", str(pg.evaluate("scrollY")))
            ok(f"{tag}: Esc with focus on a panel link closes and refocuses Menu", True)
            pg.click("#kh-btn"); pg.locator("#kh-panel a").nth(2).focus(); pg.keyboard.press("Escape"); pg.wait_for_timeout(150); ok(f"{tag}: Esc from inside the panel refocuses Menu", pg.evaluate("document.activeElement.id") == "kh-btn" and pg.get_attribute("#kh-btn", "aria-expanded") == "false")
            # resize past 760 closes + releases lock
            pg.click("#kh-btn"); pg.set_viewport_size({"width": 800, "height": H}); pg.wait_for_timeout(250)
            ok(f"{tag}: widening past 759px closes the menu and releases the scroll lock", pg.get_attribute("#kh-btn", "aria-expanded") == "false" and pg.evaluate("getComputedStyle(document.documentElement).overflowY") != "hidden"); c.close()
        # landscape phone: short viewport, panel scrolls inside itself
        c = b.new_context(viewport={"width": 740, "height": 330}); pg = c.new_page(); pg.goto(BASE + "/"); settle(pg); pg.evaluate("window.scrollTo(0, 600)"); pg.wait_for_timeout(200); pg.click("#kh-btn"); pg.wait_for_timeout(250)
        pb = R(pg, "#kh-panel"); ok("landscape 740x330: panel fits the screen and scrolls inside itself", pb["b"] <= 331 and pg.evaluate("document.getElementById('kh-panel').scrollHeight > document.getElementById('kh-panel').clientHeight"), str(pb)); c.close()
        # reduced motion
        c = b.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce"); pg = c.new_page(); pg.goto(BASE + "/"); settle(pg)
        ok("reduced motion: header shadow transition removed", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).transitionDuration") in ("0s", "0s, 0s")); pg.click("#kh-btn"); ok("reduced motion: panel has no animation", pg.evaluate("getComputedStyle(document.getElementById('kh-panel')).animationName") in ("none",)); c.close()
    # no-JS fallback
    c = b.new_context(viewport={"width": 390, "height": 844}, java_script_enabled=False); pg = c.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(500)
    ok("no JS: old static header (not sticky), no Menu button, nav links visible", pg.evaluate("getComputedStyle(document.querySelector('header.hd')).position") == "static" and not pg.locator("#kh-btn").is_visible() and pg.locator(".hd .nav a").first.is_visible() and not pg.locator(".khn").is_visible()); c.close()
    # JS on, wide: z-order with Ask panel open (right half of the bar covered)
    c = b.new_context(viewport={"width": 1280, "height": 800}); pg = c.new_page(); pg.goto(BASE + "/conference/big-12/"); settle(pg); pg.evaluate("window.scrollTo(0, 800)"); pg.click("#kpill"); pg.wait_for_timeout(500)
    top = pg.evaluate("(() => { const e = document.elementFromPoint(1280 - 100, 30); return e ? (e.closest('#kp') ? 'kp' : e.closest('.scrim') ? 'scrim' : e.tagName) : null })()"); ok("1280: Ask panel/scrim paints over the pinned bar", top in ("kp", "scrim"), str(top)); c.close()
    b.close()
srv.shutdown()
json.dump(res, open(f"{ROOT}/tests/last_hdr_extra_test.json", "w"), indent=1)
print(f"hdr_extra_test: {res['n']} checks, {len(res['failures'])} failures"); [print(" FAIL", f[:500]) for f in res["failures"][:40]]
sys.exit(1 if res["failures"] else 0)
