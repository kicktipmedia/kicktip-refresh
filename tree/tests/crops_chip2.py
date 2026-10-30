"""chip2 crops -> crops-chip2/ (home with chips from the synthetic fixture build/site-chipdemo at 1280/390/320, plus a Big 12 conference row at 1280 and 320, and a gap measurement). python3 tests/crops_chip2.py"""
import sys, os, re, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-chip2"; os.makedirs(OUT, exist_ok=True)
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
GAP = "[...document.querySelectorAll('#top12 .tcn, .tw .tcn')].map(w=>{const a=w.querySelector('a.tl'),m=w.querySelector('.mv');if(!m)return null;const ra=a.getBoundingClientRect(),rm=m.getBoundingClientRect(),rp=m.querySelector('.pl').getBoundingClientRect(),rr=document.createRange();rr.selectNodeContents(a);const t=rr.getBoundingClientRect();const lines=rr.getClientRects().length;return {team:a.textContent.trim(),sameRow:rm.top<ra.bottom&&rp.top>=ra.top-20&&lines==1&&Math.abs((rm.top+rm.height/2)-(ra.top+ra.height/2))<30,textRight:Math.round(t.right),pillLeft:Math.round(rp.left),gap:Math.round(rp.left-t.right),btnLeft:Math.round(rm.left)}}).filter(x=>x)"
rep = {}
with sync_playwright() as p:
    b = p.chromium.launch(); srv, BASE = serve.start(f"{ROOT}/build/site-chipdemo")
    for W in (1280, 390, 320):
        c = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=2 if W < 1000 else 1); c.add_init_script(ACC); pg = c.new_page()
        pg.goto(BASE + "/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector("#top12 tbody tr .mv"); pg.wait_for_timeout(600)
        rep[f"home-{W}"] = pg.evaluate(GAP); rep[f"home-{W}-overflow"] = pg.evaluate("document.documentElement.scrollWidth<=innerWidth"); rep[f"home-{W}-tablew"] = pg.evaluate("[document.querySelector('#top12').scrollWidth, document.querySelector('#top12').parentElement.clientWidth]")
        el = pg.locator(".tw.tk-n").first; el.scroll_into_view_if_needed(); pg.wait_for_timeout(150); el.screenshot(path=f"{OUT}/home-chips-{W}.png")
        if W == 1280:  # tight zoom on the name+chip rows for the gap
            pg.locator("#top12 tbody tr").nth(1).screenshot(path=f"{OUT}/home-chips-1280-row-notre-dame.png")
        if W in (1280, 320):
            pg.goto(BASE + "/conference/big-12/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector(".mv"); pg.wait_for_timeout(500); rep[f"big12-{W}"] = pg.evaluate(GAP); rep[f"big12-{W}-overflow"] = pg.evaluate("document.documentElement.scrollWidth<=innerWidth")
            pg.locator("table").first.screenshot(path=f"{OUT}/conf-big12-{W}.png")
        c.close()
    b.close()
json.dump(rep, open(f"{OUT}/gap-measure.json", "w"), indent=1); print(json.dumps(rep)[:1800])
