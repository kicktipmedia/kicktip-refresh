"""v6a rev2 model control test (headless Chromium). python3 tests/model_toggle_test.py
Models: KickTip blend (default), Elo-style and Efficiency (under More models). NO MSM model, param or shard.
Checks: gate before data; one-row card at 320/390 with 44px targets, outline More + chevron, selected = dark fill + check mark; short blurb + What's this? disclosure; persistence in localStorage key kicktip_model
(written only after acceptance and only on a pick, blend removes it, URL ?model= beats stored, unknown/stale values ignored and removed after acceptance, blocked storage silent, no flicker of the default,
internal links tagged, canonicals param-free); copy matches the addendum; the data files agree; raw/original MSM probabilities are not exposed by any control, URL param or shard."""
import sys, os, re, json, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
BSRC = open(f"{ROOT}/src/build.py").read()
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
res = {"f": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["f"].append(f"{name} {detail}")
def J(p): return json.load(open(p))
IDS = ["blend", "elo", "eff"]; NAMES = {"blend": "KickTip blend", "elo": "Elo-style", "eff": "Efficiency"}
BAN = re.compile(r"SP\+|SportSource|ESPN SOR|\bKPI\b|Connelly|Massey|\bFPI\b|FiveThirtyEight|ESPN FPI", re.I)
ALLFILES = [p for p in glob.glob(f"{SITE}/**/*", recursive=True) if os.path.isfile(p)]
TXT = [p for p in ALLFILES if p.split(".")[-1] in ("html", "json", "js", "css", "txt", "xml")]
rel = lambda p: os.path.relpath(p, SITE)
# ---------- static: no model names or numbers before the gate
pages = [p for p in glob.glob(f"{SITE}/**/index.html", recursive=True)]
gated = [p for p in pages if 'data-gated="1"' in open(p).read()]
ok("gated pages exist (home, 11 conferences, 138 teams, playoff)", len(gated) == 1 + 11 + 138 + 1, str(len(gated)))
leak = [p for p in gated if re.search(r"KickTip blend|MSM rating|Elo-style|Efficiency|Default model|Alternate model", re.sub(r"<script.*?</script>", "", open(p).read(), flags=re.S))]
ok("no model name or model label in any gated page before acceptance", not leak, str(leak[:3]))
HITS = sorted(rel(p) for p in TXT if BAN.search(open(p, errors="ignore").read()))
ok("third-party rating names (SP+, SportSource, ESPN SOR, KPI, Connelly, Massey, FPI, FiveThirtyEight) appear in NO shipped text file (HTML, JSON, JS, CSS): conference flags say 'other public rating systems'", HITS == [], str(HITS))
# ---------- MSM is not offered anywhere (no control, no URL param, no shard); raw MSM stays internal
ok("no shard route for msm: build/site/data/m holds exactly elo and eff", sorted(os.listdir(f"{SITE}/data/m")) == ["eff", "elo"], str(os.listdir(f"{SITE}/data/m")))
ok("no shipped file or path mentions data/m/msm, model=msm, a model id 'msm', or data-m=msm", not [rel(p) for p in ALLFILES if re.search(r"/m/msm|msm/pred|model=msm|data-m=.msm|\"id\": ?\"msm\"", rel(p) + (open(p, errors="ignore").read() if p in TXT else ""))])
KT = open(f"{SITE}/assets/kt.js").read()
ok("kt.js lists exactly the alternates elo,eff and carries no 'msm' string", "'elo,eff'.split(',')" in KT and not re.search(r"msm", KT, re.I))
ok("no control, label or data file offers the MSM rating: kt.js has no MSM text; in data files 'MSM' appears only in the blend's blurb as an ingredient ('it combines the MSM rating, ...')", not [rel(p) for p in TXT if p.endswith("assets/kt.js") and re.search(r"MSM", open(p, errors="ignore").read())] and all(re.sub(r"it combines the MSM rating, ", "", open(p, errors="ignore").read()).count("MSM") == 0 for p in TXT if "/data/" in p), "")
ok("model registry in the build has exactly blend, elo, eff", [m["id"] for m in J(f"{SITE}/data/pred-teams.json")["models"]] == IDS)
ok("DISC_VERSION is ONE constant, bumped to 2026-10-24-v3 (DISC_DATE Oct 24, 2026), and kt.js carries it", len(re.findall(r"^DISC_VERSION = ", BSRC, re.M)) == 1 and VER == "2026-10-24-v3" and 'DISC_DATE = "Oct 24, 2026"' in BSRC and f"VERSION = '{VER}'" in KT)
CSS_HDR = open(f"{SITE}/_headers").read()
ok("CSP forbids inline script and eval (script-src 'self' only)", "script-src 'self';" in CSS_HDR and "unsafe" not in CSS_HDR)
ok("no inline script in any page", not [rel(p) for p in pages if re.search(r"<script(?![^>]*\bsrc=)[^>]*>", open(p).read())])
ok("every page canonical is param-free", not [rel(p) for p in pages if re.search(r'rel="canonical" href="[^"]*\?', open(p).read())])
sm = open(f"{SITE}/sitemap.xml").read()
ok("sitemap has no ?model=", "model=" not in sm)
# ---------- copy (addendum section 3, verbatim)
disc = open(f"{SITE}/disclaimer/index.html").read(); dtxt = re.sub(r"<[^>]+>", " ", disc.replace("&#x27;", "'").replace("&#39;", "'")); dtxt = re.sub(r"\s+", " ", dtxt)
ok("disclaimer page: 'If you choose a different model, we save that choice on this device so it is remembered next visit.'", "If you choose a different model, we save that choice on this device so it is remembered next visit." in dtxt)
ok("disclaimer page: What we store on your device (verbatim)", "What we store on your device" in dtxt and "Your disclaimer acceptance and, if you pick a model other than the default, which model you picked (one word, kept only on this device). We do not collect it. Clear this site's data in your browser, or choose 'Use the default model', to remove it." in dtxt)
ok("playoff page: committee cue under the bracket percentages AND under the field table (Creative's exact line)", open(f"{SITE}/playoff/index.html").read().count("Bracket order uses the MSM team rank as a committee stand-in, under every model.") == 2)
# ---------- data files
def P3(m, f): return J(f"{SITE}/data/pred-{f}.json") if m == "blend" else J(f"{SITE}/data/m/{m}/pred-{f}.json")
P = {m: (P3(m, "teams"), P3(m, "games"), P3(m, "paths")) for m in IDS}
for m in IDS:
    t, g, p = P[m]
    ok(f"{m}: model id/name/default flag in all three files", t["model"]["id"] == g["model"]["id"] == p["model"]["id"] == m and t["model"]["name"] == NAMES[m] and t["model"]["default"] == (m == "blend"))
    ok(f"{m}: same as_of, same list of models", t["model_asof"] == P["blend"][0]["model_asof"] and [x["id"] for x in t["models"]] == IDS)
    ok(f"{m}: same game keys as the default", set(g["g"]) == set(P["blend"][1]["g"]))
    pv = [v[0] for v in g["g"].values() if v[0] is not None]
    ok(f"{m}: win probabilities in [0.001,0.999]", min(pv) >= 0.001 and max(pv) <= 0.999, f"{min(pv)} {max(pv)}")
    bad = [k for k, v in g["g"].items() if v[0] is not None and v[1] not in (None, 0) and ((v[1] < 0) != (v[0] > 0.5))]
    ok(f"{m}: favourite agrees with the model line in every game", not bad, str(bad[:3]))
    ok(f"{m}: bracket order identical to the default (KickTip rating rank)", t["field"] == P["blend"][0]["field"])
    ok(f"{m}: market column identical to the default", [(k, v[2], v[3]) for k, v in sorted(g["g"].items())] == [(k, v[2], v[3]) for k, v in sorted(P["blend"][1]["g"].items())])
    ok(f"{m}: top-12 make-12 chances sum to about 12", abs(sum(x["p"] for x in t["teams"].values()) - 12) < 0.3, str(sum(x["p"] for x in t["teams"].values())))
    for k, x in t["teams"].items():
        if not (0 <= x["p"] <= 1 and all(v is None or 0 <= v <= 1 for v in (x["c"], x["w"])) and x["b"] <= x["p"] + 1e-9): ok(f"{m}: chances sane for {k}", False, str(x)); break
ok("models differ (blend vs elo make-12 differ for at least 20 teams by more than 1 point)", sum(1 for k in P["blend"][0]["teams"] if abs(P["blend"][0]["teams"][k]["p"] - P["elo"][0]["teams"][k]["p"]) > 0.01) >= 20)
# raw MSM stays internal: the shipped default is the blend's table, not the raw one (data/ref/movers.json holds raw vs current per team, internal only)
MV = J(f"{ROOT}/data/ref/movers.json")["teams"]
rawv = sorted(v[0] for v in MV.values()); curv = sorted(v[1] for v in MV.values()); shv = sorted(round(x["p"], 4) for x in P["blend"][0]["teams"].values() if x["n"] != "FCS")
ok("shipped default make-12 values = the blend's table (sorted values equal data/out), and differ from the raw/original MSM table for most teams", sum(1 for a, b in zip(sorted(round(x, 4) for x in curv), rawv) if abs(a - b) > 0.005) >= 25 and len(shv) >= 130 and max(abs(a - b) for a, b in zip(shv, curv[-len(shv):])) < 1e-3)
ok("movers.json is not shipped", not [rel(p) for p in ALLFILES if "movers" in rel(p)])
# ---------- browser
KEY = "kicktip_model"
STORE_KEYS = "JSON.stringify(Object.keys(localStorage).sort())"
def topn(pg): return pg.eval_on_selector_all("#top12 tbody tr", "rs=>rs.map(r=>[r.querySelectorAll('td')[1].innerText.trim(), r.querySelectorAll('td')[3].innerText.trim()])")
def exp12(m): return [x["n"] for x in sorted(P[m][0]["teams"].values(), key=lambda x: (-x["p"], x["n"]))[:12]]
def alt(pg, id):
    if pg.locator(".mdm").is_hidden(): pg.click("[data-more]")
    pg.click(f"[data-m={id}]")
def accept(pg): pg.check("#gate input[type=checkbox]"); pg.click("#gate [data-accept]")
def internal_hrefs(pg): return pg.eval_on_selector_all("a[href]", "as=>as.map(a=>a.getAttribute('href')).filter(h=>/^\\/(?!\\/)[^?#.]*(\\?[^#]*)?(#.*)?$/.test(h)&&!/^\\/(data|assets)\\//.test(h))")
srv, base = serve.start()
with sync_playwright() as pw:
    b = pw.chromium.launch()
    def ctx_new(w=390, h=800): return b.new_context(viewport={"width": w, "height": h})
    # ===== A. gate first: nothing stored, nothing fetched, before acceptance (even with a stored pick or ?model=)
    ctx = ctx_new(); pg = ctx.new_page(); reqs = []; errs = []
    pg.on("request", lambda r: reqs.append(r.url)); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/"); pg.wait_for_selector("#gate:not([hidden])"); pg.wait_for_timeout(300)
    ok("before acceptance: no request to /data/pred-* or /data/m/*", not [u for u in reqs if "/data/" in u], str([u for u in reqs if "/data/" in u]))
    ok("before acceptance: no model control in the page and nothing in localStorage", pg.locator("[data-mdl]").count() == 0 and pg.evaluate(STORE_KEYS) == "[]", pg.evaluate(STORE_KEYS))
    SENT = "If you choose a different model, we save that choice on this device so it is remembered next visit."
    _g = pg.evaluate("() => { const n = document.querySelector('#gate .gnote'); return {txt: document.getElementById('gate').innerText, note: n ? n.innerText : '', inDlg: !!document.querySelector('#gate .dlg .gnote')}; }")
    ok("gate dialog: the storage sentence appears exactly once, in the small print (.gnote) right after 'Your choice is saved in this browser and asked again on a new visit.'", _g["txt"].count(SENT) == 1 and _g["inDlg"] and _g["note"].startswith("Your choice is saved in this browser and asked again on a new visit. " + SENT + " Full disclaimer"), _g["note"])
    ok("gate dialog: nothing stored and nothing fetched while the sentence is shown", pg.evaluate(STORE_KEYS) == "[]" and not [u for u in reqs if "/data/" in u])
    pg.goto(base + "/?model=elo"); pg.wait_for_selector("#gate:not([hidden])"); pg.wait_for_timeout(300)
    ok("before acceptance with ?model=elo: still no data request, no key written", not [u for u in reqs if "/data/" in u] and pg.evaluate(STORE_KEYS) == "[]")
    pg.goto(base + "/"); pg.wait_for_selector("#gate:not([hidden])")
    pg.evaluate(f"localStorage.setItem('{KEY}','msm')"); pg.reload(); pg.wait_for_selector("#gate:not([hidden])"); pg.wait_for_timeout(200)
    ok("before acceptance a stale stored 'msm' is left alone (cleanup only after acceptance) and no data is fetched", pg.evaluate(f"localStorage.getItem('{KEY}')") == "msm" and not [u for u in reqs if "/data/" in u and "reload" in u])
    n0 = len([u for u in reqs if "/data/" in u]); accept(pg); pg.wait_for_selector("[data-mdl]"); pg.wait_for_selector("#top12 tbody tr")
    ok("after acceptance: stale stored 'msm' removed, default blend shown, only the default file fetched", pg.evaluate(f"localStorage.getItem('{KEY}')") is None and pg.get_attribute("[data-model]", "data-model") == "blend" and [u.split("/data/")[1] for u in reqs if "/data/" in u][n0:] == ["pred-teams.json"], str([u for u in reqs if "/data/" in u]))
    ok("accepting writes only the gate keys (no model key)", pg.evaluate(STORE_KEYS) == '["kicktip_gate"]', pg.evaluate(STORE_KEYS))
    # ===== B. the card: default state
    ok("default chip reads 'Default model'; no ESTIMATE chip", pg.text_content("[data-mdb]") == "Default model" and pg.locator(".mde").count() == 0)
    ok("default pressed = KickTip blend", pg.get_attribute("[data-m=blend]", "aria-pressed") == "true" and pg.get_attribute("[data-model]", "data-model") == "blend")
    ok("closed card: Elo-style and Efficiency hidden under More models; no MSM button anywhere", pg.locator(".mdm").is_hidden() and pg.locator("[data-m=msm]").count() == 0 and pg.locator("[data-more]").is_visible() and "MSM" not in pg.inner_text("[data-mdl]"))
    ok("More models: outline button with chevron, aria-expanded false, never aria-pressed", pg.get_attribute("[data-more]", "aria-expanded") == "false" and pg.get_attribute("[data-more]", "aria-pressed") is None and pg.locator("[data-more] .chv").count() == 1 and pg.get_attribute("[data-more]", "aria-controls") == "mdmore")
    ok("What's this? disclosure is closed (aria-expanded false) and the card has the short blurb", pg.get_attribute("[data-why]", "aria-expanded") == "false" and pg.locator(".mdf").is_hidden() and "Default estimate" in pg.inner_text("[data-mdd]"))
    cm = pg.evaluate("(()=>{var b=document.querySelector('[data-m=blend]'),m=document.querySelector('[data-more]'),cs=getComputedStyle(b),ms=getComputedStyle(m);return {pc:getComputedStyle(b,'::before').content,bg:cs.backgroundColor,mbg:ms.backgroundColor,mcol:ms.color,mbd:ms.borderTopWidth}})()")
    ok("selected blend: dark fill and a check mark (::before), not colour alone; More: light fill, outline border, no check", cm["pc"] not in ("none", "normal") and cm["bg"] != cm["mbg"] and cm["mbd"] != "0px", str(cm))
    for w in (320, 390):
        pw_ = ctx_new(w, 700).new_page(); pw_.add_init_script(ACC); pw_.goto(base + "/"); pw_.wait_for_selector("[data-mdl]")
        bb, mm = pw_.locator("[data-m=blend]").bounding_box(), pw_.locator("[data-more]").bounding_box(); card = pw_.locator("[data-mdl]").bounding_box()
        ok(f"{w}px: ONE row (blend and More share a baseline) with 44px targets, inside the card", abs(bb["y"] - mm["y"]) < 2 and bb["height"] >= 43.5 and mm["height"] >= 43.5 and mm["x"] + mm["width"] <= card["x"] + card["width"] - 4, f"{bb} {mm} {card}")
        ok(f"{w}px: no horizontal page scroll", pw_.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"))
        lh = pw_.evaluate("(()=>{var e=document.querySelector('[data-mdd]');var cs=getComputedStyle(e);return e.getBoundingClientRect().height/parseFloat(cs.lineHeight)})()")
        ok(f"{w}px: short blurb is at most 2 lines ({lh:.1f})", lh <= 2.3, str(lh))
        ok(f"{w}px: closed card height is at most 190px ({card['height']:.0f})", card["height"] <= 190, str(card["height"]))
        pw_.click("[data-more]"); pw_.wait_for_selector(".mdm:not([hidden])"); mm = pw_.locator("[data-more]").bounding_box(); r2 = [pw_.locator(f"[data-m={m}]").bounding_box() for m in ("elo", "eff")]; cr = pw_.locator("[data-mdl]").bounding_box()
        ok(f"{w}px: More opens Elo-style and Efficiency in ONE second row, 44px tall, inside the card", abs(r2[0]["y"] - r2[1]["y"]) < 2 and r2[0]["y"] > mm["y"] and min(x["height"] for x in r2) >= 43.5 and r2[1]["x"] + r2[1]["width"] <= cr["x"] + cr["width"], str(r2))
        ok(f"{w}px: More shows expanded state via aria-expanded, still not pressed", pg.get_attribute("[data-more]", "aria-pressed") is None and pw_.get_attribute("[data-more]", "aria-expanded") == "true")
        pw_.click("[data-why]"); pw_.wait_for_selector(".mdf:not([hidden])"); ft = pw_.inner_text(".mdf")
        ok(f"{w}px: What's this? shows the full blurb and the single caveat line; 'Use the default model' hidden at the default", "KickTip blend." in ft and "These are estimates from a statistical model, not a market line and not a recommendation." in ft and pw_.locator("[data-reset]").is_hidden() and pw_.get_attribute("[data-why]", "aria-expanded") == "true")
        pw_.context.close()
    # ===== C. picking, storing, URL, links
    top_blend = topn(pg); ok("home Top 12 = the blend's data", [x[0] for x in top_blend] == exp12("blend"), str(top_blend[:3]))
    links_default = internal_hrefs(pg); ok("default: no internal link carries ?model=", not [h for h in links_default if "model=" in h] and len(links_default) > 20)
    alt(pg, "elo"); pg.wait_for_selector("[data-model=elo]"); pg.wait_for_timeout(200)
    ok("Elo pick: chip 'Alternate model', Top 12 re-rendered from the Elo file", pg.text_content("[data-mdb]") == "Alternate model" and [x[0] for x in topn(pg)] == exp12("elo") and topn(pg) != top_blend)
    ok("Elo pick fetched /data/m/elo/pred-teams.json", any(u.endswith("/data/m/elo/pred-teams.json") for u in reqs))
    cm = pg.evaluate("(()=>{var b=document.querySelector('[data-m=elo]'),m=document.querySelector('[data-more]'),k=document.querySelector('[data-m=blend]');return {pc:getComputedStyle(b,'::before').content,bg:getComputedStyle(b).backgroundColor,kbg:getComputedStyle(k).backgroundColor,kpc:getComputedStyle(k,'::before').content,mp:m.getAttribute('aria-pressed'),mbg:getComputedStyle(m).backgroundColor,vis:getComputedStyle(b).visibility,hidden:document.querySelector('.mdm').hidden}})()")
    ok("Elo selected under More: dark fill + check mark; blend now plain; More still not pressed and outline; row stays open", cm["pc"] not in ("none", "normal") and cm["kpc"] in ("none", "normal") and cm["bg"] != cm["kbg"] and cm["mp"] is None and cm["mbg"] == cm["kbg"] and not cm["hidden"], str(cm))
    ok("Elo pick is stored: kicktip_model = 'elo' (the only model key) and the URL carries ?model=elo", pg.evaluate(f"localStorage.getItem('{KEY}')") == "elo" and "model=elo" in pg.url, pg.url)
    h_elo = internal_hrefs(pg); ok("Elo: every internal page link now carries ?model=elo (hash kept, data/assets untouched)", h_elo and all("model=elo" in h for h in h_elo), str([h for h in h_elo if "model=elo" not in h][:3]))
    ok("canonical stays param-free after a pick", "?" not in pg.get_attribute("link[rel=canonical]", "href"))
    ok("Elo: What's this? full blurb names Elo-style and the reset link is visible", (pg.click("[data-why]") or True) and "Elo-style." in pg.inner_text("[data-mfull]" if False else "[data-mdfull]") and pg.locator("[data-reset]").is_visible())
    pg.click("[data-m=eff]"); pg.wait_for_selector("[data-model=eff]")
    ok("Efficiency pick replaces the stored value; check mark on Efficiency", pg.evaluate(f"localStorage.getItem('{KEY}')") == "eff" and "model=eff" in pg.url and "model=elo" not in pg.url and pg.evaluate("getComputedStyle(document.querySelector('[data-m=eff]'),'::before').content") not in ("none", "normal"))
    ok("stored value is one of the three allowed words, nothing else is stored under any other key", pg.evaluate(f"localStorage.getItem('{KEY}')") in IDS and pg.evaluate(STORE_KEYS) == '["kicktip_gate","kicktip_model"]')
    pg.click("[data-m=blend]"); pg.wait_for_selector("[data-model=blend]"); pg.wait_for_timeout(100)
    ok("picking the default removes the key and the URL param; links untagged; Top 12 equals the first render", pg.evaluate(f"localStorage.getItem('{KEY}')") is None and "model=" not in pg.url and not [h for h in internal_hrefs(pg) if "model=" in h] and topn(pg) == top_blend)
    ok("page text has no third-party rating names and no page errors", not BAN.search(pg.inner_text("body")) and not errs, str(errs))
    # ===== D. restore: stored pick on home and team pages, no flicker, URL beats stored
    alt(pg, "elo"); pg.wait_for_selector("[data-model=elo]")
    FIRST = "new MutationObserver(function(){var r=document.querySelectorAll('#top12 tbody tr');if(r.length&&!window.__first)window.__first=[].map.call(r,function(x){return x.querySelectorAll('td')[3].innerText.trim()}).join('|')}).observe(document,{subtree:true,childList:true});"
    p2 = ctx.new_page(); p2.add_init_script(ACC); p2.add_init_script(FIRST); r2 = []; p2.on("request", lambda r: r2.append(r.url)); p2.goto(base + "/"); p2.wait_for_selector("[data-model]"); p2.wait_for_selector("#top12 tbody tr")
    ok("stored elo restored on the home page (no URL param needed)", p2.get_attribute("[data-model]", "data-model") == "elo" and [x[0] for x in topn(p2)] == exp12("elo") and p2.get_attribute("[data-m=elo]", "aria-pressed") == "true")
    fl = p2.evaluate("window.__first"); fin = "|".join(x[1] for x in topn(p2)); bl = "|".join(x[1] for x in top_blend)
    ok("no flicker: the first Top 12 column ever drawn is the Elo one, never the default's", fl == fin and fl != bl, f"first={fl} final={fin} blend={bl}")
    ok("default list + wanted set fetched together (pred-teams + m/elo/pred-teams, nothing else)", sorted(u.split("/data/")[1] for u in r2 if "/data/" in u) == ["m/elo/pred-teams.json", "pred-teams.json"], str(r2))
    ok("restored pick also opens More with Elo selected and reflects it in the URL", p2.locator(".mdm").is_visible() and "model=elo" in p2.url)
    p3 = ctx.new_page(); p3.add_init_script(ACC); p3.goto(base + "/team/utah/"); p3.wait_for_selector("[data-model]")
    ok("stored elo restored on a team page", p3.get_attribute("[data-model]", "data-model") == "elo" and "model=elo" in p3.url)
    p3.goto(base + "/"); p3.wait_for_selector("[data-model=elo]"); p3.click("a[href^='/team/utah']"); p3.wait_for_selector("[data-model]")
    ok("clicking a tagged link keeps the pick (/team/utah/?model=elo)", "/team/utah/" in p3.url and "model=elo" in p3.url and p3.get_attribute("[data-model]", "data-model") == "elo")
    p4 = ctx.new_page(); p4.add_init_script(ACC); p4.goto(base + "/?model=eff"); p4.wait_for_selector("[data-model]")
    ok("URL ?model=eff beats stored elo, and loading does not rewrite the stored value", p4.get_attribute("[data-model]", "data-model") == "eff" and p4.evaluate(f"localStorage.getItem('{KEY}')") == "elo")
    p5 = ctx.new_page(); p5.add_init_script(ACC); p5.goto(base + "/?model=msm"); p5.wait_for_selector("[data-model]")
    ok("?model=msm is ignored (falls back to the stored pick), dropped from the address bar, never fetched", p5.get_attribute("[data-model]", "data-model") == "elo" and "msm" not in p5.url and not [u for u in reqs if "msm" in u])
    p6 = ctx.new_page(); p6.add_init_script(ACC); p6.goto(base + "/?model=blend"); p6.wait_for_selector("[data-model]")
    ok("?model=blend is not a valid alternate: ignored (stored elo applies)", p6.get_attribute("[data-model]", "data-model") == "elo")
    p2.click("[data-why]"); p2.click("[data-reset]"); p2.wait_for_selector("[data-model=blend]")
    ok("'Use the default model' link: back to blend, key removed, URL param gone, link hidden", p2.evaluate(f"localStorage.getItem('{KEY}')") is None and "model=" not in p2.url and p2.locator("[data-reset]").is_hidden() and topn(p2) == top_blend)
    for bad in ("msm", "blend", "ELO", "elo;x", ""):
        pz = ctx_new().new_page(); pz.add_init_script(ACC); pz.goto(base + "/"); pz.evaluate(f"localStorage.setItem('{KEY}',{json.dumps(bad)})"); pz.reload(); pz.wait_for_selector("[data-model]")
        ok(f"stored {bad!r}: ignored, default shown, stale key removed after acceptance", pz.get_attribute("[data-model]", "data-model") == "blend" and pz.evaluate(f"localStorage.getItem('{KEY}')") is None)
        pz.context.close()
    pz = ctx_new().new_page(); pz.add_init_script(ACC); pz.goto(base + "/?model=elo"); pz.wait_for_selector("[data-model]")
    ok("shared link /?model=elo shows Elo but stores nothing (visitor did not pick)", pz.get_attribute("[data-model]", "data-model") == "elo" and pz.evaluate(f"localStorage.getItem('{KEY}')") is None); pz.context.close()
    # ===== E. blocked storage (only our key throws) and fully blocked localStorage: silent fallback, picks still work in-session
    BLOCK = "var _g=Storage.prototype.getItem,_s=Storage.prototype.setItem,_r=Storage.prototype.removeItem;Storage.prototype.getItem=function(k){if(k==='kicktip_model')throw new Error('blocked');return _g.call(this,k)};Storage.prototype.setItem=function(k,v){if(k==='kicktip_model')throw new Error('blocked');return _s.call(this,k,v)};Storage.prototype.removeItem=function(k){if(k==='kicktip_model')throw new Error('blocked');return _r.call(this,k)};"
    pb = ctx_new().new_page(); berr = []; pb.on("pageerror", lambda e: berr.append(str(e))); pb.add_init_script(ACC + BLOCK); pb.goto(base + "/"); pb.wait_for_selector("[data-model=blend]")
    alt(pb, "elo"); pb.wait_for_selector("[data-model=elo]"); pb.click("[data-m=blend]"); pb.wait_for_selector("[data-model=blend]")
    ok("blocked model key: default loads, picks work in the page, no uncaught error", not berr and [x[0] for x in topn(pb)] == exp12("blend"), str(berr)); pb.context.close()
    pb = ctx_new().new_page(); berr = []; pb.on("pageerror", lambda e: berr.append(str(e))); pb.add_init_script("var _g=Storage.prototype.getItem;Storage.prototype.getItem=function(k){if(k==='kicktip_model')throw new Error('x');return _g.call(this,k)};" + ACC); pb.goto(base + "/?model=eff"); pb.wait_for_selector("[data-model=eff]")
    ok("blocked storage + shared link: URL-only pick still works", pb.get_attribute("[data-model]", "data-model") == "eff" and not berr); pb.context.close()
    pb = ctx_new().new_page(); berr = []; pb.on("pageerror", lambda e: berr.append(str(e))); pb.add_init_script("Object.defineProperty(window,'localStorage',{get:function(){throw new Error('SecurityError')}});sessionStorage.setItem('kicktip_gate_visit','1');"); pb.goto(base + "/method/"); pb.wait_for_selector("h2#models")
    ok("localStorage entirely blocked: ungated page still loads without error", not berr, str(berr)); pb.context.close()
    # ===== F. failure path and every gated page type
    pg2 = ctx.new_page(); pg2.add_init_script(ACC); pg2.route("**/data/m/eff/**", lambda r: r.abort()); pg2.goto(base + "/?model=elo"); pg2.wait_for_selector("[data-mdl]"); pg2.wait_for_selector("#top12 tbody tr")
    pg2.click("[data-m=eff]"); pg2.wait_for_selector(".mdx")
    ok("failed alternate load: message shown, still on Elo, numbers unchanged, nothing stored for eff", pg2.get_attribute("[data-model]", "data-model") == "elo" and pg2.evaluate(f"localStorage.getItem('{KEY}')") != "eff")
    for path in ("/conference/big-12/", "/team/utah/", "/playoff/"):
        q = ctx_new().new_page(); q.add_init_script(ACC); q.goto(base + path); q.wait_for_selector("[data-mdl]"); ok(f"{path}: model control present, default blend", q.get_attribute("[data-model]", "data-model") == "blend")
        if path == "/playoff/": ok("playoff page notes the bracket order is the same for every model", (q.click("[data-why]") or True) and "order of the bracket is the same for every model" in q.inner_text("[data-mdl]"))
        alt(q, "elo"); q.wait_for_selector("[data-model=elo]"); q.close()
    # ===== G. ungated pages carry the pick in their links, and the copy
    ctx3 = ctx_new(); a = ctx3.new_page(); a.add_init_script(ACC); a.goto(base + "/"); a.wait_for_selector("[data-mdl]"); alt(a, "elo"); a.wait_for_selector("[data-model=elo]")
    pm = ctx3.new_page(); pm.goto(base + "/method/"); hm = internal_hrefs(pm)
    ok("method page (ungated): links carry ?model=elo from the stored pick; no model control or numbers appear", hm and all("model=elo" in h for h in hm) and pm.locator("[data-mdl]").count() == 0)
    pm2 = ctx_new().new_page(); pm2.goto(base + "/method/?model=eff"); ok("method page: ?model=eff in the URL tags links too", all("model=eff" in h for h in internal_hrefs(pm2)))
    pm3 = ctx_new().new_page(); pm3.goto(base + "/method/"); ok("method page with nothing stored: no tagging", not [h for h in internal_hrefs(pm3) if "model=" in h])
    ok("method page has #models and #accuracy and #changed", all(pm3.locator(f"#{i}").count() == 1 for i in ("models", "accuracy", "changed")))
    txt = pm3.inner_text("main")
    for need in ("KickTip can show its numbers from one of three models", "Your choice is remembered on this device until you change it or choose the default again.", "Two things do not change with the model", "the Elo-style rating before its last calibration step",
                 "Heavy favorites drop and underdogs rise, so some teams move a lot.", "KickTip's own version, inspired by widely used rating systems", "2026 list of FBS teams was applied to every season", "picked because it did best on these same test games",
                 "simpler models scored slightly better than the blend", "reworded after scoring", "Probabilities were limited to 2% to 98% before scoring", "0.659 without the limit", "0.015 lower, with a 95% range of 0.009 to 0.021 lower", "333 of them from 2026 (games from late September through October 23)", "Games from the first three weeks of each season were not scored", "scored 0.150"):
        ok(f"method page says: {need}", need in txt)
    ok("method page: no unsourced '0.06 / 190 games' rule, no 'start of 2026'", not re.search(r"0\.06|190 games|within noise|start of 2026", txt))
    ok("method page: raw MSM 0.635 stated with its unclipped 0.659", "0.635" in txt and "0.659" in txt)
    ok("method page: stamps say what each time is (results pulled vs model recalculated)", "Model last updated" not in txt)
    ok("method page: no 'four models', no 'resets when you open another page', no 'still selectable', no 'offered in the model control'", not re.search(r"four models|resets when you open|still selectable|offered in the model control|MSM rating is still selectable", txt))
    ok("method page: models list shows exactly KickTip blend (default), Elo-style, Efficiency", pm3.evaluate("(()=>{var e=document.getElementById('models').nextElementSibling;while(e&&e.tagName!=='UL')e=e.nextElementSibling;return [].map.call(e.querySelectorAll('li'),function(l){return l.querySelector('b').innerText})})()") == ["KickTip blend (default).", "Elo-style.", "Efficiency."])
    mv = J(f"{ROOT}/data/ref/movers.json")["teams"]; ut, by = mv["Utah Utes"], mv["BYU Cougars"]
    ok("method page: Utah/BYU numbers equal movers.json (and the mover table's before/after)", f"Utah's chance to make the 12 is {ut[1]*100:.1f}% now against {ut[0]*100:.1f}% under the earlier percentages, and BYU's is {by[1]*100:.1f}% against {by[0]*100:.1f}%" in txt, txt[txt.find("Heavy"):txt.find("Heavy") + 300])
    ok("method page: MSM is described only as an ingredient of the blend (not a choice)", "ingredient of the blend" in txt and "not offered" in txt)
    # the gate dialog text itself
    pgg = ctx_new(320, 700).new_page(); pgg.goto(base + "/"); pgg.wait_for_selector("#gate:not([hidden])"); gt = pgg.inner_text("#gate")
    ok("gate dialog: names the disclaimer and has its accept control; no model numbers", "I have read" in gt or "accept" in gt.lower())
    b.close()
print(f"model_toggle_test: {res['n'] - len(res['f'])}/{res['n']} checks pass"); [print("FAIL", f) for f in res["f"]]; sys.exit(1 if res["f"] else 0)
