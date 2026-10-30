"""CCG label test. Static: (1) no 'title game'/'title-game' without 'conference ' before it in ANY shipped text file (allowance below); (2) every page with 'CCG' carries the definition paragraph
<p class="ccgdef">CCG = conference championship game</p> in each region that shows the label, above that region's table/tiles; (3) meta description / og / twitter text never carries bare 'CCG';
(4) every JS/CSS/JSON file that renders 'CCG' carries the definition; chat/Ask bundles and data files never render bare 'CCG'; (5) Rootables ccg control: aria-label full words, visible 'Reach CCG'.
Browser: definition style (13px, regular, #4C5560), no horizontal overflow at 320/390/430/1280 on home, conference, team, playoff, method, 404; definition not clipped; Rootables definition directly under the segmented control.
python3 tests/ccg_test.py"""
import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
res = {"f": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["f"].append(name); print("FAIL", name, str(detail)[:300])
DEF = '<p class="ccgdef">CCG = conference championship game</p>'; DEFTXT = "CCG = conference championship game"
TXT = (".html", ".js", ".css", ".json", ".txt", ".xml", ".webmanifest", "_headers", ".svg")
files = {f[len(SITE):]: open(f, encoding="utf-8", errors="replace").read() for f in glob.glob(f"{SITE}/**/*", recursive=True) if os.path.isfile(f) and f.endswith(TXT)}
ok("many shipped text files read", len(files) > 200, len(files))
# (1) bare 'title game'. ALLOWANCE (documented): assets/ks/parse.js contains the INPUT-RECOGNITION patterns that decide what a typed question means; they are never displayed.
ALLOW = {"assets/ks/parse.js": ["(?:championship game|title game|ccg|conference championship game|conference title game|league title game|play in the", "(?:title|championship|ccg) game"]}
BARE = re.compile(r"(?<!conference )title[ -]game", re.I); bad = []
for k, v in files.items():
    t = v
    for a in ALLOW.get(k.lstrip("/"), []): t = t.replace(a, "")
    if BARE.search(t): bad.append((k, BARE.search(t).group(0), t[max(0, BARE.search(t).start() - 30):BARE.search(t).end() + 20]))
ok("no shipped file has 'title game' / 'title-game' without 'conference ' before it (allowance: parse.js input-matching patterns only)", not bad, bad[:4])
# (2) pages
pages = {k: v for k, v in files.items() if k.endswith(".html")}
withccg = {k: v for k, v in pages.items() if re.search(r"\bCCG\b", v)}
ok("pages that show the CCG label: home, 11 conferences minus Independents (10), 136 teams minus independents, playoff", len(withccg) > 100, len(withccg))
nodef = [k for k, v in withccg.items() if DEF not in v]; ok("every page showing 'CCG' carries the definition paragraph", not nodef, nodef[:3])
badpos = []
for k, v in withccg.items():
    for m in re.finditer(r"Reach CCG", v):
        before = v[:m.start()]
        # the nearest preceding region start (<h2) must be followed, before this label, by the definition
        h = before.rfind("<h2")
        if h < 0 or DEF not in before[h:]: badpos.append(k); break
ok("each region that shows 'Reach CCG' has the definition under its heading, above the table/tiles", not badpos, badpos[:3])
many = [k for k, v in withccg.items() if v.count(DEF) > 2]; ok("definition once per region (<=2 per page: team page has tiles + paths regions)", not many, many[:3])
ok("definition sits directly after the region heading on home / conference / team / playoff", all(re.search(r"</h2>(?:\{CRED\}|<p class=\"cred\"[^>]*>.*?</p>)?" + re.escape(DEF), v) or re.search(r"</h2>" + re.escape(DEF), v) for k, v in withccg.items() if k in ("/index.html", "/playoff/index.html", "/team/utah/index.html", "/conference/big-12/index.html")), "")
ok("no 'CCG' on pages for independents' region (conference/independents, team notre-dame)", not [k for k in ("/conference/independents/index.html", "/team/notre-dame/index.html") if k in withccg], [k for k in withccg if "independ" in k or "notre" in k])
# (3) meta
badmeta = []
for k, v in pages.items():
    for m in re.finditer(r'<meta[^>]+(?:name|property)="(?:description|og:[a-z:]+|twitter:[a-z:]+)"[^>]*>', v):
        if re.search(r"\bCCG\b", m.group(0)): badmeta.append(k)
ok("meta description / og / twitter text never carries bare CCG", not badmeta, badmeta[:3])
badtitle = [k for k, v in pages.items() if re.search(r"<title>[^<]*\bCCG\b", v)]; ok("page titles never carry bare CCG", not badtitle, badtitle[:3])
# (4) JS / JSON
ccgjs = {k: v for k, v in files.items() if not k.endswith(".html") and re.search(r"\bCCG\b", v)}
ok("only rootables.js, top25.js, ccgsim-ui.js and myteams.js (+ the CSS comments, kt.css and ccgsim.css) render CCG outside pages", set(ccgjs) <= {"/assets/rootables.js", "/assets/kt.css", "/assets/top25.js", "/assets/ccgsim-ui.js", "/assets/myteams.js", "/assets/ccgsim.css"}, list(ccgjs))
# ccgsim-ui.js writes only into the 10 simulator pages, each of which carries the static definition line (checked above and in ccg_text_test.py); the other scripts carry the text themselves
ok("every non-page file with 'CCG' carries the definition text (ccgsim-ui.js: its pages carry it)", all(DEFTXT in v for k, v in ccgjs.items() if k.endswith(".js") and k != "/assets/ccgsim-ui.js"), list(ccgjs))
import glob as _g
ok("each of the 10 simulator pages carries the definition paragraph next to the label", len(_g.glob(f"{SITE}/conference/*/simulator/index.html")) == 10 and all(DEF in open(f, encoding="utf-8").read() and open(f, encoding="utf-8").read().index("id=\"lab\"") < open(f, encoding="utf-8").read().index(DEF) for f in _g.glob(f"{SITE}/conference/*/simulator/index.html")))
for k in ("/assets/ks/answer.js", "/assets/ks/parse.js", "/assets/ks/sim.js", "/assets/chat.js", "/assets/chat-worker.js", "/assets/kt.js"):
    if k in files: ok(f"{k}: chat/Ask/answer code never renders bare 'CCG'", not re.search(r"\bCCG\b", files[k]), k)
ok("answer.js labels use full words", '"Reach the conference championship game"' in files["/assets/ks/answer.js"] and '"reach the conference championship game"' in files["/assets/ks/answer.js"])
ok("data files (all /data/*.json) carry no 'CCG' and no title-game label text", not [k for k, v in files.items() if k.startswith("/data/") and (re.search(r"\bCCG\b", v) or BARE.search(v))])
rj = files["/assets/rootables.js"]
ok("rootables.js: visible 'Reach CCG', aria-label full words, definition paragraph under the segmented control", "short: 'Reach CCG'" in rj and "aria: 'Reach the conference championship game'" in rj and "' aria-label=\"' + m.aria" in rj and "</div><p class=\"ccgdef\">CCG = conference championship game</p>'" in rj)
ok("rootables.js phrase uses full words", "phrase: 'chance to reach the conference championship game'" in rj)
kc = files["/assets/kt.css"]; ok("kt.css .ccgdef: 13px, 400, #4C5560 (light) and #D5DBE0 (dark), margin-top 5px", ".ccgdef{margin:5px 0 8px;font:400 13px/1.4 'Source Sans 3',Arial,sans-serif;font-style:normal;color:#4C5560}" in kc and ".on-dark .ccgdef{color:#D5DBE0}" in kc)
# (5) browser
srv, BASE = serve.start()
PAGES = {"home": "/", "conf": "/conference/big-12/", "team": "/team/utah/", "playoff": "/playoff/", "method": "/method/", "404": "/nope-404/", "indep": "/team/notre-dame/"}
DEFJS = """()=>[...document.querySelectorAll('.ccgdef')].map(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();return {t:e.textContent,fs:c.fontSize,fw:c.fontWeight,st:c.fontStyle,col:c.color,mt:c.marginTop,ff:c.fontFamily.slice(0,14),l:r.left,r:r.right,w:r.width,h:r.height,sw:e.scrollWidth,cw:e.clientWidth,prev:e.previousElementSibling&&e.previousElementSibling.tagName,imgs:e.querySelectorAll('img,svg,abbr,details').length,title:e.hasAttribute('title')}})"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
        for n, u in PAGES.items():
            pg.goto(BASE + u); pg.wait_for_timeout(900); pg.evaluate("document.fonts.ready")
            sw = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]"); ok(f"{n} {w}: no horizontal overflow", sw[0] <= sw[1], sw)
            d = pg.evaluate(DEFJS)
            if n in ("home", "conf", "playoff"): ok(f"{n} {w}: one definition line", len(d) == 1, len(d))
            if n == "team": ok(f"team {w}: two definition regions (tiles, paths)", len(d) == 2, len(d))
            if n in ("method", "404", "indep"): ok(f"{n} {w}: no CCG label, so no definition", len(d) == 0 and "CCG" not in pg.inner_text("body").replace("CCG = conference championship game", ""), len(d))
            for x in d:
                ok(f"{n} {w}: def text exact", x["t"] == DEFTXT, x["t"])
                ok(f"{n} {w}: def 13px regular non-italic #4C5560 Source Sans 3, margin-top 5px, no icon/tooltip/disclosure", x["fs"] == "13px" and x["fw"] == "400" and x["st"] == "normal" and x["col"] == "rgb(76, 85, 96)" and x["mt"] == "5px" and x["ff"].startswith("\"Source Sans 3") and x["imgs"] == 0 and not x["title"], x)
                ok(f"{n} {w}: def inside viewport, not clipped", x["l"] >= 0 and x["r"] <= w + 0.5 and x["sw"] <= x["cw"] + 1, x)
                ok(f"{n} {w}: def follows a heading (or the model credit line)", x["prev"] in ("H2", "P", "DIV"), x["prev"])
        if w in (320, 390):
            pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(500); pg.click("#rootables [data-run]"); pg.wait_for_selector("#rootables[data-rb=on]:not([aria-busy])", timeout=10000); pg.wait_for_timeout(300)
            r = pg.evaluate("""()=>{const s=document.querySelector('#rootables .rb-seg'),d=s.nextElementSibling,bs=[...s.querySelectorAll('button')].map(x=>{const r=x.getBoundingClientRect();return {t:x.innerText.replace(/\\s+/g,' '),a:x.getAttribute('aria-label'),w:r.width,h:r.height,o:x.dataset.outcome}}),dr=d.getBoundingClientRect(),sr=s.getBoundingClientRect(),cs=getComputedStyle(d);
              return {dcls:d.className,dt:d.textContent,gap:dr.top-sr.bottom,fs:cs.fontSize,col:cs.color,bs,sw:document.documentElement.scrollWidth,iw:innerWidth,dl:dr.left,dr:dr.right}}""")
            ok(f"rootables {w}: definition is the paragraph directly under the segmented control", r["dcls"] == "ccgdef" and r["dt"] == DEFTXT and 3 <= r["gap"] <= 8, r)
            ok(f"rootables {w}: controls >=44px, labels 'Make the 12' / 'Reach CCG' (visible), ccg aria-label full words", all(x["h"] >= 43.5 and x["w"] >= 43.5 for x in r["bs"]) and r["bs"][1]["a"] == "Reach the conference championship game" and "Reach CCG" in r["bs"][1]["t"] and r["bs"][0]["t"].startswith("Make the 12"), r["bs"])
            ok(f"rootables {w}: definition 13px #4C5560 inside viewport, no overflow", r["fs"] == "13px" and r["col"] == "rgb(76, 85, 96)" and r["dl"] >= 0 and r["dr"] <= w + .5 and r["sw"] <= r["iw"], r)
            # Run-text still under the card, not crowded by the definition (definition is above the list; Run-line is a separate paragraph below)
            ok(f"rootables {w}: exactly one definition line inside the card", pg.locator("#rootables .ccgdef").count() == 1, pg.locator("#rootables .ccgdef").count())
            pg.click("[data-outcome=ccg]"); pg.wait_for_timeout(300); ok(f"rootables {w}: switching to Reach CCG keeps the single definition", pg.locator("#rootables .ccgdef").count() == 1)
        ctx.close()
    b.close()
print(f"ccg_test: {res['n']} checks, {len(res['f'])} failures"); sys.exit(1 if res["f"] else 0)
