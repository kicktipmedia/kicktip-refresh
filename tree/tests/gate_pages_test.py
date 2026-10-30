"""All-pages test for the run-gate build: banner + viewport-fit + colours in the initial HTML of EVERY built page, no gate markup, no provider name,
Run-control text under every Run control, and (browser) overflow / 44px / contrast / computed graphite at 320/390/430/1280. python3 tests/gate_pages_test.py"""
import sys, os, re, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve, terms_copy_loader as TC
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
res = {"failures": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["failures"].append(f"{name} {detail}"); print("FAIL", name, str(detail)[:300])
pages = {f[len(SITE):]: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/**/*.html", recursive=True)}
ok("166 pages + 404 found (153 gate2 pages + /top25/ + /games/ + 10 simulator pages + /privacy/)", len(pages) == 167, len(pages))
VP = '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
bad_ban = [k for k, v in pages.items() if not re.search(r'<body[^>]*>\s*<a class="skip" href="#main">[^<]*</a>\s*' + re.escape(TC.BANNER_HTML) + r'\s*<header class="hd">', v)]
ok("banner is in the initial HTML of every page, exactly after the skip link and before the header", not bad_ban, bad_ban[:3])
ok("banner exactly once per page", not [k for k, v in pages.items() if v.count('class="tb"') != 1])
ok("viewport meta is exactly width=device-width,initial-scale=1,viewport-fit=cover on EVERY page (incl. /disclaimer/ and 404)", not [k for k, v in pages.items() if v.count('name="viewport"') != 1 or VP not in v])
ok("theme-color #262B31 on every page", not [k for k, v in pages.items() if '<meta name="theme-color" content="#262B31">' not in v])
ok("banner has no link, no button, no dismiss", re.search(r'<div class="tb".*?</div></div>', pages["/index.html"]).group(0).count("<a") == 0)
GATE = re.compile(r'id="gate"|kicktip_gate|DISC_VERSION|data-gate|data-gated|data-lockbar|data-open-gate|gnote|class="nb"|Locked|unlock', re.I)
allf = [f for f in glob.glob(f"{SITE}/**/*", recursive=True) if os.path.isfile(f) and f.endswith((".html", ".js", ".css", ".json", ".txt", ".xml", ".webmanifest", "_headers"))]
badg = [f[len(SITE):] for f in allf if GATE.search(open(f, encoding="utf-8", errors="replace").read()) and not f.endswith("kt.js")]
kt = open(f"{SITE}/assets/kt.js").read(); ok("kt.js: only ignores (never touches) old gate keys; no gate markup/handlers", not re.search(r"kicktip_gate|DISC_VERSION|data-gate|#gate", kt), re.findall(r".{20}kicktip_gate.{20}", kt)[:2])
ok("no gate markup / keys / 'Locked' text in any shipped file", not badg, badg[:5])
PROV = re.compile(r"odds[ _\-]?api|the-odds", re.I)
badp = [f[len(SITE):] for f in allf if PROV.search(open(f, encoding="utf-8", errors="replace").read())]
ok("no 'Odds API' / 'odds-api' / 'odds_api' string in any shipped html, js, json, css, txt, xml", not badp, badp[:5])
ok("no 'N books' / 'consensus' wording shipped", not [f[len(SITE):] for f in allf if re.search(r"\b\d+ books\b|[Cc]onsensus", open(f, encoding="utf-8", errors="replace").read())])
# Run controls: static
for k, v in pages.items():
    if k.startswith("/team/"):
        m = re.search(r'<button type="button" class="rb-run" data-run>Run Rootables</button>(<p class="rn">.*?</p>)', v)
        ok(f"{k}: Run Rootables button has the FULL line directly under it", bool(m) and m.group(1) == TC.RUN_FULL_HTML)
ok("team pages carry the always-visible Ask pill (no hidden attribute); the 10 official-rules simulator pages deliberately have no Ask pill (it answers from the KickTip model)", all('id="kpill"' in v and not re.search(r'id="kpill"[^>]*hidden', v) for k, v in pages.items() if k.startswith(("/team/", "/conference/", "/playoff/")) and "/simulator/" not in k))
ok("no Run-text link points anywhere but /disclaimer/", set(re.findall(r'<p class="rn[ s]*">.*?<a href="([^"]+)">', "".join(pages.values()))) <= {TC.TERMS_HREF})
ok("disclaimer/method: use is acceptance, nothing saved, no gate", all(re.search("accept", pages[p_], re.I) for p_ in ("/disclaimer/index.html",)) and not re.search(r"acceptance (is )?(saved|stored|remembered)|remember(s|ed)? (that )?you (accepted|agreed)", pages["/disclaimer/index.html"] + pages["/method/index.html"]) and "No cookies unless you sign in" in pages["/disclaimer/index.html"])
css = open(f"{SITE}/assets/kt.css").read()
ok("kt.css: .tb has safe-area-inset-top padding, .hd has none, GFX1 html gradient intact, no plain html{background:#262B31} override after it",
   "padding-top:env(safe-area-inset-top,0px)" in re.search(r"\.tb\{[^}]*\}", css).group(0) and "safe-area" not in re.search(r"\.hd\{[^}]*\}", css).group(0)
   and "linear-gradient(#262B31 50%,#121519 50%)" in css and css.rfind("html{background:#262B31}") == -1)
TAP = open(f"{ROOT}/tests/site_test.py").read()
TAP = re.search(r'TAP = """(.*?)"""', TAP, re.S).group(1)
LUMJS = """()=>{const parse=c=>{const m=c.match(/rgba?\\(([^)]+)\\)/);const p=m[1].split(',').map(Number);return p.length<4?[...p,1]:p};
const bgOf=e=>{while(e){const c=parse(getComputedStyle(e).backgroundColor);if(c[3]>0)return c;e=e.parentElement}return [255,255,255,1]};
const lum=c=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};
const out=[];for(const sel of ['.tb','.tb b','.rn','.rn a','.hd']){for(const e of document.querySelectorAll(sel)){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;const fg=parse(getComputedStyle(e).color),bg=bgOf(e);const a=lum(fg),b=lum(bg);out.push([sel,((Math.max(a,b)+.05)/(Math.min(a,b)+.05))])}}return out}"""
srv, BASE = serve.start()
TYPES = {"home": "/", "conference": "/conference/big-12/", "team": "/team/utah/", "playoff": "/playoff/", "top25": "/top25/", "method": "/method/", "disclaimer": "/disclaimer/", "404": "/nope-404/"}
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900})
        for name, path in TYPES.items():
            pg = ctx.new_page(); pg.goto(BASE + path); pg.wait_for_timeout(700)
            sw = pg.evaluate("document.documentElement.scrollWidth"); ok(f"{name}@{w}: no horizontal overflow", sw <= w, sw)
            ok(f"{name}@{w}: no overflow outside scroll boxes", not pg.evaluate("""()=>[...document.querySelectorAll('body *')].filter(e=>!e.closest('.tw,.tabs,.bkw')&&getComputedStyle(e).position!='fixed'&&e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).map(e=>e.tagName+'.'+e.className)"""))
            t = pg.evaluate(TAP); ok(f"{name}@{w}: tap targets >= 44px", not t["out"], t["out"][:3])
            cr = pg.evaluate(LUMJS); ok(f"{name}@{w}: banner/Run-text/header contrast >= 4.5:1", all(c >= 4.5 for _, c in cr), [c for c in cr if c[1] < 4.5][:3])
            col = pg.evaluate("""()=>{const g=s=>getComputedStyle(document.querySelector(s)).backgroundColor;const body=getComputedStyle(document.body).backgroundColor,mainbg=g('main'),ftbg=g('.ft');const h=getComputedStyle(document.documentElement).backgroundImage;return {body,mainbg,ftbg,html:h,tb:g('.tb'),hd:g('.hd'),tbBottom:document.querySelector('.tb').getBoundingClientRect().bottom,hdTop:document.querySelector('.hd').getBoundingClientRect().top,tbTop:document.querySelector('.tb').getBoundingClientRect().top,pos:getComputedStyle(document.querySelector('.tb')).position}}""")
            ok(f"{name}@{w}: html top half, body, .tb and .hd all rgb(38, 43, 49); main Paper; footer ink; banner not sticky, flush at the top, header directly under it",
               "rgb(38, 43, 49) 50%" in col["html"] and col["tb"] == col["hd"] == col["body"] == "rgb(38, 43, 49)" and col["mainbg"] == "rgb(241, 243, 244)" and col["ftbg"] == "rgb(18, 21, 25)" and col["pos"] == "static" and col["tbTop"] == 0 and abs(col["tbBottom"] - col["hdTop"]) <= 0.5, str(col))
            if w == 390 and name in ("team", "conference"):
                pg.click("#kpill"); pg.wait_for_timeout(1000)
            pg.close()
        ctx.close()
    # tall window: short pages fill the window with the Paper main; no body graphite can show between content and footer
    for w, h in ((390, 2400), (1280, 2400)):
        ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
        for name in ("404", "disclaimer", "home"):
            pg.goto(BASE + TYPES[name]); pg.wait_for_timeout(500)
            g = pg.evaluate("""()=>{const r=s=>document.querySelector(s).getBoundingClientRect();return {tbHd:r('.tb').bottom-r('.hd').top,hdMain:r('main').top-r('.hd').bottom,mainSrc:r('.src').top-r('main').bottom,srcFt:r('.ft').top-r('.src').bottom,ftBottom:r('.ft').bottom,ih:innerHeight,sh:document.documentElement.scrollHeight}}""")
            ok(f"{name}@{w}x{h}: tb/hd/main/src/ft stack with no gaps (nothing but Paper, white or ink between them) and the footer reaches the window bottom on short pages", abs(g["tbHd"]) < .6 and abs(g["hdMain"]) < .6 and abs(g["mainSrc"]) < .6 and abs(g["srcFt"]) < .6 and g["ftBottom"] >= min(g["ih"], g["sh"]) - 1, str(g))
        ctx.close()
    # Ask panel: one FULL line, Run labels, and exactly what a run changes
    ctx = b.new_context(viewport={"width": 390, "height": 800}); pg = ctx.new_page(); reqs = []; pg.on("request", lambda r: reqs.append(r.url))
    pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(600); pg.click("#kpill"); pg.wait_for_timeout(600)
    ok("Ask panel before Run: nothing fetched", not [u for u in reqs if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/", u)])
    pg.fill("#kask", "What if Utah loses its next game?"); pg.click(".snd"); pg.wait_for_selector(".pnl .bd [data-q], .pnl .bd .res, .pnl .bd h3", timeout=20000); pg.wait_for_timeout(2500)
    ok("after tapping Run: the simulator and shards load", bool([u for u in reqs if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/", u)]), [u[-40:] for u in reqs][-5:])
    ok("Ask panel after a run: still exactly one FULL line (last child of .cmp)", pg.evaluate("document.querySelectorAll('.pnl .rn').length")==1 and pg.evaluate("document.querySelector('.pnl .cmp').lastElementChild.matches('p.rn:not(.s)')"))
    labs = pg.evaluate("[...document.querySelectorAll('.pnl .bd button,.pnl .bd a')].map(e=>e.textContent.trim())")
    ok("no 'Try again' / 'Send' / 'Ask' run labels in the answer view", not [l for l in labs if re.fullmatch(r"Try again|Send|Ask", l)], labs)
    ctx.close(); b.close()
print(f"gate_pages_test: {res['n']} checks, {len(res['failures'])} failures"); sys.exit(1 if res["failures"] else 0)
