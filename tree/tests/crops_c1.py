"""c1 R1 crops -> crops/c1r1/{before,after}/ at 320, 390, 1280 (python3 tests/crops_c1.py).
before = v6a zip extracted (before-site/, no chat exists there: only the page tops where the pill is added), after = build/site (c1r1).
After: pill, gate, composer, typing, running, answer (+bottom with footers/regenerate), combo, next-game chip, need, refusal, clarify chips, not-understood, error, margin, title, 8-cap, in-progress, Elo model."""
import sys, os, re, json, shutil; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops/c1r1"; SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
SLOW = "self.onmessage=function(e){var m=e.data;if(m.op!=='run')return;self.postMessage({id:m.id,type:'progress',done:3000,total:10000})}"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + "/before"); os.makedirs(OUT + "/after")
srv, BASE = serve.start(); bsrv, BBASE = serve.start(site=f"{ROOT}/before-site")
B = json.load(open(f"{SITE}/data/sim-bundle.json")); T = B["teams"]
G = [g for g in B["games"] if g["h"] != B["fcs"] and g["a"] != B["fcs"]]
unamb = lambda t: len(B["aliases"]["map"].get(T[t]["s"].lower(), [])) == 1
q = lambda t: T[t]["s"] if unamb(t) else T[t]["n"]
live = next((g for g in G if g.get("ip") == 1 and unamb(g["h"])), None)
nl = next(g for g in sorted(G, key=lambda g: g["date"]) if not g.get("ip") and unamb(g["h"]) and unamb(g["a"]))
used, pairs = set(), []
for g in sorted(G, key=lambda g: len(q(g["h"])) + len(q(g["a"]))):
    if g["h"] in used or g["a"] in used or not (unamb(g["h"]) and unamb(g["a"])) or g.get("ip"): continue
    used |= {g["h"], g["a"]}; pairs.append(g)
    if len(pairs) == 9: break
nine = "What if " + " and ".join(f"{q(g['h'])} beats {q(g['a'])}" for g in pairs[:9]) + "?"
def wv(pg, sel, t=60000): pg.wait_for_selector(sel, timeout=t)
with sync_playwright() as p:
    b = p.chromium.launch(); n = 0
    for W, H, S in ((320, 640, 2), (390, 844, 2), (1280, 800, 1)):
        def new(init=ACC, path="/team/utah/", base=BASE, pill=True):
            c = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=S); c.add_init_script(init); pg = c.new_page(); pg.goto(base + path)
            if pill: wv(pg, "#kpill:not([hidden])")
            pg.wait_for_timeout(300); return c, pg
        def shot(pg, name, side="after"):
            global n; pg.wait_for_timeout(250); pg.screenshot(path=f"{OUT}/{side}/{W}-{name}.png"); n += 1
        def ask(pg, text, sel): pg.fill("#kask", text); pg.click("#kform .snd"); wv(pg, sel); pg.wait_for_timeout(300)
        for nmx, path in (("pill-conference", "/conference/big-12/"), ("pill-team", "/team/utah/"), ("pill-playoff", "/playoff/")):
            c, pg = new(path=path, base=BBASE, pill=False); shot(pg, nmx, "before"); c.close()
            c, pg = new(path=path); shot(pg, nmx); c.close()
        c, pg = new(); pg.evaluate("localStorage.clear(); sessionStorage.clear()"); pg.click("#kpill"); wv(pg, "#kgk"); shot(pg, "01-gate"); pg.check("#kgk"); shot(pg, "02-gate-checked"); pg.click("#kga"); wv(pg, ".q"); shot(pg, "03-composer-empty")
        pg.fill("#kask", "What if Utah Utes lo"); shot(pg, "04-typing"); pg.fill("#kask", "")
        pg.locator(".q").first.click(); wv(pg, ".ba"); shot(pg, "06-answer"); pg.locator("#kbd").evaluate("e => e.scrollTop = e.scrollHeight"); shot(pg, "07-answer-bottom-footers-regenerate")
        ask(pg, f"What if {q(nl['h'])} wins?", ".chip button"); shot(pg, "08-next-game-chip")
        ask(pg, f"What if {q(pairs[0]['h'])} beats {q(pairs[0]['a'])} and {q(pairs[1]['h'])} beats {q(pairs[1]['a'])} and {q(pairs[2]['a'])} beats {q(pairs[2]['h'])}?", ".ba"); shot(pg, "09-multi-chips")
        ask(pg, "What does Utah Utes need to make the playoff?", ".ba caption"); shot(pg, "10-need")
        ask(pg, "Who should I bet on, BYU or Texas Tech?", ".st2 h3"); shot(pg, "11-refusal")
        ask(pg, "What if Miami loses to Louisville?", "[data-pick]"); shot(pg, "12-clarify-chips")
        ask(pg, "what about the big game lol", ".ico"); shot(pg, "13-unparsed")
        ask(pg, "What if Utah Utes beat BYU by 10?", ".st2 h3"); shot(pg, "14-margin")
        ask(pg, "What if Utah Utes win the Big 12?", ".st2 h3"); shot(pg, "15-title-not-supported")
        ask(pg, nine[:200], ".st2 h3"); shot(pg, "16-eight-game-cap")
        if live: ask(pg, f"What if {q(live['h'])} loses?", ".ba, .st2 h3"); pg.locator("#kbd").evaluate("e => e.scrollTop = e.scrollHeight"); shot(pg, "17-in-progress-game")
        c.close()
        c, pg = new(path="/team/utah/?model=elo"); pg.click("#kpill"); wv(pg, ".q"); pg.locator(".q").first.click(); wv(pg, ".ba"); shot(pg, "18-answer-elo-model"); c.close()
        c, pg = new(); pg.route("**/assets/chat-worker.js", lambda r: r.fulfill(body=SLOW, content_type="text/javascript")); pg.click("#kpill"); wv(pg, ".q"); pg.locator(".q").nth(1).click(); wv(pg, ".prog"); pg.wait_for_timeout(500); shot(pg, "05-running"); c.close()
        c, pg = new(); pg.route("**/data/sim-bundle.json", lambda r: r.abort()); pg.click("#kpill"); wv(pg, "[data-retry]"); shot(pg, "19-error"); pg.fill("#kask", "What if Utah Utes wins out?"); pg.click("#kform .snd"); wv(pg, ".ub"); pg.wait_for_timeout(300); shot(pg, "20-error-with-question"); c.close()
        c, pg = new(); pg.click("#kpill"); wv(pg, ".q"); pg.keyboard.press("Escape"); shot(pg, "21-closed-pill-focused"); c.close()
    b.close()
srv.shutdown(); bsrv.shutdown(); print(n, "crops in", OUT)
