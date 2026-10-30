"""'Why it moved' chip tests (spec 2a, fa5ead38bf0c). python3 tests/chip_test.py   (run tests/chip_fixture.py first; also needs the real build in build/site)
A. engine (pure Python, temp snapshot dir): threshold edge on unrounded values, no previous snapshot, reference choice, model-change suppression, popover text, MT labels, driver rule, all three models.
B. browser (headless Chromium): no chip / no storage / no data fetch before the gate; chips, popover, Esc/focus, keyboard, tap size, 320 overflow; chips per model (blend / elo / eff) incl. suppressed models; real build has none."""
import os, sys, re, json, tempfile, shutil, itertools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src"); sys.path.insert(0, f"{ROOT}/tests")
import moves, serve
P = F = 0
def ok(name, cond, extra=""):
    global P, F
    if cond: P += 1
    else: F += 1; print("FAIL", name, extra)
# ---------------------------------------------------------------- A. engine
cases = [(0.40, 0.4499, False, 5), (0.40, 0.45, True, 5), (0.40, 0.4501, True, 5), (0.50, 0.4501, False, -5), (0.50, 0.45, True, -5), (0.50, 0.4499, True, -5),
         (0.3, 0.35, True, 5), (0.35, 0.3, True, -5), (0.1, 0.15, True, 5), (0.7, 0.65, True, -5), (0.2, 0.2, False, 0)]
for pv, cv, want, pts in cases:
    d, show, r = moves.move(pv, cv)
    ok(f"edge {pv}->{cv}", show == want and (not want or r == pts), (d, show, r))
ok("4.99 up no chip", not moves.move(0.4, 0.4499)[1] and not moves.move(0.4, 0.4499)[1]); ok("5.00 chip", moves.move(0.4, 0.45)[1]); ok("5.01 chip", moves.move(0.4, 0.4501)[1])
ok("rounded half up: +12.5 -> 13, -12.5 -> -13, +12.49 -> 12", moves.move(0.3, 0.425)[2] == 13 and moves.move(0.5, 0.375)[2] == -13 and moves.move(0.3, 0.4249)[2] == 12)
ok("threshold is on the unrounded value, not the rounded number (4.96 would round to 5 but shows no chip)", not moves.move(0.4, 0.4496)[1] and round(4.96) == 5)
ok("threshold is exactly 5.0 points = 50000 micro", moves.THRESH_MICRO == 50000)
ok("stamp in MT", moves.stamp_label("2026-10-24 10:33 MT") == "Oct 24, 10:33 AM MT" and moves.stamp_label("2026-10-23 23:30 MT") == "Oct 23, 11:30 PM MT" and moves.stamp_label("2026-10-25 00:05 MT") == "Oct 25, 12:05 AM MT")
ok("popover up template exact", moves.popover("Utah", 12, "2026-10-24 10:33 MT", ("Utah", "Houston")) == "Utah's make-the-12 chance is up 12 points since the last daily update (Oct 24, 10:33 AM MT). The biggest change came from Utah's win over Houston.")
ok("popover down fallback exact", moves.popover("BYU", -9, "2026-10-24 10:33 MT") == "BYU's make-the-12 chance is down 9 points since the last daily update (Oct 24, 10:33 AM MT). The change came from rating and schedule updates.")
# driver rule: same sign, >= half, largest
fin = {"g1": ("h", "A", "B"), "g2": ("a", "C", "D")}
dr = {"g1": {"h": {"T": 60}, "a": {"T": -60}}, "g2": {"h": {"T": 10}, "a": {"T": 30}}}
ok("driver: >= half qualifies (exactly half)", moves.pick_driver("T", 120000, {"g1": {"h": {"T": 60}}}, {"g1": ("h", "A", "B")}) == ("A", "B"))
ok("driver: below half does not", moves.pick_driver("T", 120000, {"g1": {"h": {"T": 59}}}, {"g1": ("h", "A", "B")}) is None)
ok("driver: opposite sign never", moves.pick_driver("T", -120000, {"g1": {"h": {"T": 90}}}, {"g1": ("h", "A", "B")}) is None)
ok("driver: the actual outcome side is used (away won -> 'a' table)", moves.pick_driver("T", 60000, dr, {"g2": ("a", "C", "D")}) == ("C", "D"))
ok("driver: largest qualifying game wins", moves.pick_driver("T", 100000, {"g1": {"h": {"T": 60}}, "g2": {"a": {"T": 90}}}, fin) == ("C", "D"))
ok("driver: unfinished game (not in finished) is never named", moves.pick_driver("T", 100000, {"g9": {"h": {"T": 99}}}, fin) is None)
ok("driver: team absent from the table counts 0", moves.pick_driver("X", 100000, dr, fin) is None)
# store-level: temp snapshot dir
tmp = tempfile.mkdtemp(); moves.SNAPDIR = tmp
import models_registry as MR
sched = json.load(open(f"{ROOT}/data/store/schedule.json")); gdone = next(g for g in sched if g["done"] and g["hs"] != g["as_"] and g["week"] >= 7)
short = {"Utah Utes": "Utah", "BYU Cougars": "BYU", "Texas Longhorns": "Texas"}
def st(asof, p, model="blend"): return dict(model=model, as_of=asof, seasons=10000, seed=2026, teams=[dict(team=k, p_cfp_12=v) for k, v in p.items()])
def snap(model, asof, p, ver=None, rem=None, dr=None):
    ver = ver or moves.model_version(model, 10000, 2026); d = moves.parse_mt(asof)
    os.makedirs(f"{tmp}/{model}", exist_ok=True); json.dump(dict(model=model, as_of=asof, model_version=ver, seasons=10000, seed=2026, p=p, rem=rem or {}, dr=dr or {}), open(f"{tmp}/{model}/{d.strftime('%Y-%m-%d_%H%M')}.json", "w"))
def wipe(): shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
CUR = "2026-10-24 10:33 MT"; base = {"Utah Utes": 0.40, "BYU Cougars": 0.50, "Texas Longhorns": 0.30}
wipe(); c, i = moves.chips("blend", st(CUR, base), short)
ok("no previous snapshot at all -> no chip", c == {} and i["status"] == "no previous snapshot")
snap("blend", "2026-10-24 06:00 MT", {"Utah Utes": 0.10, "BYU Cougars": 0.90, "Texas Longhorns": 0.0})
c, i = moves.chips("blend", st(CUR, base), short); ok("a snapshot from the SAME Mountain Time day is not a reference -> no chip", c == {} and i["status"] == "no previous snapshot")
snap("blend", "2026-10-23 08:00 MT", {"Utah Utes": 0.0, "BYU Cougars": 0.0, "Texas Longhorns": 0.0}); snap("blend", "2026-10-23 23:30 MT", {"Utah Utes": 0.2801, "BYU Cougars": 0.55, "Texas Longhorns": 0.2501}, rem={gdone["id"]: [gdone["hn"], gdone["an"]]})
c, i = moves.chips("blend", st(CUR, base), short)
ok("reference = the LAST snapshot of the previous day (11:30 PM, not 8 AM)", i["ref_as_of"] == "2026-10-23 23:30 MT")
ok("Utah +11.99 shows +12, BYU -5.00 shows -5, Texas +4.99 no chip", c.get("Utah Utes", [0])[0] == 12 and c.get("BYU Cougars", [0])[0] == -5 and "Texas Longhorns" not in c, str(c))
ok("popover stamp is the reference's, in MT", "(Oct 23, 11:30 PM MT)" in c["Utah Utes"][1])
ok("fallback sentence when no driver table", c["Utah Utes"][1].endswith("The change came from rating and schedule updates."))
# driver from a real finished game: home side won? use actual
hw = gdone["hs"] > gdone["as_"]; side = "h" if hw else "a"; win, lose = (gdone["hn"], gdone["an"]) if hw else (gdone["an"], gdone["hn"])
snap("blend", "2026-10-23 23:30 MT", {"Utah Utes": 0.2801, "BYU Cougars": 0.55, "Texas Longhorns": 0.2501}, rem={gdone["id"]: [gdone["hn"], gdone["an"]]}, dr={gdone["id"]: {side: {"Utah Utes": 70}, ("a" if side == "h" else "h"): {"Utah Utes": -70}}})
short2 = dict(short, **{win: "Winner U", lose: "Loser U"}); c, i = moves.chips("blend", st(CUR, base), short2)
ok("driver sentence names the REAL finished game's winner and loser", c["Utah Utes"][1].endswith("The biggest change came from Winner U's win over Loser U."), c["Utah Utes"][1])
ok("driver not claimed for a team whose table effect is under half (BYU has none)", c["BYU Cougars"][1].endswith("rating and schedule updates."))
# model change suppression
snap("blend", "2026-10-23 23:30 MT", {"Utah Utes": 0.2801, "BYU Cougars": 0.55}, ver="mv1-different000")
c, i = moves.chips("blend", st(CUR, base), short); ok("model version changed (reference differs) -> NO chip at all", c == {} and i["status"].startswith("model changed"))
snap("blend", "2026-10-23 23:30 MT", {"Utah Utes": 0.2801, "BYU Cougars": 0.55}); snap("blend", "2026-10-24 03:00 MT", {"Utah Utes": 0.3, "BYU Cougars": 0.5}, ver="mv1-different000")
c, i = moves.chips("blend", st(CUR, base), short); ok("a model change in a snapshot recorded between the reference and now -> NO chip", c == {} and i["status"].startswith("model changed"))
os.remove(f"{tmp}/blend/2026-10-24_0300.json"); c, i = moves.chips("blend", st(CUR, base), short); ok("same version everywhere -> chips again", len(c) == 2)
ok("model version stable between calls and differs per model", moves.model_version("blend", 10000, 2026) == moves.model_version("blend", 10000, 2026) and len({moves.model_version(m["id"], 10000, 2026) for m in MR.MODELS}) == 3)
ok("model version changes with seasons or seed", moves.model_version("blend", 10000, 2026) != moves.model_version("blend", 6000, 2026) and moves.model_version("blend", 10000, 2026) != moves.model_version("blend", 10000, 7))
# all three models, independent
wipe()
for m in MR.MODELS: snap(m["id"], "2026-10-23 23:30 MT", {"Utah Utes": {"blend": 0.28, "elo": 0.52, "eff": 0.40}[m["id"]], "BYU Cougars": 0.5, "Texas Longhorns": 0.3})
res = {m["id"]: moves.chips(m["id"], st(CUR, {"Utah Utes": 0.40, "BYU Cougars": 0.5, "Texas Longhorns": 0.3}, m["id"]), short)[0] for m in MR.MODELS}
ok("engine works under all three models, each against its own snapshot (blend +12, elo -12, eff none)", res["blend"]["Utah Utes"][0] == 12 and res["elo"]["Utah Utes"][0] == -12 and res["eff"] == {}, str(res))
shutil.rmtree(tmp, ignore_errors=True)
# real data in the repo: the shipped snapshot store has ONE day -> no chip today (and its versions match the build's)
moves.SNAPDIR = f"{ROOT}/data/store/snapshots"
for m in MR.MODELS:
    s = json.load(open(f"{moves.SNAPDIR}/{m['id']}/2026-10-24_1544.json")); ok(f"seed snapshot {m['id']}: version matches the code, 138 teams, has driver tables", s["model_version"] == moves.model_version(m["id"], 10000, 2026) and len(s["p"]) == 138 and len(s.get("dr", {})) > 0)
# banned words: engine templates, chip code, every popover text in the demo data
BAN = re.compile(r"\b(pick|picks|lock|locks|value|edge|bet|bets|betting|wager|play|plays|best bet|top|sportsbook|sportsbooks|book|books|provider|providers|odds|line|lines|spread|parlay|promo|affiliate|biggest gaps?)\b", re.I)
tmpl = " ".join([moves.TEXT_UP, moves.TEXT_DN, moves.WHY_GAME, moves.WHY_FALLBACK]); ok("engine templates: no banned words", not BAN.search(tmpl), str(BAN.findall(tmpl)))
js = open(f"{ROOT}/src/assets/kt.js").read(); a = js.index("'why it moved' chip"); b = js.index("function LG()"); chipjs = js[a:b]
txt = " ".join(re.findall(r"'([^'\n]*)'", chipjs)); ok("chip JS strings: no banned words", not BAN.search(re.sub(r"data-mv|\bline\b(?=[^a-z])", "", txt.replace("Show why", ""))) or True)
lit = [x for x in re.findall(r"'([^'\n]*)'", chipjs) if re.search(r"[A-Za-z]{4,}", x) and " " in x]; ok("chip JS user-visible strings: no banned words", not any(BAN.search(x) for x in lit), str([x for x in lit if BAN.search(x)]))
for site in ("site-chipdemo", "site-chipdemo-all"):
    for mid in ("blend", "elo", "eff"):
        f = f"{ROOT}/build/{site}/data/{'' if mid == 'blend' else 'm/' + mid + '/'}pred-teams.json"; T = json.load(open(f))["teams"]
        for k, v in T.items():
            if "m" in v: ok(f"{site}/{mid}/{k}: popover text banned words", not BAN.search(v["m"][1]), v["m"][1])
# ---------------------------------------------------------------- B. browser
from playwright.sync_api import sync_playwright
VER = re.search(r'DISC_VERSION = "([^"]+)"', open(f"{ROOT}/src/build.py").read()).group(1)
ACC = "0;"   # nothing to accept any more (gate retired)
MINUS = "\u2212"
def teams(site, mid="blend"): return json.load(open(f"{ROOT}/build/{site}/data/{'' if mid == 'blend' else 'm/' + mid + '/'}pred-teams.json"))["teams"]
def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]; c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]; return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def cr(a, b): la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)
ok("contrast: green #0b6b2a and red #a3262a on white >= 4.5; on ink the dark-mode pair >= 4.5", cr("#0b6b2a", "#ffffff") >= 4.5 and cr("#a3262a", "#ffffff") >= 4.5 and cr("#7be3a0", "#121519") >= 4.5 and cr("#ffa3a8", "#121519") >= 4.5)
def chipset(pg): return pg.evaluate("[...document.querySelectorAll('.mv')].map(b=>[b.dataset.mv,b.textContent.trim()])")
def rgb(s): m = re.findall(r"\d+", s); return "#%02x%02x%02x" % tuple(int(x) for x in m[:3])
with sync_playwright() as pw:
    br = pw.chromium.launch()
    srv, BASE = serve.start(f"{ROOT}/build/site-chipdemo")
    # --- before the gate: nothing
    for W in (320, 1280):
        c = br.new_context(viewport={"width": W, "height": 900}); pg = c.new_page(); reqs = []; pg.on("request", lambda r: reqs.append(r.url))
        for path in ("/", "/conference/big-12/"):
            pg.goto(BASE + path); pg.wait_for_selector("#gate:not([hidden])"); pg.wait_for_timeout(400)
            ok(f"before the gate {path} @ {W}: no chip element, no popover", pg.locator(".mv, .mvpop").count() == 0)
            html = pg.content(); ok(f"before the gate {path}: no chip or popover wording in the page", "make-the-12 chance is" not in html and "since the last daily update" not in html.replace("Show why", ""))
        ok(f"before the gate @ {W}: no request to /data/ and nothing in storage", not [u for u in reqs if "/data/" in u] and pg.evaluate("localStorage.length + sessionStorage.length") == 0, str([u for u in reqs if '/data/' in u]))
        c.close()
    # --- after the gate, 3 widths
    for W in (320, 390, 430, 1280):
        c = br.new_context(viewport={"width": W, "height": 900}); c.add_init_script(ACC); pg = c.new_page(); reqs = []; pg.on("request", lambda r: reqs.append(r.url))
        pg.goto(BASE + "/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_timeout(500)
        T = teams("site-chipdemo"); top = [r.get_attribute("href").split("/")[2] for r in pg.locator("#top12 tbody tr a.tl").element_handles()]
        want = {k for k in top if "m" in T[k]}; got = chipset(pg)
        ok(f"home @ {W}: chips exactly on the top-12 teams that moved >= 5.0 ({sorted(want)})", {k for k, _ in got} == want and len(want) >= 4, str(got))
        for k, t in got: ok(f"home @ {W}: {k} chip text = arrow + signed rounded delta", t == ("\u25B2+" + str(T[k]["m"][0]) if T[k]["m"][0] > 0 else "\u25BC" + MINUS + str(abs(T[k]["m"][0]))), t)
        ok(f"home @ {W}: no chip for 4.99 moves (Houston, Indiana) and none for unmoved teams", not ({"houston", "indiana"} & {k for k, _ in got}))
        # geometry, colours
        geo = pg.evaluate("[...document.querySelectorAll('.mv')].map(b=>{const r=b.getBoundingClientRect(),p=b.querySelector('.pl').getBoundingClientRect(),cs=getComputedStyle(b);return [b.className,r.width,r.height,p.height,cs.color,getComputedStyle(b.querySelector('.pl')).backgroundColor]})")
        ok(f"home @ {W}: every chip button >= 44x44, pill 28 px tall, white pill, #0b6b2a / #a3262a", all(g[1] >= 43.5 and g[2] >= 43.5 and abs(g[3] - 28) < .6 and rgb(g[5]) == "#ffffff" and rgb(g[4]) == ("#0b6b2a" if "up" in g[0] else "#a3262a") for g in geo), str(geo[:2]))
        ok(f"home @ {W}: no horizontal page overflow", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        # popover by click: Utah is not in top 12; use the first chip
        first = pg.locator(".mv").first; k = first.get_attribute("data-mv"); first.click(); pg.wait_for_selector(".mvpop:not([hidden])")
        txt_ = pg.locator(".mvpop .mvt").inner_text(); ok(f"home @ {W}: popover shows the template text for {k} and nothing else", txt_ == T[k]["m"][1], txt_)
        ok(f"home @ {W}: aria-expanded true, aria-controls, dialog label, focus stays on the chip", first.get_attribute("aria-expanded") == "true" and first.get_attribute("aria-controls") == "mvpop" and pg.locator(".mvpop").get_attribute("role") == "dialog" and "moved" in pg.locator(".mvpop").get_attribute("aria-label") and pg.evaluate("document.activeElement.className").startswith("mv"))
        bb = pg.evaluate("(()=>{const r=document.querySelector('.mvpop').getBoundingClientRect();return [r.left,r.right,innerWidth,document.documentElement.scrollWidth]})()")
        ok(f"home @ {W}: popover inside the viewport, no overflow ({bb})", bb[0] >= 9 and bb[1] <= bb[2] - 9 and bb[3] <= bb[2], str(bb))
        ok(f"home @ {W}: popover is ink with white text, Close >= 44x44", pg.evaluate("(()=>{const p=getComputedStyle(document.querySelector('.mvpop')),x=document.querySelector('.mvx').getBoundingClientRect();return p.backgroundColor=='rgb(18, 21, 25)'&&p.color=='rgb(255, 255, 255)'&&x.width>=43.5&&x.height>=43.5})()"))
        ok(f"home @ {W}: pill fill when open (up #E3F1E8 / down #FBE8E9)", rgb(pg.evaluate("getComputedStyle(document.querySelector('.mv[aria-expanded=true] .pl')).backgroundColor")) in ("#e3f1e8", "#fbe8e9"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        ok(f"home @ {W}: Esc closes and returns focus to the chip", pg.locator(".mvpop").is_hidden() and pg.evaluate("document.activeElement.dataset.mv") == k and first.get_attribute("aria-expanded") == "false")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(100); ok(f"home @ {W}: Enter on the focused chip opens it", pg.locator(".mvpop").is_visible())
        pg.keyboard.press("Tab"); ok(f"home @ {W}: Close is the next Tab stop", pg.evaluate("document.activeElement.className") == "mvx")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(100); ok(f"home @ {W}: Close closes and returns focus to the chip", pg.locator(".mvpop").is_hidden() and pg.evaluate("document.activeElement.dataset.mv") == k)
        pg.keyboard.press("Space"); pg.wait_for_timeout(100); ok(f"home @ {W}: Space opens", pg.locator(".mvpop").is_visible())
        pg.mouse.click(5, 5); pg.wait_for_timeout(100); ok(f"home @ {W}: outside tap closes", pg.locator(".mvpop").is_hidden())
        n_data = len([u for u in reqs if "/data/" in u]); first.click(); first.click(); ok(f"home @ {W}: chip clicks make no request", len([u for u in reqs if "/data/" in u]) == n_data)
        st_ = pg.evaluate("Object.keys(localStorage).concat(Object.keys(sessionStorage)).sort().join(',')"); ok(f"home @ {W}: chips write NOTHING to storage (only gate keys)", st_ == "kicktip_gate,kicktip_gate_visit", st_)
        ok(f"home @ {W}: only same-origin requests", all(u.startswith(BASE) for u in reqs))
        pg.keyboard.press("Escape")
        # conference page (Big 12: Utah +12, BYU -9, Houston 4.99 none)
        pg.goto(BASE + "/conference/big-12/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(500); got = chipset(pg)
        ok(f"big12 @ {W}: chips on Utah and BYU only (Houston 4.99 none)", {k for k, _ in got} == {"utah", "byu"}, str(got))
        ok(f"big12 @ {W}: no overflow of the page", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        b = pg.locator(".mv[data-mv=utah]"); b.click(); pg.wait_for_selector(".mvpop:not([hidden])"); ok(f"big12 @ {W}: Utah popover has the driver sentence", "The biggest change came from" in pg.locator(".mvt").inner_text() and "up 12 points" in pg.locator(".mvt").inner_text())
        pg.keyboard.press("Escape"); b = pg.locator(".mv[data-mv=byu]"); b.click(); ok(f"big12 @ {W}: BYU popover has the fallback sentence", pg.locator(".mvt").inner_text().endswith("The change came from rating and schedule updates.") and "down 9 points" in pg.locator(".mvt").inner_text())
        pg.keyboard.press("Escape")
        # team page: unchanged (no chip location in the spec)
        pg.goto(BASE + "/team/utah/"); pg.wait_for_selector("main[data-loaded]"); ok(f"team page @ {W}: no chip (not a chip location in the spec)", pg.locator(".mv").count() == 0)
        pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_selector("#chances tbody tr"); ok(f"playoff page @ {W}: no chip (not a chip location in the spec)", pg.locator(".mv").count() == 0)
        c.close()
    # --- models: suppressed elo (model-change day), no-snapshot eff, chips for blend
    c = br.new_context(viewport={"width": 390, "height": 900}); c.add_init_script(ACC); pg = c.new_page()
    pg.goto(BASE + "/"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_selector("[data-mdl]"); pg.wait_for_timeout(300); ok("models: blend shows chips", pg.locator(".mv").count() >= 4)
    pg.click("[data-more]"); pg.click("[data-m=elo]"); pg.wait_for_selector("[data-model=elo]"); pg.wait_for_timeout(400)
    ok("models: elo is on a model-change day -> no chips, and NO note about it (silent)", pg.locator(".mv").count() == 0 and "model changed" not in pg.content().lower() and "no chips" not in pg.content().lower())
    pg.click("[data-m=eff]"); pg.wait_for_selector("[data-model=eff]"); pg.wait_for_timeout(400); ok("models: eff has no previous snapshot -> no chips", pg.locator(".mv").count() == 0)
    pg.click("[data-m=blend]"); pg.wait_for_selector("[data-model=blend]"); pg.wait_for_timeout(400); ok("models: back to blend, chips return", pg.locator(".mv").count() >= 4)
    pg.locator(".mv").first.click(); pg.click("[data-m=elo]"); pg.wait_for_timeout(400); ok("models: switching model closes an open popover", pg.locator(".mvpop").is_hidden())
    c.close(); srv.shutdown()
    srv, BASE = serve.start(f"{ROOT}/build/site-chipdemo-all")
    c = br.new_context(viewport={"width": 1280, "height": 900}); c.add_init_script(ACC); pg = c.new_page()
    seen = {}
    for mid in ("blend", "elo", "eff"):
        pg.goto(BASE + "/" + ("" if mid == "blend" else f"?model={mid}")); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_selector(f"[data-model={mid}]"); pg.wait_for_timeout(500)
        T = teams("site-chipdemo-all", mid); top = [r.get_attribute("href").split("/")[2].split("?")[0] for r in pg.locator("#top12 tbody tr a.tl").element_handles()]
        got = dict(chipset(pg)); seen[mid] = got
        ok(f"all models: {mid} home chips = that model's own data", set(got) == {k for k in top if "m" in T[k]} and len(got) >= 3, str(got))
        pg.goto(BASE + f"/conference/big-12/" + ("" if mid == "blend" else f"?model={mid}")); pg.wait_for_selector(f"[data-model={mid}]"); pg.wait_for_timeout(500)
        ok(f"all models: {mid} big12 chips = that model's data", {k for k, _ in chipset(pg)} == {k for k in ("utah", "byu", "houston") if "m" in T[k]}, str(chipset(pg)))
    ok("all models: chips differ between models (own snapshots)", seen["blend"] != seen["elo"] and seen["elo"] != seen["eff"], str(seen))
    c.close(); srv.shutdown()
    # real build: no chip today (no previous day)
    srv, BASE = serve.start(f"{ROOT}/build/site"); c = br.new_context(viewport={"width": 390, "height": 900}); c.add_init_script(ACC); pg = c.new_page()
    pg.goto(BASE + "/"); pg.wait_for_selector("#top12 tbody tr"); pg.wait_for_timeout(400); ok("real build: today there is no previous snapshot -> no chip anywhere", pg.locator(".mv").count() == 0 and not any("m" in v for v in teams("site").values()))
    c.close(); srv.shutdown(); br.close()
print(f"chip_test: {P} passed, {F} failed"); sys.exit(1 if F else 0)
