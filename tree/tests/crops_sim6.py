"""sim6 crops: KT_SITE_DIR=<site> python3 tests/crops_sim6.py [outdir]. 320/390/1280: top, scrolled, changed row, tie state, last week, standings, CCG bar + box, fallback tile (logo images blocked). Real pred-lines.json with read times refreshed."""
import sys, os, json, time, subprocess; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/crops-sim6"; os.makedirs(OUT, exist_ok=True)
SITE = os.environ.get("KT_SITE_DIR") or f"{ROOT}/build/site"; srv, BASE = serve.start(SITE)
L = json.load(open(f"{SITE}/data/pred-lines.json")); now = int(time.time())
for k, v in L["l"].items(): v[1] = now - 3600; v[2] = now + 86400 * 4
body = json.dumps(L)
T = json.loads(subprocess.run(["node", f"{ROOT}/tests/ccg_find_tie.js", "big12"], capture_output=True, text=True).stdout)
def load(b, W, block=False):
    c = b.new_context(viewport={"width": W, "height": 844 if W < 500 else 800}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
    pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=200, content_type="application/json", body=body))
    if block: pg.route("**/assets/logos/**", lambda r: r.abort())
    pg.goto(f"{BASE}/conference/big-12/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(700); return c, pg
def pin(pg, dy=300):
    pg.evaluate("() => document.getElementById('weeks').scrollIntoView()"); pg.evaluate(f"() => scrollBy(0, {dy})"); pg.wait_for_timeout(500)
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in (320, 390, 1280):
        c, pg = load(b, W); n = f"big-12-{W}"
        pg.screenshot(path=f"{OUT}/{n}-1-top.png")
        pg.screenshot(path=f"{OUT}/{n}-1b-top-tall.png", full_page=True, clip={"x": 0, "y": 0, "width": W, "height": 1900 if W < 500 else 1500})
        pin(pg); pg.screenshot(path=f"{OUT}/{n}-2-scrolled.png")
        pg.click('#wkstrip .tab[data-w="10"]'); pg.wait_for_timeout(400)
        gid = pg.evaluate("() => [...document.querySelectorAll('#games > li')].filter(x => !x.hidden)[2].querySelector('.wb[aria-pressed=false]').dataset.g")
        pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first.click(); pg.wait_for_timeout(300)
        pg.evaluate("g => { const e = document.querySelector('.gcard:has(.wb[data-g=\"' + g + '\"])'); e.scrollIntoView({block: 'center'}); }", gid); pg.wait_for_timeout(400)
        pg.screenshot(path=f"{OUT}/{n}-3-changed-row.png")
        pg.click('#wkstrip .tab[data-w="13"]'); pg.wait_for_timeout(400); pg.evaluate("() => document.getElementById('wnavs').scrollIntoView({block: 'end'})"); pg.wait_for_timeout(400)
        pg.screenshot(path=f"{OUT}/{n}-5-last-week.png")
        pg.evaluate("() => scrollTo(0, 0)"); pg.wait_for_timeout(200)
        pg.evaluate("() => document.getElementById('sh').scrollIntoView()"); pg.evaluate("() => scrollBy(0, -70)"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/{n}-6-standings.png")
        pg.evaluate("() => scrollTo(0, 0)"); pg.evaluate("() => document.getElementById('ccg').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(300)
        pg.locator("#ccg").screenshot(path=f"{OUT}/{n}-7-ccg-box.png")
        pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('ccg').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(300); pg.locator("#ccg").screenshot(path=f"{OUT}/{n}-4b-tie-box.png")
        pin(pg); pg.screenshot(path=f"{OUT}/{n}-4-tie-scrolled.png")
        pg.click("#rfav"); pg.wait_for_timeout(400); pin(pg, 200); pg.screenshot(path=f"{OUT}/{n}-7b-bar-decided.png", clip={"x": 0, "y": 0, "width": W, "height": 190})
        c.close()
        c, pg = load(b, W, block=True)
        pg.click("#wkstrip .tab[data-w=\"9\"]") if False else None
        pin(pg); pg.wait_for_timeout(900); pg.screenshot(path=f"{OUT}/{n}-8-fallback-tile.png"); c.close()
    # L9: level-records row (SEC Missouri-Texas) in a week that also holds a Better-record row; strip legend with only the kinds present
    for W in (390, 320, 1280):
        c = b.new_context(viewport={"width": W, "height": 844 if W < 500 else 800}, device_scale_factor=2 if W < 500 else 1); pg = c.new_page()
        pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=404, body="no"))
        pg.goto(f"{BASE}/conference/sec/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(700)
        wk = pg.evaluate("() => { const l = [...document.querySelectorAll('#games > li')].find(li => /Records level/.test(li.textContent) && /Missouri/.test(li.textContent) && /Texas/.test(li.textContent)); return l ? l.dataset.w : null; }")
        print("sec Missouri-Texas week", wk)
        pg.click(f'#wkstrip .tab[data-w="{wk}"]'); pg.wait_for_timeout(400)
        pg.evaluate("() => { const l = [...document.querySelectorAll('#games > li')].find(li => !li.hidden && /Records level/.test(li.textContent) && /Missouri/.test(li.textContent)); l.scrollIntoView({block: 'center'}); }"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/sec-{W}-9-level-row-viewport.png")
        li = pg.locator("#games > li:visible:has-text('Records level')").first; li.screenshot(path=f"{OUT}/sec-{W}-9a-level-row.png")
        pg.locator("#games > li:visible:has(.r-rec .gt:has-text('Better record'))").first.screenshot(path=f"{OUT}/sec-{W}-9b-better-record-row.png") if pg.locator("#games > li:visible:has(.gt:has-text('Better record'))").count() else None
        pg.locator("#wpanel").screenshot(path=f"{OUT}/sec-{W}-9c-mixed-week-panel.png")
        pg.locator("#strip").screenshot(path=f"{OUT}/sec-{W}-9d-strip-no-lines.png")
        pg.evaluate("() => document.querySelector('#games > li:not([hidden]) .wb[aria-pressed=false]').click()"); pg.wait_for_timeout(300)
        pg.locator("#strip").screenshot(path=f"{OUT}/sec-{W}-9e-strip-one-changed.png")
        c.close()
        c, pg = load(b, W); pg.evaluate("() => document.getElementById('strip').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(300); pg.locator("#strip").screenshot(path=f"{OUT}/big-12-{W}-9f-strip-espn-lines.png"); c.close()
    b.close()
srv.shutdown(); print("crops done", OUT)
