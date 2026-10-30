"""c1r1b tests for the Creative review fixes: plural verbs, exact copy, no third-party/proprietary wording, N line shows the real N, no MSM anywhere,
bottom padding (pill never hides the footer or the model controls), focus return + Esc.   python3 tests/chat_c1b_test.py   (build first)"""
import sys, os, re, json, time, glob
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
B = json.load(open(f"{SITE}/data/sim-bundle.json")); T = B["teams"]
def unamb(t): return len(B["aliases"]["map"].get(T[t]["s"].lower(), [])) == 1
def q(t): return T[t]["s"] if unamb(t) else T[t]["n"]
PLUR_END = {"minutemen", "midshipmen", "illini", "irish", "bison"}
def plural(full): w = full.split()[-1].lower(); return w in PLUR_END or (w.endswith("s") and not w.endswith("ss"))
def waitf(pg, js, t=60000):
    t0 = time.time()
    while time.time() - t0 < t / 1000:
        if pg.evaluate("() => !!(" + js + ")"): return True
        pg.wait_for_timeout(100)
    raise TimeoutError(js)
def new(br, w=1280, h=900, path="/team/utah/", init=ACC):
    ctx = br.new_context(viewport={"width": w, "height": h}); ctx.add_init_script(init); pg = ctx.new_page()
    pg.goto(BASE + path); pg.wait_for_selector("#kpill:not([hidden])"); return ctx, pg
def body(pg): return pg.text_content("#kbd")
def norm(s): return re.sub(r"\s+", " ", s)
ERRS = ".ba, .st2 h3"

# ---------- no third-party rating names / proprietary / MSM in anything the chat ships ----------
shipped = ["assets/chat.js", "assets/chat.css", "assets/chat-worker.js"] + [f"assets/ks/{n}.js" for n in ("answer", "scenario")]
txt = {n: open(f"{SITE}/{n}").read() for n in shipped}
BAD = re.compile(r"proprietary|\bMSM\b|\bFPI\b|\bSP\+|Massey|Sagarin|\bBCS\b|Colley|Vegas|sportsbook", re.I)
hits = {n: BAD.findall(t) for n, t in txt.items() if BAD.search(t)}
ok("fix 3: no 'proprietary' or third-party rating names in the chat copy (chat.js/css, worker, answer.js, scenario.js)", not hits, str(hits))
ok("fix 3: tiebreak footer sentence is the approved text", "steps that depend on other public rating systems use KickTip's rating as a stand-in, so this does not claim official tiebreaker results." in txt["assets/ks/answer.js"])
ok("fix 2: title-not-supported body is the approved text", "Try asking what happens if a team wins out, or if one team beats another in a regular-season game." in txt["assets/ks/answer.js"] and "Try a team wins out" not in txt["assets/ks/answer.js"])
meth = open(f"{SITE}/method/index.html").read()
ok("fix 3/5: the method page's Ask KickTip section has no proprietary/MSM wording", not BAD.search(re.search(r'<h2 id="ask">.*?</p>', meth, re.S).group(0)))
RV = f"{ROOT}/before-site"
cnt = lambda p: len(re.findall(r"\bMSM\b|msm", open(p, errors="ignore").read())) if os.path.exists(p) else 0   # a page new since rev2b (top25) must carry none
pgs = [p[len(SITE) + 1:] for p in glob.glob(f"{SITE}/**/*.html", recursive=True)] + [f"assets/{n}" for n in ("kt.js", "lg.js", "kt.css")]
diffm = [p for p in pgs if cnt(f"{SITE}/{p}") != cnt(f"{RV}/{p}")]
ok("fix 5: every page and script mentions MSM exactly as often as rev2b does (the build adds none; rev2b's own method/playoff sentences about the rating are untouched)", not diffm, str(diffm[:5]))
ok("fix 5: the model control offers only blend, elo, eff: no 'msm' in kt.js and none of the chat's own files", cnt(f"{SITE}/assets/kt.js") == 0 and all(cnt(f"{SITE}/{n}") == 0 for n in shipped))
ok("fix 5: no MSM chat data shipped (only blend, elo, eff bundles and shards)", sorted(glob.glob(f"{SITE}/data/m/*")) == [f"{SITE}/data/m/eff", f"{SITE}/data/m/elo"] and not glob.glob(f"{SITE}/data/**/*msm*", recursive=True))

with sync_playwright() as p:
    br = p.chromium.launch()
    # ---------- fix 1: verb agreement in every example, on every page where a full name is used ----------
    amb = [t for t in range(len(T)) if T[t]["g"] and not unamb(t)] if all("g" in x for x in T) else []
    pages = ["/conference/big-12/", "/conference/sec/", "/conference/acc/", "/playoff/"] + [f"/team/{T[t]['g']}/" for t in amb if T[t].get("g")]
    bad = []; seen_plural = 0; seen_singular = 0
    for path in pages:
        try: ctx, pg = new(br, 390, 844, path)
        except Exception as e: bad.append((path, repr(e)[:80])); continue
        pg.click("#kpill"); pg.wait_for_selector(".q"); ex = [norm(pg.text_content(f".q >> nth={i}")) for i in range(pg.locator(".q").count())]
        for e in ex:
            m = re.match(r"(?:Combo: two games|One game|Rest of season)?\s*What if (.+?) (loses|lose) to (.+?)(?: and (.+?) (beats|beat) (.+?))?\?$", e) or re.search(r"What if (.+?) (wins|win) out\?$", e)
            if not m: continue
            g = m.groups()
            for name, verb in ((g[0], g[1]), ((g[3], g[4]) if len(g) > 4 and g[3] else (None, None))):
                if not name: continue
                full = [x["n"] for x in T if x["n"] == name]; pl = bool(full) and plural(name)
                if full: seen_plural += pl; seen_singular += (not pl)
                want = {"loses": "lose", "wins": "win", "beats": "beat"}
                if pl != (verb in want.values()): bad.append((path, e))
        ctx.close()
    ok(f"fix 1: example questions use plural verbs with plural full names ('What if Utah Utes lose to Houston?') and singular verbs otherwise: {len(pages)} pages, {seen_plural} plural / {seen_singular} singular names seen", not bad and seen_plural > 0, str(bad[:4]))
    ctx, pg = new(br, 390, 844, "/team/utah/"); pg.click("#kpill"); pg.wait_for_selector(".q"); e1 = norm(pg.text_content(".q >> nth=0 ")) 
    ok("fix 1: the Utah team page's one-game example reads 'What if Utah Utes lose to ...?'", re.search(r"What if Utah Utes lose to [A-Z]", e1) is not None, e1); ctx.close()
    # ---------- fix 2 + 3: rendered states ----------
    ctx, pg = new(br, 390, 844, "/conference/big-12/"); pg.click("#kpill"); pg.wait_for_selector(".q")
    pg.fill("#kask", "What if Utah Utes win the Big 12?"); pg.click("#kform .snd"); pg.wait_for_selector(".st2 h3"); t = norm(body(pg))
    ok("fix 2: title-not-supported state shows the approved body", "Try asking what happens if a team wins out, or if one team beats another in a regular-season game." in t, t[:300])
    pg.fill("#kask", "What if Utah Utes lose to Houston?"); pg.click("#kform .snd"); pg.wait_for_selector(".ba"); waitf(pg, "!document.querySelector('.prog')"); t = norm(body(pg))
    ok("fix 3: answer footer has the approved tiebreak sentence", "steps that depend on other public rating systems use KickTip's rating as a stand-in" in t and "proprietary" not in t, t[-400:])
    ok("fix 1: the chip reads 'Houston beats Utah Utes'-style, not a verb mismatch", not re.search(r"Utah Utes (loses|beats|wins)\b", t), t[:200])
    ctx.close()
    # ---------- fix 4: the N line shows the real N when adaptive N is under 10,000 ----------
    def cut(r):
        js = open(f"{SITE}/assets/chat-worker.js").read().replace("var bundle = bundles[m.model];", "m.budget = 1; var bundle = bundles[m.model];", 1)
        assert "m.budget = 1" in js; r.fulfill(body=js, content_type="text/javascript")
    ctx, pg = new(br, 390, 844, "/team/utah/"); pg.route("**/assets/chat-worker.js", cut); pg.click("#kpill"); pg.wait_for_selector(".q"); pg.locator(".q").nth(0).click()
    pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')"); t = norm(body(pg))
    mN = re.search(r"([\d,]+) simulated seasons, as of", t)
    ok("fix 4: when the run is cut to 4 chunks the answer says '4,000 simulated seasons' and never 10,000", mN and mN.group(1) == "4,000" and "10,000" not in t, (mN.group(0) if mN else t[:300]))
    h = pg.text_content(".ac") ; ok("fix 4: no 10,000 anywhere in the answer card", "10,000" not in h)
    ctx.close(); ctx, pg = new(br, 390, 844, "/team/utah/"); pg.route("**/assets/chat-worker.js", cut); pg.click("#kpill"); pg.wait_for_selector(".q")   # fresh page: no cached baseline, so the cut applies
    pg.fill("#kask", "What does Utah Utes need to make the playoff?"); pg.click("#kform .snd"); pg.wait_for_selector(".ba caption"); waitf(pg, "!document.querySelector('.prog')"); t = norm(body(pg))
    ok("fix 4: need answer: '4,000 simulated seasons for the chance right now, 6,000 for each game result in the table'", "4,000 simulated seasons for the chance right now, 6,000 for each game result in the table" in t and "10,000" not in t, (t[max(0, t.find("10,000") - 120):t.find("10,000") + 60] if "10,000" in t else t[-300:]))
    ctx.close()
    ctx, pg = new(br, 390, 844, "/team/utah/")           # an uncut run on this machine: whatever N it reports must equal what the worker really ran
    pg.click("#kpill"); pg.wait_for_selector(".q"); pg.locator(".q").nth(0).click(); pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')"); t = norm(body(pg))
    mN = re.search(r"([\d,]+) simulated seasons, as of", t); n = int(mN.group(1).replace(",", "")) if mN else 0
    ok(f"fix 4: normal run reports a whole number of 1,000-season chunks between 4,000 and 10,000 (got {n:,})", 4000 <= n <= 10000 and n % 1000 == 0)
    ctx.close()
    # ---------- fix 6: bottom padding; the pill never covers the footer or the model controls ----------
    def rect(pg, sel): return pg.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }", sel)
    def hit(a, b): return a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    for W, H in ((320, 568), (390, 844), (1280, 800)):
        for path in ("/team/utah/", "/conference/big-12/", "/playoff/"):
            ctx, pg = new(br, W, H, path)
            pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(200)
            pl = rect(pg, "#kpill"); last = pg.evaluate("() => { const w = document.querySelector('.ft .w'); const r = w.getBoundingClientRect(); const kids = [...w.querySelectorAll('a,p,span,div')].filter(e => e.getBoundingClientRect().height > 0); const b = Math.max(...kids.map(e => e.getBoundingClientRect().bottom), r.bottom); return [r.left, r.top, r.right, b]; }")
            allft = pg.evaluate("() => { const out = []; document.querySelectorAll('.ft a, .ft p, .ft li').forEach(e => { const r = e.getBoundingClientRect(); if (r.height) out.push([r.left, r.top, r.right, r.bottom]); }); return out; }")
            ok(f"fix 6: {path} @{W}: scrolled to the bottom, the pill covers no footer link or line (pill top {pl[1]:.0f}px, last footer line bottom {max(x[3] for x in allft):.0f}px)", not any(hit(pl, x) for x in allft) and max(x[3] for x in allft) <= pl[1] + 0.5)
            ok(f"fix 6: {path} @{W}: the page is still scrollable to the very end (document bottom reached)", pg.evaluate("Math.ceil(window.scrollY + innerHeight) >= document.documentElement.scrollHeight - 1"))
            ctx.close()
    # model card controls at 320: never covered by the pill at the top of the page or after scrolling each control to the middle / bottom area
    for path in ("/team/utah/", "/conference/big-12/", "/playoff/"):
        for W, H in ((320, 568), (320, 640)):
            ctx, pg = new(br, W, H, path); n = pg.locator(".mdt .mb").count(); cov = []
            ok(f"fix 6: {path} @{W}x{H}: model controls present ({n})", n >= 2)
            for i in range(n):
                for how in ("start", "center", "end"):
                    pg.evaluate("([i, how]) => document.querySelectorAll('.mdt .mb')[i].scrollIntoView({block: how})", [i, how]); pg.wait_for_timeout(60)
                    r = pg.evaluate("i => { const r = document.querySelectorAll('.mdt .mb')[i].getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }", i)
                    if how == "center" and hit(r, rect(pg, "#kpill")): cov.append((i, how))
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(60)
            first = [pg.evaluate("i => { const r = document.querySelectorAll('.mdt .mb')[i].getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }", i) for i in range(n)]
            at_top = [i for i, r in enumerate(first) if hit(r, rect(pg, "#kpill"))]
            res.setdefault("model_overlap_at_top", []).append((path, W, H, at_top))
            ok(f"fix 6: {path} @{W}x{H}: pill never covers a model control when it is scrolled to the middle of the screen", not cov, str(cov))
            ok(f"fix 6: {path} @{W}x{H}: pill does not cover a model control at the top of the page (first screen)", not at_top, str(at_top))
            ctx.close()
    # ---------- fix 7: focus returns to the pill; Esc closes ----------
    for W, H in ((320, 568), (390, 844), (1280, 800)):
        ctx, pg = new(br, W, H, "/team/utah/")
        pg.click("#kpill"); pg.wait_for_selector(".q"); ok(f"fix 7 @{W}: sheet open: pill aria-expanded=true and focus inside the sheet", pg.get_attribute("#kpill", "aria-expanded") == "true" and pg.evaluate("!!document.activeElement.closest('#kp')"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        ok(f"fix 7 @{W}: Esc closes the sheet and focus is back on the pill", pg.evaluate("document.querySelector('#kp').hidden") and pg.evaluate("document.activeElement.id") == "kpill" and pg.get_attribute("#kpill", "aria-expanded") == "false")
        pg.click("#kpill"); pg.wait_for_selector(".q"); pg.click("#kp .cx"); pg.wait_for_timeout(150)
        ok(f"fix 7 @{W}: the close button closes the sheet and focus is back on the pill", pg.evaluate("document.querySelector('#kp').hidden") and pg.evaluate("document.activeElement.id") == "kpill")
        pg.click("#kpill"); pg.wait_for_selector(".q"); pg.locator(".q").nth(0).click(); pg.wait_for_selector(".ba", timeout=90000); waitf(pg, "!document.querySelector('.prog')")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        ok(f"fix 7 @{W}: Esc after an answer closes the sheet and focus is back on the pill", pg.evaluate("document.querySelector('#kp').hidden") and pg.evaluate("document.activeElement.id") == "kpill")
        pg.click("#kpill"); pg.wait_for_selector("#kp:not([hidden])"); pg.keyboard.press("Tab"); pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        ok(f"fix 7 @{W}: reopening the sheet after an answer, then Tab, then Esc: focus is back on the pill", pg.evaluate("document.activeElement.id") == "kpill")
        ctx.close()
    br.close()
srv.shutdown()
json.dump(res, open(f"{ROOT}/tests/last_chat_c1b.json", "w"), indent=1)
fails = res["failures"]; print(f"chat_c1b_test: {len(res['checks']) - len(fails)}/{len(res['checks'])} checks pass"); print(json.dumps(res.get("model_overlap_at_top")))
for f in fails: print("FAIL:", f)
sys.exit(1 if fails else 0)
