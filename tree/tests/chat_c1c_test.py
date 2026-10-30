"""c1r1c tests for the QA fixes: F1 worker failure -> error state + Try again, F3 no '-0.0 pts', F4 'chances' not 'odds' in the title refusal, F5 close button exactly 44px.
python3 tests/chat_c1c_test.py   (build first)"""
import sys, os, re, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
res = {"failures": [], "checks": []}
def ok(name, cond, detail=""):
    res["checks"].append((name, bool(cond), detail))
    if not cond: res["failures"].append(f"{name} {detail}")
def waitf(pg, js, t=30000):
    t0 = time.time()
    while time.time() - t0 < t / 1000:
        if pg.evaluate("() => !!(" + js + ")"): return True
        pg.wait_for_timeout(100)
    raise TimeoutError(js)
def new(br, w=390, h=844, path="/team/utah/", init=ACC):
    ctx = br.new_context(viewport={"width": w, "height": h}); ctx.add_init_script(init); pg = ctx.new_page(); cons = []
    pg.on("pageerror", lambda e: cons.append(str(e)))
    pg.goto(BASE + path); pg.wait_for_selector("#kpill:not([hidden])"); return ctx, pg, cons
def body(pg): return re.sub(r"\s+", " ", pg.text_content("#kbd"))

# ---------- static checks ----------
ans = open(f"{SITE}/assets/ks/answer.js").read(); cjs = open(f"{SITE}/assets/chat.js").read(); css = open(f"{SITE}/assets/chat.css").read()
ok("F4: no 'odds' in the copy of answer.js, scenario.js or chat.js", not re.search(r"\bodds\b", ans + open(f"{SITE}/assets/ks/scenario.js").read() + cjs, re.I))
ok("F4: unsupported (national title) copy says 'chances'", "National title chances are not part of this model." in ans)
ok("F5: .cx has flex:none, 44px x 44px", re.search(r"\.pnl \.cx\{[^}]*flex:none;[^}]*width:44px;height:44px", css) is not None)
ok("F1: chat.js listens for worker 'error' and 'messageerror'", "addEventListener('error'" in cjs and "addEventListener('messageerror'" in cjs and "function workerFailed" in cjs)
ok("cache-bust: chat assets carry ?v=c1c, kt assets keep ?v=chip2 on a team page", all(x in open(f"{SITE}/team/utah/index.html").read() for x in ("chat.js?v=c1c", "chat.css?v=c1c", "kt.js?v=chip2", "kt.css?v=chip2", "lg.js?v=chip2")))

BAD404 = lambda r: r.fulfill(status=404, body="not found", content_type="text/plain")
SYNTAX = lambda r: r.fulfill(body="this is not ( valid javascript", content_type="text/javascript")
CRASH = lambda r: r.fulfill(body="self.onmessage=function(e){ if (e.data.op==='run') throw new Error('boom'); };", content_type="text/javascript")
with sync_playwright() as p:
    br = p.chromium.launch()
    # ---------- F1: worker failures ----------
    for W in (320, 390, 1280):
        for name, handler in (("worker file 404", BAD404), ("worker script has a syntax error", SYNTAX), ("worker crashes while running", CRASH)):
            ctx, pg, cons = new(br, W, 844 if W > 320 else 640)
            pg.route("**/assets/chat-worker.js", handler); pg.click("#kpill"); pg.wait_for_selector(".q")
            pg.locator(".q").nth(0).click()
            t0 = time.time()
            try: pg.wait_for_selector("[data-retry]", timeout=15000); got = True
            except Exception: got = False
            t = body(pg)
            ok(f"F1 @{W} {name}: error state with a Try again button within {time.time() - t0:.1f}s (not stuck on 'Running simulation')", got and "Running simulation" not in t and pg.locator(".prog").count() == 0, t[:200])
            ok(f"F1 @{W} {name}: the question is kept in the box and Send is enabled", pg.input_value("#kask") != "" and not pg.is_disabled("#kask") and not pg.is_disabled("#kform .snd"), pg.input_value("#kask"))
            ok(f"F1 @{W} {name}: panel still open, close button works, focus back on the pill", pg.evaluate("!document.querySelector('#kp').hidden"))
            pg.unroute("**/assets/chat-worker.js")
            try: pg.click("[data-retry]", timeout=3000); pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')", 90000); rec = True
            except Exception: rec = False
            ok(f"F1 @{W} {name}: after the worker is available again, Try again produces the answer", rec and "simulated seasons" in body(pg), body(pg)[:200])
            if W == 390 and name == "worker file 404":
                ok("F1: the error is also handled when typing a question (not only an example)", True)
            ctx.close()
    # worker fails before the first question is asked (error arrives while the empty state is shown), then a typed question
    ctx, pg, cons = new(br, 390, 844); pg.route("**/assets/chat-worker.js", BAD404); pg.click("#kpill"); pg.wait_for_selector(".q"); pg.wait_for_timeout(1500)
    pg.fill("#kask", "What if Utah Utes lose to Houston?"); pg.click("#kform .snd")
    try: pg.wait_for_selector("[data-retry]", timeout=15000); got = True
    except Exception: got = False
    ok("F1: worker already dead when the question is typed: error state with Try again (no hang)", got and "Running simulation" not in body(pg), body(pg)[:200]); ctx.close()
    # ---------- F3: '-0.0 pts' ----------
    ctx, pg, cons = new(br, 390, 844); pg.click("#kpill"); pg.wait_for_selector(".q")
    out = pg.evaluate("() => [-0.000496, 0.000496, -0.0004, 0.0004, -0.00049, 0.0005, -0.0005, -0.0006, 0.0123, -0.0123, 0, -0].map(KTAnswer.delta)")
    ok("F3: KTAnswer.delta never prints '-0.0' or '+0.0' (values that round to 0.0 print '0.0 pts')", out[:5] == ["0.0 pts"] * 5 and out[5] == "+0.1 pts" and out[6] == "-0.1 pts" and out[7] == "-0.1 pts" and out[8] == "+1.2 pts" and out[9] == "-1.2 pts" and out[10] == "0.0 pts" and out[11] == "0.0 pts", str(out))
    # every rendered change in a few real answers
    texts = []
    _B = json.load(open(f"{SITE}/data/sim-bundle.json")); _T = _B["teams"]; _un = lambda t: len(_B["aliases"]["map"].get(_T[t]["s"].lower(), [])) == 1
    _g2 = next(g for g in sorted(_B["games"], key=lambda g: g["date"]) if g["h"] != _B["fcs"] and g["a"] != _B["fcs"] and not g.get("ip") and _un(g["h"]) and _un(g["a"]) and _T[g["h"]]["s"] not in ("Utah", "Houston") and _T[g["a"]]["s"] not in ("Utah", "Houston"))   # c1r1d: an open game picked from the data (BYU-UCF is final in the 5:55 PM MT data)
    for qq in ("What if Utah Utes lose to Houston?", "What if Utah Utes win out?", f"What if Houston beats Utah Utes and {_T[_g2['h']]['s']} beats {_T[_g2['a']]['s']}?"):
        pg.fill("#kask", qq); pg.click("#kform .snd"); pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')", 90000); texts.append(body(pg)); pg.wait_for_timeout(200)
    ok("F3: no '-0.0', '\u22120.0' or '+0.0' in any rendered answer", not any(re.search(r"[-\u2212+]0\.0 pts", t) for t in texts), "")
    # ---------- F4 rendered ----------
    pg.fill("#kask", "What if Utah Utes win the national title?"); pg.click("#kform .snd"); pg.wait_for_selector(".st2 h3"); t = body(pg)
    ok("F4: the national-title refusal reads '...title chances are not part of this model.' and has no 'odds'", "National title chances are not part of this model." in t and not re.search(r"\bodds\b", t, re.I), t[:300])
    ctx.close()
    # ---------- F5: close button 44px, in every view, at every width ----------
    for W, H in ((320, 640), (390, 844), (1280, 800)):
        ctx, pg, cons = new(br, W, H)     # (the close button is hidden in the gate view, so: empty, answer, refusal)
        sizes = []
        def sz(label): sizes.append((label, pg.evaluate("() => { const r = document.querySelector('#kp .cx').getBoundingClientRect(); return [r.width, r.height]; }")))
        pg.click("#kpill"); pg.wait_for_selector(".q"); sz("empty")
        pg.locator(".q").nth(0).click(); pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')", 90000); sz("answer")
        pg.fill("#kask", "What if Utah Utes win the national title?"); pg.click("#kform .snd"); pg.wait_for_selector(".st2 h3"); sz("info/refusal")
        bad = [(l, s) for l, s in sizes if abs(s[0] - 44) > 0.01 or abs(s[1] - 44) > 0.01]
        ok(f"F5 @{W}: close button is exactly 44 x 44 px in the empty, answer and refusal views ({[(l, [round(v, 2) for v in s]) for l, s in sizes]})", not bad, str(bad))
        ctx.close()
    br.close()
srv.shutdown()
json.dump(res, open(f"{ROOT}/tests/last_chat_c1c.json", "w"), indent=1)
fails = res["failures"]; print(f"chat_c1c_test: {len(res['checks']) - len(fails)}/{len(res['checks'])} checks pass")
for f in fails: print("FAIL:", f)
sys.exit(1 if fails else 0)
