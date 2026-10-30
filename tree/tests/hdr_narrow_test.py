"""Header at very narrow viewports (200% zoom on a 320 phone = ~160px CSS wide): python3 tests/hdr_narrow_test.py
Menu button fully on screen, header 56px, no overlaps, panel usable, at EVERY width 160-359 (step 1 in chromium, step 7 + the named widths in WebKit); Current-page tag hidden under 240; 320/390 unchanged."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
srv, BASE = serve.start(os.environ.get("KT_SITE")); F = []; N = [0]
def ok(n, c, d=""):
    N[0] += 1
    if not c: F.append(n); print("FAIL", n, d)
JS = """() => { const R = e => { const r = e.getBoundingClientRect(); return {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height} };
  const hd = document.querySelector('header.hd'), btn = document.getElementById('kh-btn'), br = document.querySelector('.hd .brand'), tog = document.querySelector('.hd .tog');
  const on = document.querySelector('.hd .tog .on'), off = document.querySelector('.hd .tog .off');
  return {W: innerWidth, hd: R(hd), btn: R(btn), brand: R(br), tog: getComputedStyle(tog).display === 'none' ? null : R(tog), on: on && getComputedStyle(tog).display !== 'none' ? R(on) : null, offShown: getComputedStyle(off).display !== 'none',
    togClip: tog.scrollWidth <= tog.clientWidth + 1, hs: document.documentElement.scrollWidth, bar: getComputedStyle(document.documentElement).getPropertyValue('--kt-bar-h'), hdScroll: hd.scrollWidth} }"""
def check(pg, W, eng, path):
    pg.goto(BASE + path); pg.wait_for_timeout(250); r = pg.evaluate(JS); t = f"{eng} {path} @{W}"
    ok(f"{t}: header is 56px tall", abs(r["hd"]["h"] - 56) < .6 and r["bar"].strip() == "56px", f'{r["hd"]["h"]} {r["bar"]}')
    ok(f"{t}: Menu button fully on screen (0 <= left, right <= width), >= 44px", r["btn"]["l"] >= 0 and r["btn"]["r"] <= W + .5 and r["btn"]["w"] >= 43.5 and r["btn"]["h"] >= 43.5, str(r["btn"]))
    ok(f"{t}: header content not wider than the viewport", r["hdScroll"] <= W + 1, str(r["hdScroll"]))
    ok(f"{t}: logo does not overlap pill or Menu", r["brand"]["r"] <= (r["tog"]["l"] if r["tog"] else r["btn"]["l"]) + .5 and (not r["tog"] or r["tog"]["r"] <= r["btn"]["l"] + .5), f'{r["brand"]} {r["tog"]} {r["btn"]}')
    ok(f"{t}: pill state (Basketball half only from 300px, pill only from 220px)", (r["tog"] is not None) == (W >= 220) and (not r["tog"] or r["offShown"] == (W >= 300)), f'{r["tog"]} {r["offShown"]}')
    if r["tog"]: ok(f"{t}: pill fully inside the row and its text not clipped", r["tog"]["l"] >= 0 and r["tog"]["r"] <= r["btn"]["l"] + .5 and r["togClip"], str(r["tog"]))
def menu(pg, W, eng, path):
    t = f"{eng} menu {path} @{W}"; pg.goto(BASE + path); pg.wait_for_timeout(250); pg.click("#kh-btn"); pg.wait_for_timeout(300)
    r = pg.evaluate("""() => { const a = [...document.querySelectorAll('#kh-panel a')].map(e => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.height] }); const cur = document.querySelector('#kh-panel a[aria-current=page]'); const after = cur ? getComputedStyle(cur, '::after').display : null;
      const b = document.getElementById('kh-btn').getBoundingClientRect(); return {a, after, ae: document.activeElement === document.querySelector('#kh-panel a[href]'), exp: document.getElementById('kh-btn').getAttribute('aria-expanded'), bl: b.left, br: b.right, W: innerWidth, hd: document.querySelector('header.hd').getBoundingClientRect().height, panelW: document.getElementById('kh-panel').scrollWidth} }""")
    ok(f"{t}: open, focus on first link, Menu/Close button on screen, header 56px", r["exp"] == "true" and r["ae"] and r["bl"] >= 0 and r["br"] <= W + .5 and abs(r["hd"] - 56) < .6, str(r))
    ok(f"{t}: every row inside the screen, >= 44px, panel not wider than the screen", all(x[0] >= 0 and x[1] <= W + .5 and x[2] >= 43.5 for x in r["a"]) and r["panelW"] <= W + 1, str(r["a"]))
    if path == "/playoff/": ok(f"{t}: 'Current page' tag hidden under 240px, shown from 240", (r["after"] == "none") == (W < 240), str(r["after"]))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(150); ok(f"{t}: Esc closes and refocuses Menu", pg.evaluate("document.activeElement.id") == "kh-btn" and pg.get_attribute("#kh-btn", "aria-expanded") == "false")
with sync_playwright() as p:
    for eng in ("chromium", "webkit"):
        b = getattr(p, eng).launch(); NAMED = {160, 200, 240, 296, 320}
        ws = sorted(NAMED | set(range(160, 360, 1 if eng == "chromium" else 7)) | {219, 220, 239, 240, 298, 299, 300, 359})
        pg = None
        for W in ws:
            c = b.new_context(viewport={"width": W, "height": 640}); pg = c.new_page()
            check(pg, W, eng, "/")
            if W in NAMED or W % 20 == 0 or W in (219, 220, 239, 240, 299, 300, 359): menu(pg, W, eng, "/playoff/"); menu(pg, W, eng, "/")
            c.close()
        b.close()
srv.shutdown(); print(f"hdr_narrow_test: {N[0]} checks, {len(F)} failures")
sys.exit(1 if F else 0)
