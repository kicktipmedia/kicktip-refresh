"""QA fixes M3/L1/L2 (odds g2b): /games/ and the other lines pages have no horizontal overflow at 320/390/430/768/834/1024/1280; 'Market line not posted yet.' does not orphan 'yet.' in the slate table; collapsed LINES label is 12px and fits at 320.
python3 tests/layout_g2b_test.py [site_dir]   (default build/site; pass /tmp/odds_g2_real to see the previous build fail M3/L1/L2)"""
import sys, os, datetime as dt; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
srv, BASE = serve.start(sys.argv[1]) if len(sys.argv) > 1 else serve.start()
n = f = 0
def ok(name, c, d=""):
    global n, f; n += 1
    if not c: f += 1
    print(("PASS " if c else "FAIL ") + name + ("" if c else " " + str(d)))
T = dt.datetime(2026, 10, 24, 23, 0, tzinfo=dt.timezone.utc)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 768, 834, 1024, 1280):
        c = b.new_context(viewport={"width": w, "height": 900}); pg = c.new_page(); pg.clock.set_fixed_time(T)
        for path in ("/games/", "/team/georgia/", "/conference/big-12/"):
            pg.goto(BASE + path); pg.wait_for_selector(".gbt", state="attached"); pg.wait_for_timeout(300)
            sw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"); ok(f"{path} no horizontal overflow at {w} (scrollWidth {sw[0]}, inner {sw[1]})", sw[0] <= sw[1], sw)
        pg.goto(BASE + "/games/"); pg.wait_for_selector(".gbt", state="attached"); pg.wait_for_timeout(300)
        if w >= 768:
            r = pg.evaluate("""() => [...document.querySelectorAll('.gt td[data-c=mk]')].filter(td => /not posted yet/.test(td.textContent)).map(td => { const e = td.querySelector('.nm') || td; const rg = document.createRange(); rg.selectNodeContents(e); const rs = [...rg.getClientRects()]; return new Set(rs.map(x => Math.round(x.top))).size; })""")
            ok(f"slate 'Market line not posted yet.' on one line at {w} ({len(r)} rows)", len(r) > 0 and all(x == 1 for x in r), r)
        else:
            fs = pg.evaluate("[...document.querySelectorAll('.gbt')].map(b => [getComputedStyle(b).fontSize, b.scrollWidth <= b.clientWidth])")
            ok(f"collapsed LINES label 12px and fits at {w} ({len(fs)} buttons)", fs and all(x[0] == "12px" and x[1] for x in fs), fs[:3])
        if w in (320, 390, 430):
            pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector(".gbt", state="attached"); pg.wait_for_timeout(300)
            fs = pg.evaluate("[...document.querySelectorAll('.gbt')].map(b => [getComputedStyle(b).fontSize, b.scrollWidth <= b.clientWidth, b.getBoundingClientRect().height >= 44])")
            ok(f"team page LINES buttons 12px, fit, >=44px tall at {w}", fs and all(x[0] == "12px" and x[1] and x[2] for x in fs), fs[:3])
        c.close()
    b.close()
srv.shutdown(); print(f"layout_g2b_test: {n} checks, {f} failures"); sys.exit(1 if f else 0)
