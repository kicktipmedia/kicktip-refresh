"""Shield spinner checks (Ask panel Run button + running card). python3 tests/shield_test.py -> tests/last_shield_test.json"""
import sys, os, re, json, glob, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
res = {"checks": 0, "failures": []}
def ok(name, cond, detail=""):
    res["checks"] += 1
    if not cond: res["failures"].append(f"{name} {detail}"); print("FAIL", name, str(detail)[:300])
D = "M139 14L257 58V130C257 154 259 180 256 200C252 220 246 232 236 248C226 264 210 284 198 296C186 308 174 315 164 322C154 329 146 335 139 339C132 335 124 329 114 322C104 315 92 308 80 296C68 284 52 264 42 248C32 232 26 220 22 200C19 180 21 154 21 130V58Z"
js = open(f"{SITE}/assets/chat.js", encoding="utf-8").read(); css = open(f"{SITE}/assets/chat.css", encoding="utf-8").read()
ok("static: Creative's exact path in chat.js, twice (track + moving stroke), viewBox 0 0 278 355, pathLength=1", js.count(D) == 2 and 'viewBox="0 0 278 355"' in js and js.count('pathLength="1"') == 2)
hub = "/workspace/hub/kicktip-shield-spinner/shield-spinner.svg"
if os.path.exists(hub): ok("static: path identical to Creative's shield-spinner.svg", D in open(hub).read())
ok("static: no inline style attribute and no <style> in the spinner markup", not re.search(r"<svg[^>]*style=|<style", js))
ok("static: keyframes as specified (1.8s, dasharray 1 1.01, 44%/62% holds, -1 end, cubic-bezier .45,0,.25,1)", all(x in css for x in ("animation:kshTrace 1.8s linear infinite", "stroke-dasharray:1 1.01", "44%{stroke-dashoffset:0}", "62%{stroke-dashoffset:0;", "100%{stroke-dashoffset:-1}", "cubic-bezier(.45,0,.25,1)")))
ok("static: no non-scaling-stroke; stroke-width 28 (button) and 11 (card); track #4C5560, moving #33E1EA", "non-scaling" not in css and "stroke-width:28px" in css and "stroke-width:11px" in css and "#4C5560" in css and "#33E1EA" in css)
ok("static: reduced-motion rule leaves a steady closed shield; forced-colors uses CanvasText/GrayText", ".ksm{stroke-dashoffset:0!important}" in css and "CanvasText" in css and "GrayText" in css)
ok("static: caption 'Running your scenario' as plain text (no role; announced once by the polite live region #kbd); button label 'Running\\u2026'", '<p class="spcap">Running your scenario</p>' in js and 'role="status"' not in js.split("var SPINCARD")[1].split(";")[0] and "Running\\u2026" in js)
bad = [f for f in glob.glob(f"{SITE}/**/*.html", recursive=True) if 'id="kpill"' in open(f, encoding="utf-8").read() and not all(t in open(f, encoding="utf-8").read() for t in ("chat.js?v=" + hashlib.sha256(open(f"{SITE}/assets/chat.js", "rb").read()).hexdigest()[:10], "chat.css?v=" + hashlib.sha256(open(f"{SITE}/assets/chat.css", "rb").read()).hexdigest()[:10]))]
ok("static: every Ask page loads chat.js and chat.css with their content-hash tokens", not bad, bad[:3])
srv, BASE = serve.start()
Q = "What if BYU loses?"
BOX = "(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.width*10)/10, Math.round(r.height*10)/10]; }"
SETT = "(t) => { document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; }); return parseFloat(getComputedStyle(document.querySelector('.ksm')).strokeDashoffset); }"
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        for path in ("/playoff/", "/top25/"):
            ctx = b.new_context(viewport={"width": w, "height": 820}); pg = ctx.new_page(); held = []; pg.route("**/data/sim-bundle.json", lambda r: held.append(r))
            pg.goto(BASE + path); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector("#kask"); pg.wait_for_timeout(250)
            pg.fill("#kask", Q); idle = pg.evaluate(BOX, "#kform .snd"); iin = pg.evaluate(BOX, "#kask")
            ok(f"{path}@{w}: idle button reads Run, graphite, no spinner", pg.inner_text("#kform .snd") == "Run" and not pg.query_selector("#kform .snd .kshd") and pg.evaluate("getComputedStyle(document.querySelector('#kform .snd')).backgroundColor") == "rgb(38, 43, 49)")
            pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(120)
            r = pg.evaluate("(() => { const s = document.querySelector('#kform .snd'); return { t: s.textContent.trim(), busy: s.getAttribute('aria-busy'), ad: s.getAttribute('aria-disabled'), dis: s.disabled, cls: s.className, bg: getComputedStyle(s).backgroundColor, col: getComputedStyle(s).color, hid: s.querySelector('svg').getAttribute('aria-hidden'), h: s.querySelector('svg').getBoundingClientRect().height } })()")
            ok(f"{path}@{w}: running button: 'Running\u2026', aria-busy, aria-disabled, NOT disabled, still graphite with white text, shield 24px aria-hidden", r["t"] == "Running\u2026" and r["busy"] == "true" and r["ad"] == "true" and not r["dis"] and r["bg"] == "rgb(38, 43, 49)" and r["col"] == "rgb(255, 255, 255)" and r["hid"] == "true" and abs(r["h"] - 24) < 0.6, r)
            run = pg.evaluate(BOX, "#kform .snd"); rin = pg.evaluate(BOX, "#kask")
            ok(f"{path}@{w}: no layout shift when the label swaps (button {idle} -> {run}; box {iin} -> {rin})", idle == run and iin == rin, (idle, run, iin, rin))
            pg.fill("#kask", "What if Utah loses?"); pg.click("#kform .snd", force=True); pg.wait_for_timeout(200)
            ok(f"{path}@{w}: clicking Run while running does nothing (text kept, still one running card)", pg.input_value("#kask") == "What if Utah loses?" and pg.locator(".spin").count() == 1 and pg.locator(".ub").count() == 1)
            c = pg.evaluate("(() => { const m = document.querySelector('.ksm'), t = document.querySelector('.kst'), cs = getComputedStyle(m), sp = document.querySelector('.spin'); const big = sp.querySelector('svg'); return { an: cs.animationName, du: cs.animationDuration, it: cs.animationIterationCount, da: cs.strokeDasharray, sw: getComputedStyle(sp.querySelector('.ksm')).strokeWidth, swb: getComputedStyle(document.querySelector('#kform .ksm')).strokeWidth, col: cs.stroke, tr: getComputedStyle(t).stroke, ov: getComputedStyle(big).overflow, h: big.getBoundingClientRect().height, cap: sp.querySelector('.spcap').textContent, role: sp.querySelector('.spcap').getAttribute('role'), live: !!sp.closest('#kbd[aria-live=polite]'), anyrole: !!sp.querySelector('[role=status],[aria-live]'), capc: getComputedStyle(sp.querySelector('.spcap')).color, bg: getComputedStyle(sp).backgroundColor, ds: document.querySelectorAll('.spin svg, #kform svg').length, st: document.querySelectorAll('svg[style]').length } })()")
            ok(f"{path}@{w}: card shield 96px, stroke 11 (button 28), cyan on #4C5560 track, 1.8s infinite kshTrace, dasharray 1 1.01, overflow visible, caption plain text without role, inside the polite live region, ink panel, no inline style", c["an"] == "kshTrace" and c["du"] == "1.8s" and c["it"] == "infinite" and c["sw"] == "11px" and c["swb"] == "28px" and abs(c["h"] - 96) < 0.6 and c["col"] == "rgb(51, 225, 234)" and c["tr"] == "rgb(76, 85, 96)" and c["ov"] == "visible" and c["cap"] == "Running your scenario" and c["role"] is None and c["live"] and not c["anyrole"] and c["capc"] == "rgb(213, 219, 224)" and c["bg"] == "rgb(18, 21, 25)" and c["ds"] == 2 and c["st"] == 0, c)
            o = {t: pg.evaluate(SETT, t) for t in (0, 400, 850, 1000, 1100, 1500, 1790)}
            ok(f"{path}@{w}: motion: nothing drawn at 0, tracing at .4s, closed through the hold (.85s-1.1s), un-tracing after, erased at 1.79s {o}", o[0] > 0.98 and 0.05 < o[400] < 0.95 and o[850] == 0 and o[1000] == 0 and o[1100] <= 0.001 and -0.95 < o[1500] < -0.05 and o[1790] < -0.97, o)
            ctx.close()
    # result arrives: spinner gone, Run back, next question works; reduced motion steady shield
    ctx = b.new_context(viewport={"width": 390, "height": 820}); pg = ctx.new_page(); pg.goto(BASE + "/playoff/"); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector("#kask"); pg.fill("#kask", Q); pg.click("#kform .snd")
    pg.wait_for_selector(".ba", timeout=90000); pg.wait_for_function("!document.querySelector('.prog')", timeout=90000); pg.wait_for_timeout(300)
    ok("result: spinner and Running state are gone, button back to 'Run' (disabled while the box is empty), no aria-busy", pg.evaluate("(() => { const s = document.querySelector('#kform .snd'); return s.textContent === 'Run' && !s.hasAttribute('aria-busy') && !s.hasAttribute('aria-disabled') && !s.className.includes('run') && !document.querySelector('.kshd') && s.disabled })()"))
    pg.fill("#kask", "What if Utah loses?"); ok("result: typing re-enables Run", not pg.is_disabled("#kform .snd")); ctx.close()
    ctx = b.new_context(viewport={"width": 390, "height": 820}, reduced_motion="reduce"); pg = ctx.new_page(); held = []; pg.route("**/data/sim-bundle.json", lambda r: held.append(r)); pg.goto(BASE + "/playoff/"); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector("#kask"); pg.fill("#kask", Q); pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(700)
    rm = pg.evaluate("[...document.querySelectorAll('.ksm')].map(e => ({ an: getComputedStyle(e).animationName, off: parseFloat(getComputedStyle(e).strokeDashoffset) }))")
    ok("reduced motion: no animation, steady closed shield (button and card), label still carries the state", len(rm) == 2 and all(x["an"] == "none" and x["off"] == 0 for x in rm) and pg.inner_text("#kform .snd") == "Running\u2026", rm); ctx.close()
    b.close()
json.dump(res, open(f"{ROOT}/tests/last_shield_test.json", "w"), indent=1)
print(f"shield_test: {res['checks']} checks, {len(res['failures'])} failures")
