"""c1r1d: the chat's numbers must match the pages' pred-* data (same data, same as_of). Static: what-if baselines (6,000 seasons) vs data/pred-teams.json (10,000) for blend/elo/eff, z-test;
browser: the 'before' column of a real chat answer (live run, 4-10k seasons) vs the same pred-teams.json for Utah under each model (?model=)."""
import sys, os, re, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
res = []; fails = []
def ok(n, c, d=""):
    res.append(n)
    if not c: fails.append(f"{n} {d}")
def z(a, b, Na, Nb):
    p = (a * Na + b * Nb) / (Na + Nb); v = max(p * (1 - p), 0.5 / (Na + Nb)) * (1 / Na + 1 / Nb); return abs(a - b) / math.sqrt(v)
MAP = {"ccg": "c", "title": "w", "cfp12": "p", "bye": "b"}
MP = {"blend": ("data", "data"), "elo": ("data/m/elo", "data/m/elo"), "eff": ("data/m/eff", "data/m/eff")}
for mid, (bd, pd_) in MP.items():
    wi = json.load(open(f"{SITE}/{bd}/whatif/index.json")); pt = json.load(open(f"{SITE}/{pd_}/pred-teams.json")); b = json.load(open(f"{SITE}/{bd}/sim-bundle.json"))
    ok(f"{mid}: as_of equal everywhere", b["as_of"] == wi["as_of"] == "2026-10-24 17:55 MT" and pt["model_asof"].startswith("Sat, Oct 24, 2026, 5:55 PM MT"), f"{b['as_of']} {wi['as_of']} {pt['model_asof']}")
    slug = {t["n"] if "g" not in t else t["g"]: i for i, t in enumerate(b["teams"])}
    worst = (0, ""); n = 0
    for sl, row in pt["teams"].items():
        i = slug.get(sl); 
        if i is None: continue
        for mi, m in enumerate(wi["metrics"]):
            a = wi["baseline"][i][mi] / 1000; bb = row.get(MAP[m])
            if bb is None: continue
            n += 1; zz = z(a, bb, wi["seasons"], pt["seasons"])
            if zz > worst[0]: worst = (zz, f"{sl} {m} {a} vs {bb}")
    ok(f"{mid}: {n} what-if baseline values vs pred-teams, max z {worst[0]:.2f} ({worst[1]}) <= 4.5", n > 400 and worst[0] <= 4.5, str(worst))
srv, BASE = serve.start()
with sync_playwright() as p:
    br = p.chromium.launch()
    for mid in ("blend", "elo", "eff"):
        pt = json.load(open(f"{SITE}/{'data' if mid == 'blend' else 'data/m/' + mid}/pred-teams.json"))["teams"]["utah"]
        ctx = br.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script(ACC); pg = ctx.new_page()
        pg.goto(BASE + "/team/utah/" + ("" if mid == "blend" else f"?model={mid}")); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector(".q")
        pg.fill("#kask", "What if Utah Utes lose to Houston?"); pg.click("#kform .snd"); pg.wait_for_selector(".ba", timeout=90000); pg.wait_for_function("!document.querySelector('.prog')", timeout=90000)
        rows = pg.evaluate("() => [...document.querySelectorAll('#kbd table')][0] ? [...document.querySelectorAll('#kbd table')][0].innerText : ''")
        t0 = pg.evaluate("() => [...document.querySelectorAll('#kbd table')].map(t => { let h = t.previousElementSibling; while (h && !/^H\\d$/.test(h.tagName) && !h.classList.contains('tn')) h = h.previousElementSibling; return [h ? h.textContent.trim() : (t.querySelector('caption') ? t.querySelector('caption').textContent.trim() : ''), [...t.querySelectorAll('tbody tr')].map(r => [...r.children].map(c => c.textContent.trim()))]; })")
        tab = next((r for h, r in t0 if h.startswith("Utah")), None); ok(f"browser {mid}: a table for Utah exists in the answer", tab is not None, str([h for h, r in t0]))
        got = {}
        for r in tab or []:
            m = re.search(r"([\d.]+)%", r[1]); lab = r[0].lower()
            if m: got["c" if "title game" in lab else "w" if "win conference" in lab else "p" if "playoff" in lab else "b" if "bye" in lab else lab] = float(m.group(1)) / 100
        N = int(re.search(r"([\d,]+) simulated seasons", pg.text_content("#kbd")).group(1).replace(",", ""))
        for k in ("c", "w", "p"):
            ok(f"browser {mid}: Utah '{k}' before-number {got.get(k)} (N={N}) vs pred-teams {pt[k]}: z {z(got[k], pt[k], N, 10000):.2f} <= 4.5", k in got and z(got[k], pt[k], N, 10000) <= 4.5)
        ok(f"browser {mid}: answer as-of is 5:55 PM MT", "5:55 PM MT" in pg.text_content("#kbd"), pg.text_content("#kbd")[-300:]); ctx.close()
    br.close()
srv.shutdown(); print(f"pred_match_c1d: {len(res) - len(fails)}/{len(res)} checks pass")
for f in fails: print("FAIL:", f)
sys.exit(1 if fails else 0)
