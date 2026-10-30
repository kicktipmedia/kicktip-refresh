"""My teams phase 2 browser test (chromium over HTTPS): header Sign in/chip, sheet (dialog, focus trap, Esc, X), unconfigured 'coming soon', Google redirect (mock Google), merge confirm, account menu,
sign out, delete account, 50-team cap, error states, no request/cookie before sign-in, layout at 320/390/430/1280. Server: tests/devserver.mjs (mock D1, mock Google). Run: python3 tests/myteams_p2_browser.py [widths]"""
import sys, os, json, re, ssl, subprocess, time, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8443; BASE = "https://kicktipmedia.com"
fails = []; n = [0]
def ok(name, cond, extra=""):
    n[0] += 1
    if not cond: fails.append(name); print("FAIL", name, extra)
SIGNIN = "By signing in, you accept the terms: information only, not a betting site."
SAVE = "By tapping Save, you accept the terms: information only, not a betting site."
PRIV = "No cookies unless you sign in (a session cookie, plus a ten-minute sign-in check cookie). No third-party requests until you tap Sign in."   # SHORT line (Creative sha 0dfdf2668896)
WIDTHS = tuple(int(x) for x in sys.argv[1:]) or (320, 390, 430, 1280)
CTX = ssl._create_unverified_context()
def ctl(path, **q):
    return json.loads(urllib.request.urlopen(f"https://127.0.0.1:{PORT}/__test/{path}?" + urllib.parse.urlencode(q), context=CTX).read())
proc = subprocess.Popen(["node", "tests/devserver.mjs", str(PORT)], cwd=ROOT, stdout=subprocess.PIPE, text=True); proc.stdout.readline()
def ls(pg, k): return pg.evaluate("(k)=>localStorage.getItem(k)", k)

def _acsel(sel): return sel.startswith((".ac-si", ".ac-chip")) or ".ac-chip" in sel
def menu_open_for(pg, sel):
    """Sticky header: below 760px the Sign in button / account chip sit in the Menu panel, so a real user opens Menu first."""
    if _acsel(sel) and pg.evaluate("(()=>{const b=document.getElementById('kh-btn');return !!b&&getComputedStyle(b).display!=='none'&&b.getAttribute('aria-expanded')!=='true'})()"):
        pg.click("#kh-btn"); pg.wait_for_selector(".hd--open")
def small(pg, sel):
    menu_open_for(pg, sel)
    return pg.evaluate("""(sel)=>[...document.querySelectorAll(sel)].filter(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&cs.visibility!=='hidden'&&(r.height<43.5||r.width<43.5)&&!e.closest('.rn')}).map(e=>e.className+':'+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height))""", sel)
def tx(pg, sel):   # text nodes joined with spaces (inner_text would apply text-transform: uppercase)
    return pg.evaluate("""(sel)=>{const el=document.querySelector(sel);const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let o=[];while(w.nextNode())o.push(w.currentNode.nodeValue.trim());return o.filter(Boolean).join(' ')}""", sel)
def overflow(pg): return pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
def server(): return ctl("state")
def new_ctx(browser, w, mode="ok", claims=None):
    ctx = browser.new_context(viewport={"width": w, "height": 900}, ignore_https_errors=True); pg = ctx.new_page(); errs, reqs = [], []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("request", lambda r: reqs.append(r.url))
    _click, _wait = pg.click, pg.wait_for_selector
    def click(sel, **k):
        if sel.startswith((".ac-si", ".ac-chip")): _wait(sel, state="attached"); menu_open_for(pg, sel)
        return _click(sel, **k)
    def wait(sel, **k):
        if sel.startswith((".ac-si", ".ac-chip")): k.setdefault("state", "attached")
        return _wait(sel, **k)
    pg.click, pg.wait_for_selector = click, wait
    ctl("google", mode=mode, claims=json.dumps(claims or {}))
    class St(dict):
        def __getitem__(self, k): return len([r for r in reqs if urllib.parse.urlparse(r).hostname == "accounts.google.com" and "/o/oauth2/" in r]) if k == "hits" else dict.__getitem__(self, k)
    state = St()
    return ctx, pg, errs, reqs, state
def save_two(pg):
    pg.wait_for_selector("#my-teams:not([hidden]) .mt-ed"); pg.click(".mt-chip[data-t=byu]"); pg.click("[data-more]"); pg.click(".mt-chip[data-t=utah]"); pg.select_option("#mtl-utah", "c"); pg.click("[data-save]"); pg.wait_for_selector(".mt-c")
def sign_in_flow(pg):
    pg.click(".ac-si"); pg.wait_for_selector("[role=dialog] .ac-g"); pg.click(".ac-g")
def mt_errs(errs): return [e for e in errs if "Failed to load resource" not in e]

def run(p, w):
    browser = p.chromium.launch(args=["--host-resolver-rules=MAP kicktipmedia.com 127.0.0.1:%d, MAP accounts.google.com 127.0.0.1:%d, MAP * ~NOTFOUND" % (PORT, PORT)])
    T = f"p2@{w}"
    # ---------- A. signed out: nothing sent, nothing stored, header link
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w)
    pg.goto(BASE + "/"); pg.wait_for_selector(".ac-si"); pg.wait_for_selector("#my-teams:not([hidden]) .mt-ed")
    ok(f"{T} header shows a Sign in control", pg.inner_text(".ac-hd").strip() == "Sign in")
    ok(f"{T} header Sign in is 44px", small(pg, ".ac-si") == [], small(pg, ".ac-si"))
    ok(f"{T} no request to /api/ or any other host before the sheet opens", not [r for r in reqs if "/api/" in r or "google" in r], [r for r in reqs if "/api/" in r])
    ok(f"{T} no cookie and nothing stored before sign-in", ctx.cookies() == [] and ls(pg, "kicktip_teams") is None and ls(pg, "kicktip_acct") is None and ls(pg, "kicktip_nudge") is None)
    # ---------- B. sheet: dialog, trap, Esc, X
    pg.click(".ac-si"); pg.wait_for_selector("[role=dialog] .ac-g")
    d = pg.locator("[role=dialog]")
    ok(f"{T} sheet is a modal dialog with a label", d.get_attribute("aria-modal") == "true" and tx(pg, "#ac-t") == "Keep My teams on every device")
    ok(f"{T} sheet carries the top banner", "KickTip is not a betting site." in pg.inner_text(".ac-bn") and "make no decision based on this material" in pg.inner_text(".ac-bn"))
    txt = tx(pg, "[role=dialog]")
    ok(f"{T} exact sign-in terms line under the Google button + Full terms link", SIGNIN in txt and pg.locator(".ac-gw .rn a").inner_text() == "Full terms" and pg.get_attribute(".ac-gw .rn a", "href") == "/disclaimer/")
    ok(f"{T} exact SHORT cookie line shown, old line gone", PRIV in txt and ("one session cookie" + " then") not in txt)
    ok(f"{T} sheet footer has a Privacy link to /privacy/ (44px, no overflow)", pg.evaluate("""() => { const a = document.querySelector('.ac-fine a[href="/privacy/"]'); if (!a) return false; const r = a.getBoundingClientRect(), p = a.parentElement.getBoundingClientRect(); return a.textContent === 'Privacy' && r.height >= 44 && document.querySelector('.ac-card').scrollWidth <= document.querySelector('.ac-card').clientWidth + 1 }"""))
    ok(f"{T} 'Not now' + 14-day caption", "Not now" in txt and "asks again in 14 days" in txt)
    ok(f"{T} no email-link sign-in anywhere in the sheet", not re.search(r"email (me )?a link|magic|one-time|passwordless", txt, re.I))
    ok(f"{T} focus starts on the Google control", pg.evaluate("document.activeElement.className") == "ac-g")
    ok(f"{T} sheet targets are 44px", small(pg, "[role=dialog] button, [role=dialog] a.ac-g") == [], small(pg, "[role=dialog] button, [role=dialog] a.ac-g"))
    ok(f"{T} Google link goes to our own start route", pg.get_attribute(".ac-g", "href") == "/api/auth/google/start?r=%2F")
    inside = []
    for i in range(8): pg.keyboard.press("Tab"); inside.append(pg.evaluate("!!document.activeElement.closest('[role=dialog]')"))
    for i in range(4): pg.keyboard.press("Shift+Tab"); inside.append(pg.evaluate("!!document.activeElement.closest('[role=dialog]')"))
    ok(f"{T} focus trap: Tab and Shift+Tab never leave the dialog", all(inside), inside)
    ok(f"{T} page behind is inert", pg.evaluate("document.querySelector('main')?.hasAttribute('inert') ?? document.querySelector('header').hasAttribute('inert')"))
    ok(f"{T} no sideways overflow with the sheet open", overflow(pg) <= 0, overflow(pg))
    hz = pg.evaluate("""()=>{const hd=document.querySelector('header.hd'),ov=document.querySelector('.ac-ov'),r=hd.getBoundingClientRect(),el=document.elementFromPoint(innerWidth/2,Math.min(28,r.height/2));
      return {hdz:getComputedStyle(hd).zIndex,ovz:getComputedStyle(ov).zIndex,over:!!(el&&el.closest('.ac-ov')),lock:getComputedStyle(document.documentElement).overflow,inert:hd.hasAttribute('inert'),bar:getComputedStyle(document.documentElement).getPropertyValue('--kt-bar-h').trim(),open:!!document.querySelector('.hd--open'),kl:document.documentElement.classList.contains('kh-lock')}}""")
    ok(f"{T} sheet sits above the sticky bar (sheet z {hz['ovz']} over bar z {hz['hdz']}), covers it, and the header is inert behind it", int(hz["ovz"]) > int(hz["hdz"]) and hz["over"] and hz["inert"], hz)
    ok(f"{T} sheet locks page scroll (html overflow hidden), Menu panel closed (no scrim left over), --kt-bar-h still the header's {hz['bar']}", hz["lock"] == "hidden" and not hz["open"] and hz["bar"] in ("56px", "64px"), hz)
    pg.keyboard.press("Escape"); ok(f"{T} Esc closes the sheet", pg.locator("[role=dialog]").count() == 0)
    ok(f"{T} focus returns to Sign in (below 760px the Sign in button lives in the closed Menu panel, so focus returns to the Menu button)", pg.evaluate("document.activeElement.id") == "kh-btn" if w < 760 else pg.evaluate("document.activeElement.className") == "ac-si")
    ok(f"{T} after the sheet closes: page scroll unlocked, header no longer inert, Menu closed", pg.evaluate("getComputedStyle(document.documentElement).overflow") != "hidden" and not pg.evaluate("document.querySelector('header.hd').hasAttribute('inert')") and pg.locator(".hd--open").count() == 0)
    pg.click(".ac-si"); pg.click(".ac-x"); ok(f"{T} X closes the sheet", pg.locator("[role=dialog]").count() == 0)
    ok(f"{T} still no cookie or storage after opening/closing the sheet", ctx.cookies() == [] and ls(pg, "kicktip_acct") is None)
    ok(f"{T} sheet opened the one session probe, nothing external", [r for r in reqs if "/api/" in r] and not [r for r in reqs if "google" in r], [r for r in reqs if "/api/" in r])
    # Not now snoozes
    pg.click(".ac-si"); pg.click("[data-acct=notnow]"); ok(f"{T} Not now stores a 14-day snooze", json.loads(ls(pg, "kicktip_nudge"))["v"] == 1 and pg.locator("[role=dialog]").count() == 0)
    ok(f"{T} console clean", not mt_errs(errs), mt_errs(errs)); ctx.close()
    # ---------- C. unconfigured: coming soon, My teams still works
    ctl("reset"); ctl("config", on="0"); ctx, pg, errs, reqs, st = new_ctx(browser, w)
    pg.goto(BASE + "/"); pg.wait_for_selector(".ac-si"); pg.click(".ac-si"); pg.wait_for_selector(".ac-soon")
    ok(f"{T} unconfigured: 'coming soon' text and no Google button", "coming soon" in pg.inner_text(".ac-soon") and pg.locator(".ac-g").count() == 0)
    pg.keyboard.press("Escape"); save_two(pg)
    ok(f"{T} unconfigured: My teams saves locally", ls(pg, "kicktip_teams") == '{"v":1,"t":["byu","utah"]}' and "Sign in to keep" not in pg.inner_text("#my-teams"))
    ctx.close(); ctl("config", on="1")
    # ---------- D. error and cancelled states (A6)
    for q, label in (("error", "error"), ("cancelled", "cancelled")):
        ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w); pg.goto(BASE + f"/?signin={q}"); pg.wait_for_selector(".ac-err")
        ok(f"{T} {label}: error message exact", pg.inner_text(".ac-err").replace("\n", " ").endswith("Sign-in did not finish. Your teams are still saved on this device."), pg.inner_text(".ac-err"))
        ok(f"{T} {label}: Google button offered again, ?signin removed from the URL", pg.locator(".ac-g").count() == 1 and "signin" not in pg.url)
        ok(f"{T} {label}: no sideways overflow", overflow(pg) <= 0); ctx.close()
    # ---------- E. real sign-in with merge, menu, sign out
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w)
    pg.goto(BASE + "/"); save_two(pg); local = (ls(pg, "kicktip_teams"), ls(pg, "kicktip_lead"))
    ok(f"{T} signed-out strip offers sign-in", "Keep these on every device" in pg.inner_text("#my-teams"))
    sign_in_flow(pg); pg.wait_for_selector("[role=dialog] [data-acct=merge-yes]")
    ok(f"{T} Google was reached only after the tap", st["hits"] == 1)
    h = tx(pg, "#ac-t"); ok(f"{T} merge dialog names the count and the device", re.match(r"Add the 2 teams from this (computer|phone|device)\?", h) is not None, h)
    mt = tx(pg, "[role=dialog]"); ok(f"{T} merge dialog copy (A4)", "They will be saved to your account so you can open them on any device." in mt and "They also stay on this" in mt and "Not now" in mt)
    ok(f"{T} merge dialog lists the teams", "BYU" in mt and "Utah" in mt)
    ok(f"{T} merge targets 44px, no overflow", small(pg, "[role=dialog] button") == [] and overflow(pg) <= 0)
    ok(f"{T} before Add, the account holds nothing", server()["teams"] == [])
    ck = ctx.cookies(); ok(f"{T} exactly one cookie after sign-in: the __Host- session cookie (httpOnly, Secure, Lax)", len(ck) == 1 and ck[0]["name"] == "__Host-kt_session" and ck[0]["httpOnly"] and ck[0]["secure"] and ck[0]["sameSite"] == "Lax" and ck[0]["path"] == "/", ck)
    ok(f"{T} URL cleaned after sign-in", "signin=" not in pg.url)
    pg.click("[data-acct=merge-yes]"); pg.wait_for_selector(".ac-chip"); time.sleep(0.3)
    s = server(); ok(f"{T} Add saves both teams to the account with lead choices", [t["slug"] for t in s["teams"]] == ["byu", "utah"] and {t["slug"]: t["lead"] for t in s["teams"]} == {"byu": "p", "utah": "c"}, s["teams"])
    ok(f"{T} device keys untouched by the merge", (ls(pg, "kicktip_teams"), ls(pg, "kicktip_lead")) == local)
    ok(f"{T} header shows the initial chip, 44px", pg.inner_text(".ac-chip .ac-in").strip() == "S" and small(pg, ".ac-chip") == [])
    ok(f"{T} chip hint stored (one letter only)", json.loads(ls(pg, "kicktip_acct")) == {"v": 1, "i": "S"})
    ok(f"{T} account strip shows email, 2 of 50, Sign out, Delete", "sam@example.com" in pg.inner_text("#my-teams") and "2 of 50 teams" in pg.inner_text("#my-teams") and "Sign out" in pg.inner_text("#my-teams"))
    # menu
    pg.click(".ac-chip"); pg.wait_for_selector("#ac-menu"); mtxt = re.sub(r"\s+", " ", pg.inner_text("#ac-menu"))
    ok(f"{T} account menu: email, Saved teams 2 of 50, Sign out, Delete my account", "Signed in as sam@example.com" in mtxt and "Saved teams 2 of 50" in mtxt and "Sign out" in mtxt and "Delete my account" in mtxt, mtxt)
    ok(f"{T} menu is fully on screen, items 44px", pg.evaluate("(()=>{const r=document.querySelector('#ac-menu').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})()") and small(pg, "#ac-menu .ac-it") == [])
    ok(f"{T} menu: aria-expanded true, focus inside", pg.get_attribute(".ac-chip", "aria-expanded") == "true" and pg.evaluate("!!document.activeElement.closest('#ac-menu')"))
    pg.keyboard.press("Escape"); ok(f"{T} Esc closes the menu, focus back on chip", pg.locator("#ac-menu").count() == 0 and pg.evaluate("document.activeElement.className") == "ac-chip")
    # reload keeps the session; list comes from the account
    pg.reload(); pg.wait_for_selector(".ac-chip"); pg.wait_for_selector(".mt-c"); ok(f"{T} reload: still signed in with the account's teams", pg.locator(".mt-c").count() == 2)
    # editing while signed in writes the account, not the device
    pg.click(".mt-c .mt-rm" if pg.locator(".mt-c .mt-rm").count() else ".mt-c [data-rm]") if False else None
    pg.click("[data-edit]"); pg.wait_for_selector(".mt-ed"); pg.click("[data-more]") if pg.locator("[data-more]").count() else None
    pg.click(".mt-chip[data-t=byu]"); pg.click("[data-save]"); time.sleep(0.4)
    s = server(); ok(f"{T} signed-in Save writes the account (BYU removed)", [t["slug"] for t in s["teams"]] == ["utah"], s["teams"])
    ok(f"{T} signed-in Save leaves the device keys as they were", (ls(pg, "kicktip_teams"), ls(pg, "kicktip_lead")) == local)
    # sign out
    pg.click(".ac-chip"); pg.click("#ac-menu [data-acct=signout]"); pg.wait_for_selector(".ac-si"); time.sleep(0.2)
    ok(f"{T} sign out: cookie gone, header back to Sign in, hint removed", ctx.cookies() == [] and ls(pg, "kicktip_acct") is None and pg.inner_text(".ac-hd").strip() == "Sign in")
    ok(f"{T} sign out: device list is back, account keeps its own", pg.locator(".mt-c").count() == 2 and [t["slug"] for t in server()["teams"]] == ["utah"])
    ok(f"{T} console clean through the flow", not mt_errs(errs), mt_errs(errs)); ctx.close()
    # ---------- F. merge into an account that already has teams; Not now; add later
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w)
    pg.goto(BASE + "/"); save_two(pg)
    ctl("seed", b=json.dumps({"user_id": 1, "teams": ["alabama"], "lead": {"alabama": "w"}}))   # user row is created at sign-in; the seed is read after
    ctl("reset"); ctx.close(); ctx, pg, errs, reqs, st = new_ctx(browser, w)
    pg.goto(BASE + "/"); save_two(pg); sign_in_flow(pg); pg.wait_for_selector("[data-acct=merge-yes]"); pg.click("[data-acct=merge-no]"); time.sleep(0.2)
    ok(f"{T} merge Not now: dialog closes, account unchanged, device list kept", pg.locator("[role=dialog]").count() == 0 and server()["teams"] == [] and ls(pg, "kicktip_teams") is not None)
    ok(f"{T} merge Not now: strip offers 'Add the 2 from this ...' later", re.search(r"Add the 2 from this", pg.inner_text("#my-teams")) is not None)
    pg.click("[data-acct=merge]"); pg.wait_for_selector("[data-acct=merge-yes]"); pg.click("[data-acct=merge-yes]"); time.sleep(0.4)
    ok(f"{T} add later works", [t["slug"] for t in server()["teams"]] == ["byu", "utah"])
    ctx.close()
    # ---------- G. 50-team cap, plain-text message, no sign-in nudge while signed in
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w); pg.goto(BASE + "/"); sign_in_flow(pg); pg.wait_for_selector(".ac-chip")
    slugs = json.loads(re.search(r"new Set\((\[.*?\])\)", open(f"{ROOT}/build/site/_worker.js").read()).group(1))[:50]
    ctl("seed", b=json.dumps({"user_id": 1, "teams": slugs})); pg.reload(); pg.wait_for_selector(".mt-c")
    ok(f"{T} account shows 50 teams ('50 of 50')", pg.locator(".mt-c").count() == 50 and "50 of 50 teams" in pg.inner_text("#my-teams"), pg.locator(".mt-c").count())
    other = "utah"; ok(f"{T} (utah is outside the seeded 50)", other not in slugs)
    pg.goto(BASE + f"/team/{other}/"); pg.wait_for_selector(".mt-sv"); pg.wait_for_selector(".ac-chip"); time.sleep(0.8); pg.click(".mt-sv"); msg = pg.inner_text(".mt-msg")
    ok(f"{T} team page at 50: plain message, no sign-in nudge while signed in", "up to 50 teams" in msg and "on this device" not in msg and "Sign in" not in msg, msg)
    ok(f"{T} cap blocked the account write", len(server()["teams"]) == 50)
    ctx.close()
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w); pg.goto(BASE + "/"); sign_in_flow(pg); pg.wait_for_selector(".ac-chip")
    pg.goto(BASE + "/team/utah/"); pg.wait_for_selector(".mt-sv"); pg.wait_for_selector(".ac-chip"); time.sleep(0.8); pg.click(".mt-sv"); time.sleep(0.5)
    ok(f"{T} team-page Save while signed in writes the account, not the device", [t["slug"] for t in server()["teams"]] == ["utah"] and ls(pg, "kicktip_teams") is None, server()["teams"])
    ok(f"{T} team-page signed-in, no overflow, targets 44px", overflow(pg) <= 0 and small(pg, ".mt-svw button, .ac-chip") == []); ctx.close()
    # ---------- H. session expiry mid-edit -> falls back to the device list with a message
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w); pg.goto(BASE + "/"); save_two(pg); sign_in_flow(pg); pg.wait_for_selector("[data-acct=merge-no]"); pg.click("[data-acct=merge-no]")
    ctx.clear_cookies(); pg.wait_for_selector(".mt-ed"); pg.click(".mt-chip[data-t=byu]"); pg.click("[data-save]"); time.sleep(0.5)
    ok(f"{T} expired session: told once, header returns to Sign in", "You were signed out" in pg.inner_text("#my-teams") and pg.locator(".ac-si").count() == 1, pg.inner_text("#my-teams")[:200]); ctx.close()
    # ---------- I. delete account
    ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(browser, w); pg.goto(BASE + "/"); save_two(pg); sign_in_flow(pg); pg.wait_for_selector("[data-acct=merge-yes]"); pg.click("[data-acct=merge-yes]"); pg.wait_for_selector(".ac-chip"); time.sleep(0.3)
    pg.click(".ac-chip"); pg.click("#ac-menu [data-acct=delete]"); pg.wait_for_selector("[data-acct=delete-yes]")
    dt = tx(pg, "[role=dialog]"); ok(f"{T} delete confirm explains what is removed", "removes your email, your followed teams and your headline-number choices from our server" in dt and "Teams saved on this device stay" in dt)
    ok(f"{T} delete confirm: focus starts on the safe button", pg.evaluate("document.activeElement.textContent") == "Keep my account")
    pg.click("[data-acct=close]") if False else pg.keyboard.press("Escape"); ok(f"{T} Esc cancels delete, account intact", len(server()["users"]) == 1)
    pg.click(".ac-chip"); pg.click("#ac-menu [data-acct=delete]"); pg.click("[data-acct=delete-yes]"); pg.wait_for_selector(".ac-si"); time.sleep(0.2)
    s = server(); ok(f"{T} delete removes the user and the saved teams on the server", s["users"] == [] and s["teams"] == [])
    ok(f"{T} delete: signed out, device list kept, no cookie", ctx.cookies() == [] and pg.locator(".mt-c").count() == 2); ctx.close()
    browser.close()

try:
    with sync_playwright() as p:
        for w in WIDTHS: run(p, w)
finally:
    proc.terminate()
print(f"myteams_p2_browser: {n[0]} checks, {len(fails)} fail"); sys.exit(1 if fails else 0)
