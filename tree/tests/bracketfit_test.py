"""Bracket "Fit to screen" test (headless Chromium + WebKit; static site served with the real _headers CSP). python3 tests/bracketfit_test.py [--crops]
Checks the three views (Fit offered at <=1100px only; >=1101px the page is the plain full bracket with no toggle, exactly as live), page lock + inert while the sheet is open (wheel, Esc from body, state restored), the portrait fallback to By round, scale and legibility at real phone/tablet/desktop sizes, the game sheet (open, focus, Tab trap, Esc, close, return focus),
the remembered choice (one localStorage key), blocked storage, orientation/resize re-evaluation, CSP, no page-level sideways scroll, and that the bracket's text/links are unchanged."""
import sys, os, json, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"; CROPS = f"{ROOT}/crops-bracketfit"
res = {"f": [], "n": 0, "info": {}}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["f"].append(f"{name} {detail}")
KEY = "kt-bracket-view"
MEAS = """() => { const w = document.querySelector('#bracket .bkw'), bk = w.querySelector('.bk'); const tn = bk.querySelector('.r1 .tn'); const r = bk.getBoundingClientRect(); const fs = tn ? parseFloat(getComputedStyle(tn).fontSize) : 0;
  const m = bk.style.getPropertyValue('--bks') || w.style.getPropertyValue('--bks'); const s = parseFloat(w.style.getPropertyValue('--bks') || '1');
  const g = [...bk.querySelectorAll('.bkgo')].map(b => { const q = b.getBoundingClientRect(); return [q.width, q.height]; });
  return { view: w.getAttribute('data-view'), fit: w.classList.contains('bkfit'), s, namePx: fs * (w.classList.contains('bkfit') ? s : 1), docW: document.documentElement.scrollWidth, vw: innerWidth, bkR: r.right, bkL: r.left, btns: g.length, minBtnW: g.length ? Math.min(...g.map(a => a[0])) : 0, minBtnH: g.length ? Math.min(...g.map(a => a[1])) : 0,
    pressed: Object.fromEntries([...document.querySelectorAll('[data-bkt] button')].map(b => [b.textContent, b.getAttribute('aria-pressed')])), note: (document.querySelector('[data-bkfnote]') || {}).textContent || '', noteHidden: (document.querySelector('[data-bkfnote]') || {}).hidden, hintHidden: (document.querySelector('#bracket .bkh') || {}).hidden,
    bkh: bk.getBoundingClientRect().height, wh: w.getBoundingClientRect().height, tabindex: w.getAttribute('tabindex'), stored: (()=>{try{return localStorage.getItem('kt-bracket-view')}catch(e){return 'ERR'}})() }; }"""
def run(browser_name, bt, p, do_crops):
    br = getattr(p, browser_name).launch()
    def page(w, h, init=None, touch=False, ctx=None):
        c = ctx or br.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=False)
        if init: c.add_init_script(init)
        pg = c.new_page(); logs = []
        pg.on("console", lambda m: logs.append(m.text) if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: logs.append("PAGEERROR " + str(e)))
        pg.goto(BASE + "/playoff/"); pg.wait_for_selector("#bracket [data-bkfit]", state="attached", timeout=15000); pg.wait_for_timeout(300)
        return c, pg, logs
    tag = browser_name[:2]
    # ---- default: nothing stored, Full, toggle has three buttons
    c, pg, logs = page(1280, 800); m = pg.evaluate(MEAS)
    ok(f"{tag} default is Full, nothing stored", m["view"] in (None, "full") and not m["fit"] and m["stored"] is None, str(m))
    labels = pg.eval_on_selector_all("[data-bkt] button", "bs=>bs.map(b=>b.textContent)")
    ok(f"{tag} toggle = Full bracket / Fit to screen / By round (order)", labels == ["Full bracket", "Fit to screen", "By round"], str(labels))
    ok(f"{tag} no inline style attribute anywhere on the page markup", not re.search(r'<[^>]+ style=', open(f"{SITE}/playoff/index.html").read()))
    # text snapshot of the bracket before touching anything
    base_txt = pg.evaluate("() => [...document.querySelectorAll('#bracket .g')].map(g => [...g.querySelectorAll('.sl')].map(s => s.textContent.trim().replace(/\\s+/g,' ')).join(' | '))")
    base_links = pg.evaluate("() => [...document.querySelectorAll('#bracket a.tl')].map(a => a.getAttribute('href'))")
    ok(f"{tag} 11 games, links present", len(base_txt) == 11 and len(base_links) >= 12 and all(l.startswith('/team/') for l in base_links), str(len(base_links)))
    # ---- 1101+ : plain full bracket, no toggle (as live shield2); 1100- : toggle with Fit
    VIS = "() => { const b = document.querySelector('[data-bkfit]'), t = document.querySelector('[data-bkt]'); const vis = e => !!(e && e.offsetParent !== null && getComputedStyle(e).visibility !== 'hidden' && e.getBoundingClientRect().height > 0); const w = document.querySelector('#bracket .bkw'); return { fitBtn: vis(b), bar: vis(t), cls: w.classList.contains('bkfit'), btns: document.querySelectorAll('.bkgo').length, view: w.getAttribute('data-view'), tabindex: w.getAttribute('tabindex'), note: vis(document.querySelector('[data-bkfnote]')) }; }"
    c.close()
    for (ww, vis_expect) in ((1280, False), (1101, False), (1100, True), (1024, True)):
        c, pg, logs = page(ww, 800); v = pg.evaluate(VIS)
        ok(f"{tag} {ww}: Fit button {'visible' if vis_expect else 'hidden'}; toggle bar {'visible' if vis_expect else 'hidden (as live)'}", v["fitBtn"] == vis_expect and v["bar"] == vis_expect, str(v))
        if do_crops and browser_name == "chromium":
            pg.locator("#bracket").screenshot(path=f"{CROPS}/playoff-bracket-{ww}-default.png"); pg.screenshot(path=f"{CROPS}/playoff-page-{ww}-default.png", full_page=True)
        c.close()
    for ww in (1280, 1101):   # a saved Fit / By round choice never changes the wide page, and the choice is kept
        for val in ("fit", "rounds"):
            c, pg, logs = page(ww, 800, init=f"try{{localStorage.setItem('kt-bracket-view','{val}')}}catch(e){{}}"); v = pg.evaluate(VIS); st = pg.evaluate("() => localStorage.getItem('kt-bracket-view')")
            ok(f"{tag} {ww} with saved '{val}': plain full bracket, no card buttons, no toggle, saved value kept", not v["cls"] and v["btns"] == 0 and v["view"] in (None, "full") and not v["bar"] and not v["note"] and st == val, str((v, st)))
            if val == "fit":   # narrow it: Fit applies; widen again: plain again
                pg.set_viewport_size({"width": 1000, "height": 700}); pg.wait_for_timeout(400); v = pg.evaluate(VIS); ok(f"{tag} {ww}->1000 with saved fit: Fit on, toggle shown", v["cls"] and v["btns"] == 11 and v["fitBtn"], str(v))
                pg.set_viewport_size({"width": ww, "height": 800}); pg.wait_for_timeout(400); v = pg.evaluate(VIS); ok(f"{tag} back to {ww}: plain full bracket again", not v["cls"] and v["btns"] == 0 and not v["bar"] and v["view"] in (None, "full") and v["tabindex"] == "0", str(v))
            c.close()
    c, pg, logs = page(1024, 800)
    # ---- 1024 Fit
    pg.click("[data-bkfit]"); pg.wait_for_timeout(200); m = pg.evaluate(MEAS)
    ok(f"{tag} 1024 Fit: fitted, 11 card buttons, stored fit", m["fit"] and 0.9 < m["s"] <= 1 and m["btns"] == 11 and m["stored"] == "fit" and m["docW"] <= m["vw"], str(m))
    ok(f"{tag} 1024 Fit: pressed state + note", m["pressed"].get("Fit to screen") == "true" and m["pressed"].get("Full bracket") == "false" and "Tap or click" in m["note"], str(m["pressed"]))
    ok(f"{tag} 1024 Fit: card buttons >= 44px", m["minBtnW"] >= 44 and m["minBtnH"] >= 44, str((m["minBtnW"], m["minBtnH"])))
    fit_txt = pg.evaluate("() => [...document.querySelectorAll('#bracket .g')].map(g => [...g.querySelectorAll('.sl')].map(s => s.textContent.trim().replace(/\\s+/g,' ')).join(' | '))")
    ok(f"{tag} Fit leaves bracket text unchanged", fit_txt == base_txt)
    ok(f"{tag} Fit: inner links not tabbable (inert)", pg.evaluate("() => [...document.querySelectorAll('#bracket .bkw.bkfit .g > :not(.bkgo)')].every(e => e.inert === true || e.hasAttribute('inert'))"))
    # ---- sheet
    pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(150)
    sh = pg.evaluate("() => { const s = document.querySelector('.bks'); const sc = document.querySelector('.bks-scrim'); return { open: sc && !sc.hidden, role: s && s.getAttribute('role'), modal: s && s.getAttribute('aria-modal'), focusInside: s && s.contains(document.activeElement), isDlg: document.activeElement === s, title: document.querySelector('#bks-t').textContent, round: document.querySelector('#bks-r').textContent, rows: document.querySelectorAll('.bks-s').length, links: [...document.querySelectorAll('.bks a.tl')].map(a => a.getAttribute('href')), minLinkH: Math.min(...[...document.querySelectorAll('.bks a.tl')].map(a => a.getBoundingClientRect().height)), closeH: document.querySelector('.bks-x').getBoundingClientRect().height, note: document.querySelector('.bks-n').textContent, label: document.querySelector('.bks').getAttribute('aria-labelledby') }; }")
    ok(f"{tag} focus moved into the sheet on open (the dialog itself)", sh["isDlg"] and sh["focusInside"], str(sh))
    ok(f"{tag} sheet opens as modal dialog with focus inside, 2 team rows, title, round", sh["open"] and sh["role"] == "dialog" and sh["modal"] == "true" and sh["focusInside"] and sh["rows"] == 2 and sh["title"].startswith("No. 5") and sh["round"] == "First round", str(sh))
    ok(f"{tag} sheet has both team links (same hrefs as the card), 44px taps", len(sh["links"]) == 2 and all(l in base_links for l in sh["links"]) and sh["minLinkH"] >= 44 and sh["closeH"] >= 43.9, str(sh))
    # Tab trap: Close -> link -> link -> back to Close
    seq = []
    for _ in range(4):
        pg.keyboard.press("Tab"); seq.append(pg.evaluate("() => document.activeElement.className || document.activeElement.tagName"))
    ok(f"{tag} Tab stays inside the sheet", pg.evaluate("() => document.querySelector('.bks').contains(document.activeElement)"), str(seq))
    pg.keyboard.press("Shift+Tab"); ok(f"{tag} Shift+Tab stays inside", pg.evaluate("() => document.querySelector('.bks').contains(document.activeElement)"))
    if do_crops and browser_name == "chromium": pg.screenshot(path=f"{CROPS}/sheet-open-1024.png")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    ok(f"{tag} Escape closes the sheet and returns focus to the game card button", pg.evaluate("() => document.querySelector('.bks-scrim').hidden && document.activeElement.classList.contains('bkgo')"))
    pg.click("#bracket .r2 .bkgo >> nth=1"); pg.wait_for_timeout(100); pg.click(".bks-x"); ok(f"{tag} Close button closes and focus returns to the tapped card", pg.evaluate("() => document.querySelector('.bks-scrim').hidden && document.activeElement.classList.contains('bkgo') && document.activeElement.closest('.rd').classList.contains('r2')"))
    pg.click("#bracket .r4 .bkgo"); pg.wait_for_timeout(100); pg.mouse.click(5, 5); ok(f"{tag} tap outside (scrim) closes", pg.evaluate("() => document.querySelector('.bks-scrim').hidden"))
    # keyboard open: Enter on a focused card button
    pg.focus("#bracket .r3 .bkgo >> nth=0"); pg.keyboard.press("Enter"); pg.wait_for_timeout(100)
    ok(f"{tag} Enter opens the sheet (semifinal, placeholder rows)", pg.evaluate("() => !document.querySelector('.bks-scrim').hidden && document.querySelectorAll('.bks .ph').length >= 1 && document.querySelector('#bks-t').textContent.startsWith('Semifinal')"))
    pg.keyboard.press("Escape")
    ok(f"{tag} no CSP / page errors at 1024 Fit", not [l for l in logs if re.search(r"Content Security|PAGEERROR|Refused", l)], str(logs[:3]))
    # persistence across reload
    pg.reload(); pg.wait_for_selector("#bracket .bkt:not([hidden])"); pg.wait_for_timeout(300); m = pg.evaluate(MEAS)
    ok(f"{tag} remembered after reload (Fit, no flash: class set)", m["fit"] and m["stored"] == "fit" and m["pressed"].get("Fit to screen") == "true", str(m))
    pg.click("[data-bkview=rounds]"); pg.wait_for_timeout(150); m = pg.evaluate(MEAS)
    ok(f"{tag} By round stores 'rounds', Fit off, hint hidden", m["view"] == "rounds" and not m["fit"] and m["stored"] == "rounds" and m["btns"] == 0 and m["hintHidden"] and m["tabindex"] == "0", str(m))
    pg.reload(); pg.wait_for_selector("#bracket .bkt:not([hidden])"); pg.wait_for_timeout(300); m = pg.evaluate(MEAS)
    ok(f"{tag} By round remembered after reload", m["view"] == "rounds" and m["pressed"].get("By round") == "true", str(m))
    pg.click("[data-bkview=full]"); pg.wait_for_timeout(150); m = pg.evaluate(MEAS)
    ok(f"{tag} Full removes the key (default stores nothing)", m["view"] == "full" and not m["fit"] and m["stored"] is None and m["pressed"].get("Full bracket") == "true", str(m))
    pg.reload(); pg.wait_for_selector("#bracket .bkt:not([hidden])"); m = pg.evaluate(MEAS); ok(f"{tag} Full after reload", not m["fit"] and m["view"] in (None, "full"), str(m))
    t2 = pg.evaluate("() => [...document.querySelectorAll('#bracket .g')].map(g => [...g.querySelectorAll('.sl')].map(s => s.textContent.trim().replace(/\\s+/g,' ')).join(' | '))")
    ok(f"{tag} back to Full: bracket text identical to the start", t2 == base_txt); c.close()
    # ---- sizes: Fit then By round
    for (w, h, nm, expect_fit) in ((390, 844, "390p", False), (430, 932, "430p", False), (320, 640, "320p", False), (844, 390, "844l", True), (932, 430, "932l", True), (667, 375, "667l", False), (768, 1024, "768", True), (1024, 768, "1024", True), (1100, 800, "1100", True)):
        c, pg, logs = page(w, h, touch=(w < 800)); pg.click("[data-bkfit]"); pg.wait_for_timeout(250); m = pg.evaluate(MEAS)
        if expect_fit:
            ok(f"{tag} {nm} Fit is true Fit (scale {m['s']:.2f}); names >= 11.5px", m["fit"] and m["btns"] == 11 and m["namePx"] >= 11.5 and m["docW"] <= m["vw"] and m["bkR"] <= m["vw"] + 1, str(m))
            ok(f"{tag} {nm} Fit: card buttons >= 44px", m["minBtnH"] >= 44 and m["minBtnW"] >= 44, str((m["minBtnW"], m["minBtnH"], m["s"])))
            ok(f"{tag} {nm} wrapper height = scaled bracket (no big gap/clip)", abs(m["wh"] - m["bkh"]) <= 3 or m["s"] == 1, str((m["wh"], m["bkh"])))
        else:
            ok(f"{tag} {nm} Fit falls back to stacked By round (not a tiny bracket), says so", m["view"] == "rounds" and not m["fit"] and m["btns"] == 0 and m["pressed"].get("Fit to screen") == "true" and "By round" in m["note"] and not m["noteHidden"] and m["docW"] <= m["vw"], str(m))
        res["info"][f"{tag}-{nm}"] = {k: m[k] for k in ("view", "fit", "s", "namePx", "minBtnW", "minBtnH", "docW")}
        if do_crops and browser_name == "chromium":
            pg.locator("#bracket").screenshot(path=f"{CROPS}/playoff-fit-{nm}.png")
            pg.click("[data-bkview=rounds]"); pg.wait_for_timeout(200); pg.locator("#bracket").screenshot(path=f"{CROPS}/playoff-rounds-{nm}.png")
            if w == 844:
                pg.click("[data-bkfit]"); pg.wait_for_timeout(200); pg.click("#bracket .r2 .bkgo >> nth=1"); pg.wait_for_timeout(250); pg.screenshot(path=f"{CROPS}/sheet-open-844l.png")
                sh = pg.evaluate("() => { const r = document.querySelector('.bks').getBoundingClientRect(); return [r.left, r.top, r.width, r.height, innerHeight, innerWidth]; }")
                ok(f"{tag} 844l sheet is a bottom sheet inside the screen", sh[1] >= 0 and abs(sh[1] + sh[3] - sh[4]) <= 1 and sh[0] >= 0 and sh[0] + sh[2] <= sh[5], str(sh))
        c.close()
    # ---- orientation / resize re-evaluation (same page)
    c, pg, logs = page(390, 844, touch=True); pg.click("[data-bkfit]"); pg.wait_for_timeout(200)
    ok(f"{tag} portrait: By round via Fit", pg.evaluate(MEAS)["view"] == "rounds")
    pg.set_viewport_size({"width": 844, "height": 390}); pg.wait_for_timeout(500); m = pg.evaluate(MEAS)
    ok(f"{tag} rotate to landscape: switches to real Fit (no reload)", m["fit"] and m["btns"] == 11 and m["s"] > 0.7 and m["namePx"] >= 12, str(m))
    pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(150)
    pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(500); m = pg.evaluate(MEAS)
    ok(f"{tag} rotate back to portrait: By round again, sheet closed, no card buttons", m["view"] == "rounds" and not m["fit"] and m["btns"] == 0 and pg.evaluate("() => document.querySelector('.bks-scrim').hidden"), str(m))
    pg.set_viewport_size({"width": 1000, "height": 700}); pg.wait_for_timeout(400); m = pg.evaluate(MEAS)
    ok(f"{tag} 1000 wide: Fit at ~0.9x", m["fit"] and 0.85 < m["s"] < 0.97 and m["docW"] <= m["vw"], str(m))
    pg.set_viewport_size({"width": 1280, "height": 800}); pg.wait_for_timeout(400); m = pg.evaluate(MEAS)
    ok(f"{tag} 1280 wide: plain full bracket (Fit off, no card buttons, hint as live)", not m["fit"] and m["btns"] == 0 and m["view"] in (None, "full") and m["docW"] <= m["vw"], str(m)); c.close()
    # ---- sheet scroll lock + inert + Esc from body (Fit at 1024 and 844 landscape)
    LS = "() => { const r = document.documentElement, m = document.querySelector('main'); return { ov: r.style.overflow, pr: r.style.paddingRight, attr: r.getAttribute('style'), inert: m.inert, inertAttr: m.hasAttribute('inert'), sheetInMain: m.contains(document.querySelector('.bks-scrim')), y: window.scrollY, hidden: document.querySelector('.bks-scrim') ? document.querySelector('.bks-scrim').hidden : true, onCard: document.activeElement.classList.contains('bkgo') }; }"
    for (vw, vh) in ((1024, 800), (844, 390)):
        c, pg, logs = page(vw, vh, touch=(vw < 900)); pg.click("[data-bkfit]"); pg.wait_for_timeout(200)
        pg.evaluate("() => { document.documentElement.style.overflow = 'scroll'; }")   # a pre-existing value must come back, not be cleared
        pg.evaluate("() => window.scrollTo(0, 150)"); pg.wait_for_timeout(100)
        b0 = pg.evaluate(LS); ok(f"{tag} {vw} before open: main not inert, overflow 'scroll' (pre-set)", not b0["inert"] and b0["ov"] == "scroll" and b0["y"] > 0, str(b0))
        pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(200); o = pg.evaluate(LS)
        ok(f"{tag} {vw} open: main inert, page overflow hidden, sheet not inside main", o["inert"] and o["ov"] == "hidden" and not o["sheetInMain"] and not o["hidden"], str(o))
        y0 = o["y"]; box = pg.evaluate("() => { const r = document.querySelector('.bks').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        pg.mouse.move(box[0], box[1]); pg.mouse.wheel(0, 400); pg.wait_for_timeout(250); pg.mouse.wheel(0, -400); pg.wait_for_timeout(100)
        ok(f"{tag} {vw} wheel over the open sheet does not scroll the page behind", pg.evaluate("() => window.scrollY") == y0, str((y0, pg.evaluate("() => window.scrollY"))))
        pg.mouse.move(box[0], 3); pg.mouse.wheel(0, 400); pg.wait_for_timeout(250)
        ok(f"{tag} {vw} wheel over the scrim does not scroll the page behind", pg.evaluate("() => window.scrollY") == y0, str(pg.evaluate("() => window.scrollY")))
        ov = pg.evaluate("() => { const d = document.querySelector('.bks'); return [d.scrollHeight, d.clientHeight]; }")
        if ov[0] > ov[1]:
            pg.mouse.move(box[0], box[1]); pg.mouse.wheel(0, 300); pg.wait_for_timeout(250)
            ok(f"{tag} {vw} sheet content itself still scrolls (page does not)", pg.evaluate("() => document.querySelector('.bks').scrollTop") > 0 and pg.evaluate("() => window.scrollY") == y0, str(ov))
        else: res["info"][f"{tag}-{vw}-sheet-no-overflow"] = ov
        pg.evaluate("() => { document.activeElement.blur(); }"); ok(f"{tag} {vw} focus is on body", pg.evaluate("() => document.activeElement === document.body"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150); a = pg.evaluate(LS)
        ok(f"{tag} {vw} Esc with focus on body closes the sheet and returns focus to the tapped card", a["hidden"] and a["onCard"], str(a))
        ok(f"{tag} {vw} after close: overflow restored to previous ('scroll'), main not inert, scroll position kept", a["ov"] == "scroll" and not a["inert"] and not a["inertAttr"] and a["pr"] == "" and a["y"] == y0, str(a))
        pg.evaluate("() => { document.documentElement.style.overflow = ''; if (!document.documentElement.getAttribute('style')) document.documentElement.removeAttribute('style'); }")
        pg.click("#bracket .r1 .bkgo >> nth=1"); pg.wait_for_timeout(150); pg.keyboard.press("Escape"); pg.wait_for_timeout(100); a = pg.evaluate(LS)
        ok(f"{tag} {vw} Esc from inside the sheet closes once; overflow back to empty, no style attribute left, main interactive", a["hidden"] and a["onCard"] and a["ov"] == "" and a["attr"] is None and not a["inert"], str(a))
        pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(100); pg.click(".bks-x"); pg.wait_for_timeout(100); a = pg.evaluate(LS)
        ok(f"{tag} {vw} Close button restores page state", a["hidden"] and a["onCard"] and a["ov"] == "" and not a["inert"] and a["attr"] is None, str(a))
        pg.click("#bracket .r4 .bkgo"); pg.wait_for_timeout(100); pg.mouse.click(5, 5); pg.wait_for_timeout(100); a = pg.evaluate(LS)
        ok(f"{tag} {vw} scrim tap restores page state", a["hidden"] and a["ov"] == "" and not a["inert"], str(a))
        dp = pg.evaluate("() => { const e = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }); document.body.dispatchEvent(e); return e.defaultPrevented; }")
        ok(f"{tag} {vw} Esc with the sheet closed is left alone (listener removed)", dp is False)
        # double-fire: Esc closes exactly once (a re-opened sheet after Esc must stay open, and a second Esc does nothing)
        pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(100); pg.keyboard.press("Escape"); pg.wait_for_timeout(100); a1 = pg.evaluate(LS); pg.keyboard.press("Escape"); pg.wait_for_timeout(100); a2 = pg.evaluate(LS)
        ok(f"{tag} {vw} Esc closes once and nothing fires after", a1["hidden"] and a2["hidden"] and a2["onCard"] and not a2["inert"], str((a1, a2)))
        # teardown by resize / rotate while open
        if vw == 844:
            pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(150); pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(500); a = pg.evaluate(LS)
            ok(f"{tag} rotate to portrait with the sheet open: sheet closed, overflow restored, main not inert", a["hidden"] and a["ov"] == "" and not a["inert"] and a["attr"] is None, str(a))
        else:
            pg.click("#bracket .r1 .bkgo >> nth=0"); pg.wait_for_timeout(150); pg.set_viewport_size({"width": 1280, "height": 800}); pg.wait_for_timeout(500); a = pg.evaluate(LS)
            ok(f"{tag} widen to 1280 with the sheet open: sheet closed, overflow restored, main not inert", a["hidden"] and a["ov"] == "" and not a["inert"] and a["attr"] is None, str(a))
        c.close()
    # ---- storage blocked
    c, pg, logs = page(1024, 800, init="Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})")
    pg.click("[data-bkfit]"); pg.wait_for_timeout(150); m = pg.evaluate("() => document.querySelector('#bracket .bkw').classList.contains('bkfit')")
    ok(f"{tag} storage blocked: Fit still works for the visit, no page error", m and not [l for l in logs if "PAGEERROR" in l], str(logs[:3])); c.close()
    # ---- a stored junk value falls back to Full
    c, pg, logs = page(1280, 800, init="try{localStorage.setItem('kt-bracket-view','weird')}catch(e){}"); m = pg.evaluate(MEAS); ok(f"{tag} junk stored value -> Full", not m["fit"] and m["view"] in (None, "full"), str(m)); c.close()
    # ---- stored fit on first paint at landscape phone
    c, pg, logs = page(844, 390, init="try{localStorage.setItem('kt-bracket-view','fit')}catch(e){}", touch=True); m = pg.evaluate(MEAS); ok(f"{tag} stored fit applies at landscape phone", m["fit"] and m["btns"] == 11, str(m))
    ok(f"{tag} no CSP errors with stored fit at landscape", not [l for l in logs if re.search(r"Content Security|PAGEERROR|Refused", l)], str(logs[:3])); c.close()
    # ---- other pages do not load the new files
    c, pg, logs = page(1280, 800); html = pg.content(); c.close()
    for path in ("/", "/conference/big-12/", "/team/byu/", "/top25/", "/games/", "/method/"):
        ok(f"{tag} {path} does not load bracket-fit", "bracket-fit" not in open(f"{SITE}{path}index.html").read())
    br.close()
if __name__ == "__main__":
    do_crops = "--crops" in sys.argv; os.makedirs(CROPS, exist_ok=True)
    srv, BASE = serve.start(SITE)
    with sync_playwright() as p:
        run("chromium", "chromium", p, do_crops)
        try: run("webkit", "webkit", p, False)
        except Exception as e: res["f"].append("webkit not run: " + str(e)[:200])
    json.dump(res["info"], open(f"{ROOT}/tests/last_bracketfit.json", "w"), indent=1)
    print(f"bracketfit_test: {res['n']} checks, {len(res['f'])} failures")
    for x in res["f"]: print("  FAIL", x[:600])
    sys.exit(1 if res["f"] else 0)
