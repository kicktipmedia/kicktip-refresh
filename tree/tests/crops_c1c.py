"""c1r1c crops -> crops/c1r1c/ at 320, 390, 1280 (python3 tests/crops_c1c.py): ONLY the new / changed states:
F1 worker-failure error state (load failure, and a crash mid-run), F3 a change that rounds to 0.0 prints '0.0 pts', F4 title refusal copy ('chances'), F5 close button exactly 44px."""
import sys, os, re, json, shutil; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops/c1r1c"; SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
CRASH = "self.onmessage=function(e){ if (e.data.op==='run') throw new Error('boom'); };"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
srv, BASE = serve.start()
B = json.load(open(f"{SITE}/data/sim-bundle.json")); T = B["teams"]
G = [g for g in B["games"] if g["h"] != B["fcs"] and g["a"] != B["fcs"] and not g.get("ip")]
unamb = lambda t: len(B["aliases"]["map"].get(T[t]["s"].lower(), [])) == 1
q = lambda t: T[t]["s"] if unamb(t) else T[t]["n"]
def wv(pg, sel, t=60000): pg.wait_for_selector(sel, timeout=t)
n = 0; found0 = None
with sync_playwright() as p:
    b = p.chromium.launch()
    # find, once, a real answer whose table has a change that rounds to 0.0 (F3): try games between lower-rated teams
    c = b.new_context(viewport={"width": 1280, "height": 800}); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + "/team/utah/"); wv(pg, "#kpill:not([hidden])"); pg.click("#kpill"); wv(pg, ".q")
    order = sorted([g for g in G if unamb(g["h"]) and unamb(g["a"])], key=lambda g: B["teams"][g["h"]].get("r", 0) if isinstance(B["teams"][g["h"]].get("r", 0), (int, float)) else 0)
    for g in order[:60]:
        qq = f"What if {q(g['h'])} loses to {q(g['a'])}?"
        pg.fill("#kask", qq); pg.click("#kform .snd"); pg.wait_for_selector(".ba, .st2 h3", timeout=90000); pg.wait_for_function("!document.querySelector('.prog')", timeout=90000)
        if re.search(r"(?<![\d.])0\.0 pts", pg.text_content("#kbd") or ""): found0 = qq; break
    c.close(); print("F3 question:", found0)
    for W, H, S in ((320, 640, 2), (390, 844, 2), (1280, 800, 1)):
        def new(path="/team/utah/"):
            c = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=S); c.add_init_script(ACC); pg = c.new_page(); pg.goto(BASE + path); wv(pg, "#kpill:not([hidden])"); pg.wait_for_timeout(300); return c, pg
        def shot(pg, name):
            global n; pg.wait_for_timeout(250); pg.screenshot(path=f"{OUT}/{W}-{name}.png"); n += 1
        # F1: worker file fails to load -> error state + Try again, question kept, Send enabled
        c, pg = new(); pg.route("**/assets/chat-worker.js", lambda r: r.fulfill(status=404, body="nf", content_type="text/plain")); pg.click("#kpill"); wv(pg, ".q"); pg.locator(".q").first.click(); wv(pg, "[data-retry]"); shot(pg, "F1-a-worker-load-failed-error-state"); c.close()
        # F1: worker loads but crashes while running
        c, pg = new(); pg.route("**/assets/chat-worker.js", lambda r: r.fulfill(body=CRASH, content_type="text/javascript")); pg.click("#kpill"); wv(pg, ".q"); pg.locator(".q").first.click(); wv(pg, "[data-retry]"); shot(pg, "F1-b-worker-crashed-mid-run-error-state")
        pg.unroute("**/assets/chat-worker.js"); pg.click("[data-retry]"); wv(pg, ".ba"); pg.wait_for_function("!document.querySelector('.prog')"); shot(pg, "F1-c-try-again-recovers-answer"); c.close()
        # F3: a change that rounds to 0.0
        if found0:
            c, pg = new(); pg.click("#kpill"); wv(pg, ".q"); pg.fill("#kask", found0); pg.click("#kform .snd"); wv(pg, ".ba"); pg.wait_for_function("!document.querySelector('.prog')"); pg.wait_for_timeout(300)
            pg.evaluate("""() => { const td = [...document.querySelectorAll('#kbd td')].find(x => /(^|[^\\d.])0\\.0 pts/.test(x.textContent)); if (td) td.scrollIntoView({block: 'center'}); }"""); shot(pg, "F3-zero-change-prints-0.0-pts"); c.close()
        # F4: title refusal copy says 'chances'
        c, pg = new(); pg.click("#kpill"); wv(pg, ".q"); pg.fill("#kask", "What if Utah Utes win the national title?"); pg.click("#kform .snd"); wv(pg, ".st2 h3"); shot(pg, "F4-title-refusal-chances"); 
        # F5: close button 44px: header close-up on the answer view, plus the refusal view above
        pg.locator("#kp .hdp").screenshot(path=f"{OUT}/{W}-F5-close-button-44px-header.png"); n += 1
        c.close()
    b.close()
srv.shutdown(); print(n, "crops in", OUT)
