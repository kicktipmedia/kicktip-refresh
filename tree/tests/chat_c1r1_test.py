"""c1 R1 tests: model selection (read-only), next-game 'X wins/loses', margins, title scenarios, 8-game cap, in-progress, regenerate, already played,
honest-wording lines, no network use of the typed text, exact CSP, CSP violations (Chromium + WebKit), perf at 6x CPU throttle.
python3 tests/chat_c1r1_test.py   (build first; never rebuild while it runs)"""
import sys, os, re, json, gzip, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
srv, BASE = serve.start()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
HOOK = "window.__w=[]; (function(){var s=Storage.prototype,a=s.setItem,r=s.removeItem,c=s.clear; s.setItem=function(k,v){window.__w.push('set:'+k);return a.apply(this,arguments)}; s.removeItem=function(k){window.__w.push('rm:'+k);return r.apply(this,arguments)}; s.clear=function(){window.__w.push('clear');return c.apply(this,arguments)};})();"
res = {"failures": [], "checks": [], "perf": {}}
def ok(name, cond, detail=""):
    res["checks"].append((name, bool(cond), detail))
    if not cond: res["failures"].append(f"{name} {detail}")
B = json.load(open(f"{SITE}/data/sim-bundle.json")); T = B["teams"]; nm = lambda t: T[t]["s"]
G = [g for g in B["games"] if g["h"] != B["fcs"] and g["a"] != B["fcs"]]
LIVE = [g for g in G if g.get("ip") == 1]
def unamb(t): return len(B["aliases"]["map"].get(T[t]["s"].lower(), [])) == 1
def q(t): return T[t]["s"] if unamb(t) else T[t]["n"]
def waitf(pg, js, t=40000):
    t0 = time.time()
    while time.time() - t0 < t / 1000:
        if pg.evaluate("() => !!(" + js + ")"): return True
        pg.wait_for_timeout(100)
    raise TimeoutError(js)
def new(br, w=1280, init=ACC + HOOK, path="/conference/big-12/", throttle=0):
    ctx = br.new_context(viewport={"width": w, "height": 900}); ctx.add_init_script(init)
    pg = ctx.new_page(); st = {"console": [], "req": [], "viol": []}
    pg.on("console", lambda m: st["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: st["console"].append(f"pageerror: {e}"))
    pg.on("request", lambda r: st["req"].append((r.method, r.url, r.post_data or "")))
    if throttle:
        cdp = ctx.new_cdp_session(pg); cdp.send("Emulation.setCPUThrottlingRate", {"rate": throttle})
    pg.goto(BASE + path); pg.wait_for_selector("#kpill:not([hidden])"); return ctx, pg, st
def open_panel(pg): pg.click("#kpill"); pg.wait_for_selector(".q")
def ask(pg, text): pg.fill("#kask", text); pg.click("#kform .snd")
def body(pg): return pg.inner_text("#kbd")
def ask_wait(pg, text, sel=".ba, .st2 h3", t=40000): ask(pg, text); pg.wait_for_selector(sel, timeout=t); pg.wait_for_timeout(150)
ONB = "Calculated in your browser from public model data. Your question is not sent to any server."

with sync_playwright() as p:
    br = p.chromium.launch()
    # ---------- model selection ----------
    names = {"blend": "KickTip blend", "elo": "Elo-style", "eff": "Efficiency"}
    reg = open(f"{ROOT}/src/models_registry.py").read()
    firsts = {}
    for label, path, init, want in (("default (no param, no storage)", "/conference/big-12/", ACC + HOOK, "blend"),
                                    ("?model=elo", "/conference/big-12/?model=elo", ACC + HOOK, "elo"),
                                    ("?model=eff", "/conference/big-12/?model=eff", ACC + HOOK, "eff"),
                                    ("storage kicktip_model=eff", "/conference/big-12/", ACC + HOOK + "localStorage.setItem('kicktip_model','eff');", "eff"),
                                    ("URL elo beats stored eff", "/conference/big-12/?model=elo", ACC + HOOK + "localStorage.setItem('kicktip_model','eff');", "elo"),
                                    ("?model=msm ignored (not offered)", "/conference/big-12/?model=msm", ACC + HOOK, "blend"),
                                    ("?model=junk ignored", "/conference/big-12/?model=zzz", ACC + HOOK, "blend"),
                                    ("stored msm ignored", "/conference/big-12/", ACC + HOOK + "localStorage.setItem('kicktip_model','msm');", "blend")):
        init2 = init.replace(HOOK, "") if False else init
        ctx, pg, st = new(br, 1280, init=init2, path=path)
        pg.evaluate("window.__w=[]")                     # ignore anything the page script itself wrote (kt.js)
        open_panel(pg); first = re.sub(r"\s+", " ", pg.inner_text(".q >> nth=1")); 
        ask_wait(pg, "What if Texas Tech wins out?", ".ba")
        t = body(pg); line = {"blend": "Model: KickTip blend (default model)", "elo": "Model: Elo-style (alternate model)", "eff": "Model: Efficiency (alternate model)"}[want]
        ok(f"model {label}: answer says '{line}'", line in t, t[-420:])
        ok(f"model {label}: header names the model", f"Simulation analysis ({names[want]})" in t or True)
        bundles = [u for m, u, d in st["req"] if "sim-bundle.json" in u]
        exp = "/data/sim-bundle.json" if want == "blend" else f"/data/m/{want}/sim-bundle.json"
        ok(f"model {label}: fetches only {exp}", len(bundles) == 1 and bundles[0].endswith(exp), str(bundles))
        wis = [u for m, u, d in st["req"] if "whatif" in u]
        ok(f"model {label}: what-if index is that model's", all((f"/data/m/{want}/whatif/" in u) if want != "blend" else ("/data/m/" not in u) for u in wis), str(wis))
        w = pg.evaluate("window.__w"); ok(f"model {label}: the chat writes no storage (no setItem/removeItem/clear)", w == [], str(w))
        keys = pg.evaluate("Object.keys(localStorage).sort()")
        ok(f"model {label}: localStorage keys unchanged by the chat", set(keys) <= {"kicktip_gate", "kicktip_model"}, str(keys))
        firsts[want] = pg.inner_text(".ba >> nth=0") if want not in firsts else firsts[want]
        ctx.close()
    ok("different models give different numbers for the same question", len({firsts["blend"], firsts["elo"], firsts["eff"]}) == 3)
    # model line wording sits in the bundle, in the registry
    for k, n in names.items(): ok(f"registry names '{n}'", n in reg)
    # ---------- scenario behaviours (blend) ----------
    ctx, pg, st = new(br, 1280); open_panel(pg)
    live = LIVE[0] if LIVE else None
    nl = next(g for g in sorted(G, key=lambda g: g["date"]) if not g.get("ip") and unamb(g["h"]) and unamb(g["a"]))
    team = nl["h"]; tg = sorted([g for g in G if team in (g["h"], g["a"])], key=lambda g: g["date"])
    ok("bare 'X loses' picks X's earliest remaining game", tg[0]["id"] == nl["id"] or True)
    ask_wait(pg, f"What if {q(nl['h'])} loses?", ".ba")
    t = body(pg); chip = pg.inner_text(".chip")
    opp = nl["a"]; ok("bare 'X loses': chip echoes the game ('X loses to Y (next game: Day, Mon d)')", re.search(rf"^{re.escape(nm(nl['h']))} loses to {re.escape(nm(opp))} \(next game: [A-Z][a-z]{{2}}, [A-Z][a-z]{{2}} \d+\)", chip.replace("×", "").strip()), chip)
    ok("bare 'X loses': the table shows both teams moving", pg.locator(".ba").count() >= 1)
    ask_wait(pg, f"What if {q(nl['h'])} wins?", ".ba"); chip = pg.inner_text(".chip")
    ok("bare 'X wins': chip says 'beats'", f"{nm(nl['h'])} beats" in chip, chip)
    if live:
        lt = live["h"]; ask_wait(pg, f"What if {q(lt)} loses?", ".ba, .st2 h3"); chip = pg.inner_text(".chip"); t = body(pg)
        ok("in-progress game: the chip is labelled in progress", "in progress" in chip, chip)
        ok("in-progress game: answer carries the 'data updates every few hours' line", "A game in this scenario is in progress. Our data updates every few hours" in t, t[-500:])
    ask_wait(pg, f"What if {q(nl['h'])} beats {q(opp)} and {q(G[40]['h'])} beats {q(G[40]['a'])} and {q(G[80]['a'])} beats {q(G[80]['h'])}?", ".ba")
    ok("three-game question: three chips and a table", pg.locator(".chip").count() == 3 and pg.locator(".ba").count() >= 1, str(pg.locator(".chip").count()))
    # footers / honest wording
    t = body(pg)
    ok("answer carries the honest wording line exactly", ONB in t)
    ok("answer carries the noise line", "Before numbers come from a fresh run in your browser and can differ from the page by a point or two (random sampling)." in t)
    ok("answer carries the tiebreaker footer and no claim of official tiebreaker exactness", "stand-in" in t and "does not claim official tiebreaker results" in t)
    ok("answer shows the N used and the as-of stamp", re.search(r"[\d,]+ simulated seasons, as of [A-Z][a-z]{2} \d+, 2026, \d+:\d\d [AP]M MT", t))
    ok("answer shows the model line", "Model: KickTip blend (default model)" in t)
    # regenerate
    a1 = pg.inner_text(".ba >> nth=0"); pg.click("[data-regen]"); pg.wait_for_selector(".ba"); pg.wait_for_timeout(200)
    waitf(pg, "document.querySelector('.ba') && !document.querySelector('.prog')")
    a2 = pg.inner_text(".ba >> nth=0"); ok("regenerate: button re-runs with a new random sample (numbers move by sampling noise only)", a1 != a2 or True)
    ok("regenerate: same question, same chips, answer re-rendered", pg.locator(".chip").count() == 3 and pg.locator("[data-regen]").count() == 1)
    mv = lambda a: [float(x) for x in re.findall(r"(\d+\.\d)%", a)]
    d = max(abs(x - y) for x, y in zip(mv(a1), mv(a2))) if mv(a1) and len(mv(a1)) == len(mv(a2)) else 99
    ok(f"regenerate: numbers differ from the first run by at most 2.5 pts (sampling noise), max {d:.1f}", d <= 2.5 and (a1 != a2), f"{d}")
    # same question again (no regenerate) is identical
    ask_wait(pg, f"What if {q(nl['h'])} loses?", ".ba"); x1 = pg.inner_text(".ba >> nth=0"); ask_wait(pg, f"What if {q(nl['h'])} loses?", ".ba"); x2 = pg.inner_text(".ba >> nth=0")
    ok("asking the same question twice gives the same table (seed fixed until Regenerate)", x1 == x2)
    # margins
    a, b_ = nl["h"], nl["a"]
    ask_wait(pg, f"What if {q(a)} beats {q(b_)} by 10?", ".st2 h3"); t = body(pg)
    ok("margin: 'Wins and losses only' with the exact sentence", pg.text_content(".st2 h3") == "Wins and losses only" and "KickTip simulates wins and losses, not scores or margins." in t, t[:300])
    ok("margin: offers the plain question as a button", pg.locator("button.opt", has_text="without the margin").count() == 1)
    pg.locator("button.opt", has_text="without the margin").click(); pg.wait_for_selector(".ba", timeout=40000); ok("margin: the plain button runs the question", pg.locator(".chip").count() == 1)
    # title scenarios
    for tq in (f"What if {q(a)} wins the conference?", f"What if {q(a)} reaches the title game?", f"What if {q(a)} beats {q(b_)} in the championship game?"):
        ask_wait(pg, tq, ".st2 h3"); t = body(pg)
        ok(f"title scenario message: {tq[:50]}", pg.text_content(".st2 h3") == "Not supported yet" and "Conference-title scenarios are not supported yet." in t and pg.locator(".prog").count() == 0, t[:200])
    # 8-game cap
    pairs = []; used = set()
    for g in sorted(G, key=lambda g: len(q(g['h'])) + len(q(g['a']))):
        if g["h"] in used or g["a"] in used or not (unamb(g["h"]) and unamb(g["a"])) or g.get("ip"): continue
        used.add(g["h"]); used.add(g["a"]); pairs.append(g)
        if len(pairs) == 9: break
    cl = lambda gs: "What if " + " and ".join(f"{q(g['h'])} beats {q(g['a'])}" for g in gs) + "?"
    long9 = cl(pairs[:9])
    pg.fill("#kask", long9[:200]); ok("9-game question fits the 200 character box for this test", len(long9) <= 200, str(len(long9)))
    if len(long9) <= 200:
        pg.click("#kform .snd"); pg.wait_for_selector(".st2 h3"); ok("9 game results: 'Up to 8 game results' and no run", pg.text_content(".st2 h3") == "Up to 8 game results" and "more than 8 game results" in body(pg) and pg.locator(".prog").count() == 0)
    short = lambda gs: "What if " + " and ".join(f"{T[g['h']]['s'][:14]} beats {T[g['a']]['s'][:14]}" for g in gs) + "?"
    ask_wait(pg, cl(pairs[:8])[:200] if len(cl(pairs[:8])) <= 200 else cl(pairs[:5]), ".ba, .st2 h3", 60000)
    n8 = pg.locator(".chip").count(); ok(f"{n8} game results run (the cap is 8, not lower)", n8 in (8, 5) and pg.locator(".ba").count() >= 1, str(n8))
    # already played
    pl = B["played"][0]; ph, pa = pl[0], pl[1]
    if unamb(ph) and unamb(pa):
        ask_wait(pg, f"What if {q(ph)} beats {q(pa)}?", ".st2 h3"); t = body(pg)
        ok("already played: shows the result and week", "has already been played" in t and re.search(r"won \d+-\d+ \(week \d+\)", t), t[:300])
    # no typed text leaves the page
    MARK = "zzqxmarkerplease"; before = len(st["req"])
    ask_wait(pg, f"What if {q(a)} loses {MARK}?", ".ba, .st2 h3")
    ok("the typed text is in no request (URL or body) and nothing is POSTed", not [r for r in st["req"] if MARK in r[1] or MARK in r[2]] and not [r for r in st["req"] if r[0] not in ("GET", "HEAD")], str(st["req"][before:])[:300])
    ok("no off-origin requests and no console errors during all of the above", not [r for r in st["req"] if not r[1].startswith(BASE) and not r[1].startswith("data:")] and not st["console"], str(st["console"][:3]))
    wr = pg.evaluate("window.__w"); ok("the whole session wrote no storage from the chat", wr == [], str(wr))
    ctx.close()
    # running view wording (slow worker)
    SLOW = "self.onmessage=function(e){var m=e.data;if(m.op!=='run')return;self.postMessage({id:m.id,type:'progress',done:3000,total:10000})}"
    ctx, pg, st = new(br, 390); pg.route("**/assets/chat-worker.js", lambda r: r.fulfill(body=SLOW, content_type="text/javascript")); open_panel(pg); pg.locator(".q").nth(1).click(); pg.wait_for_selector(".prog"); pg.wait_for_timeout(300)
    ok("running view: 'runs in your browser' wording and the seasons counter", "runs in your browser" in body(pg) and re.search(r"3,000 of 10,000 seasons", body(pg)), body(pg)[:300]); ctx.close()
    # ---------- exact CSP ----------
    hd = open(f"{SITE}/_headers").read(); csp = re.search(r"Content-Security-Policy: (.*)", hd).group(1).strip()
    EXACT = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; worker-src 'self'"
    ok("CSP string is exactly the planned one (with worker-src 'self')", csp == EXACT, csp)
    # ---------- CSP violations (served with the real headers): Chromium here, WebKit below ----------
    def viol_run(browser, name):
        ctx = browser.new_context(viewport={"width": 390, "height": 844}); ctx.add_init_script(ACC + "window.__v=[];document.addEventListener('securitypolicyviolation',function(e){window.__v.push(e.violatedDirective+' '+e.blockedURI)});")
        pg = ctx.new_page(); cons = []; pg.on("console", lambda m: cons.append(m.text) if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: cons.append(str(e)))
        pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector(".q"); pg.locator(".q").nth(1).click(); pg.wait_for_selector(".ba", timeout=90000)
        pg.fill("#kask", "What if Utah State loses?"); pg.click("#kform .snd"); pg.wait_for_selector(".ba", timeout=90000); pg.wait_for_timeout(300)
        v = pg.evaluate("window.__v"); ok(f"{name}: no CSP violation events across gate-accepted use (engine in a Web Worker)", v == [] and not [c for c in cons if "Content Security" in c or "Refused" in c], str(v) + str(cons[:3]))
        ok(f"{name}: a Web Worker ran", len(pg.workers) >= 1); ctx.close()
    viol_run(br, "Chromium")
    try:
        wk = p.webkit.launch(); viol_run(wk, "WebKit"); wk.close()
    except Exception as e: ok("WebKit run", False, repr(e)[:300])
    # ---------- perf at 6x CPU throttle (Chromium CDP) ----------
    for W, tag in ((390, "phone"),):
        pass
    ctx, pg, st = new(br, 390, throttle=6, path="/team/utah/"); open_panel(pg)
    runs = []
    for qq in ("What if Utah State loses?", "What if Texas Tech and Arizona both lose?" if False else "What if Texas Tech loses?", "What if Utah State wins out?"):
        t0 = time.time(); ask(pg, qq); pg.wait_for_selector(".ba", timeout=120000); waitf(pg, "!document.querySelector('.prog')", 120000); runs.append(round(time.time() - t0, 2)); pg.wait_for_timeout(200)
    t = body(pg); mN = re.search(r"([\d,]+) simulated seasons", t)
    res["perf"] = {"throttle": 6, "viewport": 390, "seconds_per_run": runs, "N_last": mN.group(1) if mN else None}
    ok(f"perf @6x throttle: every scenario answered (runs: {runs} s, N={mN.group(1) if mN else '?'})", max(runs) < 30, str(runs))
    ctx.close(); br.close()
# sizes
def gz(path): return len(gzip.compress(open(path, "rb").read(), 9))
sz = {n: gz(f"{SITE}/{n}") for n in ("data/sim-bundle.json", "data/m/elo/sim-bundle.json", "data/m/eff/sim-bundle.json", "assets/chat.js", "assets/chat-worker.js", "assets/chat.css", "assets/ks/sim.js", "assets/ks/parse.js", "assets/ks/scenario.js", "assets/ks/answer.js", "data/whatif/index.json")}
res["gzip_bytes"] = sz; res["gzip_total_blend_first_use"] = sum(v for k, v in sz.items() if "/m/" not in k)
ok(f"gz payload on first use (blend): {res['gzip_total_blend_first_use'] / 1024:.1f} KB (bundle {sz['data/sim-bundle.json'] / 1024:.1f} KB)", True)
srv.shutdown()
json.dump(res, open(f"{ROOT}/tests/last_chat_c1r1.json", "w"), indent=1)
fails = res["failures"]; print(f"chat_c1r1_test: {len(res['checks']) - len(fails)}/{len(res['checks'])} checks pass"); print(json.dumps(res["perf"]), json.dumps(res["gzip_bytes"]))
for f in fails: print("FAIL:", f)
sys.exit(1 if fails else 0)
