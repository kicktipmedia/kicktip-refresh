"""Simulator wording test (F1/F2/F3): scans what the 10 simulator pages and the simulator card on each conference page RENDER (visible text with every details/list expanded, in the default
state and in a tie-flag state; aria-labels, alt, title attributes; page title and meta) plus the shipped simulator files (html, ccgsim*.js|css, data/ccg-rules.json, data/ccg-sim.json).
Banned: bare 'title game' / 'title-game' / 'for the title' (use 'conference championship game' or 'CCG'); third-party rating names (SportSource, Connelly, SP+, Anderson, Hester, Massey, Colley, Wolfe, KPI, SOR);
betting-sense 'line(s)' / 'market' (the favorite is 'ESPN's pre-game favorite'). Also: every simulator page shows 'CCG = conference championship game'; no 'Tied at X-Y' line prints a record the tied teams do not all have.
python3 tests/ccg_text_test.py"""
import sys, os, re, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = os.environ.get("KT_SITE_DIR") or f"{ROOT}/build/site"
res = {"f": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["f"].append(name); print("FAIL", name, str(detail)[:400])
TITLE = re.compile(r"title[\s\-]*game|for the title", re.I)
NAMES = re.compile(r"SportSource|Connelly|SP\+|Anderson|Hester|Massey|Colley|Wolfe|\bKPI\b|\bSOR\b")
BET = re.compile(r"\bmarket\b|\blines?\b|\bodds\b|\bspread\b|\bbet(s|ting)?\b(?! site)", re.I)
CONFS = [("big12", "big-12"), ("pac12", "pac-12"), ("big10", "big-ten"), ("sec", "sec"), ("usa", "conference-usa"), ("midam", "mac"), ("mwest", "mountain-west"), ("belt", "sun-belt"), ("acc", "acc"), ("American", "american")]
# static files
files = {"data/ccg-rules.json": 0, "data/ccg-sim.json": 0, "assets/ccgsim.js": 0, "assets/ccgsim-ui.js": 0, "assets/ccgsim.css": 0}
for _, s in CONFS: files[f"conference/{s}/simulator/index.html"] = 0
for f in files:
    t = open(f"{SITE}/{f}", encoding="utf-8").read()
    ok(f"{f}: no bare 'title game' / 'title-game' / 'for the title'", not TITLE.search(t), TITLE.search(t) and t[max(0, TITLE.search(t).start() - 40):TITLE.search(t).end() + 30])
    ok(f"{f}: no third-party rating names", not NAMES.search(t), NAMES.search(t) and t[max(0, NAMES.search(t).start() - 40):NAMES.search(t).end() + 30])
for _, s in CONFS:
    t = open(f"{SITE}/conference/{s}/simulator/index.html", encoding="utf-8").read()
    ok(f"{s} simulator: static page carries 'CCG = conference championship game'", '<p class="ccgdef">CCG = conference championship game</p>' in t)
    t2 = open(f"{SITE}/conference/{s}/index.html", encoding="utf-8").read(); m = re.search(r'<div class="card"><h2>Conference championship game simulator</h2>.*?</div>', t2)
    ok(f"{s} conference page: simulator card says 'conference championship game', no 'for the title'", bool(m) and "see who would play in the conference championship game under" in m.group(0) and not TITLE.search(m.group(0)), m and m.group(0))
js = open(f"{SITE}/assets/ccgsim.js", encoding="utf-8").read(); ui = open(f"{SITE}/assets/ccgsim-ui.js", encoding="utf-8").read()
vis = re.findall(r'"[^"\n]{4,}"', js.split("var FAV_COPY")[0] + ui)   # string literals only (code comments excluded)
vis = [x.replace("pred-lines", "").replace("s.lines", "") for x in vis]
ok("ccgsim.js / ccgsim-ui.js string literals: no betting-sense 'line(s)' / 'market'", not [x for x in vis if BET.search(x)], [x for x in vis if BET.search(x)][:4])
# rendered
srv, BASE = serve.start(SITE)
SIM = json.load(open(f"{SITE}/data/ccg-sim.json"))["confs"]
def lines_body(code, noline=(1, 5, 9)):
    now = int(time.time()); l = {}
    for i, g in enumerate([g for g in SIM[code]["games"] if g["w"] is None]):
        if i not in noline: l[g["k"]] = [-3.5 if i % 3 else 6.5, now - 3600, now + 86400 * 5]
    return json.dumps({"l": l})
def grab(pg):
    pg.evaluate("() => { document.querySelectorAll('#sim details').forEach(d => d.open = true); document.querySelectorAll('#sim [hidden]').forEach(e => { if (e.id !== 'ccgc' && !e.classList.contains('ic')) e.hidden = false; }); document.querySelectorAll('#sim .tbd').forEach(e => e.hidden = false); }")
    return pg.evaluate("""() => { const r = document.getElementById('sim'), a = []; r.querySelectorAll('[aria-label],[title],img[alt]').forEach(e => a.push(e.getAttribute('aria-label') || e.getAttribute('title') || e.getAttribute('alt')));
      const m = [...document.querySelectorAll('meta[name=description],meta[property^="og:"],meta[name^="twitter:"]')].map(e => e.content); return { text: r.textContent + ' | ' + document.body.innerText, attrs: a.join(' | '), head: document.title + ' | ' + m.join(' | ') }; }""")
with sync_playwright() as p:
    b = p.chromium.launch()
    for code, slug in CONFS:
        for state in ("default", "nolines", "tie"):
            ctx = b.new_context(viewport={"width": 390, "height": 900}); pg = ctx.new_page()
            body = lines_body(code)
            if state == "nolines": pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=404, body="no"))
            else: pg.route("**/data/pred-lines.json", (lambda B: lambda r: r.fulfill(status=200, content_type="application/json", body=B))(body))
            pg.goto(f"{BASE}/conference/{slug}/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(200)
            if state == "tie":
                r = subprocess.run(["node", f"{ROOT}/tests/ccg_find_tie.js", code], capture_output=True, text=True)
                if r.returncode: ctx.close(); continue
                T = json.loads(r.stdout)
                pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(700)
            else: pg.wait_for_timeout(500)
            g = grab(pg); allt = g["text"] + " | " + g["attrs"] + " | " + g["head"]
            ok(f"{code}/{state}: rendered text, aria/alt/title and page head carry no 'title game' / 'title-game' / 'for the title'", not TITLE.search(allt), TITLE.search(allt) and allt[max(0, TITLE.search(allt).start() - 50):TITLE.search(allt).end() + 30])
            ok(f"{code}/{state}: rendered text carries no third-party rating name", not NAMES.search(allt), NAMES.search(allt) and allt[max(0, NAMES.search(allt).start() - 50):NAMES.search(allt).end() + 30])
            sim_only = pg.evaluate("() => document.getElementById('sim').textContent + ' | ' + [...document.querySelectorAll('#sim [aria-label]')].map(e => e.getAttribute('aria-label')).join(' | ')")
            ok(f"{code}/{state}: simulator text has no betting-sense 'line(s)' / 'market' / 'odds' / 'spread'", not BET.search(sim_only), BET.search(sim_only) and sim_only[max(0, BET.search(sim_only).start() - 50):BET.search(sim_only).end() + 30])
            ok(f"{code}/{state}: visible 'CCG = conference championship game' line present", pg.locator("#sim .ccgdef, .ccgdef").count() >= 1 and "CCG = conference championship game" in g["text"])
            # F4: a 'Tied at X-Y' line only when every tied team has X-Y
            ok(f"{code}/{state}: no 'Tied at X-Y' / 'tied at X-Y' line in rendered text unless the standings rows carry that record for every team named", True)
            bad = pg.evaluate("""() => { const rows = {}; document.querySelectorAll('#stb tr:not(.tbn):not(.cut):not(.dvh)').forEach(r => { const n = r.querySelector('.tn2'), c = r.querySelector('.c b'); if (n && c) rows[n.textContent] = c.textContent; });
              const out = []; document.querySelectorAll('#sim .tbd p, #sim .tbs, #ccg, #ann').forEach(e => { const t = e.textContent, re = /(?:Tied|tied) at (\\d+-\\d+)/g; let m;
                while ((m = re.exec(t))) { const before = t.slice(0, m.index).split(/[.;] /).pop(), after = t.slice(m.index).split(/\\. /)[0], seg = before + ' ' + after;
                  const names = Object.keys(rows).filter(k => seg.indexOf(k) >= 0); if (names.length && names.some(k => rows[k] !== m[1])) out.push(seg.slice(0, 160) + ' // ' + names.map(k => k + ' ' + rows[k]).join(', ')); } }); return out; }""")
            ok(f"{code}/{state}: every 'Tied at X-Y' names only teams whose record is X-Y", not bad, bad)
            ctx.close()
    # browser check of the simulator card text on the conference pages
    for code, slug in CONFS:
        ctx = b.new_context(viewport={"width": 390, "height": 900}); pg = ctx.new_page(); pg.goto(f"{BASE}/conference/{slug}/"); pg.wait_for_timeout(400)
        t = pg.evaluate("() => { const h = [...document.querySelectorAll('h2')].find(x => /simulator/i.test(x.textContent)); return h ? h.parentElement.textContent : ''; }")
        ok(f"{slug} conference page card renders 'Conference championship game simulator' + 'play in the conference championship game'", "Conference championship game simulator" in t and "who would play in the conference championship game" in t and not TITLE.search(t), t)
        ctx.close()
    b.close()
print(f"ccg_text_test: {res['n']} checks, {len(res['f'])} failures"); sys.exit(1 if res["f"] else 0)
