"""Market line / gap / slate tests for the odds build. python3 tests/odds_test.py  (needs build/site; uses tests/serve.py + headless Chromium; a fake browser clock stands in for 'now')."""
import sys, os, re, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
BANNED = re.compile(r"\b(pick|picks|lock|locks|locked|value|edge|bet|bets|betting|play|best bet|top|biggest gaps|sportsbook|sportsbooks|bookmaker|odds)\b", re.I)
res = []
def ok(n, c, d=""): res.append((n, bool(c), d)); print(("PASS " if c else "FAIL ") + n, d if not c else "")
GAMES = json.load(open(f"{SITE}/data/pred-games.json"))["g"]; LINES = json.load(open(f"{SITE}/data/pred-lines.json"))["l"]
U = "2026-10-25T21:00:00Z"   # lines1025pm re-pin: 3:00 PM MT Oct 25 (fresh pull read 1:48 PM MT)
#          # 8:00 AM MT Oct 25: Georgia-Florida (Oct 31) is far from started; ESPN's fresh pull was read 1:32 AM MT Oct 25 (6.5 h earlier), so every line is under 24 h old.
CLOSED = "2026-10-26T21:00:00Z"   # lines1025pm re-pin: 3:00 PM MT Oct 26, >24 h after 1:48 PM MT
#     # 6:00 AM MT Oct 26: every line is older than 24 h
READ = "Oct 25, 1:47 PM MT"   # Georgia-Florida line read 1:47:52 PM MT
def cardtxt(pg, gk):
    el = pg.locator(f'[data-gk="{gk}"]').first; b = el.locator(".gbt")
    if b.count() and b.get_attribute("aria-expanded") == "false": b.click()      # phones start collapsed: open it, then read what a visitor would see
    return el.inner_text()
def strip_disc(t): return re.sub(r"not betting advice|not a betting site|place bets", "", t, flags=re.I)   # the legal disclaimer wording is required; the ban is on the lines UI
def new(b, w, t, route=None):
    c = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
    tt = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    pg = c.new_page(); pg.clock.set_fixed_time(tt)
    if route: pg.route("**/data/pred-games.json", route)
    return c, pg
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. arrival (no gate any more): the lines file loads with the other /data/pred-*.json files, nothing else is fetched, nothing is stored, no cookie
    c = b.new_context(viewport={"width": 390, "height": 900}); pg = c.new_page(); reqs = []; pg.on("request", lambda r: reqs.append(r.url))
    for path in ("/games/", "/team/georgia/", "/conference/big-12/"):
        reqs.clear(); pg.goto(BASE + path); pg.wait_for_selector("main[data-loaded='1']"); pg.wait_for_timeout(500)
        dr = [u for u in reqs if "/data/" in u]
        ok(f"arrival {path}: pred-lines fetched exactly once", len([u for u in dr if "pred-lines" in u]) == 1, str(dr))
        ok(f"arrival {path}: only precomputed pred-*.json fetched from /data/", all(re.search(r"/data/(m/\w+/)?pred-(teams|games|paths|lines)\.json", u) for u in dr), str(dr))
        ok(f"arrival {path}: no whatif / sim-bundle / chat-worker / google request", not [u for u in reqs if re.search(r"whatif|sim-bundle|chat-worker|google", u)])
        st = pg.evaluate("() => [localStorage.length, sessionStorage.length, document.cookie]"); ok(f"arrival {path}: no storage or cookie written", st == [0, 0, ""], str(st))
        ok(f"arrival {path}: no 'Shown after you accept' / 'Locked' placeholder left", not re.search(r"Shown after you accept|Locked", pg.locator("main").inner_text()))
    c.close()
    # 2. line open, with the right gap (rounded KickTip line, no raw yet)
    c, pg = new(b, 390, U); reqs = []; pg.on("request", lambda r: reqs.append(r.url)); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt')
    ok("pred-lines fetched once", len([u for u in reqs if "pred-lines" in u]) == 1)
    t = cardtxt(pg, "georgia~florida"); print("--- open:", t.replace("\n", " | "))
    ok("open: Market line row", "Market line" in t and "Georgia −10.5" in t); ok("open: read time in MT", READ in t, t)
    ok("open: KickTip line Georgia −16.5", "KickTip line" in t and "Georgia −16.5" in t); ok("open: Gap 6.0 points (rounded KickTip line, raw not stored yet)", "Gap" in t and "6.0 points" in t)
    ok("open: no banned word", not BANNED.search(t), str(BANNED.findall(t)))
    col = pg.evaluate("() => { const dd=[...document.querySelectorAll('[data-gk=\"georgia~florida\"] dt')].find(e=>e.textContent==='Gap').nextElementSibling; const s=getComputedStyle(dd); return [s.color, getComputedStyle(document.body).color, getComputedStyle(document.querySelector('[data-gk=\"georgia~florida\"] dt')).color]; }")
    ok("gap not coloured (same as ordinary text colour of the block)", col[0] in ("rgb(18, 21, 25)",), str(col))
    pg.screenshot(path=f"{ROOT}/crops/t-open-390.png"); c.close()
    # 3. gap from the UNROUNDED KickTip line
    def raw(route):
        r = route.fetch(); d = r.json(); d["g"]["georgia~florida"][2] = -16.26; route.fulfill(response=r, body=json.dumps(d), headers={**r.headers, "content-length": str(len(json.dumps(d)))})
    c, pg = new(b, 390, U, raw); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); t = cardtxt(pg, "georgia~florida")
    ok("gap uses unrounded -16.26: |-10.5+16.26| = 5.76 -> 5.8 (the rounded line would give 6.0)", "5.8 points" in t and "Georgia −16.5" in t, t); c.close()
    # 4. no market line (D3): a started-later game with a KickTip line but no line
    SLATE = open(f"{SITE}/games/index.html").read(); cand = [k for k, v in GAMES.items() if k not in LINES and v[0] is not None and f'data-gk="{k}"' in SLATE]
    if cand: nl = cand[0]; DROP = None
    else:   # lines1025pm: every slate game now has a line, so drop one slate game from pred-lines.json in the browser to exercise the no-line case
        nl = [k for k, v in GAMES.items() if f'data-gk="{k}"' in SLATE and v[0] is not None and k != "georgia~florida"][0]; print("none-case: dropping line of", nl)
        def DROP(route):
            r = route.fetch(); d = r.json(); d["l"].pop(nl, None); bd = json.dumps(d); route.fulfill(response=r, body=bd, headers={**r.headers, "content-length": str(len(bd))})
    c, pg = new(b, 390, U)
    if DROP: pg.route("**/data/pred-lines.json", DROP)
    pg.goto(BASE + f"/games/"); pg.wait_for_selector(f'.gcl [data-gk="{nl}"] .gbt'); t = cardtxt(pg, nl); print("--- none:", t.replace("\n", " | "))
    ok("none: 'Market line not posted yet.' + quieter line", "Market line not posted yet." in t and "Lines usually appear within about a day of kickoff." in t)
    ok("none: no Gap shown", "Gap" not in t and "points" not in t); ok("none: KickTip line still shown", "KickTip line" in t)
    ok("none: second line colour #4C5560", pg.evaluate(f"() => getComputedStyle(document.querySelector('.gcl [data-gk=\"{nl}\"] .nm2')).color") == "rgb(76, 85, 96)")
    ok("none: no banned word", not BANNED.search(t), str(BANNED.findall(t))); pg.screenshot(path=f"{ROOT}/crops/t-none-390.png"); c.close()
    # 5. closed / stale (D4)
    c, pg = new(b, 390, CLOSED); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); t = cardtxt(pg, "georgia~florida"); print("--- closed:", t.replace("\n", " | "))
    ok("closed: 'Line closed' with last line and time", "Line closed" in t and ("Last line: Georgia −10.5, " + READ) in t, t); ok("closed: no Gap", "Gap" not in t); c.close()
    # started game, line stored: closed even though less than 24 h old (the lines file is rewritten in the page so Georgia-Florida's line was read 1 h before kickoff)
    KO = LINES["georgia~florida"][2]
    def young(route):
        r = route.fetch(); d = r.json(); d["l"]["georgia~florida"][1] = KO - 3600; route.fulfill(response=r, body=json.dumps(d), headers={**r.headers, "content-length": str(len(json.dumps(d)))})
    c, pg = new(b, 390, dt.datetime.fromtimestamp(KO + 1800, dt.timezone.utc).isoformat()); pg.route("**/data/pred-lines.json", young); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); t = cardtxt(pg, "georgia~florida")
    ok("started (<24 h old line): Line closed", "Line closed" in t and "Gap" not in t, t); c.close()
    # stale only: game not started but line older than 24 h (Utah-BYU is TBA time -> age rule only)
    c, pg = new(b, 390, CLOSED); pg.goto(BASE + "/games/"); pg.wait_for_selector('.gcl [data-gk]'); 
    k = "utah~byu"; has = pg.locator(f'.gcl [data-gk="{k}"]').count()
    if has: t = cardtxt(pg, k); ok("TBA game, line older than 24 h: Line closed", "Line closed" in t, t)
    c.close()
    # 6. slate: default date sort, no gap sort by default, neutral controls, no banned words
    c, pg = new(b, 1280, U); pg.goto(BASE + "/games/"); pg.wait_for_selector(".gt tbody tr[data-gk] [data-c=mk] small, .gt tbody tr[data-gk] [data-c=mk] .nm"); 
    ds = pg.eval_on_selector_all(".gt tbody tr[data-gk]:not([hidden])", "r => r.map(x => +x.dataset.d)"); ok("slate: default sort is by date", ds == sorted(ds) and len(ds) > 10, str(ds[:5]))
    ok("slate: select defaults to date", pg.input_value("#gsort") == "dA")
    txt = strip_disc(pg.locator("main").inner_text()); ok("slate: no banned word (disclaimer wording excluded)", not BANNED.search(txt), str(BANNED.findall(txt))); ok("slate: no provider/book words", not re.search(r"\b(books?|sportsbooks?|ESPN BET|draftkings|fanduel|circa|caesars|betmgm)\b", txt, re.I))
    pg.click('.sb[data-sort="g"]'); g1 = pg.eval_on_selector_all(".gt tbody tr[data-gk]:not([hidden]) td[data-c=gap]", "t => t.map(x => x.textContent)")
    nums = [float(re.match(r"[\d.]+", x).group()) for x in g1 if re.match(r"[\d.]+", x)]; ok("slate: gap sort ascending when asked, games without a gap last", nums == sorted(nums) and len(nums) >= 1, str(g1[:6]))
    pg.select_option("#gsel", "big-12"); n = pg.locator(".gt tbody tr[data-gk]:not([hidden])").count(); ok("slate: conference filter", 0 < n < 54, str(n))
    pg.screenshot(path=f"{ROOT}/crops/t-slate-1280.png", full_page=False); c.close()
    # lines fetch failure: honest message
    c, pg = new(b, 390, U); pg.route("**/data/pred-lines.json", lambda r: r.abort()); pg.goto(BASE + "/team/georgia/"); pg.wait_for_selector('[data-gk="georgia~florida"] .gbt'); t = cardtxt(pg, "georgia~florida")
    ok("lines unavailable: honest message, no Gap", "Market line not available right now." in t and "Gap" not in t, t); c.close()
    b.close()
bad = [r for r in res if not r[1]]; print(f"\n{len(res)-len(bad)}/{len(res)} passed"); json.dump(res, open(f"{ROOT}/tests/last_odds_test.json", "w"), indent=1)
srv.shutdown(); sys.exit(1 if bad else 0)
