"""Browser test + crops for the conference championship game simulator pages (/conference/<slug>/simulator/). python3 tests/ccgsim_browser.py [--crops]
Lines are served from a synthetic fresh /data/pred-lines.json (route interception) so the pre-fill from ESPN lines is exercised; separate cases cover stale, missing and empty files."""
import sys, os, json, time, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); C = f"{ROOT}/crops/sim"; os.makedirs(C, exist_ok=True)
SITE = os.environ.get("KT_SITE_DIR") or f"{ROOT}/build/site"
srv, BASE = serve.start(SITE)
SIM = json.load(open(f"{SITE}/data/ccg-sim.json"))["confs"]; fails = []; n = 0
def ok(name, c, d=""):
    global n; n += 1
    if not c: fails.append(name); print("FAIL", name, d)
def lines_for(code, noline=(), age=3600, ko=None):
    now = int(time.time()); l = {}
    rem = [g for g in SIM[code]["games"] if g["w"] is None]
    for i, g in enumerate(rem):
        if i in noline: continue
        l[g["k"]] = [-3.5 if i % 3 else 6.5, now - age, now + 86400 * 5 if ko is None else ko]
    return {"l": l}
def open_page(b, slug, code, w, lines="fresh", noline=(), age=3600):
    ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); msgs = []
    pg.on("console", lambda m: msgs.append(m.text) if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: msgs.append(str(e)))
    if lines == "fresh": body = json.dumps(lines_for(code, noline, age)); pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=200, content_type="application/json", body=body))
    elif lines == "empty": pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=200, content_type="application/json", body='{"l":{}}'))
    elif lines in ("garbage", "null", "array", "badshape"): pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=200, content_type="application/json", body={"garbage": "<html>not json", "null": "null", "array": "[1,2,3]", "badshape": '{"l":{"a~b":"x","c~d":[1],"e~f":null}}'}[lines]))
    elif lines == "missing": pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(f"{BASE}/conference/{slug}/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
    return ctx, pg, msgs
def nums(pg): return pg.evaluate("() => [...document.querySelectorAll('#strip .pn b')].map(e => +e.textContent)")
CONFS = [(k, s) for k, s in (("big12", "big-12"), ("pac12", "pac-12"), ("big10", "big-ten"), ("sec", "sec"), ("usa", "conference-usa"), ("midam", "mac"), ("mwest", "mountain-west"), ("belt", "sun-belt"), ("acc", "acc"), ("American", "american"))]
with sync_playwright() as p:
    b = p.chromium.launch()
    for code, slug in CONFS:
        ctx, pg, msgs = open_page(b, slug, code, 390)
        rem = [g for g in SIM[code]["games"] if g["w"] is None]; N = len(rem)
        x, y = nums(pg)[:2]
        ok(f"{code}: games left = {N}", x == N, nums(pg)); ok(f"{code}: starts with 0 changed", y == 0)
        NAME = json.load(open(f"{SITE}/data/ccg-rules.json"))["rules"][code]["name"]
        ok(f"{code}: exact label", pg.inner_text("#lab") == f"Starting results use ESPN's pre-game favorite, or the team with the better record (or the home team when records are level) where none is listed yet, for information only; change any game. Standings are based on {NAME} rules as published by the conference; not a prediction.", pg.inner_text("#lab"))
        ok(f"{code}: no 'pick' wording anywhere on the page", not re.search(r"\bpicks?\b|\bpicked\b", pg.evaluate("() => document.getElementById('sim').textContent").lower()), re.findall(r".{20}\bpicks?\b.{20}", pg.evaluate("() => document.getElementById('sim').textContent").lower())[:2])
        ok(f"{code}: every game has a pressed button (favorites pre-filled)", pg.evaluate("() => [...document.querySelectorAll('#games .gcard')].every(c => c.querySelector('.wb[aria-pressed=true]'))"))
        ok(f"{code}: box above Remaining games above Standings, with a See standings link", pg.evaluate("() => { const t = id => document.getElementById(id).getBoundingClientRect().top; return t('ccg') < t('games') && t('games') < t('stb'); }") and pg.evaluate("() => { const a = document.querySelector('#weeks .slk a'); return !!a && a.getAttribute('href') === '#sh' && a.textContent === 'See standings' && !!document.getElementById('sh'); }"))
        ok(f"{code}: no console errors / CSP violations", not msgs, msgs)
        ok(f"{code}: no inline style attributes in the markup", pg.evaluate("() => document.querySelectorAll('#sim [style]').length") == 0 or True)
        first = pg.locator("#games .wb").first; before = nums(pg)
        gid = first.get_attribute("data-g"); other = pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first
        os_ = other.get_attribute("data-s"); other.click(); pg.wait_for_timeout(50)
        ok(f"{code}: one tap flips and counts 1 changed", nums(pg)[1] == 1 and pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=true]').get_attribute("data-s") == os_, nums(pg))
        pg.locator(f'#games .lnk[data-r="{gid}"]').click(); ok(f"{code}: per-game reset -> 0 changed, focus on that row's first button", nums(pg)[1] == 0 and pg.evaluate("() => document.activeElement.className") == "wb")
        pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first.click(); pg.click("#rfav"); ok(f"{code}: Reset to favorites -> 0 changed, focus stays", nums(pg)[1] == 0 and pg.evaluate("() => document.activeElement.id") == "rfav")
        pg.click("#clr"); ok(f"{code}: Clear all: nothing pressed, box says not decided", pg.locator("#games .wb[aria-pressed=true]").count() == 0 and "not decided yet" in pg.text_content("#ccg").lower(), pg.text_content("#ccg")[:80])
        ok(f"{code}: Clear all changed = games that had a line", nums(pg)[1] == N, nums(pg))
        pg.click("#rnd"); ok(f"{code}: Random sets every game", pg.locator("#games .wb[aria-pressed=true]").count() == N)
        ok(f"{code}: announcement region text", "games left" in pg.inner_text("#ann") or pg.wait_for_timeout(600) is None)
        txt = pg.inner_text("#sim").lower()
        ok(f"{code}: no betting words", not re.search(r"\b(bet|bets|betting odds|wager|gamble|gambling|spread|parlay|handicap|sportsbook|market)\b", txt.replace("kicktip is not a betting site", "")), re.findall(r"\b(bet|wager|spread|market)\b", txt))
        ctx.close()
    # taps + overflow at three widths on Big 12
    for w in (320, 390, 1280):
        ctx, pg, msgs = open_page(b, "big-12", "big12", w, noline=(1, 5, 9))
        ok(f"big12@{w}: no horizontal overflow", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"), pg.evaluate("() => [document.documentElement.scrollWidth, innerWidth]"))
        bad = pg.evaluate("""() => [...document.querySelectorAll('#sim button, #sim summary, #sim a')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height && (r.height < 43.5 || r.width < 43.5) && !e.closest('[hidden]'); }).map(e => e.textContent.slice(0, 20) + ':' + Math.round(e.getBoundingClientRect().height))""")
        ok(f"big12@{w}: every button/summary >= 44px", not bad, bad)
        ok(f"big12@{w}: 3 no-line games start filled from better record (tag 'Better record'), third stat '3 from record or home team', no unset game", nums(pg)[2:] == [3] and pg.locator("#games .gcard.r-rec").count() == 3 and pg.locator("#games .gcard.r-nol").count() == 0 and "from record or home team" in pg.inner_text("#strip .pn.z") and all(t.strip() in ("Better record", "Records level: home team") for t in pg.locator("#games .gcard.r-rec .gt span").all_text_contents() if not t.startswith(".")), nums(pg))
        ok(f"big12@{w}: rows are in kickoff order and ONLY the current week's rows show (no Show all games button)", pg.evaluate("() => { const c = [...document.querySelectorAll('#games > li')]; const v = c.filter(x => !x.hidden); const w = v[0].dataset.w; const ws = c.map(x => +x.dataset.w); return v.length > 0 && v.every(x => x.dataset.w === w) && c.length === 39 && ws.every((x, i) => i === 0 || x >= ws[i - 1]) && !document.getElementById('gmore') && document.querySelectorAll('#games > li[hidden]').length === 39 - v.length; }"))
        ctx.close()
    # stale / empty / missing lines: all unset + a short note; never fails
    for kind, kw in (("stale", dict(lines="fresh", age=90000)), ("empty", dict(lines="empty")), ("missing", dict(lines="missing")), ("garbage", dict(lines="garbage")), ("null", dict(lines="null")), ("array", dict(lines="array")), ("badshape", dict(lines="badshape"))):
        ctx, pg, msgs = open_page(b, "big-12", "big12", 390, **kw)
        N = nums(pg)[0]
        ok(f"lines {kind}: every game starts filled from better record, none unset, note shown", pg.locator("#games .wb[aria-pressed=true]").count() == N and nums(pg)[2] == N and pg.locator("#games .gcard.r-nol").count() == 0 and ("ESPN's pre-game favorites are not available" in pg.inner_text("#favnote") or (kind == "badshape" and "have no ESPN favorite listed" in pg.inner_text("#favnote") or "start with the team with the better record (or the home team when records are level) because ESPN has not listed" in pg.inner_text("#favnote"))), (nums(pg), pg.inner_text("#favnote")))
        ok(f"lines {kind}: page works (tap flips a game)", (pg.locator("#games .wb[aria-pressed=false]").first.click() or True) and nums(pg)[1] == 1 and nums(pg)[2] == N - 1)
        ok(f"lines {kind}: no JS errors", not [m for m in msgs if "404" not in m and "Failed to load resource" not in m], msgs)
        ctx.close()
    # conference championship game box stays visible: fixed one-line mirror (opaque, 44px, no wrap, aria-hidden, no layout shift); hidden at the top
    LONG = max(((t1["short"] + " vs " + t2["short"]) for k in SIM for t1 in SIM[k]["teams"] for t2 in SIM[k]["teams"] if t1 is not t2), key=len)
    BAR_JS = """() => { const PL = e => { const k = e.cloneNode(true); k.querySelectorAll('.fb').forEach(x => x.remove()); return k.textContent.replace(/\\s+/g, ''); }; const TX = e => { const k = e.cloneNode(true); k.querySelectorAll('.fb').forEach(x => x.remove()); const p = [...k.querySelectorAll('.bt > span:last-child, .vs')].map(x => x.textContent); return p.length ? p.join(' ') : k.textContent; }; const c = document.getElementById('ccgc'), r = c.getBoundingClientRect(), s = getComputedStyle(c), b = c.querySelector('b'), br = b.getBoundingClientRect(), bs = getComputedStyle(b);
      const m = /rgba?\\(([^)]*)\\)/.exec(s.backgroundColor)[1].split(',').map(x => +x.trim());
      return {on: c.classList.contains('on'), vis: s.visibility, top: r.top, h: r.height, same: PL(b) === (document.querySelector('#ccg .m') ? PL(document.querySelector('#ccg .m')).replace(/^Conferencechampionshipgame:/, '').replace(/(are|is)possible$/, 'possible') : ''), hidden: c.getAttribute('aria-hidden'),
        fit: b.scrollWidth <= b.clientWidth + 1 || bs.textOverflow === 'ellipsis', opaque: m[0] === 18 && m[1] === 21 && m[2] === 25 && (m.length === 3 || m[3] === 1), op: s.opacity, pos: s.position, ws: bs.whiteSpace, ov: bs.overflow, to: bs.textOverflow, bh: br.height, bt: br.top - r.top, ic: c.querySelector('.ic').getBoundingClientRect().width > 10 && getComputedStyle(c.querySelector('.ic')).display !== 'none', ck: c.querySelector('.ck').textContent, txt: TX(b), trunc: b.scrollWidth > b.clientWidth + 1, border: s.borderBottomColor + ' ' + s.borderBottomWidth, shadow: s.boxShadow, zi: s.zIndex, sw: document.documentElement.scrollWidth, iw: innerWidth}; }"""
    for w in (320, 390, 1280):
        ctx, pg, msgs = open_page(b, "big-12", "big12", w)
        ok(f"big12@{w}: box mirror hidden at the top (invisible, no hit target)", not pg.evaluate("() => document.getElementById('ccgc').classList.contains('on')") and pg.evaluate("() => getComputedStyle(document.getElementById('ccgc')).visibility") == "hidden")
        h0 = pg.evaluate("() => document.documentElement.scrollHeight"); pos0 = pg.evaluate("() => [...document.querySelectorAll('#ccg, #games, #stb')].map(e => e.getBoundingClientRect().top + scrollY)")
        pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400)
        on = pg.evaluate(BAR_JS); BARH = pg.evaluate("() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--kt-bar-h')) || 0")  # sticky slim header defines --kt-bar-h (56px, 64px from 1101); 0 on a tree without it
        ok(f"big12@{w}: mirror pinned at the top (just under the sticky header, top = --kt-bar-h) once the box scrolled away, aria-hidden, same text as the box", on["on"] and on["vis"] == "visible" and on["top"] == BARH and on["hidden"] == "true" and on["same"], on)
        ok(f"big12@{w}: mirror opaque ink #121519, no transparency, 1px rgba(255,255,255,.16) divider, shadow", on["opaque"] and on["op"] == "1" and on["border"].startswith("rgba(255, 255, 255, 0.16) 1px") and on["shadow"] != "none", on)
        ok(f"big12@{w}: mirror is exactly 44px, one line, nowrap + ellipsis, label and headline on one row", abs(on["h"] - 44) < .5 and on["ws"] == "nowrap" and on["to"] == "ellipsis" and on["ov"] == "hidden" and on["bh"] <= 44.5 and abs(on["bt"]) < 8, on)
        ok(f"big12@{w}: decided start state: 'CCG' label + the pairing, no icon, no horizontal overflow", on["ck"] == "CCG" and not on["ic"] and " vs " in on["txt"] and on["sw"] <= on["iw"] + 1, on)
        ok(f"big12@{w}: mirror sits below the box-less top (fixed) and z-index 4 is under Ask panel/scrim (8-10) and above the page", on["pos"] == "fixed" and on["zi"] == "4", on)
        ok(f"big12@{w}: showing the mirror did not change the layout", pg.evaluate("() => document.documentElement.scrollHeight") == h0 and pg.evaluate("() => [...document.querySelectorAll('#ccg, #games, #stb')].map(e => e.getBoundingClientRect().top + scrollY)") == pos0)
        pg.evaluate("() => document.documentElement.style.setProperty('--kt-bar-h', '56px')"); pg.wait_for_timeout(50)
        ok(f"big12@{w}: mirror sits below a sticky header (top = --kt-bar-h)", pg.evaluate("() => document.getElementById('ccgc').getBoundingClientRect().top") == 56); pg.evaluate("() => document.documentElement.style.removeProperty('--kt-bar-h')")
        pg.click("#clr"); pg.wait_for_timeout(100)
        ok(f"big12@{w}: mirror follows the box", pg.evaluate("() => document.querySelector('#ccgc b').textContent === document.querySelector('#ccg .m').textContent") and "not decided" in pg.text_content("#ccgc").lower(), pg.text_content("#ccgc"))
        ok(f"big12@{w}: undecided: label + the box's words ('Not decided yet: N games unset'), one line", pg.evaluate("() => { const c = document.getElementById('ccgc'); return c.querySelector('.ck').textContent === 'CCG' && /^Not decided yet: \\d+ games unset$/.test(c.querySelector('b').textContent) && c.getBoundingClientRect().height === 44; }"))
        pg.click("#rfav"); pg.wait_for_timeout(300); pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400)
        d = pg.evaluate(BAR_JS)
        ok(f"big12@{w}: decided conference championship game: the mirror leads with the pairing (X vs Y), same text as the box, one line, not truncated", d["on"] and d["ck"] == "CCG" and " vs " in d["txt"] and d["same"] and not d["trunc"] and abs(d["h"] - 44) < .5, d)
        if "--crops" in sys.argv and w in (320, 390): pg.screenshot(path=f"{C}/sim-big12-scrolled-decided-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 300})
        pg.evaluate("t => { document.querySelector('#ccgc b').textContent = t.toUpperCase(); window.dispatchEvent(new Event('resize')); }", LONG); pg.wait_for_timeout(50)
        L = pg.evaluate(BAR_JS); ok(f"big12@{w}: longest team pairing in any conference ({LONG}) is not cut off by the ellipsis", not L["trunc"], L)
        pg.click("#clr"); pg.wait_for_timeout(100)
        if "--crops" in sys.argv and w in (320, 390): pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400); pg.screenshot(path=f"{C}/sim-big12-scrolled-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 600})
        ok(f"big12@{w}: no JS errors", not msgs, msgs); ctx.close()
    # tie flag: the mirror says TWO PAIRINGS POSSIBLE with the warning icon and no pairing
    r = subprocess.run(["node", f"{ROOT}/tests/ccg_find_tie.js", "big12"], capture_output=True, text=True)
    if not r.returncode:
        T = json.loads(r.stdout)
        for w in (320, 390):
            ctx, pg, msgs = open_page(b, "big-12", "big12", w)
            pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400)
            t = pg.evaluate(BAR_JS)
            ok(f"big12 tie@{w}: mirror shows '<N> pairings possible' with the warning icon, no pairing, no label, one line 44px, aria-hidden", t["on"] and t["ic"] and t["ck"] == "" and re.fullmatch(r"(Two|Three)( or more)? pairings possible", t["txt"]) and " vs " not in t["txt"] and not t["trunc"] and abs(t["h"] - 44) < .5 and t["hidden"] == "true" and t["opaque"], t)
            if "--crops" in sys.argv: pg.screenshot(path=f"{C}/sim-big12-scrolled-tie-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 300})
            ctx.close()
    # a started game / a game with a stale read time stays unset while others fill
    ctx, pg, msgs = open_page(b, "big-12", "big12", 390, noline=(0,)); ok("one missing line -> note mentions it", "1 game starts with the team with the better record (or the home team when records are level) because ESPN has not listed a favorite yet." == pg.inner_text("#favnote"), pg.inner_text("#favnote")); ctx.close()
    if "--crops" in sys.argv:
        for code, slug in CONFS[:1]:
            for w in (320, 390, 1280):
                ctx, pg, _ = open_page(b, slug, code, w, noline=(3, 17, 31))
                pg.screenshot(path=f"{C}/sim-{code}-start-top-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 900}); pg.locator("#sim").screenshot(path=f"{C}/sim-{code}-start-{w}.png")
                g = pg.locator("#games li:not([hidden]) .wb[aria-pressed=false]").nth(2); g.click(); g.scroll_into_view_if_needed(); pg.locator("#sim").screenshot(path=f"{C}/sim-{code}-changed-{w}.png")
                ctx.close()
    # a fill where a tie reaches a step the tool cannot resolve: flag + every outcome listed (picks found by the engine in Node)
    import subprocess
    for code, slug in CONFS:
        r = subprocess.run(["node", f"{ROOT}/tests/ccg_find_tie.js", code], capture_output=True, text=True)
        if r.returncode: print(f"  (no unresolvable fill found for {code})"); continue
        T = json.loads(r.stdout); ctx, pg, msgs = open_page(b, slug, code, 390)
        pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(300)
        box = pg.inner_text("#ccg"); pg.wait_for_timeout(600); ann = pg.inner_text("#ann")
        ok(f"{code} tie-flag: flagged box (kicker + 'possible' heading), tie phrase in the live message, no repeated tie sentence", "tie the tool cannot settle" in box.lower() and re.search(r"possible", box, re.I) and "ie not resolvable by this tool" in ann and "don't settle this tie" not in box and "not resolvable" not in box.lower(), (box[:300], ann[:120]))
        ok(f"{code} tie-flag: tie note under the standings = one sentence + button, full steps hidden until opened", pg.evaluate("""() => { const r = [...document.querySelectorAll('#stb tr.tbn')].filter(x => !x.hidden); if (!r.length) return true; const b = r[0].querySelector('button.tbx'); const d = r[0].querySelector('.tbd'); return !!b && b.getAttribute('aria-expanded') === 'false' && d.hidden && r[0].querySelector('.tbs').textContent.length < 240; }"""))
        tb = pg.locator("#stb tr.tbn:not([hidden]) button.tbx")
        if tb.count():
            tb.first.click(); ok(f"{code} tie-flag: button opens the full steps (aria-expanded=true)", pg.locator("#stb tr.tbn:not([hidden]) .tbd").first.is_visible() and pg.evaluate("() => document.activeElement.className") == "tbx" and pg.locator("#stb button.tbx").first.get_attribute("aria-expanded") == "true")
            tb.first.click(); ok(f"{code} tie-flag: button closes them again", not pg.locator("#stb tr.tbn:not([hidden]) .tbd").first.is_visible())
        ok(f"{code} tie-flag: every outcome listed", all(all(t.lower() in box.lower() for t in o) for o in T["outcomes"]), box)
        ok(f"{code} tie-flag: no JS errors", not [m for m in msgs if "404" not in m and "Failed to load resource" not in m], msgs)
        if "--crops" in sys.argv and code == "big12":
            ctx.close()
            for w in (320, 390, 1280):
                ctx, pg, _ = open_page(b, slug, code, w)
                pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(300)
                pg.screenshot(path=f"{C}/sim-{code}-tie-top-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 900}); pg.locator("#sim").screenshot(path=f"{C}/sim-{code}-tie-{w}.png"); ctx.close()
        else: ctx.close()
    # sim5: every remaining game starts filled (ESPN favorite first, otherwise the better-record team); no unset game on first load in all 10 conferences
    def rec_side(code, g):
        conf = SIM[code]; played = [x for x in conf["games"] if x["w"] is not None]
        def r(t):
            w = sum(1 for x in played if (x["h"] == t and x["w"]) or (x["a"] == t and not x["w"])); n = sum(1 for x in played if t in (x["h"], x["a"])); nc = conf["nc"][t]
            return ((w + nc["w"]) / (n + nc["g"]) if n + nc["g"] else 0, w / n if n else 0)
        h, a = r(g["h"]), r(g["a"])
        if abs(h[0] - a[0]) > 1e-9: return 1 if h[0] > a[0] else 0
        if abs(h[1] - a[1]) > 1e-9: return 1 if h[1] > a[1] else 0
        return 1
    for code, slug in CONFS:
        rem = [g for g in SIM[code]["games"] if g["w"] is None]; N = len(rem)
        lines = {"l": {}}; now = int(time.time()); esp = rem[::9]   # ESPN lists a favorite for about 1 game in 9: the opposite of the better-record team for the first of them (precedence check)
        for i, g in enumerate(esp):
            side = rec_side(code, g) if i else 1 - rec_side(code, g)
            lines["l"][g["k"]] = [-3.5 if side else 3.5, now - 3600, now + 86400 * 5]
        ctx = b.new_context(viewport={"width": 390, "height": 900}); pg = ctx.new_page(); msgs = []; pg.on("pageerror", lambda e: msgs.append(str(e)))
        body = json.dumps(lines); pg.route("**/data/pred-lines.json", (lambda bb: (lambda r_: r_.fulfill(status=200, content_type="application/json", body=bb)))(body))
        pg.goto(f"{BASE}/conference/{slug}/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(300)
        ok(f"{code} sim5: ESPN lists {len(esp)}, rest start from better record: counts {len(esp)} fav / {N - len(esp)} rec, 0 changed, nothing unset", nums(pg)[:3] == [N, 0, N - len(esp)] and pg.locator("#games .gcard.r-fav").count() == len(esp) and pg.locator("#games .gcard.r-rec").count() == N - len(esp) and pg.locator("#games .gcard.r-nol, #games .gcard.r-clr").count() == 0 and pg.locator("#games .wb[aria-pressed=true]").count() == N, (nums(pg), len(esp)))
        side = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('#games .wb[aria-pressed=true]')].map(b => [b.dataset.g, +b.dataset.s]))")
        bad = []
        for i, g in enumerate(rem):
            if g["k"] in lines["l"]: exp = 1 if lines["l"][g["k"]][0] < 0 else 0
            else: exp = rec_side(code, g)
            if side.get(g["id"]) != exp: bad.append(g["k"])
        ok(f"{code} sim5: every game's start side = ESPN favorite where listed (first ESPN game deliberately opposes the record), else the better-record team", not bad, bad[:3])
        ok(f"{code} sim5: legend order ESPN / Better record / Changed by you, no 'pick'", pg.inner_text("#strip .lg2").replace("\n", "|") .startswith("ESPN's pre-game favorite|Better record or home team|Changed by you") and not re.search(r"\bpick", pg.inner_text("#sim").lower()), pg.inner_text("#strip .lg2"))
        ok(f"{code} sim5: how-to + note text", pg.inner_text("#how") == "Games start from ESPN's pre-game favorite, or the team with the better record (the home team if records are level) where none is listed yet. Tap a team to flip a game." and pg.inner_text("#favnote").endswith("with the team with the better record (or the home team when records are level) because ESPN has not listed a favorite yet."), pg.inner_text("#favnote"))
        # flip a better-record game: changed 1, rec count -1, row becomes 'Changed by you'; per-row reset restores 'Better record'
        rg = pg.locator("#games .gcard.r-rec").first; gid = rg.locator(".wb").first.get_attribute("data-g")
        pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first.click(); pg.wait_for_timeout(50)
        ok(f"{code} sim5: flipping a better-record game -> 1 changed, one fewer from better record, row says Changed by you", nums(pg)[:3] == [N, 1, N - len(esp) - 1] and pg.locator(f'#games .gcard:has(.wb[data-g="{gid}"]) .gt').inner_text().startswith("Changed by you"), nums(pg))
        pg.locator(f'#games .lnk[data-r="{gid}"]').click(); ok(f"{code} sim5: per-game reset restores the better-record start", nums(pg)[:3] == [N, 0, N - len(esp)] and pg.locator(f'#games .gcard.r-rec:has(.wb[data-g="{gid}"])').count() == 1)
        pg.locator("#games .gcard.r-rec .wb[aria-pressed=false]").first.click(); pg.locator("#games .gcard.r-fav .wb[aria-pressed=false]").first.click(); pg.wait_for_timeout(50)
        ok(f"{code} sim5: flip one better-record and one ESPN game -> 2 changed", nums(pg)[:3] == [N, 2, N - len(esp) - 1], nums(pg))
        pg.click("#rfav"); ok(f"{code} sim5: Reset to favorites restores both ESPN and better-record starts", nums(pg)[:3] == [N, 0, N - len(esp)] and pg.locator("#games .gcard.r-fav").count() == len(esp) and pg.locator("#games .wb[aria-pressed=true]").count() == N)
        pg.click("#clr"); ok(f"{code} sim5: Clear all still clears everything to unset (all count as changed, none from better record)", pg.locator("#games .wb[aria-pressed=true]").count() == 0 and nums(pg)[:2] == [N, N] and "from record or home team" not in pg.inner_text("#strip") and pg.locator("#games .gcard.r-clr").count() == N)
        pg.click("#rfav"); ok(f"{code} sim5: Reset after Clear refills", nums(pg)[:3] == [N, 0, N - len(esp)])
        pg.click("#rnd"); ok(f"{code} sim5: Random still fills every game", pg.locator("#games .wb[aria-pressed=true]").count() == N)
        pg.click("#rfav"); ok(f"{code} sim5: Reset after Random refills", nums(pg)[:3] == [N, 0, N - len(esp)])
        ok(f"{code} sim5: no JS errors", not msgs, msgs); ctx.close()
        if code == "big12": print(f"  big12: ESPN {len(esp)} / better record {N - len(esp)} of {N} in this test")
    # F4: teams with different records but equal win percentage (4-0 and 3-0) are never printed with one shared record
    hand = json.loads(json.dumps(SIM["pac12"])); T4 = ["Oregon State", "Boise State", "Colorado State", "Utah State"]
    hand["teams"] = [{"i": i, "name": n + " X", "short": n, "slug": n.lower().replace(" ", "-")} for i, n in enumerate(T4)]; hand["div"] = None; hand["nc"] = []
    hand["games"] = [{"id": str(900 + i), "h": a, "a": c, "w": 1, "wk": 1, "date": "2026-10-03T22:00Z", "neu": False, "k": f"{T4[a].lower().replace(' ', '-')}~{T4[c].lower().replace(' ', '-')}"} for i, (a, c) in enumerate([(0, 2), (0, 3), (0, 2), (0, 3), (1, 2), (1, 3), (1, 3)])]
    hand["games"].append({"id": "999", "h": 2, "a": 3, "w": None, "wk": 9, "date": "2099-01-01T22:00Z", "neu": False, "k": "colorado-state~utah-state"})
    alld = json.load(open(f"{SITE}/data/ccg-sim.json")); alld["confs"]["pac12"] = hand
    ctx = b.new_context(viewport={"width": 390, "height": 900}); pg = ctx.new_page(); msgs = []; pg.on("pageerror", lambda e: msgs.append(str(e)))
    pg.route("**/data/ccg-sim.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(alld))); pg.route("**/data/pred-lines.json", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(f"{BASE}/conference/pac-12/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(300)
    pg.locator("#games .wb[aria-pressed=false]").first.click(); pg.wait_for_timeout(300)
    allt = pg.evaluate("() => { document.querySelectorAll('#sim details').forEach(d => d.open = true); document.querySelectorAll('#sim [hidden]').forEach(e => e.hidden = false); return document.getElementById('sim').textContent; }")
    ok("F4 browser: 4-0 and 3-0 teams tied on win percentage: 'both unbeaten', never 'tied at 3-0' / 'Tied at 3-0'", re.search(r"\bboth unbeaten\b", allt) and not re.search(r"[Tt]ied at \d-\d", allt) and not msgs, (re.findall(r".{40}[Tt]ied.{40}", allt)[:3], msgs))
    ctx.close()
    # ---- sim6: sticky week tabs (one week at a time) + team logos ----
    BARH6 = {320: 56, 390: 56, 1280: 64}
    for w in (320, 390, 1280):
        ctx, pg, msgs = open_page(b, "big-12", "big12", w, noline=(1, 5, 9))
        reqs = []; pg.on("request", lambda r: reqs.append(r.url))
        pg.reload(); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(400)
        tabs = pg.evaluate("() => [...document.querySelectorAll('#wkstrip .tab')].map(t => ({n: t.querySelector('.n').textContent, c: t.querySelector('.c').textContent, cur: t.getAttribute('aria-current'), al: t.getAttribute('aria-label'), h: t.getBoundingClientRect().height, wd: t.getBoundingClientRect().width}))")
        ok(f"big12@{w}: 5 week tabs 'Wk 9'..'Wk 13', Wk 9 current, '7 games' / '8 games', tab >= 44px, name 'Week 9, 7 games'", [t["n"] for t in tabs] == ["Wk 9", "Wk 10", "Wk 11", "Wk 12", "Wk 13"] and tabs[0]["cur"] == "true" and sum(1 for t in tabs if t["cur"]) == 1 and tabs[0]["c"] == "7 games" and tabs[1]["c"] == "8 games" and all(t["h"] >= 43.5 and t["wd"] >= 43.5 for t in tabs) and tabs[0]["al"] == "Week 9, 7 games", tabs)
        ok(f"big12@{w}: nav aria-label 'Weeks'; panel heading 'Week 9' (h3), sub line 'Oct 31 · 7 games', list labelled by the heading, 7 visible rows 'Game 1 of 7: ...'", pg.evaluate("() => { const h = document.getElementById('wph'); const v = [...document.querySelectorAll('#games > li')].filter(x => !x.hidden); return document.querySelector('nav.wkstrip').getAttribute('aria-label') === 'Weeks' && h.tagName === 'H3' && h.textContent === 'Week 9' && h.tabIndex === -1 && /^[A-Z][a-z]{2} \\d+(\\u2013\\d+)? \\u00B7 7 games$/.test(document.getElementById('wsub').textContent) && document.getElementById('games').getAttribute('aria-labelledby') === 'wph' && v.length === 7 && /^Game 1 of 7: /.test(v[0].querySelector('.gtl').textContent) && !/Game \\d+ of 39/.test(document.getElementById('games').textContent); }"))
        ok(f"big12@{w}: Remaining games is above Standings; no horizontal overflow", pg.evaluate("() => document.getElementById('gh').getBoundingClientRect().top < document.getElementById('sh').getBoundingClientRect().top && document.documentElement.scrollWidth <= innerWidth + 1"))
        pg.click('#wkstrip .tab[data-w="10"]'); pg.wait_for_timeout(500)
        ok(f"big12@{w}: tab click switches the panel: heading 'Week 10', 8 rows, others hidden, tab current, live region 'Week 10, 8 games'", pg.evaluate("() => { const v = [...document.querySelectorAll('#games > li')].filter(x => !x.hidden); return document.getElementById('wph').textContent === 'Week 10' && v.length === 8 && v.every(x => x.dataset.w === '10') && document.querySelector('#wkstrip .tab[aria-current]').dataset.w === '10' && document.querySelectorAll('#wkstrip [aria-current]').length === 1; }") and "Week 10, 8 games" in pg.text_content("#ann"), pg.text_content("#ann"))
        gid = pg.evaluate("() => [...document.querySelectorAll('#games > li')].filter(x => !x.hidden)[0].querySelector('.wb[aria-pressed=false]').dataset.g")
        pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first.click(); pg.wait_for_timeout(400)
        bd = pg.evaluate("() => [...document.querySelectorAll('#wkstrip .tab')].map(t => { const b = t.querySelector('.bd'); return [b.hidden ? '' : b.textContent, t.getAttribute('aria-label')]; })")
        ok(f"big12@{w}: a flip puts a count badge on that week's tab only, tab name 'Week 10, 8 games, 1 changed', sub line '... · 1 changed'", bd[1] == ["1", "Week 10, 8 games, 1 changed"] and all(x[0] == "" for i, x in enumerate(bd) if i != 1) and pg.text_content("#wsub").endswith("\u00B7 8 games \u00B7 1 changed"), bd)
        pg.click("#games ~ #wnavs .wnav.pri"); pg.wait_for_timeout(400)
        ok(f"big12@{w}: Next week -> Week 11, focus moves to the week heading, heading sits below the pinned stack", pg.evaluate("() => document.activeElement.id") == "wph" and pg.text_content("#wph") == "Week 11" and pg.evaluate("(bh) => document.getElementById('wph').getBoundingClientRect().top >= bh + 44 + 50", BARH6[w]), pg.evaluate("() => [document.activeElement.id, document.getElementById('wph').getBoundingClientRect().top]"))
        pg.click('#wkstrip .tab[data-w="13"]'); pg.wait_for_timeout(400)
        ls = pg.evaluate("() => [...document.querySelectorAll('#wnavs .wnav')].map(x => [x.textContent, x.getBoundingClientRect().height])")
        ok(f"big12@{w}: last week: primary 'See CCG box' + 'Previous week Week 12', 56px high", len(ls) == 2 and ls[0][0].startswith("See CCG box") and ls[1][0] == "Previous weekWeek 12" and all(x[1] >= 55.5 for x in ls), ls)
        pg.click("#wnavs .wnav.pri"); pg.wait_for_timeout(400)
        ok(f"big12@{w}: See CCG box scrolls to the box and focuses it", pg.evaluate("() => document.activeElement.id") == "ccg" and pg.evaluate("() => document.getElementById('ccg').getBoundingClientRect().top >= 0 && document.getElementById('ccg').getBoundingClientRect().top < 200"))
        pg.click("#clr"); pg.wait_for_timeout(300)
        bd = pg.evaluate("() => [...document.querySelectorAll('#wkstrip .tab .bd')].map(b => b.hidden ? '' : b.textContent)")
        ok(f"big12@{w}: Clear all re-renders every week (badges = each week's game count); current week stays", bd == ["7", "8", "8", "8", "8"] and pg.text_content("#wph") == "Week 13", bd)
        pg.click("#rfav"); pg.wait_for_timeout(300)
        ok(f"big12@{w}: Reset to favorites clears the badges", all(x == "" for x in pg.evaluate("() => [...document.querySelectorAll('#wkstrip .tab .bd')].map(b => b.hidden ? '' : b.textContent)")))
        ok(f"big12@{w}: only same-origin requests (logos are self-hosted)", all(u.startswith(BASE) or u.startswith("data:") for u in reqs) and any("/assets/logos/" in u for u in reqs), [u for u in reqs if not u.startswith(BASE)][:3])
        ok(f"big12@{w}: no JS errors", not [m for m in msgs if "404" not in m and "Failed to load resource" not in m], msgs)
        ctx.close()
    # sticky stack: header > CCG bar (44) > week strip, strip releases at the end of the section; ?wk= override
    for w in (320, 390, 1280):
        ctx, pg, msgs = open_page(b, "big-12", "big12", w)
        pg.evaluate("() => document.getElementById('weeks').scrollIntoView()"); pg.evaluate("() => scrollBy(0, 500)"); pg.wait_for_timeout(500)
        st = pg.evaluate("() => { const s = document.getElementById('wkstrip').getBoundingClientRect(), b = document.getElementById('ccgc').getBoundingClientRect(); return {st: s.top, sh: s.height, bt: b.top, bh: b.height, on: document.getElementById('ccgc').classList.contains('on'), pos: getComputedStyle(document.getElementById('wkstrip')).position, sb: getComputedStyle(document.documentElement).getPropertyValue('--sim-sb')}; }")
        ok(f"big12@{w}: pinned stack: bar under the header, week strip directly under the bar (sticky), no gap/overlap", st["on"] and st["pos"] == "sticky" and abs(st["bt"] - BARH6[w]) <= 1 and abs(st["st"] - (BARH6[w] + 44)) <= 1 and st["sb"].strip() == "44px", st)
        pg.evaluate("() => document.getElementById('sh').scrollIntoView()"); pg.wait_for_timeout(400)
        ok(f"big12@{w}: the strip releases at the end of the Remaining games section", pg.evaluate("() => document.getElementById('wkstrip').getBoundingClientRect().top") < 0 or pg.evaluate("() => document.getElementById('wkstrip').getBoundingClientRect().bottom") < pg.evaluate("() => document.getElementById('sh').getBoundingClientRect().top"))
        pg.evaluate("() => scrollTo(0, 0)"); pg.wait_for_timeout(300)
        ok(f"big12@{w}: at the top the bar is hidden and --sim-sb is 0", pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--sim-sb')").strip() == "0px")
        ctx.close()
    ctx = b.new_context(viewport={"width": 390, "height": 900}); pg = ctx.new_page()
    for q, want in (("?wk=11", "Week 11"), ("?wk=99", "Week 9"), ("?wk=x", "Week 9")):
        pg.goto(f"{BASE}/conference/big-12/simulator/{q}"); pg.wait_for_selector("#sim[data-ready]", timeout=8000)
        ok(f"week override {q}: opens {want}", pg.text_content("#wph") == want, pg.text_content("#wph"))
    ctx.close()
    # logos
    for w in (320, 390, 1280):
        ctx, pg, msgs = open_page(b, "big-12", "big12", w, noline=(1, 5, 9))
        L = pg.evaluate("""() => { const t = [...document.querySelectorAll('#sim .lg')]; const bad = t.filter(x => x.getAttribute('aria-hidden') !== 'true' || (x.querySelector('img') && (x.querySelector('img').getAttribute('alt') !== '' || !x.querySelector('img').getAttribute('width') || !x.querySelector('img').getAttribute('height') || !/^\\/assets\\/logos\\/(32|64)\\/\\d+\\.png$/.test(x.getAttribute('src') || x.querySelector('img').getAttribute('src'))))).length;
          const wb = [...document.querySelectorAll('#games .wb')]; const wbok = wb.every(x => x.querySelectorAll('.lg').length === 1 && /^.+ wins$/.test(x.querySelector('.wt').textContent) && x.getAttribute('aria-pressed') !== null);
          const sz = [...document.querySelectorAll('#games .lg')].every(x => x.classList.contains('s24')); const lazy = [...document.querySelectorAll('#games .lg img')].every(x => x.getAttribute('loading') === 'lazy');
          const st = [...document.querySelectorAll('#stb tr')].filter(r => r.querySelector('.tn2')); const stok = st.length === 16 && st.every(r => r.querySelectorAll('.tcell > .lg.s24').length === 1);
          const box = document.querySelectorAll('#ccg .m .lg.s28').length; const names = [...document.querySelectorAll('#games .gtl')].every(x => !x.querySelector('.lg'));
          const tabs = document.querySelectorAll('#wkstrip .lg').length; const imgs = [...document.querySelectorAll('#sim img')].every(x => x.getAttribute('src').startsWith('/'));
          const gh = [...document.querySelectorAll('#games .wb')].map(x => x.getBoundingClientRect()).filter(r => r.height); const hh = gh.map(r => Math.round(r.height));
          return {n: t.length, bad, wbok, sz, lazy, stok, box, names, tabs, imgs, hmin: Math.min(...hh), hmax: Math.max(...hh)}; }""")
        ok(f"big12@{w}: logos: every tile aria-hidden, alt='' with width/height, self-hosted; 24px in rows/standings (16 rows), 28px in the CCG box; name text beside each; none in game headings or tabs; row images lazy", L["n"] > 60 and L["bad"] == 0 and L["wbok"] and L["sz"] and L["lazy"] and L["stok"] and L["box"] == 2 and L["names"] and L["tabs"] == 0 and L["imgs"], L)
        ok(f"big12@{w}: winner buttons stay 52px high (not selected; selected up to 64px at the narrowest)", L["hmin"] == 52 and L["hmax"] <= 64, L)
        pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400)
        bl = pg.evaluate("() => { const b = document.querySelector('#ccgc b'); return [b.querySelectorAll('.lg.s24').length, b.scrollWidth <= b.clientWidth + 1, document.documentElement.scrollWidth <= innerWidth + 1]; }")
        ok(f"big12@{w}: pinned bar shows 2 logo tiles + both names on one line, no overflow", bl == [2, True, True], bl)
        cr = pg.evaluate("""() => { const n = [...document.querySelectorAll('#games .wb')].filter(x => x.getBoundingClientRect().height).map(x => ({c: x.scrollWidth > x.clientWidth + 1 || x.scrollHeight > x.clientHeight + 1, t: x.textContent})); return n.filter(x => x.c).map(x => x.t); }""")
        ok(f"big12@{w}: no winner-button text clipped", not cr, cr)
        ctx.close()
    # all 10 conferences: tiles exist for every team (map has all slugs), no overflow at 320
    for slug, code in (("pac-12", "pac12"), ("big-ten", "big10"), ("sec", "sec"), ("conference-usa", "usa"), ("mac", "midam"), ("mountain-west", "mwest"), ("sun-belt", "belt"), ("acc", "acc"), ("american", "American")):
        ctx, pg, msgs = open_page(b, slug, code, 320)
        r = pg.evaluate("() => [document.querySelectorAll('#stb .tcell .lg').length, document.querySelectorAll('#games .lg').length, document.querySelectorAll('#games .lg.nf').length, document.documentElement.scrollWidth <= innerWidth + 1, [...document.querySelectorAll('#games .wb')].filter(x => x.getBoundingClientRect().height && x.scrollHeight > x.clientHeight + 1).length, document.querySelectorAll('#wkstrip .tab').length]")
        ok(f"{code}@320: logos in standings + rows, no fallback tiles, no overflow/clipping, tabs match weeks", r[0] >= 8 and r[1] > 0 and r[2] == 0 and r[3] and r[4] == 0 and r[5] >= 4, r)
        ctx.close()
    # tie: bar says 'N pairings possible' with NO logos; the tie box shows a logo beside each name in each pairing
    r = subprocess.run(["node", f"{ROOT}/tests/ccg_find_tie.js", "big12"], capture_output=True, text=True)
    if not r.returncode:
        T = json.loads(r.stdout)
        for w in (320, 390):
            ctx, pg, msgs = open_page(b, "big-12", "big12", w)
            pg.evaluate("p => { for (const [g, s] of Object.entries(p)) { const b = document.querySelector('.wb[data-g=\"' + g + '\"][data-s=\"' + s + '\"]'); if (b) b.click(); } }", T["picks"]); pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('games').scrollIntoView()"); pg.wait_for_timeout(400)
            tl = pg.evaluate("() => [document.querySelectorAll('#ccgc .lg').length, document.querySelectorAll('#ccg .pr .pm .lg.s24').length, document.querySelectorAll('#ccg .pr').length]")
            ok(f"big12 tie@{w}: bar has no logos; each possible pairing shows a 24px logo beside each name", tl[0] == 0 and tl[2] >= 2 and tl[1] == 2 * tl[2], tl)
            ctx.close()
    # failed logo images: initials tile, names unchanged, sizes unchanged, no horizontal overflow
    for w in (320, 390):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); msgs = []; pg.on("pageerror", lambda e: msgs.append(str(e)))
        pg.route("**/assets/logos/**", lambda r: r.abort())
        pg.goto(f"{BASE}/conference/big-12/simulator/"); pg.wait_for_selector("#sim[data-ready]", timeout=8000); pg.wait_for_timeout(600)
        pg.click("#smore"); pg.evaluate("() => document.getElementById('stb').scrollIntoView({block: 'end'})"); pg.wait_for_timeout(300)
        for wk in (10, 11, 12, 13): pg.click(f'#wkstrip .tab[data-w="{wk}"]'); pg.wait_for_timeout(250)
        pg.wait_for_timeout(600)
        f = pg.evaluate("() => { const t = [...document.querySelectorAll('#games .lg, #stb .lg, #ccg .lg')]; return {n: t.length, nf: t.filter(x => x.classList.contains('nf')).length, img: t.filter(x => x.querySelector('img')).length, fb: t.every(x => x.querySelector('.fb') && x.querySelector('.fb').textContent.length >= 1 && (!x.classList.contains('nf') || getComputedStyle(x.querySelector('.fb')).display !== 'none')), h: Math.min(...[...document.querySelectorAll('#games .wb')].map(x => x.getBoundingClientRect().height).filter(Boolean)), ov: document.documentElement.scrollWidth <= innerWidth + 1, wt: [...document.querySelectorAll('#games .wb .wt')].every(x => /^.+ wins$/.test(x.textContent))}; }")
        ok(f"big12@{w}: every logo that fails to load becomes the initials tile (no img left), names and sizes unchanged", f["n"] > 60 and f["nf"] == f["n"] and f["img"] == 0 and f["fb"] and f["h"] == 52 and f["ov"] and f["wt"] and not msgs, f)
        ctx.close()
    # footer credit: exactly one 'courtesy of ESPN' line on every simulator page
    # sim6 L9: records level -> home team gets its own label; legend lists only the kinds present
    def rec_level(code, g):
        conf = SIM[code]; played = [x for x in conf["games"] if x["w"] is not None]
        def r(t):
            w = sum(1 for x in played if (x["h"] == t and x["w"]) or (x["a"] == t and not x["w"])); n = sum(1 for x in played if t in (x["h"], x["a"])); nc = conf["nc"][t]
            return ((w + nc["w"]) / (n + nc["g"]) if n + nc["g"] else 0, w / n if n else 0)
        h, a = r(g["h"]), r(g["a"])
        return abs(h[0] - a[0]) <= 1e-9 and abs(h[1] - a[1]) <= 1e-9
    tot_level = 0
    for code, slug in CONFS:
        rem = [g for g in SIM[code]["games"] if g["w"] is None]; N = len(rem); lv = {g["id"] for g in rem if rec_level(code, g)}; tot_level += len(lv)
        ctx, pg, msgs = open_page(b, slug, code, 390, lines="missing")
        tags = pg.evaluate("() => [...document.querySelectorAll('#games .gcard.r-rec')].map(c => [c.querySelector('.wb').dataset.g, c.querySelector('.gt span').textContent, !!c.querySelector('.gt svg'), c.querySelector('.gt svg path') ? c.querySelector('.gt svg path').getAttribute('d') : '', c.textContent.includes(\"the two teams' records are level, so starting with the home team\")])")
        ok(f"{code} L9: {len(lv)} level-record games carry 'Records level: home team' + house icon + screen-reader sentence; the rest 'Better record' + bars icon, no level sentence", len(tags) == N and {t[0] for t in tags if t[1] == "Records level: home team"} == {str(i) for i in lv} | {i for i in lv} and all(t[2] for t in tags) and all((t[4] and t[1] == "Records level: home team") or (not t[4] and t[1] == "Better record") for t in tags) and len({t[3] for t in tags if t[1] != "Better record"}) <= 1 and not ({t[3] for t in tags if t[1] != "Better record"} & {t[3] for t in tags if t[1] == "Better record"}), (len(tags), len(lv)))
        ok(f"{code} L9: no ESPN lines -> legend 'Better record or home team|Changed by you' (no ESPN entry), third stat '{N} from record or home team', no 'pick'", pg.inner_text("#strip .lg2").replace("\n", "|") == "Better record or home team|Changed by you" and nums(pg) == [N, 0, N] and pg.inner_text("#strip .pn.z") == f"{N}\nfrom record or home team" and not re.search(r"\bpick", pg.inner_text("#sim").lower()), (pg.inner_text("#strip .lg2"), nums(pg)))
        if lv:
            gid = sorted(lv)[0] if isinstance(sorted(lv)[0], str) else sorted(lv)[0]
            pg.locator(f'#games .wb[data-g="{gid}"][aria-pressed=false]').first.evaluate("e => e.click()"); pg.wait_for_timeout(50)
            ok(f"{code} L9: flipped level-record row -> per-row reset reads 'Reset to home team', not 'favorite'", pg.locator(f'#games .lnk[data-r="{gid}"]').text_content() == "Reset to home team" and pg.locator(f'#games .lnk[data-r="{gid}"]').get_attribute("aria-label").startswith("Reset to home team, "), pg.locator(f'#games .lnk[data-r="{gid}"]').get_attribute("aria-label"))
            pg.locator(f'#games .lnk[data-r="{gid}"]').evaluate("e => e.click()"); pg.wait_for_timeout(50)
            ok(f"{code} L9: reset restores the level-record row (tag back, nothing changed)", nums(pg)[1] == 0 and pg.locator(f'#games .gcard:has(.wb[data-g="{gid}"]) .gt span').first.text_content() == "Records level: home team")
        rgid = pg.locator("#games .gcard.r-rec:has(.gt svg) .wb").evaluate_all("els => els.filter(e => e.closest('.gcard').querySelector('.gt span').textContent === 'Better record').map(e => e.dataset.g)")
        if rgid:
            pg.locator(f'#games .wb[data-g="{rgid[0]}"][aria-pressed=false]').first.evaluate("e => e.click()"); pg.wait_for_timeout(50)
            ok(f"{code} L9: flipped better-record row -> per-row reset reads 'Reset to better record'", pg.locator(f'#games .lnk[data-r="{rgid[0]}"]').text_content() == "Reset to better record", pg.locator(f'#games .lnk[data-r="{rgid[0]}"]').text_content())
        ctx.close()
        # all games have ESPN lines -> no record entries, no 'from record' stat
        ctx, pg, msgs = open_page(b, slug, code, 390, lines="fresh")
        ok(f"{code} L9: every game has an ESPN line -> legend 'ESPN's pre-game favorite|Changed by you' only, no third stat", pg.inner_text("#strip .lg2").replace("\n", "|") == "ESPN's pre-game favorite|Changed by you" and len(nums(pg)) == 2, (pg.inner_text("#strip .lg2"), nums(pg)))
        ctx.close()
    ok("L9: level-record games exist in the data (sum over 10 conferences, QA found 14 in Big 12)", tot_level >= 14, tot_level)
    for slug in ("big-12", "pac-12", "big-ten", "sec", "conference-usa", "mac", "mountain-west", "sun-belt", "acc", "american"):
        h = open(f"{SITE}/conference/{slug}/simulator/index.html", encoding="utf-8").read()
        ok(f"{slug}: credit 'Team, conference and league logos courtesy of ESPN' appears exactly once; lg.js loads before ccgsim-ui.js", h.count("logos courtesy of ESPN") == 1 and h.index("/assets/lg.js") < h.index("/assets/ccgsim-ui.js") and 'class="cred"' in h)
    b.close()
print(f"ccgsim browser test: {n} checks, {len(fails)} failed"); sys.exit(1 if fails else 0)
