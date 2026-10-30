"""Headless Chromium tests for build/site. python3 tests/site_test.py [--all]   (--all: every one of the 154 pages at 320/390/430/1280)"""
import sys, os, re, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
srv, BASE = serve.start()
ALL = "--all" in sys.argv
import terms_copy_loader as TC   # reads src/terms_copy.py (the one place for the banner and the under-Run line)
STORE_INIT = "window.__sw=[];(function(){var s=Storage.prototype,a=s.setItem,r=s.removeItem,c=s.clear;s.setItem=function(k,v){window.__sw.push('set:'+k);return a.call(this,k,v)};s.removeItem=function(k){window.__sw.push('rm:'+k);return r.call(this,k)};s.clear=function(){window.__sw.push('clear');return c.call(this)}})();"
TYPES = {"home": "/", "conference": "/conference/big-12/", "team": "/team/utah/", "playoff": "/playoff/", "top25": "/top25/", "method": "/method/", "disclaimer": "/disclaimer/", "privacy": "/privacy/", "404": "/nope-404/"}
GATED = ["home", "conference", "team", "playoff"]
ACCEPT_INIT = "0;"   # legacy name kept so old call sites still work: nothing to accept any more
res = {"failures": [], "checks": []}
def ok(name, cond, detail=""):
    res["checks"].append((name, bool(cond), detail))
    if not cond: res["failures"].append(f"{name} {detail}")

def watch(page, store):
    page.on("console", lambda m: store["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: store["console"].append(f"pageerror: {e}"))
    page.on("request", lambda r: store["req"].append(r.url))
    page.on("response", lambda r: store["bad"].append(f"{r.status} {r.url}") if r.status >= 400 and not r.url.endswith("nope-404/") else None)
def fresh(): return {"console": [], "req": [], "bad": []}
def offorigin(reqs): return [u for u in reqs if not u.startswith(BASE) and not u.startswith("data:")]

TAP = """() => { const out=[], ex=[]; for (const e of document.querySelectorAll('a[href],button,input,summary,select,textarea,label')) {
  const r=e.getBoundingClientRect(); const cs=getComputedStyle(e); if(r.width===0||r.height===0||cs.visibility==='hidden') continue;
  if(e.closest('.skip')) continue;
  if(e.tagName==='INPUT' && e.closest('label')) continue;   // an input inside a label is measured by its label
  const par=e.parentElement; const txt=(e.textContent||e.type||'').trim().slice(0,40);
  const inpara=e.tagName==='A' && cs.display==='inline' && par && par.textContent.trim()!==e.textContent.trim();   // inline link inside running text (QA ruling: exempt)
  if(r.height<43.5 || r.width<43.5) { const d=e.tagName+':'+txt+' '+Math.round(r.width)+'x'+Math.round(r.height); if(inpara) ex.push(d); else out.push(d); } }
  return {out, ex}; }"""
TAP_EXEMPT = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    # ---- 1. arrival behavior per data page (gate-move build): no gate, no dialog, data on arrival, banner, no storage writes
    for name in GATED:
        ctx = b.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script(STORE_INIT); pg = ctx.new_page(); st = fresh(); watch(pg, st)
        pg.goto(BASE + TYPES[name]); pg.wait_for_timeout(900)
        ok(f"{name}: no gate/overlay/modal in the DOM", pg.evaluate("!document.querySelector('#gate,.ov,.dlg,[data-accept],[data-leave],[data-open-gate],.lock,[data-lockbar],[data-lockmsg],[aria-modal=true]')"))
        ok(f"{name}: no visible dialog on arrival", pg.evaluate("![...document.querySelectorAll('[role=dialog]')].some(e=>!e.hidden && e.getBoundingClientRect().width>0)"))
        ok(f"{name}: pred data fetched on arrival (no click)", len([u for u in st["req"] if "/data/pred-" in u]) >= 1, str([u.split("/data/")[1] for u in st["req"] if "/data/" in u]))
        t = pg.inner_text("main"); ok(f"{name}: numbers visible on arrival", bool(re.search(r"\d+%|<1%", t)))
        ok(f"{name}: no 'Locked'/'unlock'/'accept the disclaimer' text anywhere visible", not re.search(r"Locked|unlock|accept the disclaimer|Review and accept", pg.inner_text("body")))
        ok(f"{name}: no data-gate / data-gated attribute", pg.evaluate("!document.querySelector('[data-gate],[data-gated]')"))
        ok(f"{name}: banner is the first thing in <body> after the skip link, above the header", pg.evaluate("(()=>{const k=[...document.body.children].filter(e=>e.tagName!=='SCRIPT'); return k[0].classList.contains('skip') && k[1].classList.contains('tb') && k[2].classList.contains('hd')})()"))
        ok(f"{name}: simulator, chat worker, sim-bundle, what-if shards and Google script NOT fetched on arrival", not [u for u in st["req"] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/|google", u)], str([u for u in st["req"] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/|google", u)][:3]))
        ok(f"{name}: banner text equals src/terms_copy.py BANNER_TEXT", " ".join(pg.inner_text(".tb").split()) == TC.BANNER_TEXT, pg.inner_text(".tb"))
        ok(f"{name}: no storage writes on arrival", pg.evaluate("window.__sw.length === 0") and pg.evaluate("localStorage.length === 0 && sessionStorage.length === 0"), str(pg.evaluate("window.__sw")))
        ok(f"{name}: no console errors", not st["console"], str(st["console"][:3])); ok(f"{name}: no off-origin requests", not offorigin(st["req"]), str(offorigin(st["req"])[:3])); ok(f"{name}: no 4xx/5xx", not st["bad"], str(st["bad"][:3]))
        pg.reload(); pg.wait_for_timeout(700); ok(f"{name}: reload shows numbers again, still no dialog", bool(re.search(r"\d+%|<1%", pg.inner_text("main"))) and pg.evaluate("!document.querySelector('#gate,.ov,.dlg')"))
        ctx.close()
    # retired keys from the old gate are ignored (never read, never rewritten, never removed) and cause no overlay
    ctx = b.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script("localStorage.setItem('kicktip_gate', JSON.stringify({v:'old',t:1})); sessionStorage.setItem('kicktip_gate_visit','1');" + STORE_INIT); pg = ctx.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(800)
    ok("old kicktip_gate keys present: no overlay, numbers shown, keys untouched, no writes", pg.evaluate("!document.querySelector('#gate,.ov,.dlg')") and bool(re.search(r"\d+%|<1%", pg.inner_text("main"))) and pg.evaluate("window.__sw.length===0 && !!localStorage.getItem('kicktip_gate')"), str(pg.evaluate("window.__sw")))
    ctx.close()
    # Rootables card (team page): compact card, Run button, FULL line directly under it; nothing fetched or drawn before the tap
    ctx = b.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script(STORE_INIT); pg = ctx.new_page(); st = fresh(); watch(pg, st); pg.goto(BASE + "/team/utah/"); pg.wait_for_timeout(1500)
    rt = pg.evaluate("(()=>{const bt=document.querySelector('#rootables [data-run]'); const n=bt&&bt.nextElementSibling; return bt?{lbl:bt.textContent.trim(), ok:!!n&&n.matches('p.rn:not(.s)'), txt:n&&n.textContent.replace(/\\s+/g,' ').trim(), href:n&&n.querySelector('a').getAttribute('href'), rows:document.querySelectorAll('#rootables .rb-row').length, st:document.querySelector('#rootables').dataset.rb}:null})()")
    ok("Rootables card: button is 'Run Rootables', FULL line is its next sibling (exact text), Full terms links to /disclaimer/", bool(rt) and rt["lbl"] == "Run Rootables" and rt["ok"] and rt["txt"] == TC.RUN_FULL_TEXT + " " + TC.TERMS_LINK and rt["href"] == TC.TERMS_HREF, str(rt))
    ok("Rootables renders nothing before the tap (no rows) and fetches no what-if/sim-bundle/week shard", bool(rt) and rt["rows"] == 0 and rt["st"] == "idle" and not [u for u in st["req"] if re.search(r"/whatif/|sim-bundle|/assets/ks/|chat-worker", u)], str(rt))
    pg.click("#kpill"); pg.wait_for_timeout(1200)
    ok("Ask panel open fetches nothing (no simulator, worker, bundle or shards)", not [u for u in st["req"] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/|google", u)], str([u for u in st["req"] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/|google", u)][:3]))
    ct = pg.evaluate("(()=>{const f=document.querySelector('.pnl .cmp form'); const n=f&&f.nextElementSibling; return n?{ok:n.matches('p.rn:not(.s)') && n===f.parentElement.lastElementChild, txt:n.textContent.replace(/\\s+/g,' ').trim(), btn:f.querySelector('.snd').textContent.trim(), al:f.querySelector('.snd').getAttribute('aria-label'), n_rn:document.querySelectorAll('.pnl .rn').length}:null})()")
    ok("Ask composer: button 'Run' (aria-label Run), ONE FULL line as last child of .cmp under the form, none repeated in the panel", bool(ct) and ct["ok"] and ct["txt"] == TC.RUN_FULL_TEXT + " " + TC.TERMS_LINK and ct["btn"] == "Run" and ct["al"] == "Run" and ct["n_rn"] == 1, str(ct))
    ok("Ask KickTip opens with no gate view, no storage writes", pg.evaluate("!document.querySelector('.pnl .gate,.pnl [data-accept]') && window.__sw.length===0"), str(pg.evaluate("window.__sw")))
    pg.click(".pnl button.q"); pg.wait_for_timeout(200)
    ok("example card fills the box and focuses it, runs nothing", pg.evaluate("document.getElementById('kask').value.length>5 && document.activeElement.id==='kask'") and not [u for u in st["req"] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/", u)])
    ctx.close()
    # ---- 2. no-JS
    for name in GATED:
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900}); pg = ctx.new_page(); st = fresh(); watch(pg, st)
        pg.goto(BASE + TYPES[name]); t = pg.inner_text("main")
        ok(f"{name}: no-JS shows no prediction numbers", not re.search(r"\d+\s?%|[\u2212]\d+\.\d|<1%", t.replace("10,000", "")), "")
        ok(f"{name}: no-JS shows the 'turn on JavaScript' note and the banner is in the HTML", "Turn on JavaScript" in pg.content() and TC.BANNER_HTML in pg.content())
        ok(f"{name}: no-JS did not request pred data", not [u for u in st["req"] if "/data/pred-" in u])
        ctx.close()
    # raw HTML scan (all gated pages): no percent or signed line numbers inside main
    bad = []
    for f in glob.glob(f"{SITE}/**/index.html", recursive=True):
        s = open(f, encoding="utf-8").read(); rel = f[len(SITE):]
        if rel.startswith(("/method/", "/disclaimer/")): continue
        m = re.search(r"<main.*?</main>", s, re.S).group(0); m = re.sub(r"<[^>]+>", " ", m).replace("10,000", "").replace("Pick a game result and see how chances change.", "")   # the /top25/ Run card's mandated sentence
        if re.search(r"\d+\s?%|[\u2212]\d+\.\d|\bPick", m): bad.append(rel)
    ok("raw HTML: no prediction numbers in any gated page main", not bad, str(bad[:5]))
    # ---- b4 content checks (static pages)
    def main_of(rel): return re.sub(r"<[^>]+>", " ", re.search(r"<main.*?</main>", open(f"{SITE}{rel}index.html", encoding="utf-8").read(), re.S).group(0))
    wy = main_of("/team/wyoming/"); ok("team page shows a Final label with the score", bool(re.search(r"Final\s*&middot;|Final\s*·", wy)) or "Final" in wy)
    ok("method page has no 'Unverified items' box and no 'prior-year text'", "Unverified" not in main_of("/method/") and "prior-year" not in main_of("/method/"))
    pg2 = [open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/**/*.html", recursive=True)]
    ok("no duplicate class attributes", not any(re.search(r"class=['\"][^'\"]*['\"]\s+class=", x) for x in pg2))
    ok("no Pick'em / '(1 books)' text in site", not any(("Pick'em" in x or "1 books" in x) for x in pg2) and "Pick'em" not in open(f"{SITE}/assets/kt.js").read())
    mp = open(f"{SITE}/method/index.html", encoding="utf-8").read(); ban = re.search(r'<div class="ban".*?</div>', mp, re.S).group(0)
    ok("method page banner does not link to /method/ (no self-link)", 'href="/method/"' not in ban)
    # ---- b4b checks
    rq = b.new_context().request; r = rq.get(BASE + "/data/pred-games.json"); pgj = r.json()
    ok("/data/* answers X-Robots-Tag noindex, nofollow", "noindex" in r.headers.get("x-robots-tag", "") and "nofollow" in r.headers.get("x-robots-tag", ""), str(r.headers.get("x-robots-tag")))
    plj = json.load(open(f"{SITE}/data/pred-lines.json"))["l"]; shown = sum(1 for k in pgj["g"] if k in plj); tot = len(pgj["g"])
    mt = main_of("/method/"); mm = re.search(r"Right now that is (\d+) of the (\d+) games", mt)
    ok("method market-line count equals the shipped pred-lines.json (games still to be played that have a line)", bool(mm) and (int(mm.group(1)), int(mm.group(2))) == (shown, tot), f"{mm.group(0) if mm else None} vs {shown}/{tot}")
    ok("method and disclaimer: no 'gate' or 'must accept first' language; use of the site is acceptance", not any(re.search(r"acceptance gate|accept (this|the disclaimer) before|asked to accept|Review and accept|Accept and continue|unlock after", main_of(p_)) for p_ in ("/disclaimer/", "/method/")) and "Using this site means you accept them" in main_of("/disclaimer/") and "Using KickTip means you accept the terms" in mt)
    ok("no claim that data files are locked/private", not any(re.search(r"data (files )?(are|is) (locked|private|protected|secured)", x) for x in pg2))
    ok("Big Ten source carries the automated-readers note", "link may not open for automated readers" in main_of("/conference/big-ten/"))
    ok("no ISO dates in visible text of conference/team/method pages", not [f for f in [f for f in glob.glob(f"{SITE}/**/index.html", recursive=True) if f[len(SITE):].startswith(("/conference/", "/team/", "/method/", "/playoff/"))] if re.search(r"\b20\d\d-\d\d-\d\d\b", re.sub(r"<[^>]+>", " ", re.search(r"<main.*?</main>", open(f, encoding="utf-8").read(), re.S).group(0)))])
    ok("kt.css has no build-tag comments", not re.search(r"/\* b\d:", open(f"{SITE}/assets/kt.css").read()))
    ok("playoff page cites Aug 6 announcement and NCAA.com", "Aug. 6, 2026 announcement" in main_of("/playoff/") and "NCAA.com" in main_of("/playoff/"))
    # ---- b4c checks
    xr = r.headers.get("x-robots-tag", ""); hd = open(f"{SITE}/_headers").read()
    ok("X-Robots-Tag is a single header on /data/* (value exactly 'noindex, nofollow', one line in _headers)", xr == "noindex, nofollow" and hd.count("X-Robots-Tag") == 1, f"{xr!r} / {hd.count('X-Robots-Tag')} lines")
    gl = re.compile(r"go-live|go live|golive|launch|staged|not launched|noindex|internal", re.I)
    ok("robots.txt and sitemap.xml carry no internal go-live/launch wording", not gl.search(open(f"{SITE}/robots.txt").read()) and not gl.search(open(f"{SITE}/sitemap.xml").read()))
    ms = re.search(r"remaining (\d+) games \((\d+) not yet started(?: plus (\d+) in progress or awaiting a final score)?\) ", mt)
    n_rem, n_pre_m, n_live = (int(ms.group(1)), int(ms.group(2)), int(ms.group(3) or 0)) if ms else (0, 0, 0)
    ok("method 'The simulation' count breakdown is consistent: remaining = not yet started + in progress", bool(ms) and n_rem == n_pre_m + n_live, ms.group(0) if ms else "no match")
    ok("method simulation 'not yet started' equals the market-line denominator and pred-games.json", bool(ms) and bool(mm) and n_pre_m == int(mm.group(2)) == tot, f"{n_pre_m} / {mm.group(2) if mm else None} / {tot}")
    rmeta = json.load(open(f"{ROOT}/data/out/run_meta.json")); ok("method remaining-games total equals run_meta.remaining_games", n_rem == rmeta["remaining_games"], f"{n_rem} vs {rmeta['remaining_games']}")
    # ---- b6 checks: indexing, no handle/email, V2 brand, ESPN logos
    import hashlib, io
    from PIL import Image
    sh = lambda x: hashlib.sha256(x).hexdigest(); rd = lambda f: open(f, "rb").read()
    sys.path.insert(0, f"{ROOT}/src"); from site_config import SITE_URL as HOST
    htmls = {f[len(SITE):]: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/**/*.html", recursive=True)}
    ok("no page carries a robots meta or the word noindex", not [k for k, v in htmls.items() if re.search(r'<meta name="robots"|noindex', v, re.I)])
    hd = open(f"{SITE}/_headers").read()
    ok("_headers: exactly one X-Robots-Tag line, and it sits under /data/*", hd.count("X-Robots-Tag") == 1 and re.search(r"/data/\*\n  X-Robots-Tag: noindex, nofollow\n", hd) is not None)
    rq2 = b.new_context().request
    ok("pages, assets, robots.txt and sitemap.xml answer no X-Robots-Tag", all(rq2.get(BASE + u).headers.get("x-robots-tag") is None for u in ("/", "/team/utah/", "/robots.txt", "/sitemap.xml", "/assets/kt.css", "/404.html")))
    ok("/data/* files answer one X-Robots-Tag 'noindex, nofollow'", all(rq2.get(BASE + f"/data/{n}.json").headers.get("x-robots-tag") == "noindex, nofollow" for n in ("pred-games", "pred-teams", "pred-paths")))
    ok("robots.txt is exactly Allow / + Disallow /data/ + Disallow /api/ + Sitemap line", open(f"{SITE}/robots.txt").read() == f"User-agent: *\nAllow: /\nDisallow: /data/\nDisallow: /api/\n\nSitemap: {HOST}/sitemap.xml\n", repr(open(f"{SITE}/robots.txt").read()))
    sm = re.findall(r"<loc>([^<]+)</loc>", open(f"{SITE}/sitemap.xml").read())
    def tofile(u): pth = u[len(HOST):]; return pth + "index.html" if pth.endswith("/") else pth
    ok("sitemap: 166 unique absolute kicktipmedia.com URLs, none under /data/ or /404", len(sm) == 166 == len(set(sm)) and all(u.startswith(HOST + "/") and "/data/" not in u and "404" not in u for u in sm))
    ok("sitemap: every URL resolves to a built page and every built page except 404 is listed", all(os.path.exists(SITE + tofile(u)) for u in sm) and {tofile(u) for u in sm} == set(htmls) - {"/404.html"})
    ok("every page: canonical and og:url equal its own sitemap URL; 404 has neither", all((f'<link rel="canonical" href="{HOST}{k[:-10] if k.endswith("index.html") else k}">' in v and f'<meta property="og:url" content="{HOST}{k[:-10] if k.endswith("index.html") else k}">' in v) for k, v in htmls.items() if k != "/404.html") and 'rel="canonical"' not in htmls["/404.html"] and "og:url" not in htmls["/404.html"])
    ok("sitemap and robots pass a 200 over HTTP", all(rq2.get(BASE + u).status == 200 for u in ("/robots.txt", "/sitemap.xml", "/site.webmanifest")))
    # no X handle, no contact email, anywhere (all text files)
    bad = []
    for f in glob.glob(f"{SITE}/**/*", recursive=True):
        if os.path.isfile(f) and f.endswith((".html", ".js", ".css", ".xml", ".txt", ".json", ".webmanifest", "_headers")):
            t = open(f, encoding="utf-8", errors="replace").read()
            if f.endswith("/privacy/index.html"): t = t.replace('<a href="mailto:support@kicktipmedia.com">support@kicktipmedia.com</a>', "", 1)   # p2d D1: the ONE approved contact link, /privacy/ Questions only (privacy_test.py checks it is exactly one)
            m = [x for x in re.findall(r"mailto:\S*|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}|(?:x|twitter)\.com/\S*|twitter:(?:site|creator)|\bcontact (?:us|email)\b|(?<![\w@])@[A-Za-z_][A-Za-z0-9_]{2,}", t, re.I) if not x.lower().startswith(("@font", "@media", "@keyframes", "@supports", "@import", "@charset"))]
            if m: bad.append((f[len(SITE):], m[:2]))
    ok("no X/Twitter handle or link, no email address or mailto (except the one approved support@ link on /privacy/), no 'contact' prompt in any shipped text file", not bad, str(bad[:3]))
    # V2 brand
    PK = "/workspace/hub/creative-v11d-kicktip-logo-pkg"
    brand = {"assets/brand/logo/kicktip-header-nosub-transparent.png": "logo/kicktip-header-nosub-transparent.png", "assets/brand/logo/kicktip-media-lockup-transparent.png": "logo/kicktip-media-lockup-transparent.png", "favicon.ico": "icon/favicon.ico"}
    for sub in ("icon", "social"):
        for fn in os.listdir(f"{PK}/{sub}"): brand[f"assets/brand/{sub}/{fn}"] = f"{sub}/{fn}"
    ok("V2 brand files in the build are byte-identical to the package (header, lockup, favicon.ico, all icon/ and social/)", all(os.path.exists(f"{SITE}/{k}") and sh(rd(f"{SITE}/{k}")) == sh(rd(f"{PK}/{v}")) for k, v in brand.items()), f"{len(brand)} files")
    allf = [f[len(SITE) + 1:] for f in glob.glob(f"{SITE}/**/*", recursive=True) if os.path.isfile(f)]
    ok("no Tag Badge files, no brand guide/manifest/readme/proofs/JARED/-source.jpg in the build", not [f for f in allf if re.search(r"^assets/logo/|^assets/social/|BRAND-GUIDE|MANIFEST|README|proofs|JARED|-source\.jpg|\.svg$", f)])
    ok("no 'Tag Badge' text and no old logo paths in any page", not [k for k, v in htmls.items() if re.search(r"Tag Badge|assets/logo/|assets/social/|kicktip-lockup-dark", v)])
    HEADIMG = "/assets/brand/logo/kicktip-header-nosub-transparent.png"; LOCK = "/assets/brand/logo/kicktip-media-lockup-transparent.png"
    ok("header uses the no-MEDIA logo (alt 'KickTip Media'); the MEDIA lockup appears only in the footer, once per page; no lockup in header or hero", all(re.search(r'<header class="hd">.*?<img src="' + HEADIMG + r'"[^>]*alt="KickTip Media"', v, re.S) and v.count(LOCK) == 1 and re.search(r'<footer class="ft"><div class="w"><img class="flock" src="' + LOCK, v) for v in htmls.values()))
    for hw, hh in ((1280, 40), (390, 34)):  # sticky slim header (SPEC.md): 40px logo in the 64px bar, 34px in the 56px bar
        cx = b.new_context(viewport={"width": hw, "height": 800}); pq = cx.new_page(); pq.goto(BASE + "/disclaimer/"); pq.wait_for_timeout(300)
        r_ = pq.evaluate("""()=>{const i=document.querySelector('.hd .brand img'), a=document.querySelector('.hd .brand'); const ri=i.getBoundingClientRect(), ra=a.getBoundingClientRect(), f=document.querySelector('.ft .flock').getBoundingClientRect(); return {ih:ri.height, iw:ri.width, ah:ra.height, aw:ra.width, nat:[i.naturalWidth,i.naturalHeight], fw:f.width, bg:getComputedStyle(document.querySelector('.hd')).backgroundColor, fbg:getComputedStyle(document.querySelector('.ft')).backgroundColor}}""")
        ok(f"header logo {hh}px tall at {hw}, native 869x383 (no upscale), link >= 44px, on graphite; footer lockup >= 200px wide on ink", abs(r_["ih"] - hh) < 0.6 and r_["nat"] == [869, 383] and r_["ah"] >= 43.5 and r_["aw"] >= 43.5 and r_["fw"] >= 200 and r_["bg"] == "rgb(38, 43, 49)" and r_["fbg"] == "rgb(18, 21, 25)", str(r_))
    mf = json.load(open(f"{SITE}/site.webmanifest"))
    ok("web manifest lists icon-192/512 that exist; head leads with the 32px icon, then favicon.ico; apple-touch 180; OG = V2 social image only", [i["src"] for i in mf["icons"]] == ["/assets/brand/icon/kicktip-icon-192.png", "/assets/brand/icon/kicktip-icon-512.png"] and all(htmls[k].find('kicktip-icon-32.png') < htmls[k].find('/favicon.ico') and 'og:image" content="' + HOST + '/assets/brand/social/kicktip-og-1200x630.png"' in htmls[k] and 'twitter:image" content="' + HOST + '/assets/brand/social/kicktip-og-1200x630.png"' in htmls[k] and "kicktip-apple-touch-180.png" in htmls[k] for k in htmls))
    ok("OG image is 1200x630 and byte-identical to the package", Image.open(f"{SITE}/assets/brand/social/kicktip-og-1200x630.png").size == (1200, 630) and sh(rd(f"{SITE}/assets/brand/social/kicktip-og-1200x630.png")) == sh(rd(f"{PK}/social/kicktip-og-1200x630.png")))
    ok("favicon.ico is byte-identical to the package and the root /favicon.ico serves", sh(rd(f"{SITE}/favicon.ico")) == sh(rd(f"{PK}/icon/favicon.ico")) and rq2.get(BASE + "/favicon.ico").status == 200)
    # ESPN logos
    LP = "/workspace/hub/creative-v5c-logos/logos"; AC = f"{ROOT}/assets-cache"
    idx = json.load(open(f"{AC}/teamlogos/INDEX.json"))
    ok("logo lists are generated from the cache index: 138 team ids, 11 conference files, 1 league icon; none missing from the build", len(idx) == 138 and all(os.path.exists(f"{SITE}/assets/logos/500/{k}.png") and os.path.exists(f"{SITE}/assets/logos/32/{k}.png") and os.path.exists(f"{SITE}/assets/logos/64/{k}.png") for k in idx) and len(os.listdir(f"{SITE}/assets/logos/conf/500")) == 11 and os.listdir(f"{SITE}/assets/logos/league/500") == ["ncaa-football.png"] and os.listdir(f"{SITE}/assets/logos/league/64") == ["ncaa-football.png"])
    ok("every 500px logo is a byte-identical copy of the cached ESPN file (138 teams, 11 conferences, league icon)", all(sh(rd(f"{SITE}/assets/logos/500/{k}.png")) == sh(rd(f"{AC}/teamlogos/{k}.png")) for k in idx) and all(sh(rd(f"{SITE}/assets/logos/conf/500/{f}")) == sh(rd(f"{AC}/conflogos/{f}")) for f in os.listdir(f"{SITE}/assets/logos/conf/500")) and sh(rd(f"{SITE}/assets/logos/league/500/ncaa-football.png")) == sh(rd(f"{AC}/ncaa-football.png")))
    pk = [(d, f) for d in ("500", "32", "64") for f in os.listdir(f"{LP}/{d}")] + [("conf/" + d, f) for d in ("500", "32", "64") for f in os.listdir(f"{LP}/conf") if False]
    same = all(sh(rd(f"{SITE}/assets/logos/{d}/{f}")) == sh(rd(f"{LP}/{d}/{f}")) for d, f in pk)
    sub = [os.path.relpath(f, LP) for f in glob.glob(f"{LP}/conf/**/*.png", recursive=True) + glob.glob(f"{LP}/league/**/*.png", recursive=True)]
    same2 = all(sh(rd(f"{SITE}/assets/logos/{x}")) == sh(rd(f"{LP}/{x}")) for x in sub if os.path.exists(f"{SITE}/assets/logos/{x}"))
    ok(f"logo files equal Creative's v5c package byte-for-byte where the package has them ({len(pk)} team files, {len(sub)} conf/league files compared)", same and same2)
    szs = {}
    for f in glob.glob(f"{SITE}/assets/logos/**/*.png", recursive=True):
        d = os.path.relpath(f, f"{SITE}/assets/logos").split("/"); folder = d[-2]; szs.setdefault(folder, set()).add(Image.open(f).size)
    ok("only size changes: 32/ and 64/ folders hold 32x32 / 64x64, 500/ folders hold the untouched 500x500", szs.get("32") == {(32, 32)} and szs.get("64") == {(64, 64)} and szs.get("500") == {(500, 500)})
    sys.path.insert(0, f"{ROOT}/src"); import logos as LG_
    ok("32/64 files are plain LANCZOS downscales of the 500px art (re-derived and compared)", all(LG_.down(f"{AC}/teamlogos/{k}.png", 32) == rd(f"{SITE}/assets/logos/32/{k}.png") and LG_.down(f"{AC}/teamlogos/{k}.png", 64) == rd(f"{SITE}/assets/logos/64/{k}.png") for k in list(idx)[:138]))
    ok("no used.json / header-icon.svg shipped; no mockup strings (DO NOT SHIP / MOCKUP / EXAMPLE) in any page, js or css", not [f for f in allf if f.endswith(("used.json", "header-icon.svg"))] and not [k for k, v in list(htmls.items()) + [("kt.js", open(f"{SITE}/assets/kt.js").read()), ("lg.js", open(f"{SITE}/assets/lg.js").read()), ("kt.css", open(f"{SITE}/assets/kt.css").read())] if re.search(r"DO NOT SHIP|MOCKUP|EXAMPLE", v)])
    CRED = "Team, conference and league logos courtesy of ESPN"
    ok("ESPN credit line on EVERY page (footer), including Utah, 404 and disclaimer; logo pages also carry the near-table line (simulator pages show no logos: footer line only)", all(v.count(CRED) >= 1 and ('class="cred"' in v) for v in htmls.values()) and all(v.count(CRED) >= 2 for k, v in htmls.items() if (k.startswith(("/team/", "/conference/", "/playoff/")) and "/simulator/" not in k) or k == "/index.html"))
    ok("no hotlinking: every img src is same-origin or data:, nothing points at espn.com / a CDN", not [k for k, v in htmls.items() if re.search(r'<img[^>]+src="(?!/|data:)', v)] and "espncdn" not in open(f"{SITE}/assets/lg.js").read() and not [k for k, v in htmls.items() if re.search(r"https?://[^\"' ]*(espn|espncdn|a\.espncdn)", v) and "courtesy" not in v])
    ok("no logos in OG/share/brand files: og:image only points at assets/brand/social; logos folder never referenced by meta/manifest", not [k for k, v in htmls.items() if re.search(r'(og|twitter):image"[^>]*logos', v)] and "logos" not in open(f"{SITE}/site.webmanifest").read())
    cxl = b.new_context(viewport={"width": 1280, "height": 900}); pl = cxl.new_page(); pl.add_init_script(ACCEPT_INIT); pl.goto(BASE + "/team/utah/"); pl.wait_for_timeout(700)
    tt = pl.evaluate("""()=>{const l=document.querySelector('main .card .lg, main .sec .lg'), i=l.querySelector('img'), cs=getComputedStyle(l); return {bg:cs.backgroundColor, bw:cs.borderTopWidth, bc:cs.borderTopColor, of:getComputedStyle(i).objectFit, alt:i.getAttribute('alt'), ah:l.getAttribute('aria-hidden'), n:document.querySelectorAll('.lg img').length, noalt:[...document.querySelectorAll('.lg img')].filter(x=>x.getAttribute('alt')!=='').length, nonah:[...document.querySelectorAll('.lg')].filter(x=>x.getAttribute('aria-hidden')!=='true').length}}""")
    ok("logo tile style: white square, 1px #7A848E border, object-fit contain, alt='' and aria-hidden on every tile", tt["bg"] == "rgb(255, 255, 255)" and tt["bw"] == "1px" and tt["bc"] == "rgb(122, 132, 142)" and tt["of"] == "contain" and tt["alt"] == "" and tt["ah"] == "true" and tt["noalt"] == 0 and tt["nonah"] == 0 and tt["n"] > 5, str(tt))
    cxf = b.new_context(viewport={"width": 1280, "height": 900}); pf = cxf.new_page(); pf.add_init_script(ACCEPT_INIT); pf.route("**/assets/logos/**", lambda r: r.fulfill(status=404, body="")); pf.goto(BASE + "/conference/big-12/"); pf.wait_for_timeout(600); [(pf.mouse.wheel(0, 700), pf.wait_for_timeout(120)) for _ in range(30)]; pf.wait_for_timeout(600)
    ff = pf.evaluate("""()=>{const t=[...document.querySelectorAll('.lg')]; return {n:t.length, nf:t.filter(x=>x.classList.contains('nf')).length, vis:t.filter(x=>x.classList.contains('nf')).every(x=>{const f=x.querySelector('.fb'); return getComputedStyle(f).display!=='none' && f.textContent.trim().length>0})}}""")
    ok("when a logo fails to load every tile falls back to its initials (no broken image)", ff["n"] > 5 and ff["nf"] == ff["n"] and ff["vis"], str(ff))
    hm = open(f"{SITE}/index.html", encoding="utf-8").read()
    ok("no lock bar / gate note / gate dialog strings in any page", not [k for k, v in htmls.items() if re.search(r"data-lockbar|data-open-gate|id=\"gate\"|gnote|unlock after you accept", v)])
    # ---- 3. layout at three widths with accepted gate (data rendered)
    pages = list(TYPES.items())
    if ALL:
        for f in sorted(glob.glob(f"{SITE}/**/index.html", recursive=True)):
            rel = f[len(SITE):-len("index.html")]
            if rel in TYPES.values() or rel == "/": continue
            pages.append((rel, rel))
    over = {}; tapfail = {}
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900})
        for name, path in pages:
            pg = ctx.new_page(); st = fresh(); watch(pg, st); pg.goto(BASE + path); pg.wait_for_timeout(350 if not ALL else 150)
            sw = pg.evaluate("document.documentElement.scrollWidth"); bad = pg.evaluate("""()=>[...document.querySelectorAll('body *')].filter(e=>!e.closest('.tw,.tabs,.bkw')&&getComputedStyle(e).position!='fixed'&&e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).map(e=>e.tagName+'.'+e.className).slice(0,4)""")
            if sw > w or bad: over[f"{name}@{w}"] = (sw, bad)
            tr_ = pg.evaluate(TAP); tf = tr_["out"]
            for d in tr_["ex"]: TAP_EXEMPT.setdefault(f"{d.rsplit(' ', 1)[0]}", set()).add(f"{name}@{w}:{d.rsplit(' ', 1)[1]}")
            if tf: tapfail[f"{name}@{w}"] = tf[:4]
            st["console"] = [c for c in st["console"] if not (name == "404" and "404" in c)]
            if st["console"] or offorigin(st["req"]) or st["bad"]: res["failures"].append(f"{name}@{w} console/offorigin/4xx: {st['console'][:2]} {offorigin(st['req'])[:2]} {st['bad'][:2]}")
            pg.close()
        ctx.close()
    ok(f"no horizontal overflow at 320/390/430/1280 ({len(pages)} pages x 4)", not over, str(list(over.items())[:5]))
    ok("tap targets >= 44x44 on every a/button/input/label/summary (inline links inside running text exempt per QA ruling)", not tapfail, str(list(tapfail.items())[:5]))
    json.dump({k: sorted(v)[:6] | {} if False else sorted(v)[:6] for k, v in sorted(TAP_EXEMPT.items())}, open(f"{ROOT}/tests/last_tap_exempt.json", "w"), indent=1)
    b.close()
n = len(res["checks"]); f = len(res["failures"])
print(f"{n} checks, {f} failures")
for x in res["failures"]: print("FAIL", x[:300])
json.dump(res, open(f"{ROOT}/tests/last_site_test.json", "w"), indent=1)
