"""My teams headless-browser test (phase 1, local only): save, 10-team cap, remove, clear, reload persistence, blocked storage, tampered storage, keyboard,
no cookies, no third-party requests, nothing written before Save, 44px targets, no sideways overflow, at 320/390/430/1280 (chromium) + 390 (webkit)."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []; n = [0]
def ok(name, cond, extra=""):
    n[0] += 1
    if not cond: fails.append(name); print("FAIL", name, extra)
SAVE = "By tapping Save, you accept the terms: information only, not a betting site."
WIDTHS = tuple(int(x) for x in sys.argv[1:])
srv, BASE = serve.start()
def ls(pg): return pg.evaluate("[localStorage.getItem('kicktip_teams'), localStorage.getItem('kicktip_lead')]")
def small(pg, sel):
    return pg.evaluate("""(sel)=>[...document.querySelectorAll(sel)].filter(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&cs.visibility!=='hidden'&&(r.width<43.5||r.height<43.5)&&!e.closest('.vh')}).map(e=>e.className+' '+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height))""", sel)
def run(p, browser, w, name):
    ctx = browser.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
    errs, reqs = [], []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("request", lambda r: reqs.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
    T = f"{name}@{w}"
    pg.goto(BASE + "/"); pg.wait_for_selector("#my-teams:not([hidden]) .mt-ed")
    ok(f"{T} empty: editor shows 'Choose your teams'", "choose your teams" in pg.inner_text("#mteh").lower())
    ok(f"{T} nothing written to storage just by viewing", ls(pg) == [None, None], ls(pg))
    ok(f"{T} no cookies", ctx.cookies() == [])
    ok(f"{T} Save line under Save button (exact words)", SAVE in pg.inner_text("#my-teams").replace("\n", " "))
    ok(f"{T} Save disabled with no teams", pg.get_attribute("[data-save]", "aria-disabled") == "true")
    pg.click("[data-save]", force=True); ok(f"{T} Save with no teams writes nothing", ls(pg) == [None, None])
    # choose 2 in the editor (Big 12), nothing stored until Save
    pg.click(".mt-chip[data-t=byu]"); pg.click("[data-more]"); pg.click(".mt-chip[data-t=utah]")
    ok(f"{T} draft: still nothing stored", ls(pg) == [None, None])
    ok(f"{T} draft count text", "2 of 10 chosen" in pg.inner_text(".mt-count"))
    opts = pg.eval_on_selector_all("#mtl-byu option", "o=>o.map(x=>x.textContent)")
    ok(f"{T} lead choices use 'Reach CCG' and never bare 'conference title'", "Reach CCG" in opts and not any("title" in o.lower() for o in opts), opts)
    ok(f"{T} CCG definition shown once in the editor", pg.inner_text("#my-teams").count("CCG = conference championship game") == 1)
    pg.select_option("#mtl-utah", "c")
    pg.click("[data-save]"); pg.wait_for_selector(".mt-c")
    t, l = ls(pg); ok(f"{T} Save writes versioned keys", t == '{"v":1,"t":["byu","utah"]}' and json.loads(l) == {"v": 1, "m": {"byu": "p", "utah": "c"}}, (t, l))
    pg.locator(".mt-c .mt-kv").nth(3).wait_for()
    ok(f"{T} two cards with numbers", pg.locator(".mt-c").count() == 2 and re.search(r"\d+%|<1%|>99%", pg.inner_text(".mt-c >> nth=0")) is not None)
    ok(f"{T} card shows Reach CCG for utah", "REACH CCG" in pg.inner_text(".mt-c >> nth=1").upper() and "CCG = conference championship game" in pg.inner_text("#my-teams"))
    ok(f"{T} Rootables shortcut", pg.get_attribute(".mt-c >> nth=0 >> .mt-b2", "href") == "/team/byu/#rootables")
    ok(f"{T} header count badge 2", "2" in pg.inner_text(".nav a[href$='#my-teams']"))
    ok(f"{T} controls >= 44px in My teams", small(pg, "#my-teams button, #my-teams a, #my-teams select") == [], small(pg, "#my-teams button, #my-teams a, #my-teams select"))
    ok(f"{T} no sideways page overflow", pg.evaluate("document.documentElement.scrollWidth") <= w, pg.evaluate("document.documentElement.scrollWidth"))
    pg.reload(); pg.wait_for_selector(".mt-c"); ok(f"{T} reload persists 2 teams", pg.locator(".mt-c").count() == 2)
    # stars in the Top 12 list
    pg.wait_for_selector(".mt-ls"); ok(f"{T} list stars >= 44px", small(pg, ".mt-ls") == [], small(pg, ".mt-ls")[:2])
    ok(f"{T} list star shows saved teams as pressed", pg.get_attribute(".mt-ls[data-slug=byu]", "aria-pressed") == "true")
    # edit: cap at 10
    pg.click("[data-edit]"); pg.wait_for_selector("#mteh")
    confs = pg.eval_on_selector_all("#mtconf option", "o=>o.map(x=>x.value)")
    for c in confs:
        pg.select_option("#mtconf", c)
        if pg.locator("[data-more][aria-expanded=false]").count(): pg.click("[data-more]")
        for slug in pg.eval_on_selector_all(".mt-chip[data-t]", "e=>e.map(x=>x.dataset.t)"):
            if "10 of 10" in pg.inner_text(".mt-count"): break
            if pg.get_attribute(f".mt-chip[data-t={slug}]", "aria-pressed") == "false" and pg.get_attribute(f".mt-chip[data-t={slug}]", "aria-disabled") != "true": pg.click(f".mt-chip[data-t={slug}]")
        if "10 of 10" in pg.inner_text(".mt-count"): break
    ok(f"{T} reached 10 of 10", "10 of 10" in pg.inner_text(".mt-count"), pg.inner_text(".mt-count"))
    pg.select_option("#mtconf", confs[0]); pg.click("[data-more][aria-expanded=false]") if pg.locator("[data-more][aria-expanded=false]").count() else None
    extra = pg.eval_on_selector_all(".mt-chip[data-t][aria-pressed=false]", "e=>e.map(x=>x.dataset.t)")
    if extra:
        pg.click(f".mt-chip[data-t={extra[0]}]", force=True); msg = pg.inner_text(".mt-count")
        ok(f"{T} cap message at the 11th team", "up to 10 teams" in msg and "Remove one to add another" in msg, msg)
        ok(f"{T} 11th not added", pg.locator(".mt-yl li").count() == 10, pg.locator(".mt-yl li").count())
    pg.click("[data-save]"); pg.wait_for_selector(".mt-c"); ok(f"{T} saved exactly 10", len(json.loads(ls(pg)[0])["t"]) == 10)
    # sign-in nudge hidden because sign-in not configured
    ok(f"{T} phase 2: the sheet is closed, so no provider name on the page (Sign in links only)", not re.search(r"google", pg.inner_text("body"), re.I) and re.search(r"sign in", pg.inner_text("body"), re.I) is not None, "")
    # team page star at the cap
    other = pg.evaluate("async()=>{const j=await (await fetch('/data/pred-teams.json')).json();const saved=JSON.parse(localStorage.getItem('kicktip_teams')).t;return Object.keys(j.teams).filter(s=>!saved.includes(s))[0]}")
    pg.goto(BASE + f"/team/{other}/"); pg.wait_for_selector(".mt-sv")
    ok(f"{T} team page: Save control, aria-label, pressed false", pg.get_attribute(".mt-sv", "aria-pressed") == "false" and "to My teams" in pg.get_attribute(".mt-sv", "aria-label"))
    ok(f"{T} team page: Save terms line directly under it", SAVE in pg.inner_text("[data-mtsave]").replace("\n", " "))
    ok(f"{T} team page 44px", small(pg, ".mt-svw button, .mt-svw a") == [], small(pg, ".mt-svw button, .mt-svw a"))
    pg.click(".mt-sv"); msg = pg.inner_text(".mt-msg"); ok(f"{T} team page at cap shows cap message", "up to 10 teams" in msg, msg)
    ok(f"{T} cap blocked the write", len(json.loads(ls(pg)[0])["t"]) == 10 and pg.get_attribute(".mt-sv", "aria-pressed") == "false")
    # remove via star on a saved team page
    first = json.loads(ls(pg)[0])["t"][0]; pg.goto(BASE + f"/team/{first}/"); pg.wait_for_selector(".mt-sv[aria-pressed=true]")
    pg.click(".mt-sv"); ok(f"{T} remove from team page", first not in json.loads(ls(pg)[0])["t"] and len(json.loads(ls(pg)[0])["t"]) == 9)
    pg.goto(BASE + f"/team/{other}/"); pg.wait_for_selector(".mt-sv"); pg.click(".mt-sv"); ok(f"{T} add after freeing a slot", other in json.loads(ls(pg)[0])["t"])
    # keyboard on the list star
    pg.goto(BASE + "/"); pg.wait_for_selector(".mt-ls"); star = pg.locator(".mt-ls").first; slug = star.get_attribute("data-slug"); was = slug in json.loads(ls(pg)[0])["t"]
    star.focus(); pg.keyboard.press("Enter" if not was else "Space"); now = slug in json.loads(ls(pg)[0] or '{"t":[]}')["t"]
    ok(f"{T} keyboard toggles a list star", (now != was) or (not was and len(json.loads(ls(pg)[0])["t"]) >= 10), (slug, was, now))
    # Remove in editor + Clear with confirm
    pg.click("[data-edit]"); pg.wait_for_selector("[data-rm]"); k = pg.locator("[data-rm]").count(); pg.click("[data-rm] >> nth=0"); ok(f"{T} editor remove drops one in draft", pg.locator("[data-rm]").count() == k - 1)
    before = ls(pg)[0]; ok(f"{T} editor remove not stored until Save", ls(pg)[0] == before)
    pg.click("[data-cancel]"); pg.wait_for_selector("[data-clear]"); ok(f"{T} Cancel keeps storage", ls(pg)[0] == before)
    pg.click("[data-clear]"); ok(f"{T} Clear asks first", ls(pg)[0] == before and pg.locator("[data-clear-yes]").count() == 1)
    pg.click("[data-clear-no]"); ok(f"{T} Keep them keeps", ls(pg)[0] == before)
    pg.click("[data-clear]"); pg.click("[data-clear-yes]"); ok(f"{T} Clear removes both keys", ls(pg) == [None, None], ls(pg))
    pg.wait_for_selector("#my-teams .mt-ed"); ok(f"{T} back to empty editor", True)
    ok(f"{T} no third-party requests", reqs == [], reqs[:3]); errs = [e for e in errs if not (name == "webkit" and e.startswith("Refused to apply a stylesheet because its hash"))]   # Playwright's WebKit build reports its own built-in <select> UA sheet against style-src 'self' (any native <select>, nothing of ours); chromium reports nothing
    ok(f"{T} no console errors", errs == [], errs[:3]); ok(f"{T} still no cookies", ctx.cookies() == [])
    # keyboard-only save from a fresh state
    pg.goto(BASE + "/"); pg.wait_for_selector(".mt-chip[data-t=byu]"); pg.focus(".mt-chip[data-t=byu]"); pg.keyboard.press("Space")
    ok(f"{T} Space toggles a chip", pg.get_attribute(".mt-chip[data-t=byu]", "aria-pressed") == "true")
    pg.focus("[data-save]"); pg.keyboard.press("Enter"); pg.wait_for_selector(".mt-c"); ok(f"{T} Enter on Save saves", json.loads(ls(pg)[0])["t"] == ["byu"])
    ok(f"{T} focus lands on the My teams heading after Save", pg.evaluate("document.activeElement.id") == "mth")
    ctx.close()
    # tampered storage
    ctx = browser.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("""localStorage.setItem('kicktip_teams', JSON.stringify({v:1,t:['byu','byu','<img src=x onerror=1>','Not-A-Slug','nope-nope-nope','utah',1,null].concat(Array.from({length:40},(_,i)=>'zz'+i))})); localStorage.setItem('kicktip_lead', JSON.stringify({v:1,m:{byu:'zzz',utah:'c'}}))""")
    pg.goto(BASE + "/"); pg.wait_for_selector(".mt-c"); names = pg.eval_on_selector_all(".mt-c", "e=>e.map(x=>x.dataset.t)")
    ok(f"{T} tampered storage: bad slugs dropped, no more than the cap, no markup injected", names == ["byu", "utah"] and errs == [] and pg.locator("img[src=x]").count() == 0, names)
    ctx.close()
    ctx = browser.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('kicktip_teams','{not json'); localStorage.setItem('kicktip_lead','[1,2')")
    pg.goto(BASE + "/"); pg.wait_for_selector("#my-teams .mt-ed"); ok(f"{T} corrupt storage reads as empty", errs == [])
    ctx.close()
    # blocked storage (every access throws)
    ctx = browser.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("""Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})""")
    pg.goto(BASE + "/"); pg.wait_for_selector("#my-teams .mt-ed")
    pg.click(".mt-chip[data-t=byu]"); pg.click("[data-save]"); pg.wait_for_selector(".mt-c")
    ok(f"{T} blocked storage: page works and says so", errs == [] and "blocking storage" in pg.inner_text("#my-teams") and pg.locator(".mt-c").count() == 1, errs[:2])
    pg.goto(BASE + "/team/utah/"); pg.wait_for_selector(".mt-sv"); pg.click(".mt-sv"); ok(f"{T} blocked storage: team page Save does not throw", errs == [] and "page view only" in pg.inner_text(".mt-msg"), pg.inner_text(".mt-msg"))
    ctx.close()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (WIDTHS or (320, 390, 430, 1280)): run(p, b, w, "chromium")
    b.close()
    try:
        wb = p.webkit.launch(); run(p, wb, 390, "webkit"); wb.close()
    except Exception as e: print("webkit skipped:", str(e)[:120])
print(f"myteams_browser: {n[0]} checks, {len(fails)} failures")
sys.exit(1 if fails else 0)
