"""b7: every position:sticky table cell has an opaque background that matches its row (normal, zebra, hover, focus). python3 tests/sticky_test.py"""
import sys, os, re, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
res = {"failures": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["failures"].append(f"{name} {detail}")
SCAN = """() => { const out = []; for (const c of document.querySelectorAll('td,th')) { const cs = getComputedStyle(c); if (cs.position !== 'sticky') continue;
  const tr = c.closest('tr'), tb = tr.parentElement.tagName, idx = [...tr.parentElement.children].indexOf(tr) + 1;
  out.push({tag: c.tagName, body: tb === 'TBODY', even: idx % 2 === 0, bg: cs.backgroundColor, z: cs.zIndex, sh: cs.boxShadow, left: cs.left, ok: c.getBoundingClientRect().width > 0, clip: c.scrollWidth - c.clientWidth, ov: cs.overflow, txt: (c.textContent||'').trim().slice(0,20)}); } return out; }"""
def alpha(bg):
    m = re.match(r"rgba?\(([^)]*)\)", bg); v = [x.strip() for x in m.group(1).replace("/", ",").split(",")] if m else []
    return 1.0 if len(v) == 3 else float(v[3]) if len(v) == 4 else 0.0
def rgb(bg): return tuple(int(float(x)) for x in re.findall(r"[\d.]+", bg)[:3])
WHITE, PALE, DARK = (255, 255, 255), (241, 243, 244), (38, 43, 49)
slugs = [os.path.basename(os.path.dirname(f)) for f in sorted(glob.glob(f"{SITE}/team/*/index.html"))]
PAGES = ["/", "/playoff/", "/method/"] + [f"/conference/{os.path.basename(os.path.dirname(f))}/" for f in sorted(glob.glob(f"{SITE}/conference/*/index.html"))] + [f"/team/{s}/" for s in slugs[::6]]
srv, BASE = serve.start(); total = 0; seen = {"tk-n": 0, "tk-g": 0}
with sync_playwright() as p:
    b = p.chromium.launch()
    for W in (390, 1280):
        c = b.new_context(viewport={"width": W, "height": 900}); c.add_init_script(ACC); pg = c.new_page()
        for path in PAGES:
            pg.goto(BASE + path); pg.wait_for_timeout(250)
            if pg.locator("main[data-gated]").count(): pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(250)
            cells = pg.evaluate(SCAN); total += len(cells)
            for k in seen: seen[k] += pg.locator(f".{k}").count()
            bad = [x for x in cells if alpha(x["bg"]) != 1.0]
            ok(f"{path}@{W}: every sticky cell has an opaque (alpha 1) background (normal + zebra)", not bad, str(bad[:2]))
            wrong = [x for x in cells if x["body"] and rgb(x["bg"]) != (PALE if x["even"] else WHITE)]
            ok(f"{path}@{W}: sticky body cells match their row (odd white, even #F1F3F4)", not wrong, str(wrong[:2]))
            ok(f"{path}@{W}: sticky header cells are the opaque dark header colour", not [x for x in cells if not x["body"] and rgb(x["bg"]) != DARK])
            ok(f"{path}@{W}: z-index (cells 2, header cells 3) and the edge shadow kept", not [x for x in cells if x["z"] != ("2" if x["body"] else "3")] and all(x["sh"] != "none" for x in cells if x["left"] not in ("0px",) ))
            ok(f"{path}@{W}: no clipped text in sticky cells (scrollWidth <= clientWidth)", not [x for x in cells if x["clip"] > 1], str([x for x in cells if x["clip"] > 1][:2]))
            # scrolled sideways: pinned cells still opaque and unclipped with content sliding underneath
            pg.evaluate("() => document.querySelectorAll('.tw').forEach(e => { e.scrollLeft = e.scrollWidth })"); now = pg.evaluate(SCAN)
            ok(f"{path}@{W}: scrolled fully right, sticky cells opaque and unclipped", not [x for x in now if alpha(x["bg"]) != 1.0 or x["clip"] > 1], str([x for x in now if alpha(x["bg"]) != 1.0 or x["clip"] > 1][:2]))
            pg.evaluate("() => document.querySelectorAll('.tw').forEach(e => { e.scrollLeft = 0 })")
            # hover and focus states on the first few pinned cells
            for i, (kind, act) in enumerate((("hover", "hover"), ("focus", "focus"))):
                st = pg.evaluate("""([kind]) => { const cs = [...document.querySelectorAll('td,th')].filter(c => getComputedStyle(c).position === 'sticky' && c.tagName === 'TD'); return cs.length }""", [kind])
                for j in (0, 1, 2, 3):
                    h = pg.evaluate("""([j]) => { const cs = [...document.querySelectorAll('td')].filter(c => getComputedStyle(c).position === 'sticky'); const c = cs[j]; if (!c) return null; c.scrollIntoView({block:'center'}); const r = c.getBoundingClientRect(); return [r.x + r.width/2, r.y + r.height/2] }""", [j])
                    if not h: continue
                    if act == "hover": pg.mouse.move(h[0], h[1])
                    else: pg.evaluate("""([j]) => { const cs = [...document.querySelectorAll('td')].filter(c => getComputedStyle(c).position === 'sticky'); const a = cs[j].closest('tr').querySelector('a'); if (a) a.focus(); }""", [j])
                    now = pg.evaluate(SCAN); bad = [x for x in now if alpha(x["bg"]) != 1.0 or (x["body"] and rgb(x["bg"]) not in (WHITE, PALE))]
                    ok(f"{path}@{W}: sticky cells stay opaque and row-matched in {kind} state ({j})", not bad, str(bad[:2]))
        c.close()
    b.close()
srv.shutdown()
ok("the site has sticky tables (tk-n and tk-g) to test", seen["tk-n"] > 0 and seen["tk-g"] > 0 and total > 200, str(seen) + f" cells={total}")
print(f"sticky_test: {res['n'] - len(res['failures'])}/{res['n']} checks pass ({total} sticky cells, {seen} tables)")
for f in res["failures"][:10]: print("FAIL:", f)
sys.exit(1 if res["failures"] else 0)
