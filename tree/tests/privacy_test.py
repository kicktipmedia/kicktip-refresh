"""/privacy/ page + cookie-line test. python3 tests/privacy_test.py   (build first: python3 src/build.py)
Static checks on build/site, a render of every mode of src/privacy_copy.py (contact empty / set, phase-3 flag off / on, TTL), and a 4-width browser pass (no sideways overflow, footer link >= 44px).
Copy source: /workspace/hub/kicktip-privacy/PRIVACY-COPY.md (sha 40c2bed37fb8); compared section by section when that file is present (the Questions section is checked per mode, not against the file)."""
import sys, os, re, html, glob, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
import privacy_copy as PC, site_config as SC
SITE = f"{ROOT}/build/site"; COPY = "/workspace/hub/kicktip-privacy/PRIVACY-COPY.md"
fails = []; warns = []; n = [0]
def ok(name, cond, extra=""):
    n[0] += 1
    if not cond: fails.append(name); print("FAIL", name, str(extra)[:300])
def text(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", "", h, flags=re.S)))).strip()
rd = lambda p: open(f"{SITE}/{p}", encoding="utf-8").read()
pages = {f[len(SITE) + 1:]: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/**/*.html", recursive=True)}
P = pages["privacy/index.html"]

# ---- 1 config state of this build ----
ok("shipped config (D1): PRIVACY_CONTACT_EMAIL = support@kicktipmedia.com, PHASE3_EMAIL_LINK off, EMAIL_LINK_TTL_SECONDS = 900", SC.PRIVACY_CONTACT_EMAIL == "support@kicktipmedia.com" and SC.PHASE3_EMAIL_LINK is False and SC.EMAIL_LINK_TTL_SECONDS == 900)
print("CONTACT: " + (f"set ({SC.PRIVACY_CONTACT_EMAIL})" if SC.PRIVACY_CONTACT_EMAIL else "empty -> 'KickTip does not have a privacy inbox' text (default, by decision)"))
if os.path.exists(COPY):
    sha = hashlib.sha256(open(COPY, "rb").read()).hexdigest(); ok("copy file sha starts 40c2bed37fb8", sha.startswith("40c2bed37fb8"), sha[:12])
else: warns.append("copy file not on this machine; section comparison skipped")

# ---- 2 page structure ----
ok("title 'Privacy | KickTip Media', one h1 'Privacy'", "<title>Privacy | KickTip Media</title>" in P and re.findall(r"<h1>(.*?)</h1>", P) == ["Privacy"])
H2 = [html.unescape(x) for x in re.findall(r"<h2>(.*?)</h2>", P)]
want = [PC.H_NOSIGN, PC.H_STORE, PC.H_GOOGLE, PC.H_COOKIES, PC.H_OTHERS, PC.H_NOT, PC.H_SAFE, PC.H_DELETE, PC.H_Q]
ok("headings in Creative's order, email-link heading absent (flag off)", H2 == want, H2)
ok("no robots/noindex; canonical + og:url", "noindex" not in P and f'<link rel="canonical" href="{SC.SITE_URL}/privacy/">' in P and f'<meta property="og:url" content="{SC.SITE_URL}/privacy/">' in P)
ok("same chrome: top banner, header, ESPN credit footer, Privacy link in footer", 'class="tb"' in P and "<header" in P and 'class="cred"' in P and '<a href="/privacy/">Privacy</a>' in P)
ok("intro + 'Last updated: October 25, 2026'", PC.INTRO in text(P) and f"Last updated: {SC.PRIVACY_UPDATED}" in text(P) and SC.PRIVACY_UPDATED == "October 25, 2026")
ok("see-also line links /disclaimer/ and /method/", 'See also: <a href="/disclaimer/">Full disclaimer</a> and <a href="/method/">How we make the numbers</a>.' in P)
ok("no inline style attribute, inline script or on* handler", not re.search(r"\sstyle\s*=", P) and not re.search(r"<script(?![^>]*\ssrc=)", P) and not re.search(r"\son[a-z]+\s*=", P) and "<style" not in P)
ok("email-link section/sentences absent while the flag is off", not re.search(r"email link|one-time link|Resend|Amazon|SES\b", P, re.I))

# Documented, brief-ordered departures from Creative's file (p2d D2 / Creative (a) / Creative (b)); everything else must still match verbatim.
DEV = [("We set no cookies and we keep no profile of you.", "Without signing in, we set no cookies and we keep no profile of you."),
       ("the teams and lead numbers you save", "the teams and headline numbers you save"),
       ("Signing out removes the session cookie from that device.", "Signing out ends your sign-in on every device you use and removes the session cookie from this one.")]
# ---- 3 verbatim against Creative's file (all sections except Questions, which is per mode) ----
if os.path.exists(COPY):
    md = open(COPY, encoding="utf-8").read().split("\n---\n")[1]
    secs = dict(re.findall(r"### (.+?)\n(.*?)(?=\n### |\n\nSee also|\Z)", md, flags=re.S))
    pt = text(P)
    for h in (PC.H_NOSIGN, PC.H_GOOGLE, PC.H_COOKIES, PC.H_NOT, PC.H_SAFE, PC.H_DELETE):
        body = re.sub(r"\s+", " ", secs[h]).strip()
        for o_, n_ in DEV: body = body.replace(o_, n_)
        ok(f"verbatim: '{h}'", body in pt, body[:60])
    ok("storage section: Creative's lead-in table headings (Setting | Saved in your browser | When it is saved) and her two confirmed rows' wording", all(x in pt for x in ("Setting Saved in your browser When it is saved", "Model choice", "Bracket view", "only after you choose Fit to screen or By round; Full bracket, the default, saves nothing")))
    oth = secs[PC.H_OTHERS]; ok("verbatim: 'Who else' Google + Cloudflare bullets and closing line", "- Google, only when you tap Sign in with Google." in oth and "Google, only when you tap Sign in with Google. Our web host and database provider, Cloudflare (our database is Cloudflare D1), which store and deliver the site and your saved teams. We do not share your information with anyone else." in pt)
    email_sec = re.sub(r"\s+", " ", secs[PC.H_EMAIL].split(")\n", 1)[1]).strip()
    _, b3 = PC.privacy_body("", True, "x", 900); ok("verbatim (flag on): email-link section", email_sec in text(b3), email_sec[:60])
    ok("Creative's 15-minute wording present in the file", "expires after 15 minutes" in md)

# ---- 4 every mode of the copy ----
_, b0 = PC.privacy_body("", False, "October 25, 2026", 900); t0 = text(b0)
ok("mode contact empty: 'no privacy inbox' sentence, no mailto", PC.QUESTIONS_NONE in t0 and "mailto:" not in b0 and "Write to" not in t0)
_, b1 = PC.privacy_body("name@example.org", False, "x", 900); t1 = re.sub(r" ([.,])", r"\1", text(b1))
ok("mode contact set: 'Write to name@example.org to ask about your data or to have it deleted.' as visible text inside the one + mailto link, then the self-service sentence; no-inbox sentence gone", 'Write to <!--email_off--><a href="mailto:name@example.org">name@example.org</a><!--/email_off--> to ask about your data or to have it deleted. ' + PC.QUESTIONS_REST in b1 and "Write to name@example.org to ask about your data or to have it deleted. " + PC.QUESTIONS_REST in t1 and "privacy inbox" not in t1)
ok("contact value is escaped", 'mailto:a&amp;b' in PC.privacy_body('a&b@x.y', False, "x", 900)[1])
_, b2 = PC.privacy_body("", True, "x", 900); t2 = text(b2); h2 = re.findall(r"<h2>(.*?)</h2>", b2)
ok("flag on: email-link heading sits after the Google section and before Cookies", h2[:5] == [PC.H_NOSIGN, PC.H_STORE, PC.H_GOOGLE, PC.H_EMAIL, PC.H_COOKIES], h2)
ok("flag on: 'expires after 15 minutes' (from EMAIL_LINK_TTL_SECONDS), Resend + Amazon SES named, processor bullet present", "The link works once and expires after 15 minutes." in t2 and "Resend and Amazon SES, only if you use an email link." in t2 and "passed to two email services" in t2)
ok("flag on: lifetime follows the one constant", "expires after 20 minutes" in text(PC.privacy_body("", True, "x", 1200)[1]) and "15 minutes" not in text(PC.privacy_body("", True, "x", 1200)[1]))
ok("flag off: neither Resend nor Amazon SES anywhere in the copy", not re.search(r"Resend|Amazon", b0 + b1))

# ---- D1 / D5 / D6 / Creative (a)(b) on the built pages ----
js = {f[len(SITE) + 1:]: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/assets/*.js") + glob.glob(f"{SITE}/assets/ks/*.js")}
qsec = P.split(f"<h2>{PC.H_Q}</h2>")[1].split("<h2", 1)[0] if f"<h2>{PC.H_Q}</h2>" in P else ""
ADDR = "support@kicktipmedia.com"
ok("D1: Questions section shows support@kicktipmedia.com as visible text and has exactly ONE mailto link", text(qsec).count(ADDR) == 1 and qsec.count("mailto:") == 1 and f'href="mailto:{ADDR}"' in qsec, qsec)
ok("D1: the address and mailto appear only in that one place on /privacy/", P.count(ADDR) == 2 and P.count("mailto:") == 1, P.count(ADDR))
ok("D1: no X handle / @ account in the Questions section", not re.search(r"(?<![\w.])@[A-Za-z0-9_]{2,}", text(qsec).replace(ADDR, "")) and "x.com" not in qsec)
ok("D1: Cloudflare opt-out comments wrap the address, and no page, asset or _worker.js contains /cdn-cgi/l/email-protection or [email protected]", "<!--email_off-->" in P and "<!--/email_off-->" in P and not [r for r, h in list(pages.items()) + list(js.items()) if "/cdn-cgi/" in h or "email-protection" in h or "[email protected]" in h])
ok("D1: the address is on no other page (only /privacy/)", not [r for r, h in pages.items() if r != "privacy/index.html" and (ADDR in h or "mailto:" in h)], [r for r, h in pages.items() if r != "privacy/index.html" and ADDR in h][:3])
ok("D1: PHASE3_EMAIL_LINK stays False", SC.PHASE3_EMAIL_LINK is False)
ok("Creative (a): first sentence under 'If you do not sign in' ... 'Without signing in, we set no cookies'", "Without signing in, we set no cookies and we keep no profile of you." in text(P) and "You can use all of KickTip without an account. We set no cookies" not in text(P))
ok("D5: kicktip_acct row says 'first letter of your name or email'", "the first letter of your name or email" in text(P) and "first letter of your email" not in text(P))
ok("Creative (b): storage row is 'Headline number' with the plain-words description; no 'lead number' anywhere on /privacy/", "Headline number" in text(P) and "which race number you chose to show first for each saved team (Make the 12, Reach CCG, Win conference or First-round bye)" in text(P) and not re.search(r"lead[- ]number", P, re.I))
ok("Creative (b): no 'lead number(s)' / 'lead-number' left on any page or built script", not [r for r, h in list(pages.items()) + list(js.items()) if re.search(r"lead[- ]numbers?", h, re.I)], [r for r, h in list(pages.items()) + list(js.items()) if re.search(r"lead[- ]numbers?", h, re.I)][:5])
ok("D2 copy: Delete section says signing out ends the sign-in on every device", "Signing out ends your sign-in on every device you use" in text(P))
for rel in ("method/index.html", "disclaimer/index.html"):
    ok(f"D6: {rel} storage text discloses the short-lived keyed-hash rate-limit counter and says 'headline-number'", "short-lived counter, a keyed hash of your connection address and never the address itself, that limits sign-in attempts and saves" in text(pages[rel]) and "headline-number" in text(pages[rel]))

# ---- 5 processor names only on /privacy/ ----
bad = []
for rel in list(pages) + [os.path.relpath(f, SITE) for f in glob.glob(f"{SITE}/assets/*.js") + glob.glob(f"{SITE}/assets/*.css") + glob.glob(f"{SITE}/assets/ks/*.js") + [f"{SITE}/_headers"]]:
    if rel == "privacy/index.html": continue
    src = pages.get(rel) or open(f"{SITE}/{rel}", encoding="utf-8", errors="replace").read()
    if re.search(r"Resend|Amazon|\bSES\b|Cloudflare", src): bad.append(rel)
ok("Resend / Amazon SES / Cloudflare appear only on /privacy/ (no page, script, stylesheet or _headers)", not bad, bad[:5])
gbad = [r for r, h in pages.items() if r not in ("privacy/index.html", "method/index.html", "disclaimer/index.html") and re.search(r"Google", h)]
ok("Google is named only on /privacy/, /method/ and /disclaimer/ pages (HTML)", not gbad, gbad[:5])
for rel in ("method/index.html", "disclaimer/index.html"):
    g = [m for m in re.findall(r"[^.]*Google[^.]*\.", text(pages[rel]))]
    ok(f"{rel}: Google appears only in the cookie line and the existing store-on-server sentence", all(("Sign in with Google" in s or "If you sign in with Google" in s or "if Google shares" in s) for s in g), g)

# ---- 6 sitemap + footer ----
sm = rd("sitemap.xml"); ok("sitemap lists /privacy/ once", sm.count(f"<loc>{SC.SITE_URL}/privacy/</loc>") == 1)
nof = [r for r, h in pages.items() if '<a href="/disclaimer/">Full disclaimer</a><a href="/privacy/">Privacy</a>' not in h]
ok(f"footer 'Privacy' link right after 'Full disclaimer' on every page ({len(pages)} incl. 404)", not nof, nof[:5])

# ---- 7 cookie lines ----
for rel in ("method/index.html", "disclaimer/index.html"): ok(f"{rel}: LONG cookie line exact", PC.COOKIE_LONG in text(pages[rel]))
ok("LONG line text is Creative's", PC.COOKIE_LONG == "No cookies unless you sign in. Signing in sets one session cookie, plus a sign-in check cookie that is deleted within ten minutes. No third-party requests until you tap Sign in with Google.")
ok("SHORT line text is Creative's", PC.COOKIE_SHORT == "No cookies unless you sign in (a session cookie, plus a ten-minute sign-in check cookie). No third-party requests until you tap Sign in.")
ok("SHORT line is in account.js (sheet footer) and myteams.js (My teams line)", all(PC.COOKIE_SHORT in rd(f"assets/{f}") for f in ("account.js", "myteams.js")))
ok("no leftover placeholders in assets or _worker.js", not any(re.search(r"__[A-Z_]{6,}__", open(f, encoding="utf-8", errors="replace").read()) for f in glob.glob(f"{SITE}/assets/*.js") + [f"{SITE}/_worker.js"]))
old = []
for f in glob.glob(f"{SITE}/**/*", recursive=True) + glob.glob(f"{ROOT}/src/**/*", recursive=True) + glob.glob(f"{ROOT}/tests/*.py") + glob.glob(f"{ROOT}/tests/*.mjs") + glob.glob(f"{ROOT}/NOTES*.md"):
    if not os.path.isfile(f) or f.endswith((".png", ".pyc", ".json", ".ico", ".webp")) or f.endswith(("privacy_copy.py", "privacy_test.py")): continue
    try: s = open(f, encoding="utf-8").read()
    except Exception: continue
    if "one session cookie then" in s or "until you open the sign-in sheet" in s: old.append(os.path.relpath(f, ROOT))
ok("old cookie line is gone everywhere (build, src, tests, NOTES)", not old, old)
sig = [r for r, h in pages.items() if "signing in sets one session cookie" in text(h).lower() and r not in ("method/index.html", "disclaimer/index.html")]
ok("LONG line only where it belongs (/method/, /disclaimer/)", not sig, sig)

# ---- 8 link lifetime is one constant ----
w = rd("_worker.js"); ok("_worker.js: EMAIL_LINK_TTL_SECONDS = 900, placeholder replaced", "const EMAIL_LINK_TTL_SECONDS = 900;" in w and "__EMAIL_LINK_TTL_SECONDS__" not in w)
mig = open(f"{ROOT}/src/d1/0003_email_tokens.sql").read(); ok("0003 migration comment: 15 minutes, no 14 days", "14 days" not in mig and "15 minutes" in mig)
nt = open(f"{ROOT}/NOTES-myteams-p2.md", encoding="utf-8").read(); ok("NOTES: no 14-day link lifetime; 15 minutes + the constant named", not re.search(r"created_at \+ 14 days|expires? (after )?14 days|14 days.{0,40}(link|token)", nt) and "EMAIL_LINK_TTL_SECONDS" in nt and "15 minutes" in nt)

# ---- 8b storage table = the real keys in the built code, and nothing else is stored ----
js = {f[len(SITE) + 1:]: open(f, encoding="utf-8").read() for f in glob.glob(f"{SITE}/assets/*.js") + glob.glob(f"{SITE}/assets/ks/*.js")}
users = sorted(k for k, v in js.items() if re.search(r"localStorage|sessionStorage|indexedDB|document\.cookie|caches\.open|serviceWorker|cookieStore", v))
ok("only these built scripts touch browser storage (kt.js, bracket-fit.js, myteams.js, account.js, rootables.js (read), chat.js (read))", users == ["assets/account.js", "assets/bracket-fit.js", "assets/chat.js", "assets/kt.js", "assets/myteams.js", "assets/rootables.js"], users)
ok("no sessionStorage / indexedDB / document.cookie / Cache API / service worker anywhere in the built scripts", not any(re.search(r"sessionStorage|indexedDB|document\.cookie|caches\.open|serviceWorker|cookieStore", v) for v in js.values()))
keys = set(); [keys.update(re.findall(r"'((?:kicktip|kt)[_-][a-z_-]+)'", v)) for v in js.values()]
want_keys = {"kicktip_model", "kt-bracket-view", "kicktip_teams", "kicktip_lead", "kicktip_acct", "kicktip_nudge"}
ok("the six localStorage keys in the built scripts are exactly the six in the table", keys == want_keys, keys)
rows = {re.search(r"\(key ([a-z_-]+)\)", b).group(1) for _, b, _ in PC.STORAGE_ROWS}
ok("every table row names its key and the rows cover exactly those keys", rows == want_keys, rows)
ok("each key is on the rendered /privacy/ page", all(k in P for k in want_keys))
wk = rd("_worker.js"); cks = set(re.findall(r"'(__Host-[a-z_]+)'", wk))
ok("the two cookies in _worker.js are the two in the cookie table, __Host- prefixed", cks == {c for c, *_ in PC.COOKIE_ROWS} == {"__Host-kt_session", "__Host-kt_oauth"}, cks)
ok("OAUTH cookie TTL is 600 s and session TTL 30 days (the page says ten minutes / up to 30 days)", "OAUTH_TTL = 600" in wk and "SESSION_TTL = 30 * 86400" in wk)
ok("cookie names on /privacy/ only (no other page or asset names them)", not [r for r, h in list(pages.items()) + [(k, v) for k, v in js.items()] if r != "privacy/index.html" and "__Host-kt" in h])

# ---- 9 browser: overflow, footer link, no third-party, no cookies ----
import serve
from playwright.sync_api import sync_playwright
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w_ in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w_, "height": 900}); pg = ctx.new_page(); errs = []; reqs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("request", lambda r: reqs.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
        pg.goto(BASE + "/privacy/"); pg.wait_for_selector("h1"); T = f"privacy@{w_}"
        ok(f"{T} no sideways overflow", pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        ok(f"{T} footer Privacy link is a >= 44px target", pg.evaluate("""() => { const a = document.querySelector('.ft a[href="/privacy/"]'); const r = a.getBoundingClientRect(); return r.height >= 43.5 && r.width >= 43.5 }"""))
        ok(f"{T} h1 'Privacy', 9 sections, no console errors, no third-party request, no cookies", pg.inner_text("h1").strip().lower() == "privacy" and pg.locator("main h2").count() == 9 and not errs and not reqs and ctx.cookies() == [], (errs[:2], reqs[:2]))
        ctx.close()
    b.close()
srv.shutdown()
for wmsg in warns: print("WARN", wmsg)
print(f"privacy_test: {n[0]} checks, {len(fails)} failures"); sys.exit(1 if fails else 0)

