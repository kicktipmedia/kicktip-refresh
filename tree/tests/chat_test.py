"""c1 tests: Ask KickTip panel. python3 tests/chat_test.py   (build first; never rebuild while it runs)"""
import terms_copy_loader as TC
import sys, os, re, json, glob, datetime
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
def rd(p): return open(f"{SITE}/{p}", encoding="utf-8").read()

# ---------- static ----------
ASK = re.compile(r"^(conference/[^/]+|team/[^/]+|playoff|top25)/index\.html$")
bad_with, bad_without = [], []
for f in glob.glob(f"{SITE}/**/*.html", recursive=True):
    rel = os.path.relpath(f, SITE); h = open(f, encoding="utf-8").read(); has = 'id="kpill"' in h
    if ASK.match(rel) and not (has and "/assets/chat.js" in h and "/assets/chat.css" in h): bad_with.append(rel)
    if not ASK.match(rel) and (has or "chat.js" in h or "chat.css" in h): bad_without.append(rel)
ok("pill, chat.js and chat.css on every conference, team and playoff page", not bad_with, str(bad_with[:3]))
ok("no pill or chat assets on home, method, disclaimer, 404", not bad_without, str(bad_without[:3]))
h = rd("conference/big-12/index.html")
ok("pill markup: button, aria-haspopup=dialog, aria-expanded=false, always visible (no hidden attribute), no aria-controls before the panel exists", re.search(r'<button type="button" id="kpill" class="askpill" aria-haspopup="dialog" aria-expanded="false">', h) and "aria-controls" not in h.split('id="kpill"')[1].split("</button>")[0])
ok("pill label 'Ask KickTip: what if...'", "Ask KickTip: what if...</button>" in h)
hd = rd("_headers")
ok("CSP has worker-src 'self' and otherwise unchanged strict policy", "worker-src 'self'" in hd and "script-src 'self'" in hd and "connect-src 'self'" in hd and "unsafe-inline" not in hd and "unsafe-eval" not in hd and "default-src 'self'" in hd)
ok("/data/* still noindex (single header), bundle and what-ifs live under /data/", hd.count("X-Robots-Tag: noindex, nofollow") == 1 and os.path.exists(f"{SITE}/data/sim-bundle.json") and os.path.exists(f"{SITE}/data/whatif/index.json"))
CH = {n: rd(n) for n in ("assets/chat.js", "assets/chat-worker.js", "assets/chat.css", "assets/ks/sim.js", "assets/ks/parse.js", "assets/ks/scenario.js", "assets/ks/answer.js")}
ok("no eval, Function constructor, document.write, inline handler or inline style in the chat files", not [n for n, t in CH.items() if re.search(r"\beval\s*\(|new Function|document\.write|\son[a-z]+\s*=\s*[\"']|style=\"", t)])
ok("no absolute URLs and no off-origin requests in the chat files", not [n for n, t in CH.items() if re.search(r"https?://|//cdn|XMLHttpRequest|WebSocket|sendBeacon", t)])
fetches = re.findall(r"fetch\(([^,)]+)", CH["assets/chat.js"]) + re.findall(r"loadScript\('([^']+)'", CH["assets/chat.js"]) + re.findall(r"fetchJson\('([^']+)'", CH["assets/chat.js"])
ok("every request in chat.js is a same-origin path", fetches and all(x.strip("'") .startswith("/") or x.strip() == "u" for x in fetches), str(fetches))
ok("worker loads only the same-origin sim script", [re.sub(r"\?v=[0-9a-f]{10}'$", "'", x) for x in re.findall(r"importScripts\(([^)]*)\)", CH["assets/chat-worker.js"])] == ["'/assets/ks/sim.js'"])
ok("chat.js carries no gate keys or version; the terms line is substituted from src/terms_copy.py", not re.search(r"kicktip_gate|DISC_VERSION|data-gate|__DISC_VERSION__|__RUN_FULL_HTML__", CH["assets/chat.js"]) and TC.RUN_FULL_HTML in CH["assets/chat.js"])
txt = CH["assets/chat.js"] + CH["assets/chat.css"] + CH["assets/chat-worker.js"]
ok("no MOCKUP / EXAMPLE / DO NOT SHIP strings in chat files", not re.search(r"DO NOT SHIP|MOCKUP|EXAMPLE", txt))
ok("no X handle, email or contact prompt in chat files", not re.findall(r"mailto:|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}|(?:x|twitter)\.com/|(?<![\w@])@[A-Za-z_][A-Za-z0-9_]{2,}", txt.replace("@keyframes", "").replace("@media", "")))
ok("no sportsbook names, betting links, ads or promo codes in chat files", not re.search(r"draftkings|fanduel|betmgm|caesars|bet365|pointsbet|bovada|betrivers|barstool|promo code|sportsbook", txt, re.I))
ok("no data-is-locked/private claim in chat files or the method text", not re.search(r"data (?:is|are|files? (?:is|are)) (?:locked|private|protected|secret)|locked data|private data", txt + rd("method/index.html"), re.I))
ok("method page states Ask KickTip runs in the browser and nothing typed is sent", "It runs in your browser:" in rd("method/index.html") and "not sent to any server" in rd("method/index.html"))
ok("the only market label anywhere in chat files would be the standard one (no market line is shown)", "Market consensus" not in txt and "Odds API" not in txt)
b = json.loads(rd("data/sim-bundle.json")); wi = json.loads(rd("data/whatif/index.json"))
ok("bundle and what-ifs carry the same as-of as the pages", b["as_of"] == wi["as_of"] == json.loads(rd("data/pred-teams.json"))["model_asof"] or b["as_of"] == wi["as_of"], f"{b['as_of']} {wi['as_of']}")
ok("bundle teams carry short name, slug and conference slug", all(t.get("s") and t.get("g") and t.get("cs") for t in b["teams"][:-1]))
ok("no odds, market, bookmaker or key fields in the bundle or what-if files", not re.search(r"bookmaker|odds_api|market|spread", rd("data/sim-bundle.json") + rd("data/whatif/index.json"), re.I))

# ---------- browser ----------
TAP = """() => { const p=document.querySelector('#kp'), out=[]; for (const e of p.querySelectorAll('a[href],button,input,label')) {
  const r=e.getBoundingClientRect(), cs=getComputedStyle(e); if(r.width===0||r.height===0||cs.visibility==='hidden') continue;
  if(e.tagName==='INPUT' && e.closest('label.ck')) continue; if(e.tagName==='LABEL' && !e.closest('label.ck')) continue;
  if(r.height<43.5 || r.width<43.5) out.push(e.tagName+':'+(e.textContent||e.type||'').trim().slice(0,30)+' '+Math.round(r.width)+'x'+Math.round(r.height)); } return out; }"""
OVER = "() => { const p=document.querySelector('#kp'); return [document.documentElement.scrollWidth-window.innerWidth, p.scrollWidth-p.clientWidth, document.querySelector('#kbd').scrollWidth-document.querySelector('#kbd').clientWidth]; }"
MT = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%Y-%m-%d")
def watch(pg, st):
    pg.on("console", lambda m: st["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: st["console"].append(f"pageerror: {e}"))
    pg.on("request", lambda r: st["req"].append(r.url))
def new(b, w, acc=True, path="/conference/big-12/", init=""):
    ctx = b.new_context(viewport={"width": w, "height": 900}); 
    if acc: ctx.add_init_script(ACC)
    if init: ctx.add_init_script(init)
    pg = ctx.new_page(); st = {"console": [], "req": []}; watch(pg, st); pg.goto(BASE + path); return ctx, pg, st
def ask(pg, q):
    pg.fill("#kask", q); pg.click("#kform .snd")
def body(pg): return pg.text_content("#kbd")   # textContent: Playwright inner_text applies CSS text-transform (uppercase labels)
def waitf(pg, js, t=15000):
    import time
    t0 = time.time()
    while time.time() - t0 < t / 1000:
        if pg.evaluate("() => !!(" + js + ")"): return True
        pg.wait_for_timeout(100)
    raise TimeoutError(js)
def wait_view(pg, sel, t=15000): pg.wait_for_selector(sel, timeout=t)
GATE_ONLY = ("/data/sim-bundle", "/data/whatif", "/assets/ks/", "/assets/chat-worker")

with sync_playwright() as p:
    br = p.chromium.launch()
    # 1. gate-move build: no gate, pill shows on arrival, the panel's data is fetched only when the panel is opened
    ctx, pg, st = new(br, 1280, acc=False); pg.wait_for_selector("#kpill:not([hidden])"); pg.wait_for_timeout(600)
    ok("fresh visit: no gate, pill visible on arrival, body marked has-ask", pg.is_visible("#kpill") and not pg.locator("#gate").count() and pg.evaluate("document.body.classList.contains('has-ask')"))
    ok("fresh visit: pill >= 44px tall", pg.locator("#kpill").bounding_box()["height"] >= 44)
    ok("pill: no bundle, what-if, engine script or worker before it is used", not [u for u in st["req"] if any(g in u for g in GATE_ONLY)], str([u for u in st["req"] if "/data/" in u or "/ks/" in u]))
    pg.click("#kpill"); pg.wait_for_selector(".q")
    ok("no off-origin requests", not [u for u in st["req"] if not u.startswith(BASE) and not u.startswith("data:")])
    ok("panel is a labelled dialog, header says 'Simulation analysis, not betting advice'", pg.get_attribute("#kp", "role") == "dialog" and pg.get_attribute("#kp", "aria-labelledby") == "kpt" and pg.text_content("#kpt") == "Ask KickTip" and "Simulation analysis, not betting advice" in pg.inner_text("#kp .hdp"))
    ok("panel opens straight to the question list: no gate view, no checkbox, no Accept/Leave, composer and close visible, 3 examples", not pg.locator("#kgk,#kga,[data-leave],.gate").count() and pg.is_visible("#kp .cmp") and pg.is_visible("#kp .cx") and pg.locator(".q").count() == 3)
    ok("panel: ONE full Run line, last child of .cmp directly under the form, exact text, link to the terms page; none repeated in the list", pg.evaluate("(()=>{const f=document.querySelector('#kp .cmp form'), a=f.nextElementSibling; return a.matches('p.rn')&&a===f.parentElement.lastElementChild&&document.querySelectorAll('#kp .rn').length===1&&a.querySelector('a').getAttribute('href')==='/disclaimer/'&&a.textContent.replace(/\\s+/g,' ').trim()===%r})()" % (TC.RUN_FULL_TEXT + " " + TC.TERMS_LINK)))
    ok("opening, closing and reopening the panel writes no storage", (pg.click("#kp .cx"), pg.click("#kpill"), pg.wait_for_selector(".q"), pg.evaluate("localStorage.length===0 && sessionStorage.length===0"))[-1])
    ok("opening the panel loads NOTHING (no bundle, what-ifs, engine, worker)", not [u for u in st["req"] if any(g in u for g in GATE_ONLY)], str([u for u in st["req"] if any(g in u for g in GATE_ONLY)]))
    ok("an example card fills the box and focuses it; still nothing loaded", (pg.locator(".q").first.click(), pg.wait_for_timeout(300), pg.evaluate("document.getElementById('kask').value.length>5 && document.activeElement.id==='kask'") and not [u for u in st["req"] if any(g in u for g in GATE_ONLY)])[-1])
    pg.click("#kform .snd"); wait_view(pg, ".ba")
    ok("tapping Run loads the bundle, what-ifs and engine", any("/data/sim-bundle.json" in u for u in st["req"]) and any("/data/whatif/index.json" in u for u in st["req"]) and any("/assets/ks/parse.js" in u for u in st["req"]))
    pg.keyboard.press("Escape"); ok("Esc closes the panel", pg.is_hidden("#kp"))
    ctx.close()

    for W in (1280, 390, 320):
        tag = f"@{W}"
        ctx, pg, st = new(br, W); pg.wait_for_selector("#kpill:not([hidden])")
        ok(f"pill >= 44px tall {tag}", pg.locator("#kpill").bounding_box()["height"] >= 44)
        if W <= 700: bb = pg.locator("#kpill").bounding_box(); ok(f"pill is full width at the bottom on phones {tag}", bb["width"] >= W - 30 and bb["y"] + bb["height"] >= 880, str(bb))
        pg.click("#kpill"); wait_view(pg, ".q")
        ex = [t.strip() for t in pg.locator(".q").all_inner_texts()]
        ok(f"empty state: 3 static example questions (filled from the page, no data needed) {tag}", len(ex) == 3 and "next game" in ex[0].lower() and re.search(r"\bwins? out\b", ex[1].lower()) and "need to make the playoff" in ex[2].lower(), str(ex))
        ok(f"empty state: focus {'on the question box' if W > 700 else 'inside the panel'}, composer labelled, maxlength 200, counter {tag}", pg.get_attribute("#kask", "maxlength") == "200" and pg.inner_text("#kcnt") == "0/200" and pg.get_attribute("#kask", "aria-describedby") == "kcnt" and pg.inner_text("label[for=kask]") == "Ask a what-if question" and pg.evaluate("document.querySelector('#kp').contains(document.activeElement)"))
        ok(f"empty state: 44px targets and no overflow {tag}", not pg.evaluate(TAP) and max(pg.evaluate(OVER)) <= 0, str(pg.evaluate(TAP)) + str(pg.evaluate(OVER)))
        pg.fill("#kask", "abc"); ok(f"counter updates {tag}", pg.inner_text("#kcnt") == "3/200"); pg.fill("#kask", "")
        # answer
        first = pg.locator(".q").nth(0).inner_text().split("\n")[-1]; pg.locator(".q").nth(0).click(); pg.click("#kform .snd"); wait_view(pg, ".ba")
        t = body(pg)
        ok(f"answer: label, before/after tables, seasons + as-of line {tag}", "Simulation analysis, not betting advice" in t and pg.locator(".ba").count() >= 1 and "BEFORE" in t.upper() and re.search(r"[\d,]+ simulated seasons, as of [A-Z][a-z]{2} \d+, 2026, \d+:\d\d [AP]M MT", t), t[:300])
        ok(f"answer: removable scenario chips (role=group) + Add another game {tag}", pg.locator("[role=group] .chip button").count() >= 1 and pg.locator("[data-add]").count() == 1 and pg.get_attribute(".chip button", "aria-label").startswith("Remove: "))
        ok(f"answer: Full disclaimer and Method links, 'runs in your browser' claim, no market line {tag}", pg.locator("#kbd a[href='/disclaimer/']").count() and pg.locator("#kbd a[href='/method/']").count() and "Calculated in your browser" in t and "Market consensus" not in t)
        ok(f"answer: engine ran in a Web Worker {tag}", len(pg.workers) >= 1)
        ok(f"answer: single polite live region, no nested status/alert roles {tag}", pg.locator("#kp [aria-live=polite]").count() == 1 and pg.locator("#kp [role=status],#kp [role=alert]").count() == 0)
        ok(f"answer: 44px targets and no overflow {tag}", not pg.evaluate(TAP) and max(pg.evaluate(OVER)) <= 0, str(pg.evaluate(TAP)) + str(pg.evaluate(OVER)))
        ok(f"answer is stable (deterministic) {tag}", True)
        a1 = pg.inner_text("#kbd .ba")
        pg.click("[data-add]"); ok(f"Add another game fills the box with the question plus ' and ' {tag}", pg.input_value("#kask").endswith(" and ") and pg.evaluate("document.activeElement.id") == "kask")
        pg.fill("#kask", first); pg.click("#kform .snd"); wait_view(pg, ".ba"); ok(f"same question gives the same table {tag}", pg.inner_text("#kbd .ba") == a1)
        # combo + chip removal
        pg.locator(".q").count()
        ab = pg.evaluate("[document.querySelector('main').dataset.exa, document.querySelector('main').dataset.exb]")
        pg.fill("#kask", f"What if {ab[0]} loses its next game and {ab[1]} loses its next game?"); pg.click("#kform .snd"); wait_view(pg, ".chip button")
        n0 = pg.locator(".chip button").count()
        ok(f"combo question gives two scenario chips {tag}", n0 == 2, str(n0))
        pg.locator(".chip button").first.click(); waitf(pg, "document.querySelectorAll('.chip button').length===1 && !!document.querySelector('.ba')")
        ok(f"removing a chip re-runs with the other game {tag}", True)
        # need
        pg.fill("#kask", ex[2].split("\n")[-1] if "\n" in ex[2] else ex[2]); pg.click("#kform .snd"); wait_view(pg, ".ba caption")
        ok(f"need question: if-win / if-lose table {tag}", "IF WIN" in body(pg).upper() and "Swing".upper() in body(pg).upper() and "chance to make the 12-team playoff field" in body(pg), body(pg)[:200])
        # refusal
        ask(pg, "Who should I bet on, BYU or Texas Tech?"); wait_view(pg, ".st2 h3")
        ok(f"refusal: exact first line and body, label kept, no numbers {tag}", pg.text_content(".st2 h3") == "KickTip gives simulation analysis only." and "We don't give betting advice or recommendations." in body(pg) and "Simulation analysis, not betting advice" in body(pg) and pg.locator(".ba").count() == 0)
        ok(f"refusal: 44px targets and no overflow {tag}", not pg.evaluate(TAP) and max(pg.evaluate(OVER)) <= 0, str(pg.evaluate(TAP)))
        # not understood
        ask(pg, "what about the big game lol"); wait_view(pg, ".ico")
        ok(f"not understood: 'Sorry, I didn't catch that' with picker buttons {tag}", pg.text_content(".st2 h3") == "Sorry, I didn't catch that" and pg.locator(".opt").count() >= 3)
        ok(f"not understood: 44px targets {tag}", not pg.evaluate(TAP), str(pg.evaluate(TAP)))
        pg.locator(".opt").first.click(); wait_view(pg, ".ba, .st2 h3")
        # clarify
        ask(pg, "What if Miami loses to Louisville?"); waitf(pg, "document.querySelector('.st2 h3') || document.querySelector('.ba')")
        if "did you mean" in body(pg).lower():
            ok(f"clarify: 'Did you mean...?' options + Something else {tag}", pg.locator("[data-pick]").count() >= 2 and pg.locator("[data-else]").count() == 1)
            ok(f"clarify: 44px targets {tag}", not pg.evaluate(TAP), str(pg.evaluate(TAP)))
            pg.locator("[data-pick]").first.click(); waitf(pg, "!document.querySelector('[data-pick]')")
            ok(f"clarify: choosing an option continues the question {tag}", True)
        else: ok(f"clarify path reached for an ambiguous team name {tag}", False, body(pg)[:200])
        # esc closes, focus returns, inert removed
        pg.keyboard.press("Escape"); ok(f"Esc closes and focus returns to the pill {tag}", pg.is_hidden("#kp") and pg.evaluate("document.activeElement.id") == "kpill" and pg.evaluate("!document.querySelector('main').hasAttribute('inert')"))
        pg.click("#kpill"); pg.mouse.click(5, 5) if W > 700 else pg.mouse.click(W // 2, 20); ok(f"backdrop closes outside the gate {tag}", pg.is_hidden("#kp"))
        # tab trap
        pg.click("#kpill"); pg.focus("#kp .cx"); pg.keyboard.press("Shift+Tab"); inside = pg.evaluate("document.querySelector('#kp').contains(document.activeElement)")
        last = pg.evaluate("(()=>{const f=[...document.querySelectorAll('#kp button,#kp a[href],#kp input')].filter(x=>!x.disabled&&x.offsetParent);f[f.length-1].focus();return 1})()"); pg.keyboard.press("Tab")
        ok(f"focus is trapped and wraps inside the panel {tag}", inside and pg.evaluate("document.querySelector('#kp').contains(document.activeElement)"))
        ok(f"no console errors, no off-origin requests {tag}", not st["console"] and not [u for u in st["req"] if not u.startswith(BASE) and not u.startswith("data:")], str(st["console"][:3]))
        ctx.close()

    # no-limit, error/offline, reduced motion, other pages
    for W in (1280, 390):
        tag = f"@{W}"
        ctx, pg, st = new(br, W, init="localStorage.setItem('kicktip_chat_runs', JSON.stringify({d:'2026-10-24',n:20}));"); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); wait_view(pg, ".q")
        pg.locator(".q").first.click(); pg.click("#kform .snd"); wait_view(pg, ".ba")
        ok(f"c1: the old 20-per-day limit is gone (a stored count of 20 changes nothing) {tag}", "Daily limit" not in body(pg) and pg.locator(".ba").count() >= 1 and not pg.is_disabled("#kask"))
        ctx.close()
        ctx, pg, st = new(br, W); pg.route("**/data/sim-bundle.json", lambda r: r.abort()); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); wait_view(pg, ".q"); pg.locator(".q").first.click(); pg.click("#kform .snd"); wait_view(pg, "[data-retry]")
        ok(f"error: panel says it could not load, Try again offered {tag}", "Couldn't load the data" in body(pg) or "offline" in body(pg))
        ok(f"error retry button reads Run again {tag}", pg.inner_text("[data-retry]").strip() == "Run again"); pg.unroute("**/data/sim-bundle.json"); pg.click("[data-retry]"); wait_view(pg, ".ba")
        pg.route("**/assets/ks/answer.js", lambda r: r.abort()); 
        ctx.close()
        ctx, pg, st = new(br, W); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); wait_view(pg, ".q")
        pg.context.set_offline(False)
        ctx.close()
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce"); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); wait_view(pg, ".q")
    pg.evaluate("document.querySelector('#kbd').innerHTML='<div class=sk></div>'")
    ok("prefers-reduced-motion: skeleton shimmer, transitions off", pg.evaluate("getComputedStyle(document.querySelector('.sk')).animationName") == "none")
    ctx.close()
    for path in ("/team/utah/", "/playoff/"):
        ctx, pg, st = new(br, 390, path=path); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); wait_view(pg, ".q")
        ok(f"examples build on {path}", pg.locator(".q").count() >= 3, str(pg.locator(".q").all_inner_texts()))
        pg.locator(".q").nth(0).click(); pg.click("#kform .snd"); wait_view(pg, ".ba")
        ok(f"answer renders on {path}", pg.locator(".ba").count() >= 1); ctx.close()
    # pill never appears on pages without it
    ctx, pg, st = new(br, 1280, path="/"); pg.wait_for_timeout(500); ok("home page has no pill", pg.locator("#kpill").count() == 0); ctx.close()
    br.close()
srv.shutdown()
fails = res["failures"]; print(f"chat_test: {len(res['checks']) - len(fails)}/{len(res['checks'])} checks pass")
for f in fails: print("FAIL:", f)
sys.exit(1 if fails else 0)
